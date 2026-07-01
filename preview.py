"""
preview.py — Quick terminal preview of the top-N ranked candidates.

Usage:
    python preview.py              # Shows top 10
    python preview.py 20           # Shows top 20
    python preview.py 100          # Shows all 100
"""

import csv
import sys


def preview(n: int = 10) -> None:
    path = "submission.csv"
    with open(path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    total = len(rows)
    n = min(n, total)

    print(f"\n{'='*110}")
    print(f"  TOP {n} CANDIDATES  |  submission.csv  ({total} total ranked)")
    print(f"{'='*110}")
    print(f"{'Rank':<6} {'Score':<8} {'Candidate ID':<16} {'Reasoning'}")
    print(f"{'-'*6} {'-'*8} {'-'*16} {'-'*75}")

    for r in rows[:n]:
        rank      = r["rank"]
        score     = r["score"]
        cid       = r["candidate_id"]
        reasoning = r["reasoning"][:75] + ("..." if len(r["reasoning"]) > 75 else "")
        print(f"{rank:<6} {score:<8} {cid:<16} {reasoning}")

    print(f"{'='*110}")
    print(f"  CSV location: {path}")
    print(f"  Open in Excel or Google Sheets to view / download all columns.")
    print(f"{'='*110}\n")


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    preview(n)
