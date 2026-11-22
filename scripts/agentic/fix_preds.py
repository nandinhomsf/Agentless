#!/usr/bin/env python3
"""Remove dos patches do agente os arquivos que JA EXISTIAM nao rastreados na imagem.

O runner extrai o patch com `git add -A -N . && git diff`, o que inclui arquivos
nao rastreados que ja estavam na imagem (por exemplo `build/lib/...` de uma
instalacao antiga do requests) como se o agente os tivesse criado. Aqui, para cada
issue, lista-se os arquivos nao rastreados de uma imagem NOVA e eliminam-se do patch
as secoes desses arquivos (e lixo de execucao: __pycache__, .pyc, .egg-info,
.pytest_cache). As edicoes do agente em arquivos rastreados e os arquivos que ele
realmente criou sao mantidos.

    .venv/bin/python scripts/agentic/fix_preds.py results/haiku_agentic/preds.jsonl \
        results/haiku_agentic/preds_fixed.jsonl
"""

import json
import re
import subprocess
import sys

JUNK = re.compile(r"(__pycache__/|\.pyc$|\.egg-info/|\.pytest_cache/)")


def untracked(iid):
    r = subprocess.run(["docker", "run", "--rm", f"sweb.eval.x86_64.{iid}:latest", "bash", "-c",
                        "cd /testbed && git ls-files --others --exclude-standard"],
                       capture_output=True, text=True)
    return set(r.stdout.split("\n")) - {""}


def clean(patch, pre):
    parts = re.split(r"(?m)^(?=diff --git a/)", patch)
    kept, dropped = [], []
    for part in parts:
        m = re.match(r"diff --git a/(\S+) b/", part)
        if m and (m.group(1) in pre or JUNK.search(m.group(1))):
            dropped.append(m.group(1))
        else:
            kept.append(part)
    out = "".join(kept)
    return (out if out.endswith("\n") or not out else out + "\n"), dropped


def main(src, dst):
    changed = 0
    with open(dst, "w") as f:
        for line in open(src):
            d = json.loads(line)
            new, dropped = clean(d["model_patch"], untracked(d["instance_id"]))
            if dropped:
                changed += 1
                print(f"{d['instance_id']}: {len(dropped)} arquivos removidos; "
                      f"patch {len(d['model_patch'].splitlines())} -> {len(new.splitlines())} linhas")
            d["model_patch"] = new
            f.write(json.dumps(d) + "\n")
    print(f"patches alterados: {changed}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
