#!/usr/bin/env bash
# Job queue for unattended runs: works through JOBS in order and can be
# restarted at any point (boot after a power cut, crash, manual restart).
# Finished jobs are marked with $RESULTS/.done_<phase>; every pipeline stage is
# resumable, so a job interrupted midway just continues where it stopped.
# Installed as the user service agentless-runner (template: scripts/systemd/).
cd "$(dirname "$0")/.."

JOBS=(
  "scripts/configs/flashlite_reduced.env exec"
  "scripts/configs/flashlite_reduced_ext.env llm"
  "scripts/configs/flashlite_reduced_ext.env exec"
)
MAX_ATTEMPTS=48        # x 30 min: keeps retrying for a day (e.g. daily LLM quota)

log() { echo "[$(date '+%d/%m %H:%M:%S')] $*"; }

wait_network() {
  # Gemini API, GitHub (repo clones) and Hugging Face (datasets, embeddings)
  until wget -q --spider --timeout=15 https://github.com &&
        wget -q --spider --timeout=15 https://huggingface.co &&
        getent hosts generativelanguage.googleapis.com > /dev/null; do
    log "waiting for internet..."; sleep 60
  done
}

wait_docker() {
  until docker info > /dev/null 2>&1; do log "waiting for docker..."; sleep 30; done
}

# a manually started transient run of the same pipeline must not overlap
wait_manual_runs() {
  while systemctl --user is-active -q agentless-exec || systemctl --user is-active -q agentless-llm; do
    log "waiting for manual run (agentless-exec/agentless-llm) to finish..."; sleep 120
  done
}

results_dir() { ( source "$1"; echo "${RESULTS:-results/replication}" ); }

save_eval_report() {
  # the harness writes <model>.agentless_replication.json in the repo root;
  # every run shares that run_id, so keep a copy next to each run's results
  local report
  report=$(ls -t ./*.agentless_replication.json 2> /dev/null | head -1)
  [ -n "$report" ] && cp "$report" "$1/eval_report.json" && log "saved $report -> $1/eval_report.json"
}

log "runner started"
wait_manual_runs
for job in "${JOBS[@]}"; do
  read -r config phase <<< "$job"
  R=$(results_dir "$config")
  marker="$R/.done_$phase"
  [ -f "$marker" ] && { log "skip (done): $job"; continue; }

  for attempt in $(seq 1 $MAX_ATTEMPTS); do
    wait_network
    [ "$phase" = exec ] && wait_docker
    log "start: $job (attempt $attempt)"
    if CONFIG="$config" scripts/pipeline.sh "$phase"; then
      [ "$phase" = exec ] && save_eval_report "$R"
      touch "$marker"; log "done: $job"; break
    fi
    log "failed: $job; retrying in 30 min"
    sleep 1800
  done
  [ -f "$marker" ] || { log "giving up on: $job"; exit 1; }
done
log "all jobs done"
