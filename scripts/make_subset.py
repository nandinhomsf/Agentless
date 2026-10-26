"""Sample a reproducible, repo-stratified subset of SWE-bench Lite-S.

Lite-S (paper Sec. 6.2) = Lite minus issues classified as "Not enough info",
"Misleading" or "Exact patch". Usage:
    python scripts/make_subset.py --n 40 --seed 42 --out data/subset_40.txt
"""

import argparse
import csv
import random
from collections import defaultdict

CSV = "classification/swebench_lite_classifications.csv"


def lite_s_ids():
    with open(CSV) as f:
        rows = list(csv.DictReader(f))
    return sorted(
        r["instance_id"]
        for r in rows
        if r["description quality"] != "Not enough info"
        and r["solution in description"] not in ("Misleading", "Exact patch")
    )


def stratified_sample(ids, n, seed):
    rng = random.Random(seed)
    by_repo = defaultdict(list)
    for i in ids:
        by_repo[i.rsplit("-", 1)[0]].append(i)

    # largest-remainder allocation so each repo keeps its share of Lite-S
    quotas = {r: n * len(v) / len(ids) for r, v in by_repo.items()}
    alloc = {r: int(q) for r, q in quotas.items()}
    for r in sorted(quotas, key=lambda r: quotas[r] - alloc[r], reverse=True)[
        : n - sum(alloc.values())
    ]:
        alloc[r] += 1

    return sorted(i for r, v in by_repo.items() for i in rng.sample(v, alloc[r]))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--n", type=int, default=40)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--out", default="data/subset_40.txt")
    args = p.parse_args()

    ids = lite_s_ids()
    subset = stratified_sample(ids, args.n, args.seed)
    with open(args.out, "w") as f:
        f.write("\n".join(subset) + "\n")
    print(f"Lite-S: {len(ids)} issues -> subset of {len(subset)} saved to {args.out}")
