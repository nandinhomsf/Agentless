"""Agentless × abordagem agêntica nas mesmas 47 issues do SWE-bench Lite-S, com dois
modelos (GPT-6 Luna e Claude Haiku 5.5), mais o Agentless do paper (GPT-4o) como
referência.

Gera pesquisa/results/summary/COMPARACAO.md e comparacao_por_issue.csv e atualiza o
bloco entre os marcadores `comparacao:inicio/fim` do pesquisa/README.md.

Fonte de cada execução: o relatório do harness do SWE-bench (eval_report*.json) no
diretório da execução. Custo: tokens registrados × preço de tabela; no agente Claude
Code, o custo informado pelo provedor (meta.jsonl).

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
README = "pesquisa/README.md"
IDS = "pesquisa/data/subset_47.txt"
S15, SEXT = "pesquisa/data/subset_15.txt", "pesquisa/data/subset_ext.txt"
# O paper reporta US$ 0,70 por issue e 96/300 resolvidas no Lite inteiro.
PAPER_CUSTO_POR_RESOLVIDA = PAPER_CUSTO_POR_ISSUE * 300 / 96

# (chave, abordagem, modelo, [(dir, ids)]); modelo None = paper (resultados oficiais)
APPROACHES = [
    ("paper", "Agentless (paper)", None, []),
    ("al_luna", "Agentless", "gpt-6-luna",
     [("pesquisa/results/luna_reduced", S15), ("pesquisa/results/luna_reduced_ext", SEXT)]),
    ("ag_luna", "Agente (mini-SWE-agent)", "gpt-6-luna", [("pesquisa/results/agent_luna", IDS)]),
    ("al_haiku", "Agentless", "claude-haiku-5-5",
     [("pesquisa/results/haiku_reduced", S15), ("pesquisa/results/haiku_reduced_ext", SEXT)]),
    ("ag_haiku", "Agente (Claude Code)", "claude-haiku-5-5", [("pesquisa/results/haiku_agentic", IDS)]),
]
MODEL_NAME = {None: "GPT-4o", "gpt-6-luna": "GPT-6 Luna", "claude-haiku-5-5": "Claude Haiku 5.5"}
SHORT = {"paper": "Paper", "al_luna": "Agentless Luna", "ag_luna": "Agente Luna",
         "al_haiku": "Agentless Haiku", "ag_haiku": "Agente Haiku"}
PAIRS = [  # (A, B, nota)
    ("ag_luna", "al_luna", "efeito da abordagem, mesmo modelo"),
    ("ag_haiku", "al_haiku", "efeito da abordagem, mesmo modelo"),
    ("al_haiku", "al_luna", "efeito do modelo no Agentless"),
    ("al_luna", "paper", ""),
    ("al_haiku", "paper", ""),
    ("ag_luna", "paper", ""),
    ("ag_haiku", "paper", ""),
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
        a = {"name": name, "model": model}
        if model is None:
            a["resolved"] = set(json.load(open(os.path.join(PAPER, "official_results.json")))["resolved"]) & set(ids)
            data[key] = a
            continue
        if not all(glob.glob(os.path.join(run, "eval_report*.json")) for run, _ in runs):
            data[key] = a  # sem relatório: fica fora das tabelas
            continue
        res, p, c, reported = set(), 0, 0, 0.0
        for run, ids_file in runs:
            run_ids = read_ids(ids_file)
            res |= resolved_ids(run) & set(run_ids)
            for per_issue in usage_by_issue(run).values():
                for i in run_ids:
                    x, y = per_issue.get(i, (0, 0))
                    p, c = p + x, c + y
            meta = os.path.join(run, "meta.jsonl")  # agente Claude Code: custo informado pelo provedor
            if os.path.exists(meta):
                rows = [json.loads(l) for l in open(meta) if l.strip()]
                reported += sum(r.get("custo_usd") or 0.0 for r in rows if r["instance_id"] in run_ids)
        pin, pout = PRECOS[model]
        a.update(resolved=res, cost=reported or p / 1e6 * pin + c / 1e6 * pout,
                 tok_in=None if reported else p, tok_out=None if reported else c)
        data[key] = a
    return data


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
    ok = [k for k, a in data.items() if a.get("resolved") is not None]
    missing = [k for k in data if k not in ok]

    md = ["# Agentless × abordagem agêntica nas 47 issues do SWE-bench Lite-S", "",
          "_Gerado por `pesquisa/scripts/compare_all.py`. Avaliação oficial do SWE-bench em Docker; "
          "as mesmas 47 issues em todas as execuções._", "",
          "## Resultado e custo", "",
          "| Abordagem | Modelo | Resolvidas | IC 95% (Wilson) | Custo total (US$) | US$/issue | "
          "US$/resolvida | Tokens/issue (entrada · saída) |",
          "|---|---|---|---|---|---|---|---|"]
    for key in ok:
        a = data[key]
        k = len(a["resolved"])
        lo, hi = wilson(k, n)
        if a["model"] is None:
            md.append(f"| {a['name']} | GPT-4o | {k}/{n} ({pct(k, n)}) | {lo * 100:.0f}–{hi * 100:.0f}% | — | "
                      f"{fmt(PAPER_CUSTO_POR_ISSUE, 2)}* | {fmt(PAPER_CUSTO_POR_RESOLVIDA, 2)}* | — |")
            continue
        tok = (f"{fmt(a['tok_in'] / n / 1000, 1)}k · {fmt(a['tok_out'] / n / 1000, 1)}k"
               if a["tok_in"] is not None else "— (custo informado pelo provedor)")
        md.append(f"| {a['name']} | {MODEL_NAME[a['model']]} | **{k}/{n} ({pct(k, n)})** | "
                  f"{lo * 100:.0f}–{hi * 100:.0f}% | {fmt(a['cost'])} | {fmt(a['cost'] / n)} | "
                  f"{fmt(a['cost'] / k) if k else '—'} | {tok} |")
    md += ["",
           "Custo = tokens registrados × preço de tabela por 1M de tokens (entrada/saída: "
           + "; ".join(f"{MODEL_NAME[m]} US$ {fmt(pi, 2)}/{fmt(po, 2)}" for m, (pi, po) in PRECOS.items()
                       if m in MODEL_NAME)
           + "), só chamadas ao LLM. No agente Claude Code, o custo é o informado pelo próprio provedor "
           "(inclui cache). Nos modelos de raciocínio, a saída inclui o raciocínio.",
           f"*Valores reportados pelo paper para o SWE-bench Lite inteiro: US$ {fmt(PAPER_CUSTO_POR_ISSUE, 2)} "
           f"por issue e 96/300 resolvidas, o que dá US$ {fmt(PAPER_CUSTO_POR_RESOLVIDA, 2)} por issue resolvida."]
    md.append("")

    md += ["## Comparações pareadas", "",
           "Mesmas issues dos dois lados; só as issues que uma abordagem resolve e a outra não "
           "pesam no teste.", "",
           "| A × B | Só A | Só B | Diferença (p.p.) | IC 95% bootstrap | McNemar p | Leitura |",
           "|---|---|---|---|---|---|---|"]
    for ka, kb, nota in PAIRS:
        if ka in missing or kb in missing:
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
        md.append(f"| {nome} | {sa} | {sb} | {pp(d)} | {pp(lo)} a {pp(hi)} | {fmt(p)} | {leitura} |")
    md += ["",
           "Critério de significância: McNemar exato a 5%. Com poucas issues discordantes, o bootstrap "
           "percentil tende a dar intervalos estreitos demais, por isso ele indica só a magnitude "
           "plausível da diferença. p alto não prova equivalência. Bootstrap pareado com 10.000 "
           "reamostragens.", ""]

    md += ["## Por repositório", "",
           "| Repositório | Issues | " + " | ".join(SHORT[k] for k in ok) + " |",
           "|---|---|" + "---|" * len(ok)]
    repos = {}
    for i in ids:
        repos.setdefault(i.split("__")[0], []).append(i)
    for r, rid in sorted(repos.items(), key=lambda x: (-len(x[1]), x[0])):
        md.append(f"| {r} | {len(rid)} | " + " | ".join(str(sum(i in data[k]['resolved'] for i in rid))
                                                         for k in ok) + " |")
    md.append(f"| **Total** | **{n}** | " + " | ".join(f"**{len(data[k]['resolved'])}**" for k in ok) + " |")

    ours = [k for k in ok if k != "paper"]
    union = set().union(*(data[k]["resolved"] for k in ours))
    never = [i for i in ids if i not in union]
    md += ["", f"Resolvidas por pelo menos uma das nossas execuções: {len(union)}/{n}.", "",
           f"### Não resolvidas por nenhuma das nossas execuções ({len(never)})", ""]
    md += [f"- `{i}`" + (" (resolvida pelo paper)" if i in data["paper"]["resolved"] else "") for i in never]
    md.append("")

    if missing:
        md += ["## Sem dados", ""]
        for k in missing:
            dirs = ", ".join(f"`{r}`" for r, _ in next(x[3] for x in APPROACHES if x[0] == k))
            md.append(f"- {data[k]['name']} · {MODEL_NAME[data[k]['model']]}: falta `eval_report*.json` em {dirs}.")
        md.append("")
    md += ["Detalhe por issue: `pesquisa/results/summary/comparacao_por_issue.csv`.", ""]

    os.makedirs(OUT, exist_ok=True)
    open(os.path.join(OUT, "COMPARACAO.md"), "w").write("\n".join(md))
    with open(os.path.join(OUT, "comparacao_por_issue.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["issue"] + ok)
        for i in ids:
            w.writerow([i] + [int(i in data[k]["resolved"]) for k in ok])

    rows = ["| Abordagem | Modelo | Resolvidas | IC 95% | US$ por issue resolvida |", "|---|---|---|---|---|"]
    for key in ok:
        a = data[key]
        k = len(a["resolved"])
        lo, hi = wilson(k, n)
        ic = f"{lo * 100:.0f}–{hi * 100:.0f}%"
        if a["model"] is None:
            rows.append(f"| {a['name']} | GPT-4o | {k}/{n} ({pct(k, n)}) | {ic} | ≈{fmt(PAPER_CUSTO_POR_RESOLVIDA, 2)} |")
        else:
            rows.append(f"| {a['name']} | {MODEL_NAME[a['model']]} | **{k}/{n} ({pct(k, n)})** | {ic} | "
                        f"{fmt(a['cost'] / k) if k else '—'} |")
    block = "\n".join(rows)
    readme = open(README).read()
    new = re.sub(r"(<!-- comparacao:inicio -->).*?(<!-- comparacao:fim -->)",
                 lambda m: m.group(1) + "\n" + block + "\n" + m.group(2), readme, flags=re.S)
    if new != readme:
        open(README, "w").write(new)
    print("\n".join(md))


if __name__ == "__main__":
    main()
