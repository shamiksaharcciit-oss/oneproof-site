import json, hashlib, os
from canonicalize import canonicalize, digest

RUN = "run-2026-09-11-0001"
COV = {
  "declared_stages": ["retrieve","rerank","generate","verify"],
  "emitting_stages": ["retrieve","rerank","generate","verify"],
  "boundaries": [],
  "completeness": "complete"
}
EMIT = {"policy":"fail-closed","gaps":[]}
ANCH = {"state":"unanchored","reason":"preview sample; epoch anchoring is a declared requirement and is not implemented"}

def base(idx, stage, prev):
    return {
      "format":"stage-receipt/0.0-preview",
      "run_id":RUN,
      "stage":{"index":str(idx),"name":stage},
      "prev":prev,
      "time":{"started":"2026-09-11T09:14:02.118+02:00","ended":"2026-09-11T09:14:02.774+02:00"},
      "coverage":COV,
      "emission":EMIT,
      "anchor":ANCH,
    }

recs=[]
prev=None

# 1 retrieve
r=base(1,"retrieve",prev)
r["instrument"]={"kind":"retriever","id":"bm25+dense-hybrid","version":"1.4.0",
  "manifest_digest":"sha256:6f1b1c0d4a2e9d7c3b58ae0f21d4c6b98e7a5f30c1d2e4b6a8093f5c7e1d2b4a",
  "config_digest":"sha256:2a7d9e4b1c8f0356ae2d4b6c8f1a3e5d7b9c0f2a4e6d8b0c2f4a6e8d0b2c4f6a",
  "rederivable":"true"}
r["inputs"]=[{"name":"question","media_type":"text/plain",
  "digest":"sha256:9c56cc51b374c3ba189210d5b6d4bf57790d351c96c47c02190ecf1e430635ab",
  "bytes":"57","trust_class":"externally-sourced"}]
r["outputs"]=[{"name":"candidates","media_type":"application/json",
  "digest":"sha256:0d5c1a8f3e7b2946d0c8a1f5e39b7d2c460a8e1f3b5d7c9a0e2f4b6d8c0a2e4f",
  "bytes":"184213","trust_class":"operator-authored"}]
r["assertions"]={"candidate_count":"1500","corpus_manifest":"sha256:b3d5f7a9c1e3d5b7f9a1c3e5d7b9f1a3c5e7d9b1f3a5c7e9d1b3f5a7c9e1d3b5",
  "constants":{"tokenizer":"unicode-nfkc-lower","join":"blank-line","top_k":"1500"}}
r["outcome"]={"class":"ok"}
recs.append(r)

# 2 rerank
d=digest(r); prev="sha256:"+d
r=base(2,"rerank",prev)
r["instrument"]={"kind":"cross-encoder","id":"reranker-a","version":"pinned",
  "manifest_digest":"sha256:233902d2f4a6c8e0b2d4f6a8c0e2b4d6f8a0c2e4b6d8f0a2c4e6b8d0f2a4c6e8",
  "config_digest":"sha256:5e7c9a1f3d5b7e9c1a3f5d7b9e1c3a5f7d9b1e3c5a7f9d1b3e5c7a9f1d3b5e7c",
  "rederivable":"true"}
r["inputs"]=[{"name":"candidates","media_type":"application/json",
  "digest":"sha256:0d5c1a8f3e7b2946d0c8a1f5e39b7d2c460a8e1f3b5d7c9a0e2f4b6d8c0a2e4f",
  "bytes":"184213","trust_class":"operator-authored"}]
r["outputs"]=[{"name":"ranked","media_type":"application/json",
  "digest":"sha256:7a9c1e3f5b7d9a1c3e5f7b9d1a3c5e7f9b1d3a5c7e9f1b3d5a7c9e1f3b5d7a9c",
  "bytes":"41120","trust_class":"operator-authored"}]
r["assertions"]={"scored_pairs":"1500","chance_floor":"3.88",
  "constants":{"batch_size":"32","truncation":"auto","max_input_tokens":"512","score_order":"descending"}}
r["outcome"]={"class":"ok"}
recs.append(r)

# 3 generate - refusal by contract
d=digest(r); prev="sha256:"+d
r=base(3,"generate",prev)
r["instrument"]={"kind":"generator","id":"instrument-b","version":"pinned",
  "manifest_digest":"sha256:c1e3a5f7d9b1c3e5a7f9d1b3c5e7a9f1d3b5c7e9a1f3d5b7c9e1a3f5d7b9c1e3",
  "config_digest":"sha256:8d0f2a4c6e8b0d2f4a6c8e0b2d4f6a8c0e2b4d6f8a0c2e4b6d8f0a2c4e6b8d0f",
  "rederivable":"false",
  "rederivable_note":"generation is not bit-reproducible; the instrument is declared, the output is recorded, replay is not promised"}
r["inputs"]=[{"name":"ranked","media_type":"application/json",
  "digest":"sha256:7a9c1e3f5b7d9a1c3e5f7b9d1a3c5e7f9b1d3a5c7e9f1b3d5a7c9e1f3b5d7a9c",
  "bytes":"41120","trust_class":"operator-authored"},
  {"name":"evidence_passages","media_type":"text/plain",
  "digest":"sha256:e5c7a9f1d3b5e7c9a1f3d5b7e9c1a3f5d7b9e1c3a5f7d9b1e3c5a7f9d1b3e5c7",
  "bytes":"12904","trust_class":"externally-sourced"}]
r["outputs"]=[]
r["assertions"]={"claims":[],"constants":{"prompt_digest":"sha256:3b5d7f9a1c3e5b7d9f1a3c5e7b9d1f3a5c7e9b1d3f5a7c9e1b3d5f7a9c1e3b5d"}}
r["outcome"]={"class":"refused",
  "reason":"contract: no claim survived evidence binding",
  "detail":"the generator produced no claim that could be bound to a retrieved passage; a refusal is recorded, not an empty answer"}
recs.append(r)

# 4 verify
d=digest(r); prev="sha256:"+d
r=base(4,"verify",prev)
r["instrument"]={"kind":"verifier","id":"claim-binder","version":"0.3.1",
  "manifest_digest":"sha256:a1c3e5b7d9f1a3c5e7b9d1f3a5c7e9b1d3f5a7c9e1b3d5f7a9c1e3b5d7f9a1c3",
  "config_digest":"sha256:f3a5c7e9b1d3f5a7c9e1b3d5f7a9c1e3b5d7f9a1c3e5b7d9f1a3c5e7b9d1f3a5",
  "rederivable":"true"}
r["inputs"]=[]
r["outputs"]=[]
r["assertions"]={"claims_examined":"0","claims_supported":"0","claims_contradicted":"0",
  "derivation":"counts recomputed from stage 3 outcome; zero claims were emitted, therefore zero were examined",
  "constants":{"support_threshold":"0.30","contradiction_threshold":"0.60"}}
r["outcome"]={"class":"ok","note":"nothing to verify is a result, not an absence"}
recs.append(r)

os.makedirs("receipts",exist_ok=True)
chain=[]
for i,r in enumerate(recs,1):
    canon=canonicalize(r)
    dg=hashlib.sha256(canon).hexdigest()
    fn=f"receipts/{i:02d}-{r['stage']['name']}.json"
    open(fn,"wb").write(canon)
    chain.append({"index":str(i),"stage":r["stage"]["name"],"file":fn,"digest":"sha256:"+dg})

man={"format":"stage-receipt-chain/0.0-preview","run_id":RUN,
 "note":"PREVIEW. Digests are over each file's exact bytes. Verify with: sha256sum receipts/*.json",
 "chain":chain,
 "chain_head":chain[-1]["digest"],
 "anchor":ANCH}
open("MANIFEST.json","wb").write(canonicalize(man))
print("chain head:",chain[-1]["digest"])
for c in chain: print(" ",c["index"],c["stage"],c["digest"])
