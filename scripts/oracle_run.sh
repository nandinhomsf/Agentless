#!/usr/bin/env bash
# Evaluate every distinct candidate patch (see scripts/oracle_eval.py); resumable.
cd "$(dirname "$0")/.."
for run in flashlite_reduced flashlite_reduced_ext; do
  for slot in results/$run/oracle/slot_*.jsonl; do
    k=$(basename "$slot" .jsonl | sed 's/slot_//')
    .venv/bin/python -m swebench.harness.run_evaluation \
      --dataset_name princeton-nlp/SWE-bench_Lite --predictions_path "$slot" \
      --max_workers 2 --run_id oracle_${run}_$k || exit 1
  done
done
