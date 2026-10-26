#!/usr/bin/env bash
# Fetch the large inputs that are not stored in the repository:
#  - preprocessed repository structures of SWE-bench Lite (Agentless release v1.5.0)
#  - artifacts of the published Agentless run (GPT-4o), used for the comparison
#  - per-issue results of that run from the official SWE-bench leaderboard
# Usage: scripts/download_data.sh   (needs ~8 GB free; run from the repo root)
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p data && cd data

# repository structures, extracted only for the issues of our subsets
if [ ! -d repo_structure/repo_structures ]; then
  ../.venv/bin/gdown -q 15-4XjTmY48ystrsc_xcvtOkMs3Fx8RoW -O repo_structures.zip
  unzip -q -o repo_structures.zip $(cat subset_*.txt | sort -u | sed 's#^#repo_structure/repo_structures/#; s#$#.json#')
  rm repo_structures.zip
fi

# published Agentless artifacts (all stages), without the per-issue logs
if [ ! -d paper_results/file_level ]; then
  wget -q https://github.com/OpenAutoCoder/Agentless/releases/download/v1.5.0/agentless_swebench_lite.zip
  unzip -q -o agentless_swebench_lite.zip -x '*_logs/*'
  mkdir -p paper_results && cp -rn agentless_swebench_lite/* paper_results/
  rm -rf agentless_swebench_lite agentless_swebench_lite.zip
fi

# which issues the published run resolved (96/300)
[ -f paper_results/official_results.json ] || wget -qO paper_results/official_results.json \
  https://raw.githubusercontent.com/swe-bench/experiments/main/evaluation/lite/20241028_agentless-1.5_gpt4o/results/results.json

echo "data ready: $(ls repo_structure/repo_structures | wc -l) repo structures, paper results in data/paper_results"
