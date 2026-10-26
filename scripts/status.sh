#!/usr/bin/env bash
# Progress summary of a pipeline run.  Usage: scripts/status.sh [config.env]
cd "$(dirname "$0")/.."
CONFIG=${1:-scripts/configs/flashlite_reduced.env}
source "$CONFIG"
R=${RESULTS:-results/replication}
N_LOC=${N_LOC:-4} N_REPAIR=${N_REPAIR:-10} N_REPRO=${N_REPRO:-40}
count() { [ -f "$1" ] && wc -l < "$1" || echo 0; }
done_if() { [ -f "$1" ] && echo "ok" || echo "--"; }

echo "== $(date '+%d/%m %H:%M')  |  $R"
for unit in agentless-runner agentless-llm agentless-exec; do
  printf "  %-15s %s\n" "$unit" "$(systemctl --user is-active $unit 2>/dev/null)"
done

echo "-- LLM"
echo "  localizacao (arquivos)      $(count $R/file_level/loc_outputs.jsonl)"
echo "  localizacao (edicao)        $(count $R/edit_location_samples/loc_outputs.jsonl)"
for i in $(seq 1 $N_LOC); do
  echo "  reparo conjunto $i           $(count $R/repair_sample_$i/output.jsonl)"
done
echo "  testes de reproducao        $(count $R/reproduction_test_samples/output.jsonl)"

echo "-- Docker"
echo "  testes que passam (orig.)   $(count $R/passing_tests.jsonl)"
echo "  testes de regressao selec.  $(count $R/select_regression/output.jsonl)"
v=$(ls $R/reproduction_test_samples/*_verified.jsonl 2>/dev/null | wc -l)
echo "  filtro reproducao           $v/$N_REPRO rodadas"
echo "  teste de reproducao final   $(done_if $R/reproduction_test_samples/reproduction_tests.jsonl)"
reg=$(ls $R/repair_sample_*/output_*_regression_test_results.jsonl 2>/dev/null | wc -l)
rep=$(ls $R/repair_sample_*/output_*_reproduction_test_results.jsonl 2>/dev/null | wc -l)
total=$((N_LOC * N_REPAIR))
echo "  regressao nos patches       $reg/$total"
echo "  reproducao nos patches      $rep/$total"
echo "  rerank (all_preds)          $(done_if $R/all_preds.jsonl)"
report=$(ls $R/eval_report.json 2>/dev/null)
if [ -n "$report" ]; then
  python3 -c "import json; r=json.load(open('$report')); print(f\"  AVALIACAO: {r['resolved_instances']}/{r['total_instances']} resolvidas\")"
else
  echo "  avaliacao                   --"
fi

running=$(pgrep -af "agentless/|swebench.harness" | grep -v pgrep | grep -oE "run_id[= ][^ ]+" | head -1)
[ -n "$running" ] && echo "-- rodando agora: $running"
errors=$(cat logs/$(basename "$CONFIG" .env)_exec.log logs/runner.log 2>/dev/null | grep -c "Traceback")
echo "-- tracebacks nos logs (inclui reinicios antigos): ${errors:-0}"
echo "-- fila: $(tail -1 logs/runner.log 2>/dev/null)"
echo "-- memoria: $(free -h | awk 'NR==2{print $3" usada, "$7" disponivel"}')"
