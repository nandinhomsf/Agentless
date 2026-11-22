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
  "scripts/configs/flashlite_reduced_r2.env llm"
  "scripts/configs/flashlite_reduced_r2.env exec"
  "scripts/configs/flashlite_reduced_ext_r2.env llm"
  "scripts/configs/flashlite_reduced_ext_r2.env exec"
  "scripts/configs/agent_flashlite.env agentic"
)
MAX_ATTEMPTS=48        # x 30 min of real failures (quota waits do not count)

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


log "runner started"
wait_manual_runs
for job in "${JOBS[@]}"; do
  read -r config phase <<< "$job"
  R=$(results_dir "$config")
  marker="$R/.done_$phase"
  [ -f "$marker" ] && { log "skip (done): $job"; continue; }

  attempt=1
  while [ $attempt -le $MAX_ATTEMPTS ]; do
    wait_network
    [ "$phase" != llm ] && wait_docker
    log "start: $job (attempt $attempt)"
    CONFIG="$config" scripts/pipeline.sh "$phase"; rc=$?
    if [ $rc -eq 0 ]; then
      touch "$marker"; log "done: $job"; break
    fi
    # exit 3 = daily LLM quota used up: a multi-day job, not a failure
    if [ $rc -eq 3 ]; then
      log "daily quota exhausted: $job; checking again in 30 min"
    else
      log "failed: $job; retrying in 30 min"
      attempt=$((attempt + 1))
    fi
    sleep 1800
  done
  [ -f "$marker" ] || { log "giving up on: $job"; exit 1; }
done
log "all jobs done"
