#!/usr/bin/env bash
# Evaluate every distinct candidate patch (see pesquisa/scripts/oracle_eval.py); resumable.
# Usage: pesquisa/scripts/oracle_run.sh [run_dir_name ...]   (default: the Flash-Lite runs)
#        ORACLE_WORKERS=6 pesquisa/scripts/oracle_run.sh haiku_reduced haiku_reduced_ext
cd "$(dirname "$0")/../.."
RUNS=("$@")
[ ${#RUNS[@]} -eq 0 ] && RUNS=(flashlite_reduced flashlite_reduced_ext)
for run in "${RUNS[@]}"; do
  for slot in pesquisa/results/$run/oracle/slot_*.jsonl; do
    k=$(basename "$slot" .jsonl | sed 's/slot_//')
    .venv/bin/python -m swebench.harness.run_evaluation \
      --dataset_name princeton-nlp/SWE-bench_Lite --predictions_path "$slot" \
      --max_workers "${ORACLE_WORKERS:-2}" --run_id oracle_${run}_$k || exit 1
  done
done
