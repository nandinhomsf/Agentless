#!/usr/bin/env bash
# Agentless pipeline (upstream README_swebench.md) adapted to: free-tier LLMs (NVIDIA NIM
# or Gemini), local embeddings, and a subset of SWE-bench Lite. Every stage is
# resumable.
#
# Usage: [CONFIG=pesquisa/scripts/configs/x.env] pesquisa/scripts/pipeline.sh <stage>
# (stages listed at the bottom; "llm" and "exec" run all LLM / all Docker
# stages respectively; "agentic" runs the mini-SWE-agent baseline and evaluates it)
set -euo pipefail
cd "$(dirname "$0")/../.."

set -a; source .env; [ -n "${CONFIG:-}" ] && source "$CONFIG"; set +a
export PYTHONPATH=$PWD
export PROJECT_FILE_LOC=$PWD/pesquisa/data/repo_structure/repo_structures
export AGENTLESS_INSTANCE_IDS_FILE=${AGENTLESS_INSTANCE_IDS_FILE:-$PWD/pesquisa/data/subset_40.txt}
export AGENTLESS_LOCAL_EMBED_MODEL=${AGENTLESS_LOCAL_EMBED_MODEL:-BAAI/bge-small-en-v1.5}
export GEMINI_RPM=${GEMINI_RPM:-10} NVIDIA_RPM=${NVIDIA_RPM:-35}

BACKEND=${BACKEND:-nvidia}
MODEL=${MODEL:-qwen/qwen3-coder-480b-a35b-instruct}
LLM="--model $MODEL --backend $BACKEND"
R=${RESULTS:-pesquisa/results/replication}
THREADS=${THREADS:-2}           # LLM threads (shared rate limiter)
WORKERS=${WORKERS:-3}           # parallel Docker containers (12 GB RAM)
N_LOC=${N_LOC:-4}               # edit-location samples (paper: 4)
N_REPAIR=${N_REPAIR:-10}        # patches per location set (paper: 10)
N_REPRO=${N_REPRO:-40}          # reproduction test samples (paper: 40)
# Docker run ids are shared across runs and the harness skips instances that
# already have a report under the same id, so repeated runs need a prefix
P=${RUN_PREFIX:-}
RUN_NAME=${RUN_NAME:-agentless_replication}
IDS=$(tr '\n' ' ' < "$AGENTLESS_INSTANCE_IDS_FILE")
PY=.venv/bin/python
mkdir -p "$R"

file_level() {
  $PY agentless/fl/localize.py --file_level $LLM \
    --output_folder $R/file_level --num_threads $THREADS --skip_existing
  $PY agentless/fl/localize.py --file_level --irrelevant $LLM \
    --output_folder $R/file_level_irrelevant --num_threads $THREADS --skip_existing
  $PY agentless/fl/retrieve.py --index_type simple --filter_type given_files \
    --filter_file $R/file_level_irrelevant/loc_outputs.jsonl \
    --output_folder $R/retrievel_embedding --persist_dir embedding/swe-bench_simple \
    --num_threads 1
  [ -f $R/file_level_combined/combined_locs.jsonl ] || $PY agentless/fl/combine.py \
    --retrieval_loc_file $R/retrievel_embedding/retrieve_locs.jsonl \
    --model_loc_file $R/file_level/loc_outputs.jsonl \
    --top_n 3 --output_folder $R/file_level_combined
}

related_level() {
  $PY agentless/fl/localize.py --related_level $LLM \
    --output_folder $R/related_elements --top_n 3 --compress_assign --compress \
    --start_file $R/file_level_combined/combined_locs.jsonl \
    --num_threads $THREADS --skip_existing
}

edit_level() {
  $PY agentless/fl/localize.py --fine_grain_line_level $LLM \
    --output_folder $R/edit_location_samples --top_n 3 --compress \
    --temperature 0.8 --num_samples $N_LOC \
    --start_file $R/related_elements/loc_outputs.jsonl \
    --num_threads $THREADS --skip_existing
  $PY agentless/fl/localize.py --merge \
    --output_folder $R/edit_location_individual --top_n 3 --num_samples $N_LOC \
    --start_file $R/edit_location_samples/loc_outputs.jsonl
}

repair() {
  for i in $(seq 0 $((N_LOC - 1))); do
    $PY agentless/repair/repair.py $LLM \
      --loc_file $R/edit_location_individual/loc_merged_${i}-${i}_outputs.jsonl \
      --output_folder $R/repair_sample_$((i + 1)) --loc_interval --top_n=3 \
      --context_window=10 --max_samples $N_REPAIR --cot --diff_format \
      --gen_and_process --num_threads $THREADS
  done
}

select_regression() {
  [ -f $R/passing_tests.jsonl ] || $PY agentless/test/run_regression_tests.py \
    --run_id ${P}generate_regression_tests --output_file $R/passing_tests.jsonl \
    --instance_ids $IDS --num_workers $WORKERS
  $PY agentless/test/select_regression_tests.py $LLM \
    --passing_tests $R/passing_tests.jsonl --output_folder $R/select_regression
}

gen_repro() {
  $PY agentless/test/generate_reproduction_tests.py $LLM --max_samples $N_REPRO \
    --output_folder $R/reproduction_test_samples --num_threads $THREADS
}

run_repro_on_original() {
  for num in $(seq 0 $((N_REPRO - 1))); do
    f=$R/reproduction_test_samples/output_${num}_processed_reproduction_test.jsonl
    [ -f "${f%.jsonl}_verified.jsonl" ] && continue
    $PY agentless/test/run_reproduction_tests.py \
      --run_id=${P}reproduction_test_generation_filter_sample_${num} \
      --test_jsonl=$f --num_workers $WORKERS --instance_ids $IDS --testing
  done
  $PY agentless/test/generate_reproduction_tests.py --max_samples $N_REPRO \
    --output_folder $R/reproduction_test_samples \
    --output_file reproduction_tests.jsonl --select
}

run_tests_on_patches() {
  for i in $(seq 1 $N_LOC); do
    folder=$R/repair_sample_$i
    for num in $(seq 0 $((N_REPAIR - 1))); do
      p=$folder/output_${num}_processed.jsonl
      [ -f $folder/output_${num}_regression_test_results.jsonl ] ||
        $PY agentless/test/run_regression_tests.py \
          --regression_tests $R/select_regression/output.jsonl \
          --predictions_path=$p --run_id=${P}repair_sample_${i}_regression_${num} \
          --instance_ids $IDS --num_workers $WORKERS
      [ -f $folder/output_${num}_reproduction_test_results.jsonl ] ||
        $PY agentless/test/run_reproduction_tests.py \
          --test_jsonl $R/reproduction_test_samples/reproduction_tests.jsonl \
          --predictions_path=$p --run_id=${P}repair_sample_${i}_reproduction_${num} \
          --instance_ids $IDS --num_workers $WORKERS
    done
  done
}

rerank() {
  folders=$(seq -s, -f "$R/repair_sample_%g/" 1 $N_LOC)
  $PY agentless/repair/rerank.py --patch_folder ${folders%,} \
    --num_samples $((N_LOC * N_REPAIR)) --deduplicate --regression --reproduction \
    --output_file $R/all_preds.jsonl
}

evaluate() {
  $PY -m swebench.harness.run_evaluation \
    --dataset_name princeton-nlp/SWE-bench_Lite --predictions_path $R/all_preds.jsonl \
    --instance_ids $IDS --max_workers $WORKERS --run_id ${P}${RUN_NAME}
  # the harness writes <model>.<run_id>.json in the repo root; move it next to the run
  mv "$(ls -t ./*.${P}${RUN_NAME}.json | head -1)" $R/eval_report.json
}

# agentic approach (mini-SWE-agent, separate venv); with the free Gemini tier it
# exits 3 when the daily quota runs out (rerun the next day; finished issues are kept)
agent() {
  .venv-agent/bin/python pesquisa/scripts/agentic/run_agent.py \
    --ids "$AGENTLESS_INSTANCE_IDS_FILE" --output $R --workers $WORKERS \
    --provider ${AGENT_PROVIDER:-openai} --model $MODEL --budget ${AGENT_BUDGET:-0} \
    --step-limit ${AGENT_STEP_LIMIT:-50} --cost-limit ${AGENT_COST_LIMIT:-1.0} \
    --temperature ${AGENT_TEMPERATURE:-0}
}

# stages are resumable, so on a crash (e.g. a long 503 outage) just rerun
retry() {
  for attempt in 1 2 3 4 5; do
    # run outside an &&/|| context so that set -e still applies inside the stage
    set +e; ( set -e; "$1" ); rc=$?; set -e
    [ $rc -eq 0 ] && return 0
    echo "[$1] failed (attempt $attempt), retrying in 5 min..." >&2
    sleep 300
  done
  return 1
}

case "${1:-}" in
  llm) for st in file_level related_level edit_level repair gen_repro; do retry $st; done ;;
  exec) select_regression; run_repro_on_original; run_tests_on_patches; rerank; evaluate ;;
  agentic) agent; evaluate ;;
  file_level|related_level|edit_level|repair|select_regression|gen_repro|run_repro_on_original|run_tests_on_patches|rerank|evaluate|agent) "$1" ;;
  *) sed -n "2,8p" "$0"; exit 1 ;;
esac
