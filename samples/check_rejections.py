#!/usr/bin/env python3
"""Runs the rejection vectors. Every one must be REFUSED. PREVIEW ARTIFACT."""
import json, sys, verify
idx = json.loads(open("rejection/INDEX.json", "rb").read().decode("utf-8"))
escaped = []
for v in idx["vectors"]:
    p = v["file"]; raw = open(p, "rb").read(); r = verify.R()
    try:
        verify.check_receipt(json.loads(raw.decode("utf-8")), raw, p, r)
    except Exception as e:
        r.add("FAIL", f"{p}: parse", str(e))
    if r.failed:
        print(f"[REFUSED] {p}\n           reason required: {v['must_fail_on']}")
    else:
        print(f"[ACCEPTED - VECTOR ESCAPED] {p}"); escaped.append(p)
print(f"\n{len(idx['vectors']) - len(escaped)}/{len(idx['vectors'])} vectors refused"
      + ("" if not escaped else f"  ESCAPED: {escaped}"))
sys.exit(1 if escaped else 0)
