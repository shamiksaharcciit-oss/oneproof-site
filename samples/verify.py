#!/usr/bin/env python3
"""Reference verifier for stage-receipt/0.0-preview. PREVIEW ARTIFACT.

Checks a chain offline, with no network, no key, no account, and no trust in
whoever produced it. Every outcome is PASS, FAIL, or NOT-RUN-with-reason -
never silence.

    python3 verify.py MANIFEST.json
"""
import hashlib, json, sys
from canonicalize import canonicalize

REQUIRED = ["format","run_id","stage","prev","time","coverage","emission",
            "anchor","instrument","inputs","outputs","assertions","outcome"]
TRUST = {"operator-authored","model-generated","externally-sourced"}
OUTCOMES = {"ok","refused","error"}

class R:
    def __init__(self): self.rows=[]; self.failed=False
    def add(self,res,name,detail=""):
        self.rows.append((res,name,detail))
        if res=="FAIL": self.failed=True
    def report(self):
        for res,name,detail in self.rows:
            print(f"[{res:7}] {name}" + (f" -- {detail}" if detail else ""))
        n=sum(1 for r,_,_ in self.rows if r=="PASS")
        f=sum(1 for r,_,_ in self.rows if r=="FAIL")
        s=sum(1 for r,_,_ in self.rows if r=="NOT-RUN")
        print(f"\n{n} pass, {f} fail, {s} not-run  ->  {'FAIL' if self.failed else 'PASS'}")
        return 1 if self.failed else 0

def check_receipt(obj, raw, path, r):
    canon = None
    try:
        canon = canonicalize(obj)
    except ValueError as e:
        r.add("FAIL", f"{path}: canonical form", str(e)); return None
    r.add("PASS" if canon==raw else "FAIL", f"{path}: bytes are canonical",
          "" if canon==raw else "file bytes differ from the canonical serialization")
    for k in REQUIRED:
        r.add("PASS" if k in obj else "FAIL", f"{path}: required field '{k}'")
    t = obj.get("time",{})
    for k in ("started","ended"):
        v = t.get(k,"")
        ok = isinstance(v,str) and (v.endswith("Z") or v[-6] in "+-")
        r.add("PASS" if ok else "FAIL", f"{path}: time.{k} carries its zone", "" if ok else repr(v))
    inst = obj.get("instrument",{})
    named = bool(inst.get("id")) and bool(inst.get("manifest_digest"))
    r.add("PASS" if named else "FAIL", f"{path}: instrument is named and pinned",
          "" if named else "a record whose instrument cannot be named is invalid")
    for side in ("inputs","outputs"):
        for item in obj.get(side,[]):
            tc = item.get("trust_class")
            r.add("PASS" if tc in TRUST else "FAIL",
                  f"{path}: {side}/{item.get('name','?')} declares a trust class", "" if tc in TRUST else repr(tc))
    a = obj.get("assertions",{})
    if a:
        r.add("PASS" if "constants" in a else "FAIL", f"{path}: assertions name their constants",
              "" if "constants" in a else "a relation that holds only under an unstated constant tests the constant")
    oc = obj.get("outcome",{}).get("class")
    r.add("PASS" if oc in OUTCOMES else "FAIL", f"{path}: outcome class is one of {sorted(OUTCOMES)}", "" if oc in OUTCOMES else repr(oc))
    if oc=="error":
        e=obj["outcome"]
        have=all(k in e for k in ("status","body","origin"))
        r.add("PASS" if have else "FAIL", f"{path}: error carries status, body and origin",
              "" if have else "an HTTP error without its body is a status code wearing an explanation")
    cov = obj.get("coverage",{})
    comp = cov.get("completeness")
    r.add("PASS" if comp in {"complete","incomplete"} else "FAIL",
          f"{path}: coverage declares completeness", "" if comp in {"complete","incomplete"} else repr(comp))
    if comp=="complete":
        missing=set(cov.get("declared_stages",[]))-set(cov.get("emitting_stages",[]))
        r.add("PASS" if not missing else "FAIL", f"{path}: 'complete' is consistent with the stage lists",
              "" if not missing else f"declared but not emitting: {sorted(missing)}")
    anc = obj.get("anchor",{})
    st = anc.get("state")
    r.add("PASS" if st in {"anchored","unanchored"} else "FAIL",
          f"{path}: anchor state is declared, not absent", "" if st in {"anchored","unanchored"} else repr(st))
    if st=="unanchored":
        r.add("NOT-RUN", f"{path}: originality",
              "record is declared unanchored; this verifier can establish consistency, not originality")
    return hashlib.sha256(raw).hexdigest()

def main(manifest_path):
    r=R()
    mraw=open(manifest_path,"rb").read()
    man=json.loads(mraw.decode("utf-8"))
    prev_expected=None
    for entry in man["chain"]:
        p=entry["file"]
        raw=open(p,"rb").read()
        obj=json.loads(raw.decode("utf-8"))
        dg=check_receipt(obj,raw,p,r)
        if dg is None: continue
        r.add("PASS" if "sha256:"+dg==entry["digest"] else "FAIL", f"{p}: digest matches the manifest")
        got=obj.get("prev")
        r.add("PASS" if got==prev_expected else "FAIL", f"{p}: chain link",
              "" if got==prev_expected else f"expected {prev_expected}, found {got}")
        prev_expected="sha256:"+dg
    r.add("PASS" if man.get("chain_head")==prev_expected else "FAIL","manifest: chain head matches the last receipt")
    return r.report()

if __name__=="__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv)>1 else "MANIFEST.json"))
