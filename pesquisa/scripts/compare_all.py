"""Comparação de todas as abordagens nas mesmas 47 issues: Agentless (paper e nossas
execuções) e as abordagens agênticas (mini-SWE-agent com GPT-6 Luna; Claude Code com
Claude Haiku 5.5).

Gera pesquisa/results/summary/COMPARACAO.md e pesquisa/results/summary/comparacao_por_issue.csv, e
atualiza o bloco entre os marcadores `comparacao:inicio/fim` do pesquisa/README.md.
Execuções cujo relatório (eval_report*.json) não está no repositório aparecem como
"sem dados" e ficam fora dos testes.

    .venv/bin/python pesquisa/scripts/compare_all.py
"""

import csv
import glob
import json
import os
import re
from math import sqrt

from extra_metrics import PAPER, PRECOS, PAPER_CUSTO_POR_ISSUE, bootstrap_diff, mcnemar, read_ids, \
    resolved_ids, usage_by_issue

OUT = "pesquisa/results/summary"
IDS = "pesquisa/data/subset_47.txt"
S15, SEXT = "pesquisa/data/subset_15.txt", "pesquisa/data/subset_ext.txt"

# (chave, nome, modelo, [(dir, ids)]); modelo None = paper (resultados oficiais)
APPROACHES = [
    ("paper", "Agentless (paper)", None, []),
    ("al_fl", "Agentless, rodada 1", "gemini-3.1-flash-lite",
     [("pesquisa/results/flashlite_reduced", S15), ("pesquisa/results/flashlite_reduced_ext", SEXT)]),
    ("al_fl2", "Agentless, rodada 2", "gemini-3.1-flash-lite",
     [("pesquisa/results/flashlite_reduced_r2", S15), ("pesquisa/results/flashlite_reduced_ext_r2", SEXT)]),
    ("al_luna", "Agentless", "gpt-6-luna",
     [("pesquisa/results/luna_reduced", S15), ("pesquisa/results/luna_reduced_ext", SEXT)]),
    ("ag_luna", "Agente (mini-SWE-agent)", "gpt-6-luna", [("pesquisa/results/agent_luna", IDS)]),
    ("al_haiku", "Agentless", "claude-haiku-5-5",
     [("pesquisa/results/haiku_reduced", S15), ("pesquisa/results/haiku_reduced_ext", SEXT)]),
    ("ag_haiku", "Agente (Claude Code)", "claude-haiku-5-5", [("pesquisa/results/haiku_agentic", IDS)]),
]
MODEL_NAME = {None: "GPT-4o", "gemini-3.1-flash-lite": "Gemini 3.1 Flash-Lite", "gpt-6-luna": "GPT-6 Luna",
              "claude-haiku-5-5": "Claude Haiku 5.5"}
PAIRS = [  # (A, B, nota)
    ("ag_luna", "al_luna", "efeito da abordagem, mesmo modelo"),
    ("ag_haiku", "al_haiku", "efeito da abordagem, mesmo modelo"),
    ("al_luna", "al_fl", "efeito do modelo no Agentless"),
    ("al_haiku", "al_fl", "efeito do modelo no Agentless"),
    ("ag_luna", "paper", ""),
    ("ag_haiku", "paper", ""),
    ("al_luna", "paper", ""),
    ("al_haiku", "paper", ""),
    ("al_fl", "paper", ""),
    ("ag_luna", "al_fl", ""),
    ("al_fl2", "al_fl", "estabilidade entre rodadas"),
]


def wilson(k, n, z=1.96):
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return c - h, c + h


def load(ids):
    data = {}
    for key, name, model, runs in APPROACHES:
        a = {"name": name, "model": model, "complete": True}
        if model is None:
            a["resolved"] = set(json.load(open(os.path.join(PAPER, "official_results.json")))["resolved"]) & set(ids)
            data[key] = a
            continue
        res, p, c, done, reported = set(), 0, 0, 0, 0.0
        for run, ids_file in runs:
            run_ids = read_ids(ids_file)
            if not glob.glob(os.path.join(run, "eval_report*.json")):
                a["complete"] = False
            res |= resolved_ids(run) & set(run_ids)
            for per_issue in usage_by_issue(run).values():
                for i in run_ids:
                    x, y = per_issue.get(i, (0, 0))
                    p, c = p + x, c + y
            usage = os.path.join(run, "agent_usage.jsonl")
            if os.path.exists(usage):
                done += len({json.loads(l)["instance_id"] for l in open(usage) if l.strip()})
            meta = os.path.join(run, "meta.jsonl")  # agente Claude Code: custo informado pelo provedor
            if os.path.exists(meta):
                rows = [json.loads(l) for l in open(meta) if l.strip()]
                reported += sum(r.get("custo_usd") or 0.0 for r in rows if r["instance_id"] in run_ids)
        pin, pout = PRECOS[model]
        cost = reported if reported else p / 1e6 * pin + c / 1e6 * pout
        a.update(resolved=res, tok_in=p, tok_out=c, cost=cost, done=done, reported=bool(reported))
        data[key] = a
    return data


SHORT = {"paper": "Paper", "al_fl": "Agentless Flash-Lite (r1)", "al_fl2": "Agentless Flash-Lite (r2)",
         "al_luna": "Agentless Luna", "ag_luna": "Agente Luna",
         "al_haiku": "Agentless Haiku", "ag_haiku": "Agente Haiku"}


def label(a):
    return f"{a['name']} · {MODEL_NAME[a['model']]}"


def pct(k, n):
    return f"{k / n * 100:.1f}%".replace(".", ",")


def pp(x):
    return f"{x * 100:+.1f}".replace(".", ",")


def fmt(x, nd=3):
    return f"{x:.{nd}f}".replace(".", ",")


def main():
    ids = read_ids(IDS)
    n = len(ids)
    data = load(ids)
    md = ["# Agentless × agente nas 47 issues do SWE-bench Lite-S", "",
          "_Gerado por `pesquisa/scripts/compare_all.py`. Avaliação oficial do SWE-bench em Docker; "
          "as mesmas 47 issues em todas as execuções._", "",
          "## Resultado, custo e tokens", "",
          "| Abordagem | Modelo | Resolvidas | IC 95% (Wilson) | Custo total (US$) | US$/issue | "
          "US$/resolvida | Tokens/issue (entrada · saída) |",
          "|---|---|---|---|---|---|---|---|"]
    pending = []
    for key, a in data.items():
        k = len(a["resolved"])
        if a["model"] is None:
            lo, hi = wilson(k, n)
            md.append(f"| {a['name']} | GPT-4o | {k}/{n} ({pct(k, n)}) | {lo * 100:.0f}–{hi * 100:.0f}% | — | "
                      f"{fmt(PAPER_CUSTO_POR_ISSUE, 2)}* | ≈{fmt(PAPER_CUSTO_POR_ISSUE * n / k, 2)}* | — |")
            continue
        if not a["complete"]:
            pending.append(key)
            md.append(f"| {a['name']} | {MODEL_NAME[a['model']]} | sem dados no repositório | — | — | — | — | — |")
            continue
        lo, hi = wilson(k, n)
        per_res = fmt(a["cost"] / k) if k else "—"
        tok = "— (custo do provedor)" if a["reported"] else \
            f"{fmt(a['tok_in'] / n / 1000, 1)}k · {fmt(a['tok_out'] / n / 1000, 1)}k"
        md.append(f"| {a['name']} | {MODEL_NAME[a['model']]} | **{k}/{n} ({pct(k, n)})** | {lo * 100:.0f}–{hi * 100:.0f}% | "
                  f"{fmt(a['cost'])} | {fmt(a['cost'] / n)} | {per_res} | {tok} |")
    md += ["",
           "Custo = tokens registrados × preço de tabela por 1M de tokens (entrada/saída: "
           + "; ".join(f"{MODEL_NAME[m]} US$ {fmt(pi, 2)}/{fmt(po, 2)}" for m, (pi, po) in PRECOS.items())
           + "), só chamadas ao LLM; no agente Claude Code, custo informado pelo próprio provedor. "
           "Nos modelos de raciocínio a saída inclui o raciocínio. "
           f"*O paper reporta US$ {fmt(PAPER_CUSTO_POR_ISSUE, 2)} por issue (GPT-4o, Lite inteiro); "
           "o custo por resolvida é uma estimativa.", ""]

    md += ["## Comparações pareadas", "",
           "Mesmas issues dos dois lados; só as issues que uma abordagem resolve e a outra não "
           "pesam no teste.", "",
           "| A × B | Só A | Só B | Diferença (p.p.) | IC 95% bootstrap | McNemar p | Leitura |",
           "|---|---|---|---|---|---|---|"]
    for ka, kb, nota in PAIRS:
        if ka in pending or kb in pending:
            continue
        A, B = data[ka], data[kb]
        a = [int(i in A["resolved"]) for i in ids]
        b = [int(i in B["resolved"]) for i in ids]
        d, lo, hi = bootstrap_diff(a, b)
        sa = sum(x and not y for x, y in zip(a, b))
        sb = sum(y and not x for x, y in zip(a, b))
        p = mcnemar(sa, sb)
        if p < 0.05:
            leitura = "diferença significativa"
        elif lo > 0 or hi < 0:
            leitura = "indício (bootstrap exclui 0, McNemar não)"
        else:
            leitura = "sem evidência de diferença"
        nome = f"{SHORT[ka]} × {SHORT[kb]}" + (f" ({nota})" if nota else "")
        md.append(f"| {nome} | {sa} | {sb} | {pp(d)} | {pp(lo)} a {pp(hi)} | "
                  f"{fmt(p)} | {leitura} |")
    md += ["",
           "Com poucas issues discordantes, o bootstrap percentil tende a dar intervalos estreitos "
           "demais; por isso a leitura usa o McNemar exato como critério (5%). p alto não prova "
           "equivalência. Bootstrap pareado com 10.000 reamostragens.", ""]

    shown = [k for k in data if k not in pending and k != "al_fl2"]
    md += ["## Por repositório", "",
           "| Repositório | Issues | " + " | ".join(SHORT[k] for k in shown) + " |",
           "|---|---|" + "---|" * len(shown)]
    repos = {}
    for i in ids:
        repos.setdefault(i.split("__")[0], []).append(i)
    for r, rid in sorted(repos.items(), key=lambda x: -len(x[1])):
        md.append(f"| {r} | {len(rid)} | " + " | ".join(str(sum(i in data[k]['resolved'] for i in rid))
                                                         for k in shown) + " |")
    md.append(f"| **Total** | **{n}** | " + " | ".join(f"**{len(data[k]['resolved'])}**" for k in shown) + " |")
    union = set().union(*(data[k]["resolved"] for k in shown))
    md += ["", f"Resolvidas por pelo menos uma abordagem: {len(union)}/{n}; por nenhuma: {n - len(union)}.", ""]

    if pending:
        md += ["## Sem dados no repositório", ""]
        for k in pending:
            dirs = ", ".join(f"`{r}`" for r, _ in APPROACHES[[x[0] for x in APPROACHES].index(k)][3])
            md.append(f"- {label(data[k])}: falta o relatório de avaliação (`eval_report*.json`) em {dirs}.")
        md.append("")
    md += ["Detalhe por issue: `pesquisa/results/summary/comparacao_por_issue.csv`.", ""]

    os.makedirs(OUT, exist_ok=True)
    open(os.path.join(OUT, "COMPARACAO.md"), "w").write("\n".join(md))
    with open(os.path.join(OUT, "comparacao_por_issue.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["issue"] + list(data))
        for i in ids:
            w.writerow([i] + [("" if k in pending else int(i in data[k]["resolved"])) for k in data])

    # README: short table between the markers
    rows = ["| Abordagem | Modelo | Resolvidas | US$ por issue resolvida |", "|---|---|---|---|"]
    for key, a in data.items():
        k = len(a["resolved"])
        if a["model"] is None:
            rows.append(f"| {a['name']} | GPT-4o | {k}/{n} ({pct(k, n)}) | ≈{fmt(PAPER_CUSTO_POR_ISSUE * n / k, 2)} (estimado) |")
        elif key in pending:
            rows.append(f"| {a['name']} | {MODEL_NAME[a['model']]} | sem dados no repositório | — |")
        else:
            rows.append(f"| {a['name']} | {MODEL_NAME[a['model']]} | {k}/{n} ({pct(k, n)}) | "
                        f"{fmt(a['cost'] / k) if k else '—'} |")
    block = "\n".join(rows)
    readme = open("pesquisa/README.md").read()
    new = re.sub(r"(<!-- comparacao:inicio -->).*?(<!-- comparacao:fim -->)",
                 lambda m: m.group(1) + "\n" + block + "\n" + m.group(2), readme, flags=re.S)
    if new != readme:
        open("pesquisa/README.md", "w").write(new)
    print("\n".join(md))


if __name__ == "__main__":
    main()
