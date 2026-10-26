"""Oracle upper bound: evaluate every distinct candidate patch of a run.

Writes one predictions file per "slot" k (the k-th distinct patch of each
issue), so the SWE-bench harness can evaluate them, and after evaluation reports
how many issues have at least one resolving candidate (pass@all, as in the
paper's Fig. 6 "126 / 42%").

    python scripts/oracle_eval.py prepare --run results/flashlite_reduced
    (evaluate each oracle/slot_k.jsonl with the harness, run_id oracle_<run>_k)
    python scripts/oracle_eval.py report --run results/flashlite_reduced
"""

import argparse
import glob
import json
import os


def distinct_patches(run):
    by_issue = {}
    for fp in sorted(glob.glob(f"{run}/repair_sample_*/output_*_processed.jsonl")):
        for line in open(fp):
            d = json.loads(line)
            patch = (d.get("model_patch") or "").strip()
            if patch and patch not in by_issue.setdefault(d["instance_id"], []):
                by_issue[d["instance_id"]].append(patch)
    return by_issue


def prepare(run):
    os.makedirs(f"{run}/oracle", exist_ok=True)
    by_issue = distinct_patches(run)
    slots = max(map(len, by_issue.values()))
    for k in range(slots):
        with open(f"{run}/oracle/slot_{k}.jsonl", "w") as f:
            for i, patches in by_issue.items():
                if k < len(patches):
                    f.write(json.dumps({"model_name_or_path": f"oracle_slot_{k}",
                                        "instance_id": i, "model_patch": patches[k] + "\n"}) + "\n")
    print(slots)


def report(run, ids_file):
    ids = [l.strip() for l in open(ids_file) if l.strip()]
    tag = os.path.basename(run.rstrip("/"))
    resolved = {}
    for fp in glob.glob(f"logs/run_evaluation/oracle_{tag}_[0-9]*/oracle_slot_*/*/report.json"):
        for i, r in json.load(open(fp)).items():
            resolved.setdefault(i, False)
            resolved[i] |= r.get("resolved", False)
    selected = set(json.load(open(f"{run}/eval_report.json"))["resolved_ids"])
    oracle = {i for i in ids if resolved.get(i)}
    print(f"{tag}: selecionado {len(selected & set(ids))}/{len(ids)} | "
          f"oráculo (algum candidato resolve) {len(oracle)}/{len(ids)} | "
          f"avaliadas {sum(i in resolved for i in ids)}/{len(ids)}")
    print("  perdidas na seleção:", sorted(oracle - selected))
    return oracle, selected


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("action", choices=["prepare", "report"])
    p.add_argument("--run", required=True)
    p.add_argument("--ids")
    a = p.parse_args()
    prepare(a.run) if a.action == "prepare" else report(a.run, a.ids)
