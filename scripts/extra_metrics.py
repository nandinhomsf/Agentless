"""Métricas extras do estudo: custo por issue resolvida e diferença pareada com IC.

Descrição das métricas: docs/METRICAS_NOVAS.md. Não depende de `datasets` nem de rede;
lê só os arquivos que o pipeline já grava em cada `results/<run>/`.

    .venv/bin/python scripts/extra_metrics.py
    .venv/bin/python scripts/extra_metrics.py --modelo claude-haiku-5-5 \
        --runs results/haiku_reduced:data/subset_15.txt \
               results/haiku_reduced_ext:data/subset_ext.txt

Agente (mini-SWE-agent) contra o Agentless, mesmas issues:

    .venv/bin/python scripts/extra_metrics.py --nome Agente \
        --runs results/agent_flashlite:data/subset_47.txt \
        --contra results/flashlite_reduced:data/subset_15.txt \
                 results/flashlite_reduced_ext:data/subset_ext.txt \
        --out results/summary/METRICAS_AGENTE.md

O scripts/summary.py chama `run_extra()` no fim; se falhar, o RESUMO.md original
já foi escrito.
"""

import argparse
import glob
import json
import os
import random

PAPER = "data/paper_results"
OUT = "results/summary"
DEFAULT_RUNS = [
    ("results/flashlite_reduced", "data/subset_15.txt"),
    ("results/flashlite_reduced_ext", "data/subset_ext.txt"),
]
# US$ por 1M de tokens (entrada, saída). Fonte: páginas de modelo da Artificial
# Analysis; confira no console do provedor antes de citar.
PRECOS = {
    "gemini-3.1-flash-lite": (0.25, 1.50),
    "claude-haiku-5-5": (0.10, 0.50),
    "gpt-6-luna": (0.10, 0.50),
}
PAPER_CUSTO_POR_ISSUE = 0.70  # US$, GPT-4o, 4x10 patches (valor reportado, não recalculado)

# (rótulo, arquivo(s) da etapa, campo com a trajetória PRÓPRIA da etapa). Cada
# arquivo carrega as trajetórias das etapas anteriores; só o campo próprio conta.
ETAPAS = [
    ("Localização: arquivos (LLM)", "file_level/loc_outputs.jsonl", "file_traj"),
    ("Localização: arquivos irrelevantes", "file_level_irrelevant/loc_outputs.jsonl", "file_traj"),
    ("Localização: elementos relacionados", "related_elements/loc_outputs.jsonl", "related_loc_traj"),
    ("Localização: linhas de edição", "edit_location_samples/loc_outputs.jsonl", "edit_loc_traj"),
    ("Geração de patches", "repair_sample_*/output.jsonl", "traj"),
    ("Testes de reprodução", "reproduction_test_samples/output.jsonl", "traj"),
    ("Seleção de testes de regressão", "select_regression/output.jsonl", "traj"),
    ("Agente (mini-SWE-agent, todas as chamadas)", "agent_usage.jsonl", "traj"),
]


def read_ids(path):
    return [l.strip() for l in open(path) if l.strip()]


def sum_usage(obj):
    """(prompt_tokens, completion_tokens) de todos os dicts 'usage' dentro de obj."""
    p = c = 0
    stack = [obj]
    while stack:
        x = stack.pop()
        if isinstance(x, dict):
            u = x.get("usage")
            if isinstance(u, dict) and "prompt_tokens" in u:
                p += u.get("prompt_tokens") or 0
                c += u.get("completion_tokens") or 0
            stack.extend(v for k, v in x.items() if k not in ("usage", "prompt", "response"))
        elif isinstance(x, list):
            stack.extend(x)
    return p, c


def usage_by_issue(run):
    """{etapa: {issue: (entrada, saída)}} para um diretório de resultados."""
    out = {}
    for label, pattern, field in ETAPAS:
        per_issue = {}
        for fp in sorted(glob.glob(os.path.join(run, pattern))):
            last = {}
            for line in open(fp):
                if not line.strip():
                    continue
                d = json.loads(line)
                last[d["instance_id"]] = sum_usage(d.get(field))  # retomadas: vale a última
            for i, (p, c) in last.items():
                a, b = per_issue.get(i, (0, 0))
                per_issue[i] = (a + p, b + c)
        out[label] = per_issue
    return out


def resolved_ids(run):
    path = os.path.join(run, "eval_report.json")
    return set(json.load(open(path))["resolved_ids"]) if os.path.exists(path) else set()


def bootstrap_diff(a, b, n_boot=10_000, seed=0):
    """Diferença pareada (média de a - b) e IC 95% percentil; a, b listas de 0/1."""
    n = len(a)
    d = [x - y for x, y in zip(a, b)]
    rng = random.Random(seed)
    boots = sorted(sum(d[rng.randrange(n)] for _ in range(n)) / n for _ in range(n_boot))
    lo, hi = boots[int(0.025 * n_boot)], boots[int(0.975 * n_boot) - 1]
    return sum(d) / n, lo, hi


def mcnemar(b, c):
    from math import comb

    m = b + c
    return 1.0 if not m else min(1.0, 2 * sum(comb(m, i) for i in range(min(b, c) + 1)) / 2**m)


def conclusao(lo, hi, margem):
    if lo > 0 or hi < 0:
        return "diferença significativa (IC exclui 0)"
    if -margem <= lo and hi <= margem:
        return f"equivalente dentro da margem de ±{margem * 100:.0f} p.p."
    return "inconclusivo (IC largo demais para afirmar equivalência ou diferença)"


def run_extra(runs=None, modelo="gemini-3.1-flash-lite", preco=None, margem=0.10,
              paper=PAPER, nome="Nós", contra=None, nome_contra="Agentless"):
    runs = runs or DEFAULT_RUNS
    pin, pout = preco or PRECOS[modelo]
    ids, resolved = [], set()
    tokens = {label: [0, 0] for label, _, _ in ETAPAS}
    for run, ids_file in runs:
        run_ids = read_ids(ids_file)
        ids += run_ids
        resolved |= resolved_ids(run) & set(run_ids)
        for label, per_issue in usage_by_issue(run).items():
            for i in run_ids:
                p, c = per_issue.get(i, (0, 0))
                tokens[label][0] += p
                tokens[label][1] += c
    n = len(ids)
    custo = lambda p, c: p / 1e6 * pin + c / 1e6 * pout
    tot_p = sum(v[0] for v in tokens.values())
    tot_c = sum(v[1] for v in tokens.values())
    total = custo(tot_p, tot_c)
    k = len(resolved)

    md = ["## Métricas extras", "",
          f"### Custo e tokens ({nome}: {modelo}; US$ {pin}/{pout} por 1M tokens entrada/saída)", "",
          "| Etapa | Tokens entrada | Tokens saída | Custo (US$) |", "|---|---|---|---|"]
    for label, (p, c) in tokens.items():
        if not (p or c) and label.startswith("Agente"):
            continue
        md.append(f"| {label} | {p:,} | {c:,} | {custo(p, c):.3f} |")
    md += [f"| **Total** | **{tot_p:,}** | **{tot_c:,}** | **{total:.3f}** |", "",
           f"- Custo por issue: US$ {total / n:.3f} ({n} issues)",
           f"- Custo por issue resolvida: " + (f"US$ {total / k:.3f} ({k} resolvidas)" if k else "— (nenhuma resolvida)"),
           f"- Tokens por issue: {tot_p / n:,.0f} entrada, {tot_c / n:,.0f} saída",
           f"- Referência do paper (GPT-4o, reportado): US$ {PAPER_CUSTO_POR_ISSUE:.2f} por issue", "",
           "_Só chamadas ao LLM. Tentativas repetidas por falha de API não aparecem nos logs._", ""]

    md += ["### Diferença pareada vs. paper (mesmas issues)", ""]
    pr_path = os.path.join(paper, "official_results.json")
    if not os.path.exists(pr_path):
        md.append(f"Resultados do paper não encontrados em `{pr_path}`.")
    else:
        paper_res = set(json.load(open(pr_path))["resolved"])
        md += paired_section(ids, resolved, nome, paper_res, "paper", margem, f"Paper (mesmas {n} issues)")
    if contra:
        contra_res = set()
        for run, ids_file in contra:
            contra_res |= resolved_ids(run) & set(read_ids(ids_file))
        md += ["", f"### Diferença pareada vs. {nome_contra} (mesmas issues)", ""]
        md += paired_section(ids, resolved, nome, contra_res, nome_contra, margem)
    return "\n".join(md) + "\n"


def paired_section(ids, res_a, nome_a, res_b, nome_b, margem, rotulo_b=None):
    n = len(ids)
    a = [int(i in res_a) for i in ids]
    b = [int(i in res_b) for i in ids]
    diff, lo, hi = bootstrap_diff(a, b)
    so_a = sum(x and not y for x, y in zip(a, b))
    so_b = sum(y and not x for x, y in zip(a, b))
    ambos = sum(x and y for x, y in zip(a, b))
    return ["| | Resolvidas |", "|---|---|",
            f"| {nome_a} | {sum(a)}/{n} ({sum(a) / n:.1%}) |",
            f"| {rotulo_b or nome_b} | {sum(b)}/{n} ({sum(b) / n:.1%}) |", "",
            f"- Diferença ({nome_a} − {nome_b}): **{diff * 100:+.1f} p.p.**, IC 95% bootstrap pareado "
            f"[{lo * 100:+.1f}, {hi * 100:+.1f}] p.p. (10.000 reamostragens)",
            f"- Discordâncias: só {nome_a} {so_a} · só {nome_b} {so_b} · ambos {ambos} · "
            f"nenhum {n - ambos - so_a - so_b} · McNemar exato p = {mcnemar(so_a, so_b):.2f}",
            f"- Conclusão: {conclusao(lo, hi, margem)}", "",
            "_A margem de equivalência é uma escolha do estudo (`--margem`); "
            "p alto no McNemar não prova equivalência._"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", nargs="*", help="pares dir:arquivo_de_ids")
    ap.add_argument("--modelo", default="gemini-3.1-flash-lite")
    ap.add_argument("--preco", nargs=2, type=float, metavar=("ENTRADA", "SAIDA"))
    ap.add_argument("--margem", type=float, default=0.10, help="margem de equivalência (fração)")
    ap.add_argument("--nome", default="Nós")
    ap.add_argument("--paper", default=PAPER)
    ap.add_argument("--contra", nargs="*", help="pares dir:arquivo_de_ids de outra abordagem a comparar")
    ap.add_argument("--nome-contra", default="Agentless")
    ap.add_argument("--out", default=f"{OUT}/METRICAS_EXTRA.md")
    args = ap.parse_args()
    runs = [tuple(r.split(":", 1)) for r in args.runs] if args.runs else None
    contra = [tuple(r.split(":", 1)) for r in args.contra] if args.contra else None
    text = run_extra(runs, args.modelo, tuple(args.preco) if args.preco else None,
                     args.margem, args.paper, args.nome, contra, args.nome_contra)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    open(args.out, "w").write(text)
    print(text)


if __name__ == "__main__":
    main()
