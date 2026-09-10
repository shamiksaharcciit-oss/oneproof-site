#!/usr/bin/env python3
"""Diff two STATUS.json snapshots. PREVIEW ARTIFACT.

    python3 whatchanged.py old-STATUS.json new-STATUS.json

Watching a repository tells you something changed. This tells you what.
"""
import json, sys

def flat(s):
    out = {}
    for k, v in s.get("artifacts", {}).items():
        out[f"artifact/{k}"] = v.get("state")
    for r in s.get("requirements", []):
        out[f"requirement/{r['id']} {r['name']}"] = r.get("state")
    for b in s.get("battery_rings", []):
        out[f"battery-ring/{b['ring']} {b['name']}"] = b.get("state")
    return out

def main(a, b):
    A = json.load(open(a, encoding="utf-8")); B = json.load(open(b, encoding="utf-8"))
    fa, fb = flat(A), flat(B)
    print(f"{A.get('as_of')}  ->  {B.get('as_of')}\n")
    moved = False
    for k in sorted(set(fa) | set(fb)):
        x, y = fa.get(k), fb.get(k)
        if x != y:
            moved = True
            print(f"  {k}\n      {x}  ->  {y}")
    ca, cb = set(A.get("commitments", [])), set(B.get("commitments", []))
    for c in sorted(ca - cb):
        moved = True
        print(f"\n  COMMITMENT REMOVED (ask why):\n      {c}")
    for c in sorted(cb - ca):
        moved = True
        print(f"\n  commitment added:\n      {c}")
    if not moved:
        print("  nothing moved")

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
