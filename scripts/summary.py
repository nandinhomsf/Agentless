"""Aggregate view of the replication: ours vs. the published Agentless run.

Writes results/summary/RESUMO.md (tables) and results/summary/por_issue.csv
(one row per issue) and prints the Markdown. Re-run any time, e.g. after the
oracle evaluation (scripts/oracle_run.sh) progresses.

    .venv/bin/python scripts/summary.py
"""

import csv
import glob
import json
import math
import os
from collections import defaultdict
from math import comb

from datasets import load_dataset

from compare_runs import PAPER, files_cover, load_jsonl, patch_locations, stage_files

RUNS = {  # results dir -> issue list
    "results/flashlite_reduced": "data/subset_15.txt",
    "results/flashlite_reduced_ext": "data/subset_ext.txt",
}
OUT = "results/summary"
STAGES = [
    ("Arquivos via LLM", "file_level/loc_outputs.jsonl"),
    ("Arquivos via embeddings", "retrievel_embedding/retrieve_locs.jsonl"),
    ("Arquivos combinados", "file_level_combined/combined_locs.jsonl"),
    ("Elementos relacionados", "related_elements/loc_outputs.jsonl"),
]


def read_ids(path):
    return [l.strip() for l in open(path) if l.strip()]


def wilson(k, n, z=1.96):
    if not n:
        return "—"
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return f"[{max(c - h, 0):.0%}, {min(c + h, 1):.0%}]"


def mcnemar(b, c):
    """Exact two-sided McNemar p-value from the discordant pair counts."""
    m = b + c
    return 1.0 if not m else min(1.0, 2 * sum(comb(m, i) for i in range(min(b, c) + 1)) / 2**m)


def candidate_stats(run):
    """Per issue: distinct non-empty patches and how many pass the reproduction test."""
    stats = defaultdict(lambda: {"distinct": set(), "pass_repro": 0})
    for fp in glob.glob(f"{run}/repair_sample_*/output_*_processed.jsonl"):
        rep = load_jsonl(fp.replace("_processed.jsonl", "_reproduction_test_results.jsonl"))
        for i, d in load_jsonl(fp).items():
            patch = (d.get("model_patch") or "").strip()
            if patch:
                stats[i]["distinct"].add(patch)
                stats[i]["pass_repro"] += rep.get(i, {}).get("reproduction") is True
    return stats


def oracle_results(run):
    """{issue: resolved by any candidate} from scripts/oracle_run.sh, plus evaluated count."""
    tag = os.path.basename(run)
    out = {}
    for fp in glob.glob(f"logs/run_evaluation/oracle_{tag}_[0-9]*/oracle_slot_*/*/report.json"):
        for i, r in json.load(open(fp)).items():
            out[i] = out.get(i, False) or r.get("resolved", False)
    slots = len(glob.glob(f"{run}/oracle/slot_*.jsonl"))
    done = len(glob.glob(f"logs/run_evaluation/oracle_{tag}_[0-9]*/oracle_slot_*/*/report.json"))
    expected = sum(1 for f in glob.glob(f"{run}/oracle/slot_*.jsonl") for _ in open(f))
    return out, done >= expected and slots > 0


def main():
    os.makedirs(OUT, exist_ok=True)
    ds = load_dataset("princeton-nlp/SWE-bench_Lite", split="test")
    gold = {d["instance_id"]: patch_locations(d["patch"]) for d in ds}
    paper_resolved = set(json.load(open(f"{PAPER}/official_results.json"))["resolved"])
    paper_preds = load_jsonl(f"{PAPER}/all_preds.jsonl")

    rows, oracle_complete = [], True
    for run, ids_file in RUNS.items():
        ids = read_ids(ids_file)
        ours_resolved = set(json.load(open(f"{run}/eval_report.json"))["resolved_ids"])
        preds = load_jsonl(f"{run}/all_preds.jsonl")
        repro = load_jsonl(f"{run}/reproduction_test_samples/reproduction_tests.jsonl")
        cands = candidate_stats(run)
        oracle, complete = oracle_results(run)
        oracle_complete &= complete
        ours_loc = {s: stage_files(run, s, ids) for _, s in STAGES}
        paper_loc = {s: stage_files(PAPER, s, ids) for _, s in STAGES}
        for i in ids:
            g = gold[i]
            ours_patch = patch_locations(preds.get(i, {}).get("model_patch"))
            paper_patch = patch_locations(paper_preds.get(i, {}).get("model_patch"))
            row = {
                "issue": i,
                "repo": i.rsplit("-", 1)[0].split("__")[0],
                "execucao": os.path.basename(run),
                "paper_resolvida": int(i in paper_resolved),
                "nossa_resolvida": int(i in ours_resolved),
                "oraculo_resolvida": "" if i not in oracle else int(oracle[i]),
                "tem_teste_reproducao": int(i in repro),
                "patches_distintos": len(cands[i]["distinct"]),
                "patches_passam_reproducao": cands[i]["pass_repro"],
                "paper_patch_arquivo_certo": int(files_cover(paper_patch, g)),
                "nosso_patch_arquivo_certo": int(files_cover(ours_patch, g)),
            }
            for label, s in STAGES:
                key = label.lower().replace(" ", "_")
                row[f"paper_{key}"] = int(files_cover(paper_loc[s].get(i), g))
                row[f"nosso_{key}"] = int(files_cover(ours_loc[s].get(i), g))
            rows.append(row)

    with open(f"{OUT}/por_issue.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    n = len(rows)
    tot = lambda key, rs=rows: sum(int(r[key] or 0) for r in rs)
    pct = lambda k, m=n: f"{k}/{m} ({k / m:.1%})" if m else "—"
    ours, paper = tot("nossa_resolvida"), tot("paper_resolvida")
    only_ours = sum(r["nossa_resolvida"] and not r["paper_resolvida"] for r in rows)
    only_paper = sum(r["paper_resolvida"] and not r["nossa_resolvida"] for r in rows)
    both = sum(r["nossa_resolvida"] and r["paper_resolvida"] for r in rows)

    md = [f"# Resumo da replicação do Agentless ({n} issues do SWE-bench Lite-S)", "",
          "## Resolução", "",
          "| | Resolvidas | IC 95% (Wilson) |", "|---|---|---|",
          f"| Paper (GPT-4o, 4×10 patches, 40 testes) | {pct(paper)} | {wilson(paper, n)} |",
          f"| Nós (Gemini 3.1 Flash-Lite, 2×3 patches, 4 testes) | {pct(ours)} | {wilson(ours, n)} |", "",
          f"Ambos: {both} · só nós: {only_ours} · só paper: {only_paper} · nenhum: {n - both - only_ours - only_paper} "
          f"· McNemar exato p = {mcnemar(only_ours, only_paper):.2f}", "",
          "### Por execução", "", "| Execução | Issues | Paper | Nós |", "|---|---|---|---|"]
    for run in RUNS:
        rs = [r for r in rows if r["execucao"] == os.path.basename(run)]
        md.append(f"| {os.path.basename(run)} | {len(rs)} | {pct(tot('paper_resolvida', rs), len(rs))} | {pct(tot('nossa_resolvida', rs), len(rs))} |")

    md += ["", "### Por repositório", "", "| Repositório | Issues | Paper | Nós |", "|---|---|---|---|"]
    for repo in sorted({r["repo"] for r in rows}, key=lambda x: -sum(r["repo"] == x for r in rows)):
        rs = [r for r in rows if r["repo"] == repo]
        md.append(f"| {repo} | {len(rs)} | {tot('paper_resolvida', rs)} | {tot('nossa_resolvida', rs)} |")

    md += ["", "## Localização (o arquivo do patch oficial foi encontrado?)", "",
           "| Etapa | Paper | Nós |", "|---|---|---|"]
    for label, _ in STAGES:
        key = label.lower().replace(" ", "_")
        md.append(f"| {label} | {pct(tot('paper_' + key))} | {pct(tot('nosso_' + key))} |")
    md.append(f"| Patch final no arquivo certo | {pct(tot('paper_patch_arquivo_certo'))} | {pct(tot('nosso_patch_arquivo_certo'))} |")

    with_t = [r for r in rows if r["tem_teste_reproducao"]]
    passing = [r for r in with_t if r["patches_passam_reproducao"]]
    failing = [r for r in with_t if not r["patches_passam_reproducao"]]
    no_t = [r for r in rows if not r["tem_teste_reproducao"]]
    md += ["", "## Diagnóstico da seleção de patch (nossa execução)", "",
           "| Situação | Issues | Resolvidas |", "|---|---|---|",
           f"| Com teste de reprodução e ≥1 patch passando nele | {len(passing)} | {pct(tot('nossa_resolvida', passing), len(passing))} |",
           f"| Com teste, mas nenhum patch passa | {len(failing)} | {pct(tot('nossa_resolvida', failing), len(failing))} |",
           f"| Sem teste de reprodução válido | {len(no_t)} | {pct(tot('nossa_resolvida', no_t), len(no_t))} |", "",
           f"Patches distintos por issue: média {sum(r['patches_distintos'] for r in rows) / n:.1f} "
           f"· issues com um só patch distinto: {sum(r['patches_distintos'] == 1 for r in rows)}"]

    evaluated = [r for r in rows if r["oraculo_resolvida"] != ""]
    md += ["", "## Oráculo (algum dos patches gerados resolve?)", ""]
    if evaluated:
        orc = tot("oraculo_resolvida", evaluated)
        sel = tot("nossa_resolvida", evaluated)
        lost = sorted(r["issue"] for r in evaluated if r["oraculo_resolvida"] and not r["nossa_resolvida"])
        status = "completo" if oracle_complete else f"**parcial: {len(evaluated)}/{n} issues avaliadas até agora**"
        md += [f"Status: {status}", "",
               "| | Resolvidas |", "|---|---|",
               f"| Patch selecionado pelo Agentless | {pct(sel, len(evaluated))} |",
               f"| Oráculo (melhor candidato possível) | {pct(orc, len(evaluated))} |", "",
               f"Issues com patch correto gerado mas não selecionado: {', '.join(lost) or 'nenhuma'}"]
    else:
        md.append("Ainda não avaliado (rode `scripts/oracle_run.sh`).")

    md += ["", f"_Detalhe por issue: `{OUT}/por_issue.csv`_"]
    text = "\n".join(md) + "\n"
    open(f"{OUT}/RESUMO.md", "w").write(text)
    print(text)


if __name__ == "__main__":
    main()
