"""Comparação de todas as abordagens nas mesmas 47 issues: Agentless (paper e nossas
execuções) e o agente (mini-SWE-agent), com Flash-Lite e GPT-6 Luna.

Gera results/summary/COMPARACAO.md e results/summary/comparacao_por_issue.csv, e
atualiza o bloco entre os marcadores `comparacao:inicio/fim` do README.md. Execuções
ainda sem eval_report.json aparecem como "em andamento" e ficam fora dos testes.

    .venv/bin/python scripts/compare_all.py
"""

import csv
import json
import os
import re
from math import sqrt

from extra_metrics import PAPER, PRECOS, PAPER_CUSTO_POR_ISSUE, bootstrap_diff, mcnemar, read_ids, \
    resolved_ids, usage_by_issue

OUT = "results/summary"
IDS = "data/subset_47.txt"
S15, SEXT = "data/subset_15.txt", "data/subset_ext.txt"

# (chave, nome, modelo, [(dir, ids)]); modelo None = paper (resultados oficiais)
APPROACHES = [
    ("paper", "Agentless (paper)", None, []),
    ("al_fl", "Agentless, rodada 1", "gemini-3.1-flash-lite",
     [("results/flashlite_reduced", S15), ("results/flashlite_reduced_ext", SEXT)]),
    ("al_fl2", "Agentless, rodada 2", "gemini-3.1-flash-lite",
     [("results/flashlite_reduced_r2", S15), ("results/flashlite_reduced_ext_r2", SEXT)]),
    ("al_luna", "Agentless", "gpt-6-luna",
     [("results/luna_reduced", S15), ("results/luna_reduced_ext", SEXT)]),
    ("ag_luna", "Agente (mini-SWE-agent)", "gpt-6-luna", [("results/agent_luna", IDS)]),
    ("ag_fl", "Agente (mini-SWE-agent)", "gemini-3.1-flash-lite", [("results/agent_flashlite", IDS)]),
]
MODEL_NAME = {None: "GPT-4o", "gemini-3.1-flash-lite": "Gemini 3.1 Flash-Lite", "gpt-6-luna": "GPT-6 Luna"}
PAIRS = [  # (A, B, nota)
    ("ag_luna", "al_luna", "efeito da abordagem, mesmo modelo"),
    ("ag_fl", "al_fl", "efeito da abordagem, mesmo modelo"),
    ("al_luna", "al_fl", "efeito do modelo no Agentless"),
    ("ag_luna", "ag_fl", "efeito do modelo no agente"),
    ("ag_luna", "paper", ""),
    ("ag_fl", "paper", ""),
    ("al_luna", "paper", ""),
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
        res, p, c, done = set(), 0, 0, 0
        for run, ids_file in runs:
            run_ids = read_ids(ids_file)
            if not os.path.exists(os.path.join(run, "eval_report.json")):
                a["complete"] = False
            res |= resolved_ids(run) & set(run_ids)
            for per_issue in usage_by_issue(run).values():
                for i in run_ids:
                    x, y = per_issue.get(i, (0, 0))
                    p, c = p + x, c + y
            usage = os.path.join(run, "agent_usage.jsonl")
            if os.path.exists(usage):
                done += len({json.loads(l)["instance_id"] for l in open(usage) if l.strip()})
        pin, pout = PRECOS[model]
        a.update(resolved=res, tok_in=p, tok_out=c, cost=p / 1e6 * pin + c / 1e6 * pout, done=done)
        data[key] = a
    return data


SHORT = {"paper": "Paper", "al_fl": "Agentless Flash-Lite (r1)", "al_fl2": "Agentless Flash-Lite (r2)",
         "al_luna": "Agentless Luna", "ag_luna": "Agente Luna", "ag_fl": "Agente Flash-Lite"}


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
          "_Gerado por `scripts/compare_all.py`. Avaliação oficial do SWE-bench em Docker; "
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
            md.append(f"| {a['name']} | {MODEL_NAME[a['model']]} | em andamento ({a['done']}/{n} issues "
                      f"executadas) | — | {fmt(a['cost'])} até agora | — | — | — |")
            continue
        lo, hi = wilson(k, n)
        per_res = fmt(a["cost"] / k) if k else "—"
        md.append(f"| {a['name']} | {MODEL_NAME[a['model']]} | **{k}/{n} ({pct(k, n)})** | {lo * 100:.0f}–{hi * 100:.0f}% | "
                  f"{fmt(a['cost'])} | {fmt(a['cost'] / n)} | {per_res} | "
                  f"{fmt(a['tok_in'] / n / 1000, 1)}k · {fmt(a['tok_out'] / n / 1000, 1)}k |")
    md += ["",
           "Custo = tokens registrados × preço de tabela por 1M de tokens (Flash-Lite US$ 0,25/1,50; "
           "Luna US$ 0,10/0,50), só chamadas ao LLM. Nos modelos de raciocínio a saída inclui o raciocínio. "
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
        md += ["## Em andamento", ""]
        for k in pending:
            md.append(f"- {label(data[k])}: {data[k]['done']}/{n} issues executadas. O agente com Flash-Lite "
                      "roda no plano grátis (500 chamadas/dia, ~29 por issue); o runner retoma quando a cota renova.")
        md.append("")
    md += ["Detalhe por issue: `results/summary/comparacao_por_issue.csv`.", ""]

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
            rows.append(f"| {a['name']} | {MODEL_NAME[a['model']]} | em andamento ({a['done']}/{n}) | — |")
        else:
            rows.append(f"| {a['name']} | {MODEL_NAME[a['model']]} | {k}/{n} ({pct(k, n)}) | "
                        f"{fmt(a['cost'] / k) if k else '—'} |")
    block = "\n".join(rows)
    readme = open("README.md").read()
    new = re.sub(r"(<!-- comparacao:inicio -->).*?(<!-- comparacao:fim -->)",
                 lambda m: m.group(1) + "\n" + block + "\n" + m.group(2), readme, flags=re.S)
    if new != readme:
        open("README.md", "w").write(new)
    print("\n".join(md))


if __name__ == "__main__":
    main()
