#!/usr/bin/env python3
"""Abordagem agêntica: o agente nativo da Anthropic (Claude Code, modo headless)
resolve cada issue dentro do container da instância do SWE-bench.

Por issue: sobe um container da imagem `sweb.eval.x86_64.<id>:latest` (repositório
em /testbed, no commit base), roda `claude -p` com o texto da issue, extrai o patch
(`git diff`) e apaga o container. Rede LIVRE (igual ao experimento do Luna): o agente
pode acessar a internet; por isso a trajetória completa é gravada para análise
posterior ("cola").

Saídas em --out:
    trajectories/<issue>.jsonl   fluxo completo (stream-json) do agente
    preds.jsonl                  predições no formato do harness do SWE-bench
    meta.jsonl                   custo, passos, duração e motivo de término por issue
Retomável: issues já presentes em meta.jsonl são puladas.

Orçamento: --max-cost limita cada issue; --stop-total para de INICIAR issues novas
quando o custo acumulado chega ao valor (as em andamento terminam).

    export ANTHROPIC_API_KEY=...   (o runner o lê do ambiente; nunca vai para argv)
    .venv/bin/python scripts/agentic/run_agentic.py --ids psf__requests-2317 \
        --out results/haiku_agentic_pilot --workers 1
Avaliação (mesmo harness do Agentless):
    .venv/bin/python -m swebench.harness.run_evaluation --dataset_name \
        princeton-nlp/SWE-bench_Lite --predictions_path <out>/preds.jsonl \
        --instance_ids <ids> --max_workers 4 --run_id agentic_haiku
"""

import argparse
import concurrent.futures as cf
import json
import os
import subprocess
import threading
import time

from datasets import load_dataset

CLAUDE_BIN = os.path.realpath(os.path.expanduser("~/.local/bin/claude"))
TOOLS = ["Bash", "Edit", "Write", "Read", "Glob", "Grep"]

PROMPT = """<uploaded_files>
/testbed
</uploaded_files>
I've uploaded a python code repository in the directory /testbed. Consider the following issue description:

<issue_description>
{issue}
</issue_description>

Can you help me implement the necessary changes to the repository so that the issue described above is resolved?
I've already taken care of all changes to any of the test files described in the issue description, so you don't need to modify the testing logic or any of the tests in any way.
Make the minimal changes to non-test files in /testbed to resolve the issue.
The Python environment is already set up; activate it with `source /opt/miniconda3/bin/activate testbed`.
When you are done, stop."""

lock = threading.Lock()
state = {"spent": 0.0}


def sh(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def run_issue(inst, a):
    iid = inst["instance_id"]
    name = f"agentic_{iid}"
    t0 = time.time()
    sh(["docker", "rm", "-f", name])
    r = sh(["docker", "run", "-d", "--name", name,
            "-v", f"{CLAUDE_BIN}:/usr/local/bin/claude:ro",
            f"sweb.eval.x86_64.{iid}:latest", "sleep", "infinity"])
    if r.returncode != 0:
        return {"instance_id": iid, "status": "erro_container", "erro": r.stderr[-300:]}, ""
    traj = os.path.join(a.out, "trajectories", f"{iid}.jsonl")
    # arquivos nao rastreados que JA existem na imagem nao fazem parte do patch do agente
    sh(["docker", "exec", "-w", "/testbed", name, "bash", "-c",
        "git ls-files --others --exclude-standard | sort > /tmp/untracked_pre.txt"])
    cmd = ["docker", "exec", "-i", "-w", "/testbed", "-e", "ANTHROPIC_API_KEY",
           "-e", "IS_SANDBOX=1", "-e", "HOME=/tmp/agent_home", name,
           "timeout", str(a.timeout), "claude", "--bare", "-p",
           "--model", a.model, "--effort", a.effort,
           "--permission-mode", "bypassPermissions", "--allowedTools", *TOOLS,
           "--output-format", "stream-json", "--verbose",
           "--max-budget-usd", str(a.max_cost), "--no-session-persistence"]
    p = sh(cmd, input=PROMPT.format(issue=inst["problem_statement"]))
    with open(traj, "w") as f:
        f.write(p.stdout)
    result = {}
    for line in reversed(p.stdout.splitlines()):
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if d.get("type") == "result":
            result = d
            break
    # patch = edicoes em arquivos rastreados + arquivos NOVOS criados pelo agente
    # (nao rastreados agora e ausentes antes), sem lixo de execucao
    d = sh(["docker", "exec", "-w", "/testbed", name, "bash", "-c",
            "git ls-files --others --exclude-standard | sort > /tmp/untracked_post.txt; "
            "comm -13 /tmp/untracked_pre.txt /tmp/untracked_post.txt "
            "| grep -vE '__pycache__/|\\.pyc$|\\.egg-info/|\\.pytest_cache/' "
            "| xargs -r -d '\\n' git add -N -- >/dev/null 2>&1; git diff"])
    patch = d.stdout
    sh(["docker", "rm", "-f", name])
    cost = float(result.get("total_cost_usd") or 0.0)
    meta = {"instance_id": iid, "status": result.get("subtype", f"sem_resultado_rc{p.returncode}"),
            "terminal_reason": result.get("terminal_reason"), "num_turns": result.get("num_turns"),
            "custo_usd": cost, "duracao_s": round(time.time() - t0, 1),
            "patch_linhas": len(patch.splitlines()), "usage": result.get("usage")}
    return meta, patch


def worker(inst, a):
    with lock:
        if a.stop_total and state["spent"] >= a.stop_total:
            return {"instance_id": inst["instance_id"], "status": "pulada_orcamento"}, None
    meta, patch = run_issue(inst, a)
    with lock:
        state["spent"] += meta.get("custo_usd", 0.0)
        meta["acumulado_usd"] = round(state["spent"], 4)
        if patch is not None and meta["status"] != "erro_container":
            with open(os.path.join(a.out, "preds.jsonl"), "a") as f:
                f.write(json.dumps({"instance_id": meta["instance_id"],
                                    "model_name_or_path": f"claude-code_{a.model}_{a.effort}",
                                    "model_patch": patch}) + "\n")
        with open(os.path.join(a.out, "meta.jsonl"), "a") as f:
            f.write(json.dumps(meta) + "\n")
    print(json.dumps({k: meta.get(k) for k in ("instance_id", "status", "num_turns", "custo_usd",
                                              "duracao_s", "patch_linhas", "acumulado_usd")}), flush=True)
    return meta, patch


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ids", nargs="*", help="issues (padrao: lote 1 e depois lote 2)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--model", default="claude-haiku-5-5")
    ap.add_argument("--effort", default="medium")
    ap.add_argument("--max-cost", type=float, default=0.5, help="teto por issue (US$)")
    ap.add_argument("--stop-total", type=float, default=6.0, help="para de iniciar issues novas (US$)")
    ap.add_argument("--timeout", type=int, default=1200, help="segundos por issue")
    a = ap.parse_args()
    assert os.environ.get("ANTHROPIC_API_KEY"), "ANTHROPIC_API_KEY nao definida"
    os.makedirs(os.path.join(a.out, "trajectories"), exist_ok=True)
    ids = a.ids or [l.strip() for f in ("data/subset_15.txt", "data/subset_ext.txt") for l in open(f) if l.strip()]
    meta_path = os.path.join(a.out, "meta.jsonl")
    done = {json.loads(l)["instance_id"] for l in open(meta_path)} if os.path.exists(meta_path) else set()
    if os.path.exists(meta_path):  # retomada: considera o gasto anterior
        state["spent"] = sum(json.loads(l).get("custo_usd", 0.0) for l in open(meta_path))
    ds = {d["instance_id"]: d for d in load_dataset("princeton-nlp/SWE-bench_Lite", split="test")}
    todo = [ds[i] for i in ids if i not in done]
    print(f"{len(todo)} issues a rodar ({len(done)} ja feitas); gasto anterior US$ {state['spent']:.4f}", flush=True)
    with cf.ThreadPoolExecutor(max_workers=a.workers) as ex:
        list(ex.map(lambda inst: worker(inst, a), todo))
    print(f"fim. gasto total US$ {state['spent']:.4f}", flush=True)


if __name__ == "__main__":
    main()
