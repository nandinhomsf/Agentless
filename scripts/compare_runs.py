"""Compare a replication run against the published Agentless run on the same subset.

Reports, per run, the % of issues whose ground-truth (gold patch) files are
covered after each localization stage (paper Table 2, file granularity), the
% of final patches touching the right file / lines (paper Table 1), and the
resolve rate when an evaluation report is available.

    python scripts/compare_runs.py --run results/replication \
        --eval_report agentless_replication.json
"""

import argparse
import json
import os
import re

from datasets import load_dataset

PAPER = "data/paper_results"


def load_jsonl(path):
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        return {d["instance_id"]: d for d in map(json.loads, f)}


def patch_locations(patch):
    """{file: set(original-side line numbers)} touched by a unified diff."""
    locs, file, line = {}, None, 0
    for row in (patch or "").splitlines():
        if row.startswith("--- "):
            continue
        if row.startswith("+++ "):
            file = row[4:].removeprefix("b/").strip()
            locs.setdefault(file, set())
        elif m := re.match(r"@@ -(\d+)", row):
            line = int(m[1])
        elif file is None:
            continue
        elif row.startswith("-"):
            locs[file].add(line)
            line += 1
        elif row.startswith("+"):
            locs[file].add(max(line - 1, 1))  # insertion: anchor on previous line
        else:
            line += 1
    return locs


def files_cover(found, gold):
    return set(gold) <= set(found or [])


def stage_files(run, stage, ids):
    """Files kept by a localization stage, per instance."""
    data = load_jsonl(f"{run}/{stage}")
    out = {}
    for i in ids:
        d = data.get(i)
        if d is None:
            continue
        if stage.startswith("related_elements"):
            rel = d.get("found_related_locs") or {}
            out[i] = {f for f, v in rel.items() if any(v)} if isinstance(rel, dict) else set()
        else:
            out[i] = set(d.get("found_files") or [])
    return out


def report(run, ids, gold, eval_resolved):
    n = len(ids)
    pct = lambda k: f"{k:>3}/{n} ({k / n:6.1%})"
    print(f"\n### {run}")
    for label, stage in [
        ("File-level LLM", "file_level/loc_outputs.jsonl"),
        ("File-level embedding", "retrievel_embedding/retrieve_locs.jsonl"),
        ("File-level combined", "file_level_combined/combined_locs.jsonl"),
        ("Related elements", "related_elements/loc_outputs.jsonl"),
    ]:
        found = stage_files(run, stage, ids)
        if found:
            k = sum(files_cover(found.get(i), gold[i]) for i in ids)
            print(f"  {label:<24} contains GT file: {pct(k)}  [{len(found)} issues with output]")

    preds = load_jsonl(f"{run}/all_preds.jsonl")
    if preds:
        f_ok = l_ok = empty = 0
        for i in ids:
            p = patch_locations(preds.get(i, {}).get("model_patch"))
            empty += not p
            f_ok += files_cover(p, gold[i])
            l_ok += all(lines <= p.get(f, set()) for f, lines in gold[i].items())
        print(f"  Final patch correct file:           {pct(f_ok)}")
        print(f"  Final patch correct lines:          {pct(l_ok)}")
        print(f"  Empty final patches:                {pct(empty)}")
    if eval_resolved is not None:
        print(f"  Resolved:                           {pct(sum(i in eval_resolved for i in ids))}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--run", default="results/replication")
    p.add_argument("--ids", default="data/subset_40.txt")
    p.add_argument("--eval_report", help="swebench harness report json for --run")
    args = p.parse_args()

    ids = [l.strip() for l in open(args.ids) if l.strip()]
    ds = load_dataset("princeton-nlp/SWE-bench_Lite", split="test")
    gold = {d["instance_id"]: patch_locations(d["patch"]) for d in ds if d["instance_id"] in ids}

    paper_resolved = set(json.load(open(f"{PAPER}/official_results.json"))["resolved"])
    report(PAPER, ids, gold, paper_resolved)

    run_resolved = None
    if args.eval_report and os.path.exists(args.eval_report):
        run_resolved = set(json.load(open(args.eval_report))["resolved_ids"])
    report(args.run, ids, gold, run_resolved)
