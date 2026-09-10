import json, copy, hashlib, os
from canonicalize import canonicalize
base=json.loads(open("receipts/01-retrieve.json","rb").read().decode("utf-8"))

def w(name, mut, why):
    o=copy.deepcopy(base); mut(o)
    try: raw=canonicalize(o)
    except ValueError:
        raw=json.dumps(o,sort_keys=True,ensure_ascii=False,separators=(",",":")).encode("utf-8")
    open(f"rejection/{name}.json","wb").write(raw)
    return {"file":f"rejection/{name}.json","must_fail_on":why}

cases=[]
cases.append(w("R01-json-number", lambda o:o["assertions"].__setitem__("candidate_count",1500),
  "a JSON number where a decimal string is required ('500.00' and '500' must stay distinct)"))
cases.append(w("R02-null-instrument", lambda o:o["instrument"].__setitem__("manifest_digest",""),
  "instrument cannot be named or pinned; refusal is required, not a blank field"))
cases.append(w("R03-timestamp-no-zone", lambda o:o["time"].__setitem__("started","2026-09-11T09:14:02.118"),
  "a timestamp without its zone is half a timestamp"))
cases.append(w("R04-missing-constants", lambda o:o["assertions"].pop("constants"),
  "an assertion that does not name its transform constants"))
cases.append(w("R05-untrusted-class", lambda o:o["inputs"][0].__setitem__("trust_class","unknown"),
  "an input with no declared trust class"))
cases.append(w("R06-error-without-body", lambda o:o.__setitem__("outcome",{"class":"error","status":"403"}),
  "an HTTP error without its body is a status code wearing an explanation"))
cases.append(w("R07-coverage-lie", lambda o:o["coverage"].__setitem__("emitting_stages",["retrieve","rerank"]),
  "'complete' asserted while declared stages are missing from the emitting list"))
cases.append(w("R08-anchor-absent", lambda o:o.pop("anchor"),
  "anchor state absent rather than declared; unanchored is a state, not a silence"))
cases.append(w("R09-self-digest", lambda o:o.__setitem__("receipt_digest","sha256:00"),
  "a record may not contain the proof of its own final state"))

def r10():
    o=copy.deepcopy(base)
    raw=json.dumps(o,sort_keys=True,ensure_ascii=False,indent=2).encode("utf-8")
    open("rejection/R10-not-canonical.json","wb").write(raw)
    return {"file":"rejection/R10-not-canonical.json","must_fail_on":"pretty-printed; file bytes are not the canonical serialization"}
cases.append(r10())

open("rejection/INDEX.json","wb").write(canonicalize(
  {"format":"stage-receipt-rejection-vectors/0.0-preview",
   "note":"Each file MUST be refused by a conforming verifier, for the stated reason. A format with no rejection vectors has not specified anything.",
   "vectors":cases}))
print(len(cases),"rejection vectors written")
