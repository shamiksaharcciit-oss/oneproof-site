# onetrace 0.1.2: developer manual

This manual takes you from knowing nothing about onetrace to recording, verifying and comparing your own pipeline's runs. Every example in it was run against the `onetrace 0.1.1` release files, installed into a fresh virtual environment. The verifier summaries in sections 2 and 8 were re-measured with the verifier in this repository, which adds one `receipt format` row per receipt (section 14).

---

## 1. What onetrace is, in one page

When a pipeline runs, whether it's a RAG system, a document processor or an agent, you usually end up with an output and maybe some logs. Later, when someone asks what exactly produced this answer, and whether anything changed since last week, logs are hard to trust and hard to compare.

onetrace makes the pipeline write a **record** as it runs:

- **one receipt per stage** (a JSON file) that says:
  - what the stage read, identified by content digest (sha256);
  - what it wrote, again by digest;
  - which tool did the work (the *instrument*) and exactly how it was configured;
  - how the stage ended: `ok`, `refused` or `error`;
  - its start and end times;
- **a manifest** that chains the receipts together. Each receipt's digest is recorded in order, ending in a **chain head**. Change, remove or reorder any receipt and the chain no longer matches.

Anyone can then check the record, and compare two runs, with tools that don't trust your code:

| Tool | What it answers |
|---|---|
| `onetrace-verify <run>` | Is this record self-consistent and unbroken? |
| `onetrace diff A B` | Stage by stage, where do two runs differ? |
| `onetrace localize A [B]` | Where did things first go wrong: the first unclean stage in one run, or the first difference between two runs, and its cause? |
| `onetrace reproduce <run>` | If I re-run the recorded stages from their recorded inputs, do I get the same outputs? |

### What onetrace does **not** do (read this before relying on it)

- **It does not say your output is true or correct.** It records what happened and lets others check that record.
- **Records in 0.1.1 are hash-chained, not signed.** Nobody's key signs a receipt. The chain proves the record hasn't been altered *relative to its own chain head*. It does **not** prove who wrote it. If you need to prove authorship or when the record existed, keep the chain head somewhere independent, such as a ticket, an email or a database you don't control. To show the record existed by a given time, anchor its chain head after the run closes (section 15).
- **`onetrace-verify` checks your output files under `artifacts/` too, when it can recognise their layout.** If the run was written by this SDK (0.1.x), the verifier finds `artifacts/<stage>/<output>` for each receipt's own outputs and reports a `FAIL` naming any that's missing or changed. If there's no `artifacts/` folder, or its layout isn't one the verifier recognises, it reports one `NOT-RUN` row and checks no files. **The summary line can still say `PASS` in that case**, because `PASS` is about the record. If you need the files checked, run `onetrace-verify --require-artifacts`, which turns that `NOT-RUN` into a `FAIL` (section 8.3).
- **The verifier reports "originality: not-run" on every receipt.** That's expected: a receipt can't show when it was written, so on its own the record establishes consistency, not originality. An anchor (section 15) gets a row of its own beside it, which shows the record existed by the time its source attests; not when the run happened.
- The format is **version 0**. It may still change before version 1.

---

## 2. Install

Requirements: **Python 3.10 or newer**. Use a virtual environment.

```bash
python -m venv .venv
# Windows PowerShell:  .\.venv\Scripts\Activate.ps1
# macOS / Linux:       source .venv/bin/activate
pip install onetrace
```

This installs two packages:

| Package | Import / command | Role |
|---|---|---|
| `onetrace` | `import onetrace`, command `onetrace` | The SDK: recording, plus the `diff` / `localize` / `reproduce` commands |
| `onetrace-verify` | command `onetrace-verify` | The reference verifier. It uses only the standard library, needs no network, and is installed automatically. |

Check the install:

```bash
python -c "import onetrace; print(onetrace.__version__)"   # 0.1.2
```

To pin exactly what was published, take each file's sha256 from the **Download files** page of the project on PyPI and put it in a requirements file:

```
onetrace==0.1.2         --hash=sha256:<from the PyPI page>
onetrace-verify==0.1.2  --hash=sha256:<from the PyPI page>
```

Then install with `pip install --require-hashes -r requirements.txt`. The hashes can't be printed here, because this manual ships inside one of the files they describe.

Optional extras pin the framework versions the examples were built against:
- `pip install "onetrace[langchain]"`
- `pip install "onetrace[llamaindex]"`
- `pip install "onetrace[langflow]"`

They only install those frameworks. The integration pattern itself is plain Python (section 9).

---

## 3. Five-minute quickstart

Save as `demo.py`:

```python
import json, sys
from pathlib import Path
from onetrace.emit import Instrument, Recorder

QUESTION = "What does the warranty cover?"
CORPUS = [
    {"id": "p1", "text": "The warranty covers manufacturing defects for twelve months."},
    {"id": "p2", "text": "Shipping delays are handled by the logistics partner."},
]

def main(out_dir, run_id):
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    corpus_path = out / "corpus.json"
    corpus_path.write_text(json.dumps(CORPUS), encoding="utf-8")

    rec = Recorder(out_dir, run_id=run_id,
                   declared_stages=["retrieve", "answer"],
                   manifest=Path(__file__),          # this file's bytes identify the code
                   policy="fail-closed",
                   anchor_reason="not anchored")

    cfg = {"tokenizer": "lower-split", "top_k": 1}   # an int is fine; see section 5.3

    @rec.stage("retrieve", Instrument("word-overlap", "retriever", "1.0.0", cfg))
    def retrieve(ctx):
        corpus = json.loads(ctx.read_external(corpus_path, "application/json",
                                              name="corpus", trust_class="operator-authored"))
        q = set(QUESTION.lower().split())
        best = max(corpus, key=lambda p: len(q & set(p["text"].lower().split())))
        for k, v in cfg.items():
            ctx.constant(k, v)
        ctx.assertion("candidate_count", len(corpus))
        return ctx.write_json("retrieved.json", best)

    @rec.stage("answer", Instrument("extractive", "answerer", "1.0.0", {"method": "extractive"}))
    def answer(ctx, retrieved_artifact):
        hit = ctx.read_json(retrieved_artifact)
        ctx.constant("method", "extractive")
        ctx.assertion("source", hit["id"])
        return ctx.write_json("answer.json", {"answer": hit["text"], "cited": hit["id"]})

    answer(retrieve())
    rec.close()

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
```

Run it twice, verify one run, and compare the two:

```bash
python demo.py run_a run-a
python demo.py run_b run-b
onetrace-verify run_a          # ... "56 pass, 0 fail, 2 not-run  ->  PASS"
onetrace diff run_a run_b      # "diff: identical", exit 0
```

---

## 4. Core concepts

| Term | Meaning |
|---|---|
| **Run** | One execution of your pipeline, written to one folder. A run folder is **write-once**: onetrace refuses to write into a folder that already holds a run. |
| **Stage** | One named step. You declare the stage names, in order, when the run starts, and the stages must emit in that order. |
| **Receipt** | The JSON record of one stage: `receipts/NN-<stage>.json`. |
| **Manifest** | `MANIFEST.json`: the ordered chain of receipt digests and the **chain head**. It is rewritten after every receipt, and is the run's "last word". |
| **Instrument** | The tool a stage used: id, kind, a pinned version, and its configuration. The configuration is digested, so a config change is always visible. |
| **Artifact** | A file a stage wrote through onetrace. It's stored under `artifacts/NN-<stage>/` and its digest goes in the receipt; `onetrace-verify` checks it there (section 8). |
| **Constant / assertion** | Constants are the settings the stage ran under. Assertions are facts the stage states about its work (a count, a chosen id). Each takes a string, or a Python int recorded as its own decimal string (section 5.6). |
| **Trust class** | Where data came from: `operator-authored`, `model-generated` or `externally-sourced`. `secret` is refused, so secrets never enter a record. |
| **Policy** | `fail-closed` or `fail-open`: what happens when a receipt can't be written or verification fails (section 5.8). |
| **Coverage** | Which declared stages have emitted. `complete` only when every declared stage has emitted and no boundary or gap stands. |
| **Boundary / gap** | An honest statement that the record doesn't see past a point (a boundary), or that a receipt is missing (a gap). Either makes coverage `incomplete`. |

---

## 5. Integrating onetrace into your code, step by step

### 5.1 Create one `Recorder` per run

```python
from pathlib import Path
from onetrace.emit import Recorder

rec = Recorder(
    "runs/run-0001",              # out_dir: a NEW folder for this run
    declared_stages=["load", "chunk", "embed", "retrieve", "answer"],
    manifest=Path(__file__),           # the file whose bytes identify your pipeline code
    policy="fail-closed",              # or "fail-open"
    anchor_reason="not anchored",      # optional: why the receipts are unanchored (section 15 anchors a closed run)
    run_id=None,                       # optional; generated if omitted
)
```

| Argument | Required | Notes |
|---|---|---|
| `out_dir` | yes | Created if missing. It must not already contain a run. One process per folder: a lock file enforces this. |
| `declared_stages` | yes | A non-empty list of distinct names, in execution order. |
| `manifest` | yes | A path to a file, usually your pipeline's main module. Its sha256 is recorded as every instrument's `manifest_digest`. `reproduce` uses it to confirm it's re-running the same code. |
| `policy` | yes | `"fail-closed"` or `"fail-open"`. Anything else is refused. |
| `run_id` | no | Your id. If omitted, one is generated: a UTC timestamp plus 8 random hex characters, which sorts chronologically. |
| `anchor_reason` | no | A free-text note, recorded with `anchor.state = "unanchored"`. |
| `instruments` | no | Declare instruments up front, keyed by stage name (5.3). |
| `declared_edges` / `topology` | no | For branching pipelines (section 6). |
| `boundaries` | no | Boundaries known at start (5.9). |
| `verify_pin` | no | Run the verifier automatically on `close()` (5.10). |
| `max_run_bytes` | no | A hard size limit for the run (5.11). |

### 5.2 Wrap each step as a stage

Use the decorator. onetrace passes a **context** (`ctx`) as the first argument. Your other arguments pass through unchanged, and your return value comes back to the caller.

```python
from onetrace.emit import Instrument

@rec.stage("chunk", Instrument("recursive-splitter", "chunker", "2.3.1",
                               {"chunk_size": 900, "overlap": 0}))
def chunk(ctx, doc_artifact):
    text = ctx.read(doc_artifact).decode("utf-8")
    ctx.constant("chunk_size", 900)
    ctx.constant("overlap", 0)
    chunks = split(text, 900)
    ctx.assertion("chunk_count", len(chunks))
    return ctx.write_json("chunks.json", chunks)

chunks_artifact = chunk(doc_artifact)
```

**Stages must run in the declared order.** Calling `answer` before `retrieve` raises `EmissionRefused: stage 'answer' is not the next declared stage (expected retrieve)`.

The same stage can be written without a decorator: `rec.run_stage("chunk", instrument, fn, *args)`.

### 5.3 Describe the instrument honestly

```python
Instrument(id, kind, version, config, rederivable="true", rederivable_note=None)
```

- `id`: your name for the tool, for example `"gpt-4o-mini"` or `"recursive-splitter"`.
- `kind`: its role, for example `"retriever"`, `"llm"` or `"chunker"`.
- `version`: **must pin an exact build.** `""`, `latest`, `current`, `head`, `main` and `master` are refused. Use the library version (`importlib.metadata.version("langchain-core")`) or a model snapshot id.
- `config`: a dict of the settings that affect the output. A **string** is always fine. A Python **`int`** (never `bool`) is accepted too, and recorded as its own decimal string — `3` and `"3"` produce the same `config_digest`, so you don't have to remember to stringify every number by hand. A **float is refused**, with a message explaining why: its digest is not stable across languages (`0.2` prints differently across implementations; `"0.2"` doesn't). Nested dicts and lists follow the same rule at every level.
- `rederivable="false"`: set this when re-running can't reproduce the output, for example a sampled LLM call. Explain why in `rederivable_note`.

If you don't want to repeat instruments at every call site, declare them once:

```python
rec = Recorder(..., instruments={"chunk": Instrument(...), "answer": Instrument(...)})

@rec.stage("chunk")          # no instrument here; it comes from the declaration
def chunk(ctx, ...): ...
```

A run that declares instruments refuses a stage that brings its own, or one that has none declared.

### 5.4 Inputs: everything a stage reads goes through `ctx`

| Call | Use it for | Returns |
|---|---|---|
| `ctx.read_external(path, media_type, name=None, trust_class="externally-sourced")` | a file from outside the run (a document, a config, a prompt file) | `bytes` |
| `ctx.read_memory(data, media_type, name, trust_class="externally-sourced")` | an input already in memory, with no path on disk (a request body, a user query). `name` is required — there's no path to default it from. Digested, never stored, exactly like `read_external`. | `bytes` (the same `data`) |
| `ctx.reference(path, media_type, name=None, trust_class="externally-sourced", digest=None)` | a **large** file you don't need in memory. It's streamed and digested in bounded memory. If you pass `digest=`, a mismatch is refused. | an `Artifact` |
| `ctx.read(artifact)` | an artifact written by an earlier stage | `bytes` (a digest mismatch is refused) |
| `ctx.read_json(artifact)` | the same, parsed as JSON | the object |
| `ctx.read_receipt(node)` | depend on an earlier stage's **receipt**; this is what records an edge in a branching pipeline | the receipt |

`trust_class="secret"` is **refused** on every input path, so a stage can't put a secret's digest into a record. Don't route API keys or credentials through `ctx`.

Reads that bypass `ctx`, such as a direct `open()` or an HTTP call, aren't recorded. That's allowed, but the receipt won't mention them. Put anything that affects the output through `ctx`.

### 5.5 Outputs

```python
art = ctx.write("report.pdf", pdf_bytes, "application/pdf", trust_class="operator-authored")
art = ctx.write_json("answer.json", obj, trust_class="model-generated")
```

- Files are stored under `artifacts/NN-<stage>/<name>` and digested over the stored bytes. `onetrace-verify` checks each one against its receipt (section 8).
- `write_json` writes canonical JSON, so **strings only, no JSON numbers** — this is unaffected by section 5.3's int-acceptance, which is metadata (config/constants/assertions), not your own stored data. Silently rewriting a caller's data is worse than refusing it, so a number here is still refused outright; put numbers in as strings: `"0.87"`.
- `write_json` needs a JSON **object** at the top level. Wrap a list: `ctx.write_json("docs.json", {"docs": docs})`.
- Use `trust_class="model-generated"` for anything an LLM produced. Readers rely on it.
- **State the class on every write.** A `ctx.write` or `write_json` with no `trust_class` records
  `operator-authored` and lists nothing as undeclared, whatever the content is. A decorated
  stage's unstated output is recorded as `externally-sourced` and listed (16.2); a hand-written
  write is not, in this version. `externally-sourced` is the class for content that arrived from
  outside: documents, passages, a prompt that quotes them.
- The name is one file name, stored in the stage's own folder: no `/` or `\`, not `.` or `..`,
  no drive, and nothing Windows would store under another name (a reserved device name such as
  `CON`, `< > : " | ? *`, a control character, a trailing space or dot, over 255 bytes). Any
  other name is refused before anything is written.
- Pass the returned `Artifact` to the next stage and read it there with `ctx.read` or `ctx.read_json`. That's how the chain records where each stage's inputs came from.
- Once the stage has ended, `artifact.path` is the file's location relative to the run folder, for example `artifacts/01-retrieve/retrieved.json`.

### 5.6 Constants and assertions

```python
ctx.constant("top_k", 4)                   # a setting the stage ran under
ctx.assertion("hits", 4)                   # a fact the stage states about its work
```

- Each takes a **string**, or a Python **`int`** (never `bool`) recorded as its own decimal string — the same rule as `Instrument.config` (section 5.3). A float is refused for the same reason: its digest isn't stable across languages.
- **A stage that makes assertions must declare at least one constant.** Otherwise you'll get `EmissionRefused: ... assertions [...] declare no constant`. The rule exists so that no stated fact can depend on an unstated setting.

### 5.7 How a stage ends

| Your function… | Receipt `outcome` | What your caller sees |
|---|---|---|
| returns normally | `{"class": "ok"}` | the return value |
| raises `Refusal(reason, detail)` | `{"class": "refused", "reason": ..., "detail": ...}` | `None`; the run continues |
| raises any other exception | `{"class": "error", "status": <type>, "body": <message>, "origin": <instrument id>}` | the exception, re-raised after the receipt is written |

Use `Refusal` when your stage deliberately declines, for example a policy check fails or the input is empty:

```python
from onetrace.emit import Refusal

@rec.stage("answer", instr)
def answer(ctx, hits_artifact):
    hits = ctx.read_json(hits_artifact)
    if not hits:
        raise Refusal("no supporting passages", "retriever returned 0 hits")
    ...
```

### 5.8 `fail-closed` or `fail-open`

This governs what happens if a **receipt can't be written**, or, with `verify_pin`, if **verification fails**:

- **`fail-closed`:** the stage's result is discarded and `EmissionRefused` is raised. A failed verification withdraws the manifest. Use this where a result without a record must not be used, as in regulated, audited or customer-facing flows.
- **`fail-open`:** the result stands. The missing receipt is recorded as a **gap**, and coverage becomes `incomplete`. Use this where availability matters more and a visible hole in the record is acceptable.

Either way, the record never pretends: a missing receipt is written down as missing.

### 5.9 Boundaries and gaps

A **boundary** says the record can't see past a point, for example a stage that calls a third-party system you can't instrument:

```python
rec = Recorder(..., boundaries=[{"name": "answer", "kind": "external service",
                                 "note": "vendor API; its implementation is not visible"}])
# or during the run:
rec.boundary("answer", "external service", "vendor API; its implementation is not visible")
```

A **gap** records a receipt you know you failed to write:

```python
rec.gap("embed", "embedding worker crashed before emitting")
```

Both must name a **declared** stage, and both make coverage `incomplete`. They exist so that a record can be honest about what it doesn't show.

### 5.10 Closing the run, and verifying automatically

**Always call `rec.close()`** at the end, in a `finally:` block if stages may raise. It writes the final manifest, including any gaps or boundaries declared after the last receipt, and runs the verify hook if you configured one:

```python
from onetrace.verify_pin import VerifyPin

rec = Recorder(..., policy="fail-closed", verify_pin=VerifyPin())
try:
    ...stages...
finally:
    rec.close()     # writes MANIFEST.json, then runs onetrace-verify and writes VERIFIER_CALL.json
```

- The verifier's result goes **beside** the record in `VERIFIER_CALL.json` (`result`, `exit`, `rows`, and the sha256 of the verifier files that ran). It is never written into the record itself.
- `VERIFIER_CALL.json` uses two spellings of the third outcome, on purpose. Its own `result` uses the SDK's words and exit codes: `PASS` 0, `FAIL` 1, `NOT RUN` 4. Its `rows` are `onetrace-verify`'s own, which spell it `NOT-RUN`. They mean the same thing; each spelling is its own tool's contract. An `onetrace-verify` exit 2 (`NOT VERIFIED`, or refused, section 10.4) is recorded there as `NOT RUN`, exit 4.
- `VerifyPin(expect_sums="<sha256>")` pins the exact verifier build. A different verifier is not run, and the mismatch is reported.
- `VerifyPin(per_receipt=True)` also verifies after every receipt.
- Under `fail-closed`, a verification failure raises and the run is not declared complete.

### 5.11 Limits, concurrency and async

- **Size bound:** `Recorder(..., max_run_bytes=500_000_000)`. A write that would exceed it raises `StoreExhausted`. That derives from `BaseException`, like `KeyboardInterrupt`, so an ordinary `except Exception` doesn't swallow it. A receipt naming the limit is written for the stage in progress when the bound leaves room for it. `max_run_bytes` itself is refused at construction if it is below the smallest a real receipt for your own declared stages could ever be — measured fresh from your run's own configuration each time, not a fixed number — so a bound too small to hold even that receipt is never accepted in the first place, rather than left to fail later with no receipt and no gap to explain why. A write whose own output already reached disk before the bound stopped it is cleaned up: the bound is a controlled refusal, not a crash, so no orphaned `*.tmp` file is left under `artifacts/`.
- **One process per run folder.** The `.lock` file enforces it. Threads and asyncio tasks inside that process are fine, because emission is serialised inside the recorder.
- **Async stages:**

```python
async with rec.stage("answer", instr) as ctx:
    hits = ctx.read_json(hits_artifact)
    ctx.constant("model", "m-1")
    result = await call_model(hits)
    ctx.write_json("answer.json", result, trust_class="model-generated")
```

---

## 6. Branching pipelines (DAGs)

If your pipeline fans out and back in, declare the approved edges between stage names, and run each instance with `run_node`:

```python
rec = Recorder("runs/dag-1", declared_stages=["load", "normalise", "merge"],
               manifest=Path(__file__), policy="fail-closed",
               declared_edges=[{"from": "load", "to": "normalise"},
                               {"from": "normalise", "to": "merge"}])

def normalise(ctx, key):
    ctx.read_receipt("load")                      # records the edge load -> normalise#<key>
    return ctx.write_json(f"{key}.json", {"k": key})

def merge(ctx):
    ctx.read_receipt("normalise#a")               # instances are named stage#instance
    ctx.read_receipt("normalise#b")
    return ctx.write_json("merged.json", {"ok": "yes"})

rec.run_node("load", None, instr_load, load)
rec.run_node("normalise", "a", instr_norm, normalise, "a")
rec.run_node("normalise", "b", instr_norm, normalise, "b")
rec.run_node("merge", None, instr_merge, merge)
rec.close()
```

- Edges are **observed** from `read_receipt` calls and written into the manifest. Each one is checked against `declared_edges` as it happens.
- A bare stage name that matches several instances is refused as ambiguous. Name the instance.
- On a DAG, `onetrace localize <run>` reports the **set** of earliest unclean nodes, sorted, never a single "first" node.
- Linear and DAG runs are **not comparable** with each other: `diff` reports `not comparable`, with exit code 2.
- **Concurrent stages** (two nodes racing for the same emission lock) are supported; onetrace-verify's own artifact check (section 8) accounts for the race correctly as of 0.1.1 (section 14).

---

## 7. What a run folder contains

```
runs/run-a/
├── .lock                       one-process guard (leave it)
├── MANIFEST.json               the chain: receipt digests in order, and chain_head
├── receipts/
│   ├── 01-retrieve.json        one canonical JSON receipt per stage
│   └── 02-answer.json
├── artifacts/
│   ├── 01-retrieve/retrieved.json
│   └── 02-answer/answer.json
└── VERIFIER_CALL.json          only if verify_pin was set
```

The files you pass to `read_external` stay where they are. The quickstart writes `corpus.json` into the run folder only for convenience.

**What a run folder stores.** Outputs are kept: a run folder holds each stage's outputs, which can include documents, prompts and answers. Inputs are fingerprinted, not stored: a receipt records an input's digest, length and trust class, never its bytes. So treat run folders like logs that may contain sensitive data.

A receipt, abridged:

```json
{"format": "stage-receipt/0.2",
 "stage": {"index": "2", "name": "answer"},
 "instrument": {"id": "extractive", "kind": "answerer", "version": "1.0.0",
                "config_digest": "sha256:…", "manifest_digest": "sha256:…", "rederivable": "true"},
 "inputs":  [{"name": "retrieved.json", "digest": "sha256:…", "trust_class": "operator-authored", …}],
 "outputs": [{"name": "answer.json", "digest": "sha256:…", "bytes": "86", …}],
 "assertions": {"source": "p1", "constants": {"method": "extractive"}},
 "outcome": {"class": "ok"},
 "coverage": {"completeness": "complete", "declared_stages": […], "emitting_stages": […], "boundaries": []},
 "emission": {"policy": "fail-closed", "gaps": []},
 "anchor": {"state": "unanchored", "reason": "not anchored"},
 "time": {"started": "…Z", "ended": "…Z"},
 "prev": "sha256:<previous receipt>", …}
```

---

## 8. Verifying a run

### 8.1 `onetrace-verify`

```bash
onetrace-verify runs/run-a            # a run folder, or a path to MANIFEST.json
onetrace-verify --help                # usage
onetrace-verify --version             # 0.1.2
onetrace-verify --require-artifacts runs/run-a   # also FAIL if the output files can't be checked
onetrace-verify --json runs/run-a     # machine-readable rows and a summary, for a CI gate
onetrace-verify --headers headers.json runs/run-a               # check OpenTimestamps anchors (15.5)
onetrace-verify --tsa-cert tsa.pem --tsa-root root.pem runs/run-a   # check RFC 3161 anchors (15.4)
```

`--json` replaces the row-by-row text with one JSON document: `{"rows": [{"result", "name",
"detail"}, ...], "summary": {"pass", "fail", "not_run", "result", "exit"}}`, using the same words
the text rows use. The exit code is the same either way: `--json` changes only how the result
is printed, not what is checked.

It prints one row per check: each receipt's own format, canonical bytes, required members, digests matching the manifest, `prev` links, stage order, coverage, the chain head, and — when it can recognise the run's own `artifacts/<stage>/<output>` layout — every output file against the digest its receipt recorded (section 8.3). It ends with a summary:

```
56 pass, 0 fail, 2 not-run  ->  PASS
```

| Exit | Meaning |
|---|---|
| 0 | PASS: the record is consistent and unbroken |
| 1 | FAIL: at least one check failed, and the `[FAIL]` rows say which |
| 2 | NOT VERIFIED: a receipt's own format is one this verifier doesn't implement, and nothing failed (section 10.4). Also exit 2: refused, when the manifest can't be read or its chain format is unknown (refused by name, never guessed), or no manifest found. |

In human mode it also writes to stderr, before the rows: one summary line drawn only from the rows it computed, which reads `record intact: 2 stages, 2 output files checked`, `record NOT intact: <the first failing row>` (with the number of failing rows when there are several), or `record not verified: <reason>`. After it comes one line for each `FAIL` row, and none for a `NOT-RUN` or `PASS` row: `fix (<row>): <what to do>; see https://oneproof.dev/onetrace/errors.md#<family>`, where the family is the errors page's section for that kind of check: `verify-receipt`, `verify-chain`, `verify-artifacts`, `verify-anchor`, `verify-signature` or `verify-plan`. These lines change nothing else: the rows and the summary on stdout, the exit code, and `--json` (which writes nothing to stderr) are as above. `ONETRACE_QUIET=1` silences them (section 16.18).

`not-run` rows for a receipt's `originality` are normal (section 1). A run with anchors also gets one row per anchor in `anchors/` (15.3): a `FAIL` fails the run like any other, and a `NOT-RUN` ("needs block headers", say) leaves the result as it would be without it, which a line after the summary says. A run with an anchor row also ends with one more line, what an anchor shows and doesn't: "anchors show this record existed by the time the source attests; not when the run happened, that its outputs were correct, or who wrote it." Neither line is printed with `--json`; the first line's count is there, as `summary.records_not_run`. (`onetrace-verify` spells the outcome `NOT-RUN`; the SDK's own verifier, `python -m onetrace.sdk_verify`, and `VERIFIER_CALL.json`'s own `result` spell it `NOT RUN`, section 5.10.) A `not-run` row can also name `run: artifacts`, when there's no `artifacts/` directory at all, or when its layout isn't one this verifier recognises (section 8.3). A `not-run` row never turns the summary into `FAIL`, so read the rows, not just the last line, or use `--require-artifacts`. `python -m onetrace.sdk_verify` checks the output files the same way, and gives the same `run: artifacts` row (`NOT RUN`) when there are none to check; it has no `--require-artifacts`. A `receipt format` `not-run` row is different: that receipt's content was not checked, and it turns the summary into `NOT VERIFIED`, exit 2.

A missing, unreadable or malformed file the manifest names — a removed receipt, a truncated write, a directory where a file should be — gives a `[FAIL]` row naming it, never a Python traceback (fixed in 0.1.1; section 14).

### 8.2 What tampering looks like

Edit a receipt and the verifier fails it, and the chain head:

```
[FAIL   ] receipts/02-answer.json: digest matches the manifest
[FAIL   ] manifest: chain head matches the last receipt
54 pass, 2 fail, 2 not-run  ->  FAIL
```

### 8.3 Output files are checked automatically

As of 0.1.1, `onetrace-verify` reads `artifacts/` itself — you no longer need a separate script. For every receipt's own recorded outputs, it looks for `artifacts/<receipt stem>/<output name>` (the layout this SDK's own `ctx.write`/`write_json` produce):

- **A run with a recognised `artifacts/` layout:** every recorded output must be present with a matching digest, or it's a `[FAIL]` row naming the file. A receipt whose own format this verifier doesn't implement is skipped: its outputs are content it can't read.
- **A run with no `artifacts/` at all, or one whose layout this verifier doesn't recognise** (an older run, or one built by hand rather than through this SDK): one `NOT-RUN` row, `run: artifacts`, naming which case it is. No file is checked. The summary can still read `PASS`, because the record itself checks out.
- **With `--require-artifacts`**, that `NOT-RUN` row becomes a `FAIL` and the exit code is 1. Use it whenever the files matter, for example when someone hands you a run folder, and in CI. Otherwise, deleting the whole `artifacts/` folder would leave the summary at `PASS`.

```bash
onetrace-verify runs/run-a
```

```
...
[FAIL   ] receipts/02-answer.json: output artifact 'answer.json' -- missing from artifacts/
...
55 pass, 1 fail, 2 not-run  ->  FAIL
```

Editing a file under `artifacts/` (or deleting one) now fails the verifier directly — it no longer takes a receipt edit to notice.

---

## 9. Framework integrations (LangChain, LlamaIndex, Langflow)

There is no magic callback. Integration means **wrapping each logical step of your chain as a stage**, so that everything it reads and writes goes through `ctx`. The published source distribution includes complete, runnable examples under `examples/`: `langchain_adapter`, `llamaindex_adapter`, `langflow_adapter`, and `plain_python_control`, a framework-free baseline.

The pattern, using LangChain:

```python
import importlib.metadata as md
from langchain_text_splitters import RecursiveCharacterTextSplitter
from onetrace.emit import Instrument

LC = md.version("langchain-core")          # pin the real installed version

@rec.stage("split", Instrument("RecursiveCharacterTextSplitter", "splitter",
                               md.version("langchain-text-splitters"),
                               {"chunk_size": 900, "chunk_overlap": 0}))
def split(ctx, cleaned_artifact):
    text = ctx.read(cleaned_artifact).decode("utf-8")
    ctx.constant("chunk_size", 900); ctx.constant("chunk_overlap", 0)
    chunks = RecursiveCharacterTextSplitter(chunk_size=900, chunk_overlap=0).split_text(text)
    ctx.assertion("chunk_count", len(chunks))
    return ctx.write_json("chunks.json", chunks)

@rec.stage("answer", Instrument("my-llm", "llm", "model-snapshot-01",
                                {"temperature": 0}, rederivable="false",
                                rederivable_note="hosted model; sampling not reproducible"))
def answer(ctx, prompt_artifact):
    prompt = ctx.read(prompt_artifact).decode("utf-8")
    ctx.constant("temperature", 0)
    reply = llm.invoke(prompt)
    ctx.assertion("reply_chars", len(reply))
    return ctx.write("answer.txt", reply.encode("utf-8"), "text/plain", trust_class="model-generated")
```

Guidelines:

- **One stage per step you'd want to point at** when something goes wrong: load, convert, clean, split, embed, index, retrieve, build the prompt, answer.
- **Version and configuration come from the real objects,** read at run time, never typed in by hand.
- **Mark every LLM output `model-generated`,** and every hosted-model stage `rederivable="false"`.
- **Vector stores and embeddings are usually in memory.** Write what matters as artifacts (ids, scores, the prompt) so that the next stage reads it through `ctx`.

---

## 10. Comparing runs

### 10.1 `diff`: a stage-by-stage ladder

```bash
onetrace diff runs/monday runs/tuesday --out reports/diff
```

```
stage         baseline            candidate           verdict
retrieve      51bd312473c4        51bd312473c4        same
answer        35a281ec6835        9f02c1d7a4be        FIRST DIFFERENCE
```

Each stage gets exactly one of five verdicts, always about the stage's **output**:

| Verdict | Meaning |
|---|---|
| `same` | the output digests match |
| `FIRST DIFFERENCE` | the first stage, in order, whose output differs |
| `downstream` | it differs after the first difference, so the divergence propagated |
| `reconverged` | it matches again after diverging |
| `COULD NOT CHECK` | it can't be evaluated (unknown format, a boundary, an unreadable file). **This is not a pass.** |

A change in an instrument's version or config never changes a verdict by itself. It's shown as an annotation, so a `same` never hides that *how* the output was produced changed.

#### The text that changed: `diff --text`

```bash
onetrace diff runs/monday runs/tuesday --text [--stage NAME]... [--all] [--context N] [--max-lines N] [--no-color]
```

Both runs are verified first. A run that doesn't verify is refused, and no text from either run is shown. A node *differs* when anything compared differs between the runs: its outputs, its inputs, or any setting, the corpus link included. Which nodes are shown:

- **By default:** every `FIRST DIFFERENCE` node, then every node downstream of it, in order. A downstream node whose outputs are the same is shown as one line, `<node>: outputs unchanged (reconverged)`, with its settings line if a setting changed, its corpus link line if the link changed, and no text.
- **`--all`:** also the nodes that differ but aren't downstream of a first difference, for example a stage whose settings changed while its output didn't. Each gets its settings line and no text.
- **`--stage NAME`:** only the named nodes. A name that matches no node is reported.

**Chunk text is opt-in.** A splitting stage that returns `ot.chunks(pairs)` records a chunk index: each chunk's id, document, length and digest, and no text. With `ot.chunks(pairs, keep_text=True)` (or the LangChain adapter's `--keep-text`), each chunk also keeps its text, and `--text` shows a changed chunk's text diff. The text is shown only after checking that the digest of its bytes equals the chunk's digest; otherwise it says `text does not match its digest; not shown`. Run folders store each stage's outputs, so treat them like logs that may contain sensitive data. `keep_text` adds the chunk text to them.

`--text` never changes a verdict or the exit code. `--json` prints the same comparison as one JSON document, `onetrace-textdiff/0.3`, whose fields and escaping are defined in [the textdiff format](textdiff-format.md).

#### Following a changed corpus link

When the first difference is at a node whose corpus link changed, `--text` follows the link one hop into the two linked ingest runs, under its own heading, `traced into the linked ingest runs: <run id> -> <run id>`:

- **They are found by chain head,** never by name or path, one level down in `--runs-root DIR` (default: the folder holding the baseline).
- **Both are verified first.** One that doesn't verify is named, and nothing from it is shown.
- **They are compared with the same rules,** starting with a sentence such as `started at: load — 1 of 214 documents changed (help-centre/warranty.md); settings unchanged`.
- **One hop only.** If the ingest runs' own corpus link changed, that is named and not followed.
- **When the trace can't be made,** it says why (not found, did not verify, a side with no link) as `COULD NOT CHECK` for the trace alone.

`--no-follow` turns the trace off.

The linked ingest runs' verifier calls are written beside the report, as the two runs' are, under `corpus/baseline/<path>/` and `corpus/candidate/<path>/`, where `<path>` is the run's folder relative to `--runs-root`. For an ingest run that doesn't verify, each call gives only its command, its exit code and the reason line, and none of the verifier's output. A run that isn't found has no calls.

Without `--text`, `diff --follow-corpus` makes the same trace and prints the ingest runs' own ladder of stages and digests after the report. It never shows stored ingest text: that needs `--text`, and the two flags aren't given together. The JSON report carries it under `corpus_trace`:
- `notes`: the plain lines, such as `trace: no corpus link recorded at <node>; …`;
- `traces`: the entries described in [the textdiff format](textdiff-format.md#a-corpus-trace). A traced entry carries `report`, the ingest pair's own `diff` or `localize` report with paths relative to `--runs-root`, in place of `nodes`.

The trace never changes a verdict or the exit code.

### 10.2 `localize`: where it went wrong

```bash
onetrace localize runs/tuesday                        # one run: first unclean stage
onetrace localize runs/monday runs/tuesday --out r    # two runs: first difference and its cause
```

On one run, an unclean stage is a refusal, an error, or a failed check.

On two runs, the cause names what changed at the first difference:
- the instrument;
- its config and constants;
- the **corpus link** a query run records with `ot.corpus_from`, by digest: `corpus link changed: <digest> -> <digest>`.

`diff` annotates a changed corpus link on every node that carries one, the way it annotates a changed setting.

`localize A B --follow-corpus` follows a changed corpus link one hop, as `diff` does, and reports where the two linked ingest runs first differ and why, after its own report. It never shows stored ingest text (see [following a changed corpus link](#following-a-changed-corpus-link)).

The corpus link is compared on run records only. A query run's retrieval stage is a run record, so the per-document receipts of the two-root form are not compared for a corpus link.

### 10.3 `reproduce`: re-run and compare

`reproduce` re-executes recorded stages and compares their outputs with the record. It needs a **runner file** that says how to run your code:

```json
{"format": "onetrace-runner/0.1",
 "code": "pipeline.py",
 "argv": ["{python}", "-B", "{code}", "{out}"],
 "cwd": "{code_dir}",
 "timeout_seconds": "600"}
```

```bash
onetrace reproduce runs/monday --runner runner.json --out reports/repro          # whole run
```

- `{python}` is the interpreter that is running `onetrace`. Run `reproduce` from the virtual environment that has your pipeline's dependencies installed.
- `{out}` is a fresh folder that `reproduce` chooses. Any further arguments your code needs, such as a run id, go in `argv` as plain strings.
- **Re-running a single stage is not available in 0.1.x.** `onetrace reproduce <run> <stage>` is accepted, but it always reports that stage as `COULD NOT CHECK` (exit 4), naming the reason. Reproduce the whole run instead.

- The code's sha256 must equal the recorded `manifest_digest`, and the instrument identity must match exactly. Otherwise the result is `COULD NOT CHECK`, never "close enough".
- Each stage is reported as `REPRODUCED`, `DIVERGED` or `COULD NOT CHECK`.
- Stages marked `rederivable="false"` are expected not to reproduce.

### 10.4 Exit codes and reports

| Command | 0 | 1 | 2 | 3 | 4 |
|---|---|---|---|---|---|
| `diff`, two-run `localize` | identical | diverged | not comparable | refused | could not check |
| one-run `localize` | clean | located | n/a | refused | could not check |
| `reproduce` | all REPRODUCED | any DIVERGED | n/a | refused | any COULD NOT CHECK (none diverged) |
| `onetrace-verify` | `PASS` | `FAIL` | `NOT VERIFIED`, or refused (below) | n/a | n/a |

For `onetrace-verify`, exit 2 is never a pass and never a fail. It has three causes:
- a receipt whose own format this verifier does not implement, with no check failing anywhere. The summary line reads `NOT VERIFIED (receipt format not implemented: N receipt(s))`.
- a manifest whose own chain format it does not implement, or that it cannot read. This is reported as a `[REFUSED]` line before any row.
- a usage error, such as a missing path.

A `FAIL` anywhere always outranks `NOT VERIFIED`, giving exit 1. With `--json`, the exit code is the same, and `summary.result` reads `NOT VERIFIED` or `REFUSED` for the first two causes.

Every command writes a JSON report and a text report into `--out` (default `onetrace-report/`), plus the verifier's rows for each input run. Use `--quiet` to skip printing.

---

### 10.5 Seeing what changed

The repository's warranty example is a help-centre corpus in two versions, where one sentence in `warranty.md` says "twelve months" in v1 and "six months" in v2. Each version is ingested (`load`, `split` with `ot.chunks(..., keep_text=True)`, `index`), and a query pipeline (`retrieve`, `prompt`, `answer`) runs over each, linked to its own ingest run with `ot.corpus_from`. The four runs are in `tests/fixtures/warranty/`. From that folder:

```bash
onetrace diff runs/query-v1 runs/query-v2 --text --no-color
```

prints this before the ladder report (this is the test suite's committed transcript, byte for byte):

```text
first difference: retrieve — output text changed; settings unchanged; corpus link changed; input help_centre changed

== retrieve (FIRST DIFFERENCE)
settings: none changed
corpus link changed: 67ffdb182dfb (ingest-v1) -> 9f88f639a4a5 (ingest-v2)
input help_centre (operator-authored) changed: cec075f03ffe -> 1e4f8fbeaa98; content not stored
--- return.json
hits: 0 entered, 0 left, 0 moved; 1 changed; 1 unchanged
~ hit help-centre/warranty.md#0001 #1 changed: b500694d27e1 -> 5ceb7e1a7fba
  - The warranty covers twelve months from the date of purchase.
  + The warranty covers six months from the date of purchase.
  ~ The warranty covers [-twelve-]{+six+} months from the date of purchase.
    It covers manufacturing faults, not accidental damage.

== prompt (downstream)
settings: none changed
--- return.json
- "Answer from these passages only.\n- The warranty covers twelve months from the date of purchase.\nIt covers manufacturing faults, not accidental damage.\n- You can return an unused item within 30 days of delivery.\nRefunds go back to the original payment method within 5 working days.\nQuestion: How long does the warranty cover?\n"
+ "Answer from these passages only.\n- The warranty covers six months from the date of purchase.\nIt covers manufacturing faults, not accidental damage.\n- You can return an unused item within 30 days of delivery.\nRefunds go back to the original payment method within 5 working days.\nQuestion: How long does the warranty cover?\n"
~ "Answer from these passages only.\n- The warranty covers [-twelve-]{+six+} months from the date of purchase.\nIt covers manufacturing faults, not accidental damage.\n- You can return an unused item within 30 days of delivery.\nRefunds go back to the original payment method within 5 working days.\nQuestion: How long does the warranty cover?\n"

== answer (downstream)
settings: none changed
--- return.json
- "The warranty covers twelve months.\n"
+ "The warranty covers six months.\n"
~ "The warranty covers [-twelve-]{+six+} months.\n"

traced into the linked ingest runs: ingest-v1 -> ingest-v2
started at: load — 1 of 3 documents changed (help-centre/warranty.md); settings unchanged

== load (FIRST DIFFERENCE)
settings: none changed
input help_centre (operator-authored) changed: 5ae58f3b8452 -> bf96196b62ce; content not stored
--- return.json
    },
    {
      "id": "help-centre/warranty.md",
-     "text": "# Warranty\n\nThe warranty covers twelve months from the date of purchase.\nIt covers manufacturing faults, not accidental damage.\n"
+     "text": "# Warranty\n\nThe warranty covers six months from the date of purchase.\nIt covers manufacturing faults, not accidental damage.\n"
~     "text": "# Warranty\n\nThe warranty covers [-twelve-]{+six+} months from the date of purchase.\nIt covers manufacturing faults, not accidental damage.\n"
    }
  ]

== split (downstream)
settings: none changed
--- return.json
chunks: 1 changed, 0 added, 0 removed; 5 unchanged
~ chunk help-centre/warranty.md#0001 changed:
  - The warranty covers twelve months from the date of purchase.
  + The warranty covers six months from the date of purchase.
  ~ The warranty covers [-twelve-]{+six+} months from the date of purchase.
    It covers manufacturing faults, not accidental damage.

== index (downstream)
settings: none changed
--- return.json
        "not",
        "of",
        "purchase",
+       "six",
        "the",
-       "twelve",
        "warranty"
      ]
    }
```

Reading it from the top:

- **The first line is a sentence:** where the runs first differ, whether its output text changed, whether any setting did, and which inputs did.
- **`retrieve` is the first difference.** No setting changed, but its corpus link did, on a line of its own: the query runs read different ingest runs, named by run id once the trace reached them. Its input `help_centre` changed too. An input's name is its parameter's name, so it is spelled as Python spells it; `help-centre/warranty.md` is a document's path, which keeps its own spelling. Inputs are fingerprinted, so only their digests are shown.
- **The changed words are marked** `[-removed-]{+added+}` on a `~` line under each changed line pair, here `twelve` to `six`. A chunk index and a hits list are compared entry by entry, by id.
- **`prompt` and `answer` change as a result:** they are downstream of `retrieve`, and their settings did not change.
- **The trace follows the changed corpus link one hop** into the two ingest runs, verified first, and compares them the same way. It starts at `load`, where one of three documents changed, and shows the sentence changing in `warranty.md` and then in its chunk.

The same comparison is available as one JSON document with `--json`. Its fields are described in [the textdiff format](textdiff-format.md), and its JSON Schema is `docs/textdiff-format.schema.json`.

What this does not claim:
- *The text diff shows what recorded outputs contained. It does not say why they changed, or that either version was correct.*
- *Inputs are fingerprinted, so their content is not shown.*

## 11. Using onetrace in CI

```yaml
# example: fail the build if the pipeline's record is broken or its output drifted
- run: python pipeline.py runs/ci run-ci-${{ github.run_id }}
- run: onetrace-verify --require-artifacts runs/ci
- run: onetrace diff baselines/golden runs/ci --out reports/diff   # exit 1 means the output changed
```

Keep a known-good run as `baselines/golden`. When a change is intended, regenerate the baseline in the same pull request, so the diff is reviewed rather than hidden. `onetrace-verify --require-artifacts` checks your output files too, and fails if they can't be checked (section 8.3), so no separate script is needed.

---

## 12. Common errors and what they mean

| Message (abridged) | Cause | Fix |
|---|---|---|
| `emission policy must be declared as one of ('fail-closed', 'fail-open')` | missing or misspelled `policy` | pass one of the two |
| `... already holds a run; a record is never overwritten` | the output folder holds a finished run (`close()` releases `.lock`, so reopening it reads as this, not as a lock conflict) | use a new folder per run |
| `another process already holds this run folder` | a second process genuinely still emitting into that folder, or a stale `.lock` left by a process that crashed before calling `close()` | one process per folder, and a fresh folder per run |
| `stage 'X' is not the next declared stage (expected Y)` | stages ran out of declared order | call them in the declared order, or fix `declared_stages` |
| `version 'latest' does not pin a build` | an unpinned instrument version | use the exact library version or model snapshot |
| `... is a bool, not an accepted metadata value` | `True`/`False` passed to a config, constant or assertion | use a string (`"true"`) or an int, not a bool |
| `a float (...) is refused -- its digest is not stable across languages` | a float in a config, constant or assertion | convert it to a string, or (for a whole-number value) an int |
| `JSON number at $.… : use a decimal string` (`write_json` only) | a number in a `write_json` payload | convert it to a string: `str(x)` |
| `write_json needs a JSON object at the top level` | a list or a string passed to `write_json` | wrap it in an object |
| `assertions [...] declare no constant` | assertions with no `ctx.constant` in the stage | declare the constants the stage ran under |
| `trust class 'x' is not one of (...)` | a wrong trust class | use `operator-authored`, `model-generated` or `externally-sourced` |
| input refused as `secret` | `trust_class="secret"` | keep secrets out of the record entirely |
| `StoreExhausted` | `max_run_bytes` reached | raise the bound, or write less |
| `max_run_bytes=... is below ..., the smallest a real receipt for this run's own declared stages could ever be` | the bound was set below what even one error receipt needs, measured from your own run at construction | raise the bound to at least the number named |

---

## 13. API summary

```python
import onetrace
onetrace.__version__                         # "0.1.2"
onetrace.digest(path_or_bytes) -> "sha256:<hex>"

from onetrace.emit import (Recorder, Instrument, Refusal,
                           EmissionRefused, StoreExhausted, current_run, current_stage)
from onetrace.verify_pin import VerifyPin

Recorder(out_dir, declared_stages, manifest, policy, anchor_reason=None, run_id=None,
         topology=False, declared_edges=None, boundaries=None, instruments=None,
         verify_pin=None, max_run_bytes=None)
  .stage(name, instrument=None, instance=None)        # decorator, or `async with`
  .run_stage(name, instrument, fn, *args, **kw)
  .run_node(name, instance, instrument, fn, *args, **kw)
  .boundary(name, kind, note=None)
  .gap(stage, reason, kind="unwritten receipt")
  .close()
  .run_id                                             # the id in use

Instrument(id, kind, version, config, rederivable="true", rederivable_note=None)

ctx (StageContext):
  .read_external(path, media_type, name=None, trust_class="externally-sourced") -> bytes
  .read_memory(data, media_type, name, trust_class="externally-sourced") -> bytes
  .reference(path, media_type, name=None, trust_class="externally-sourced", digest=None) -> Artifact
  .read(artifact) -> bytes          .read_json(artifact) -> object
  .read_receipt(node) -> dict
  .write(name, data, media_type, trust_class="operator-authored") -> Artifact
  .write_json(name, obj, trust_class="operator-authored") -> Artifact
  .constant(key, value)             .assertion(key, value)   # value: str, or int (never bool/float)
  .corpus_manifest(digest, member=None, preimage=None, proof=None)

Refusal(reason, detail=None)        # raise inside a stage to decline

VerifyPin(verifier=None, expect_sums=None, per_receipt=False)
```

Commands: `onetrace-verify [--require-artifacts] [--json] [--headers FILE] [--tsa-cert FILE --tsa-root FILE] <run>`, `onetrace anchor <run> --source rfc3161|opentimestamps` (section 15), `onetrace diff A B`, `onetrace localize A [B]`, `onetrace reproduce <run> [stage] --runner R`. The common options are `--out`, `--quiet`, `--stages` and `--verifier`. `onetrace-verify -h`/`--help`/`--version` print usage and the version and exit 0.

---

## 14. Known limitations in 0.1.1

- Records are **hash-chained, not signed**. To show a record existed by a given time, anchor its chain head (section 15); otherwise keep the chain head somewhere independent.
- Framework "adapters" are worked examples in the source distribution, not importable modules.
- The format is version 0 and may change before version 1. Every record carries its format version. The manifest's own chain format is checked, and an unknown one is refused by name, never guessed. **A receipt's own format was not checked in 0.1.1** (0.1.0 behaved the same): only its presence was checked, not its value. **From 0.1.2 it is checked.** A missing format, one that is not a string, or one that is not a `stage-receipt/<major>.<minor>` label is a `FAIL`. A version this verifier doesn't implement (a major other than 0, or a minor that isn't ASCII decimal digits) gets one `NOT-RUN` row naming it: that receipt's digest against the manifest and its chain link are still checked, but none of its content is (canonical form, fields, originality, output files). The summary then reads `NOT VERIFIED (receipt format not implemented: N receipt(s))` and the exit code is 2, unless a check failed anywhere, which gives `FAIL` and exit 1 (section 10.4).
- `onetrace-verify`'s artifact check only applies when it can recognise a run's own `artifacts/<stage>/<output>` layout. A run built by hand, or with a different layout, reads `NOT-RUN` for its files (section 8.3). Receipts don't record where an output file is stored, so the check depends on this SDK's folder convention; a later format version will record the path.
- `reproduce` re-runs whole runs only (section 10.3).
- Licence: Apache-2.0.

### Fixed since 0.1.0 — if you have run folders from 0.1.0

- **`onetrace-verify` did not check `artifacts/` files at all** in 0.1.0; as of 0.1.1 it does (section 8.3). This makes the verifier **stricter**, not looser: a run whose output files were edited or deleted after the fact, which passed under 0.1.0, now correctly fails.
- **A concurrent pipeline's output files could land under the wrong numbered folder** in 0.1.0: `ctx.write`'s target directory was chosen from a stage's provisional position, before the real one was decided under the lock, and the two could disagree once two stages genuinely raced. The receipts themselves were never affected — only where the output *files* ended up on disk. **If you have run folders emitted concurrently by 0.1.0**, re-verifying them under 0.1.1 may now show `[FAIL]` rows naming misplaced output files that 0.1.0's own verifier could not see. This is 0.1.1 correctly reporting a real, pre-existing mismatch, not a new defect in the run itself.
- **`onetrace-verify -h`/`--help` were previously treated as a path**, and a run with a missing or malformed receipt file made it stop with a Python traceback instead of a clean `[FAIL]` row. Both are fixed in 0.1.1: usage/version print and exit 0; any file problem the manifest names gives a `[FAIL]` row (or, for the manifest itself, `[REFUSED]`), never a traceback.
- **`reproduce` could not run your code from a virtual environment on Linux or macOS.** `{python}` resolved the venv's interpreter link to the system Python, which doesn't have your packages, so every stage read `COULD NOT CHECK`. Fixed in 0.1.1: `{python}` is the interpreter running `onetrace`, exactly as invoked.
- **A config, constant or assertion value had to be a string**, including numbers (`"3"`, not `3`) — a JSON number anywhere in a receipt was refused outright. As of 0.1.1, a Python `int` (never `bool`) is accepted directly and recorded as its own decimal string (section 5.3). `write_json` payloads are unaffected: a number there is still refused, now with a clearer message naming the output.

## 15. Anchoring a run

`onetrace.anchor.add_anchor(run_dir, record)` stores each anchor as its own file, `anchors/<n>.json`, beside the run's receipts. The writer holds `anchors/` open while it links the record in and reads it back, and it reports a record stored only when it has confirmed that the record is there, in this run's folder, with the bytes it wrote. If it can't confirm that, it says so ("stored as N.json; could not confirm it landed in this run"), and you should check the folder before relying on it. It never reports a record stored that it hasn't confirmed.

### 15.1 Run folders on a network share

- **An SMB share of an NTFS volume (Windows):** anchors are stored and confirmed. This was measured through the loopback admin share (`\\localhost\C$`). Windows can't open a file by its id over SMB, so the writer opens the stored name relative to the directory it holds. Over SMB the server resolves that "relative" open by path; what keeps it safe is that the writer then checks the file it opened is the file it wrote, by its file id.
- **The limit over a share.** Over a network share, someone who can write to the run folder on the server during the write can make the record land in another run. The writer then reports that nothing is claimed, and the stray record reads FAIL there. On a local disk this can't happen. To anchor a run folder that others can write to, anchor a local copy of it.
- **A ReFS volume, local or shared:** not measured. A record there may not be confirmed: the writer refuses to confirm a file whose id is wider than 64 bits, which ReFS can use.
- **A share without hard links** (for example WSL's `\\wsl.localhost\...` share): the record is refused before anything is claimed, because the writer needs a hard link so that no reader ever sees a partial record.
- **Other SMB servers** (for example Samba) haven't been measured. If the writer can't confirm a record there, it says "not confirmed", never "stored".

### 15.2 Someone else writing in the run folder at the same time

The writer links the file it wrote itself, not whatever is at the temporary file's name. On Windows the link is made from the file's own handle, and while the writer holds it, the temporary file can't be renamed away. On Linux the link is made through `/proc/self/fd`.

On Windows, someone can make the stored record a reparse point after it is written, which keeps the file's id. The verifier then reads the record as FAIL. If the reparse point is set before the writer reads the record back, the writer says "stored as N.json; could not confirm…", naming the reparse point: it doesn't report that record stored. If it is set after the read-back, the writer reports the record stored, and only the verifier's FAIL shows it.

On a system without `/proc/self/fd` (macOS, for example), the temporary file is linked by its name. Someone with write access to the run folder during the write can then put a copy in its place. The writer detects this and refuses with "nothing is claimed", but the copy stays in `anchors/`. This behaviour was measured on Linux with the `/proc` route turned off; macOS itself hasn't been measured. **Anchor a run folder that nobody else is writing to.**

### 15.3 What the verifier reports for an anchor

Each file in `anchors/` gets one row, beside the receipts' own rows. It reads PASS, FAIL or NOT-RUN, with its reason:

- **PASS:** the proof is valid, it commits to this run's chain head, and it comes from the source you pinned.
- **FAIL:** something is shown to be wrong. The verifier's result is then FAIL.
- **NOT-RUN:** a check that can't be computed here. It is never a pass, and it leaves the verifier's result as it would be without the anchor. The reasons are:
  - "needs block headers": an OpenTimestamps proof, with no header file for its block;
  - "pending: not yet in a block": an OpenTimestamps proof the calendar hasn't put in a block yet;
  - an operation or attestation this verifier can't compute, named;
  - a `method` this verifier doesn't implement, named;
  - without `onetrace-verify[crypto]`, the install line.

**The order of the checks is fixed.** The record's structure, its size and nesting caps, and its binding to this run's chain head always come first, with or without the extra and whatever the method. A failure there is FAIL. So a malformed record, or one for another run, is never shown as NOT-RUN.

**The record's format is `stage-receipt-anchor/0.1`.** A record written as `onetrace-anchor/0.1`, the name before 0.2.0, is FAIL, and the row's `fix:` names the new one.

**`asserted_time`** is the time the proof attests:
- it is `null` while the proof attests no time yet (a pending OpenTimestamps proof), and only then;
- `null` beside a proof that attests a time is FAIL, and so is a time beside a proof that attests none;
- any RFC 3339 time with `Z` or a UTC offset is accepted, and times are compared as instants: `2024-09-22T12:13:20+02:00` and `2024-09-22T10:13:20Z` are the same time.

**onetrace's own record shape.** The approved −01 text leaves these open; this is what onetrace writes and accepts:
- **`source`** is `{"tsa_certificate_sha256": "<64 lowercase hex>"}` for `rfc3161`, and `{"calendars": ["https://…", …]}` (a non-empty list) for `opentimestamps`. For a method it doesn't implement, the verifier doesn't read `source`.
- **Strictness:**
  - a member the record format doesn't define is FAIL;
  - a file in `anchors/` that isn't named `<n>.json` (n from 1, no leading zero, lower case) is FAIL;
  - an `anchors/` that is a link (a symlink or a junction) is FAIL, and nothing in it is read.

### 15.4 Anchoring with RFC 3161 (a time-stamp authority)

An RFC 3161 time-stamp service (TSA) is the method to use where no outside calendar can be reached: its answer is checked fully offline against the service's certificate. With no outside access, point `--tsa-url` at a time-stamp service you run yourself and pin its certificate; onetrace has none built in. It needs the `[crypto]` extra (15.6).

```
onetrace anchor runs/<run_id> --source rfc3161 --tsa-url https://tsa.example/tsr \
    --tsa-cert tsa.pem --tsa-root root.pem
```

- The request is a time-stamp query over the chain head: SHA-256 over its 32 raw bytes, with a nonce. This is the only onetrace command that contacts a network, and only when you run it.
- Before anything is stored, the TSA's answer is checked the way the verifier will check it, against the certificate and root you pinned. An answer that isn't granted, carries another nonce, is for another chain head, or doesn't verify is refused, with nothing stored and a `fix:` line.
- The record keeps the TSA's answer byte for byte, names the pinned certificate by its sha256, and carries the token's own time as `asserted_time`.
- Exit status: 0 stored, 1 refused (nothing stored), 2 a usage error (nothing asked of any source), 3 stored but not confirmed (15.1, 15.2). For `--upgrade`, 0 also when every upgrade is already stored and nothing is still pending (it names the record that holds it, and stores nothing).

To check the anchor, pin the same certificate and root:

```
onetrace-verify runs/<run_id> --tsa-cert tsa.pem --tsa-root root.pem
```

Without them, the row reads NOT-RUN: "needs the TSA certificate and root you trust". Some TSAs built on OpenSSL send their certificates in an order the parser refuses. The verifier puts only that set in order (it is not covered by the TSA's signature), and the row says so: "certificate set re-ordered, unsigned; signature unaffected".

### 15.5 Anchoring with OpenTimestamps (public calendars)

OpenTimestamps is public and free. A proof is first pending, then, after some hours, completed in a Bitcoin block. It needs no extra to write.

```
onetrace anchor runs/<run_id> --source opentimestamps \
    --calendar https://a.pool.opentimestamps.org --calendar https://b.pool.opentimestamps.org
```

- A random nonce is added to the chain head before it is hashed and sent, so a calendar never sees the chain head itself. No calendar is built in.
- The pending record reads NOT-RUN, "pending: not yet in a block".
- Later, complete it:

  ```
  onetrace anchor runs/<run_id> --source opentimestamps --upgrade --headers headers.json
  ```

  The completed proof is stored as a new record; the pending one is kept, since a record is never rewritten. Its `asserted_time` is the block's time, from your header file. You learn which block to fetch only once a calendar has completed the proof: if that block isn't in your header file yet, `--upgrade` stores nothing and names its height. Add that block's header and run it again. Every upgrade is checked before any is stored, so a refusal stores nothing. An upgrade already stored is named and not stored again; that exits 0 only when no proof is still pending.
- A header file is a JSON object mapping each block height (decimal) to its 80-byte header as 160 lowercase hex characters. It is your trust (see `non-claims.md`).
- To check a completed anchor:

  ```
  onetrace-verify runs/<run_id> --headers headers.json
  ```

  Without a header file, the row reads NOT-RUN, "needs block headers". The block's time is Bitcoin's own and can be up to two hours off: Bitcoin's own consensus rule allows a block's timestamp that much leeway. So an `asserted_time` within two hours of it agrees.

`onetrace diff` and `onetrace localize` show each run's anchors as an annotation (`anchoring [side]: …`). An anchor never changes a stage's verdict or the exit status.

### 15.6 The `[crypto]` extra, pinned

Anchor checks, and RFC 3161 anchoring, need one extra: `pip install "onetrace-verify[crypto]"` (or `onetrace[crypto]`). Its dependencies are pinned exactly, and `requirements-crypto.txt` beside each `pyproject.toml` lists every file of each by its sha256. For a hash-checked install:

```
pip install --require-hashes -r requirements-crypto.txt
pip install --no-deps onetrace-verify
```

Without the extra, each anchor still has its structure, size limits and chain-head binding checked; a failure there is FAIL, and only then does it read NOT-RUN, "install onetrace-verify[crypto] to check anchors".

## 16. Decorators

`@ot.run` and `@ot.stage` record a pipeline from two decorators, over the same Recorder described
above. This section grows with them; what is documented here is what is built.

### 16.1 What a decorated stage stores

Each call of a decorated stage is one node. Its arguments are recorded as inputs, named by
parameter. Its return value is stored as the node's output artifact, so a later comparison can
show what changed in it, not only that it changed:

- **`bytes`** (or `bytearray`) are stored exactly as returned, as `return.bin`, media type
  `application/octet-stream`.
- **Any other value** is stored as `return.json`, media type `application/json`, in the decorated
  values' encoding: RFC 8785 JSON, with numbers allowed (floats in their shortest round-trip form,
  integers up to 2^53 - 1), keys in a fixed order and no whitespace. This is not `ctx.write_json`'s
  form, which refuses numbers: the two encodings are kept apart on purpose.
- **A value neither covers** (an object with no registered encoder) stops the stage with
  `UnencodableValue`, naming the stage, the parameter and the type. It is never stored as
  `repr()`.

An argument that is an earlier stage's return value, passed on unchanged, is recorded as an edge
from that stage (`receipt:<stage>`), not as a second copy of the value.

### 16.2 Fields you didn't state

Three fields say what a value means, and the decorators never guess them:

- **`trust=`**, the trust class of the values a stage records (its arguments and its `files=`).
  A stage's own `trust=` applies; otherwise its run's `trust=`. With neither, the values are
  recorded as `externally-sourced`, the most cautious class, and the stage lists `"trust"` in
  `assertions.undeclared`. A stage whose only inputs are earlier stages' return values records no
  value under a trust class, so it lists nothing for it. The run's own arguments (the `intake`
  stage) follow the run's `trust=` the same way.
- **`rederivable=`**, whether the stage's output can be made again from its inputs. Stated on the
  stage (with an optional `note=` saying why) or on `ot.pkg`, it is recorded as stated. Stated on
  neither, the instrument records `rederivable: "false"` with `rederivable_note: "not stated by a
  person"`, and the stage lists `"rederivable"` in `assertions.undeclared`. A `note=` on a stage
  without `rederivable=` is refused when the stage is decorated.
- **`output_trust=`**, the trust class of what the stage returns: `operator-authored` for content
  your code constructed (counts, digests, an index of ids), `externally-sourced` for content that
  arrived from outside (documents, passages, a prompt that quotes them), `model-generated` for a
  model's output. It is separate from `trust=`: a retriever reads your query and returns someone
  else's documents. Unstated, the return value is recorded as `externally-sourced`, and the stage
  lists `"output_trust"` in `assertions.undeclared`. Any other value is refused when the stage is
  decorated. The examples state it on every stage; none of them calls a model, so none shows
  `model-generated`.

The list is written by onetrace, not by your code, so it needs no constant beside it. A stage that
declared no constants of its own carries no `constants` at all:

```json
"assertions": {"undeclared": ["output_trust", "rederivable", "trust"]}
```

A run with undeclared fields is valid and verifies. Nothing is inferred: a field listed in
`undeclared` was not stated by a person, and its recorded value is the cautious default. Add the
meaning when you know it, and the list shrinks.

### 16.3 Which stages a run expects

A decorated run declares its stages up front, as every run does: `"intake"` first when the run
function has parameters, then every `@ot.stage` defined in the run function's module, in the order
they are defined. Pass `@ot.run(stages=[...])` to declare them yourself, for example when the stages
live in several modules.

A stage called during the run that isn't declared is refused at the call. The message names both
fixes: add it to `@ot.run(stages=[...])`, or define the stage in the run's module. Because the
run's arguments are recorded as the `intake` stage, a stage named `"intake"` in the same module as
a run with parameters is refused when it is decorated.

### 16.4 `async def`

Both decorators take `async def` functions, and the decorated function is still a coroutine
function. An async run keeps its record open across every `await`, including in the tasks it
starts with `asyncio.gather` or `asyncio.create_task`: they copy the run with the rest of their
context. Sync and async stages mix freely in one run. The same pipeline written sync and async
records the same nodes, inputs, outputs and edges; only the times, and the order in which
concurrent stages finish, can differ.

### 16.5 A stage called more than once

By default a stage runs once in a run, and its node is the stage's bare name (`retrieve`), as in a
hand-written run. A second call of such a stage is refused with `AmbiguousInstance`, and the message
names both ways to allow it:

- **Declare the stage repeating:** `@ot.stage("refine", ..., repeats=True)`. Every call is
  numbered from the first, `refine#1`, `refine#2`, and so on, even when it runs only once. Loops
  and retries are declared this way.
- **Name each call:** `refine.instance("en")(...)` records that call as `refine#en`. A name given
  this way always wins, in either kind of stage.

A name used twice in one run is refused. So is mixing named and unnamed calls of a stage that runs
once. Calls of one stage that overlap in time (in `asyncio.gather`, or in threads) must each be
named with `.instance()`: numbering them in the order they arrive would not be stable from one run
to the next, so an unnamed overlapping call is refused, even for a repeating stage.

`@ot.run(rederivable=..., note=...)` describe the `intake` stage's instrument, and nothing else.
Left out, the intake records the cautious `"false"` and lists `"rederivable"` in
`assertions.undeclared`. A run function without parameters has no intake, so passing them there is
refused.

### 16.6 Files a stage reads: `files=`

`@ot.stage(..., files=["data/corpus.json"])` digests each named file when the stage starts, before
the function is called, and records it as an input named by its basename (`corpus.json`), with the
stage's trust class. A relative path is read from the working directory at the call.

**This records the file's content when the stage began; it does not prove the function read it.**
If the function changes the file, the record still holds the content it had at the start. Reads
that aren't named in `files=` are not seen.

A missing file is the stage's failure: its receipt records the error, the function isn't called,
and the `FileNotFoundError` reaches you unchanged. Two files with one basename, or a file whose
basename is also a parameter's name, are refused when the stage is decorated, since the two inputs
couldn't be told apart. With `trust="secret"`, nothing is digested and the stage is refused.

### 16.7 When a stage fails

A decorated stage that raises gets a receipt recording the failure exactly as the Recorder API
records it: class `error`, the exception's type as the status, its text as the body, and the
instrument as the origin. The same exception object then reaches your code, unchanged. A stage
that raises `Refusal` records `refused` with its reason and detail, and the call returns `None`. A
return value that can't be encoded fails the stage the same way, with `UnencodableValue`.

The run is still closed and verifies. Each attempt of a retried stage is its own receipt, and all
are kept: declare the stage `repeats=True`, and the failed attempt and the retry are recorded as
`#1` and `#2`.

### 16.8 Switching recording off: `ONETRACE_DISABLE=1`

With `ONETRACE_DISABLE=1` in the environment, `@ot.run` and `@ot.stage` pass every call straight
through: the functions return what they always return, no run folder is created and no file is
written, and none of the refusals that only a recording run makes apply (a second call of a stage,
an undeclared stage, overlapping unnamed calls). `.instance(name)(...)` is a plain call. Nothing
optional is imported because of it.

The variable is read at each call, and only the value `1` switches recording off; unset, empty or
`0`, runs record as usual. Mistakes found when a function is decorated (a lambda as a stage, a run
with no source file and no `manifest=`) are still reported, since they don't depend on recording.

### 16.9 Values of your own types: encoders

Arguments and return values of the types in 16.1 (strings, numbers, booleans, `None`, lists and
dicts of these) are recorded as they are. Two more kinds are recorded without any setup:

- a **dataclass**, as the dict of its fields (a dataclass inside it the same way);
- a **pydantic model**, as `model_dump(mode="json")`. onetrace never imports pydantic itself.

For any other type, register an encoder, a function that turns the value into one of the above:

```python
ot.encoder(Money, lambda m: {"currency": m.currency, "cents": str(m.cents)})
```

An encoder covers subclasses of its type too, unless they have their own, and a registered encoder
wins over the built-in ones. If the encoder raises, or hands back a value of the same type, the
stage stops with `UnencodableValue`, naming the stage, the parameter and the type. A value with no
encoder stops the stage the same way: it is never recorded as `repr()`.

`bytes` passed as an argument are recorded exactly as they are, media type
`application/octet-stream`, the same way a stage's `bytes` return value is stored as `return.bin`.
Bytes inside a list or dict have no JSON form, so they stop the stage; pass them as their own
argument, or register an encoder for the type that holds them.

### 16.10 Choosing the run id: `ONETRACE_RUN_ID`

A decorated run takes its id from `ONETRACE_RUN_ID` when that is set and not empty, and records
`run_id_source: "caller"`; this is how a CI job runs a pipeline and then finds `runs/<id>`.
Otherwise the id is generated, as before. Either way, a `:` in the id is written as `-` in the
folder name only.

The id must be usable as one folder name on Windows and POSIX alike (after `:` becomes `-`): no
`/` or `\`, none of `< > " | ? *`, no control character or line break (16.12), no trailing space
or dot, not `.` or `..`, and not a name Windows reserves (`CON`, `NUL`, `COM1`, ...). Anything else
is refused at the call, naming the variable, and nothing is written.

A run folder that already holds anything is refused at the call, before it is touched: a record is
never merged into or overwritten. That includes a second decorated run in the same process with the
variable still set. Unset the variable or set a new id, or remove the old run. Under
`ONETRACE_DISABLE=1` nothing is written, whatever the variable says.

### 16.11 Stages in other threads

A decorated run is found through the calling context, and a thread pool's threads start with an
empty one. So `pool.submit(stage, x)` or `pool.map(stage, xs)` inside a run would find no run and,
as a plain function, record nothing. That is refused instead: a decorated stage called in a thread
with no run, while a decorated run is active anywhere in the process, raises `EmissionRefused`
naming the stage. Carry the run into the thread:

```python
pool.submit(contextvars.copy_context().run, retrieve.instance("en"), query)
```

`asyncio.to_thread` copies the context itself, so it needs nothing. If a call in another thread
really belongs to no run, call the undecorated function, `retrieve.__wrapped__(query)`. With no
decorated run active anywhere in the process, a stage in any thread is a plain function, as
outside a run.

### 16.12 Names that become folders

A stage's name and instance name the folder its outputs are staged in, and a decorated run's id
names its run folder. Each must be usable as one folder name on Windows and on POSIX alike,
whichever system records the run, because a run recorded on one is verified and reproduced on the
other. A name that can't be is refused before anything is written, with a `fix:` line naming it:
a stage name when the stage is decorated or the run is opened, an instance when `.instance(name)`
is called or the node starts. Refused: an empty name, `.` and `..`, `/` or `\`, any of
`< > : " | ? *`, a trailing space or dot, a name Windows reserves (`CON`,
`PRN`, `AUX`, `NUL`, `COM1`-`COM9`, `LPT1`-`LPT9`, with or without an extension), and more than
255 bytes. A stage name, an instance and a run id are also refused if they contain a control
character or a line break of any kind (Unicode categories Cc, Cf, Zl and Zp, among them a
right-to-left override or a zero-width space) or a lone surrogate: every name has to print as
itself, in the verifiers' output and the reports. Windows also limits a whole path to 260 characters unless long paths are enabled, which
a name check can't see: keep run folders and names short there.

### 16.13 Linking a query run to its ingest run

Ingest (load, split, embed, index) usually runs once, and query runs read what it built. Say which
recorded ingest run a query run read, on the stages that read it:

```python
@ot.run(corpus=ot.corpus_from("runs/2026-10-01T09-00-00Z-ingest", stages=["retrieve"],
                              index_stage="split"))
def query(question): ...
```

- The first argument is the ingest run's folder, or its chain head (`sha256:` and 64 lower-case
  hex), looked up one level down in the folder that holds your query runs.
- `stages` is required and names stages of this run. A name the run doesn't have, or `"intake"`, is
  refused: when the run is decorated if it states `stages=[...]`, otherwise when it starts, before
  anything is written.
- When the run starts, the ingest run is verified, as `onetrace diff` verifies a run. If it doesn't
  verify, or the chain head isn't found, the query run is refused before anything is written: it
  never links to a record that hasn't been checked.
- `index_stage`, when you give it, names the ingest stage whose output is the chunk index. That
  stage must exist and have one, or the run is refused naming which is missing.
  It is recorded on the linked stages as the constant `corpus_index_stage`, only when given, so a
  change of index stage between two runs shows as a changed setting.
- The link, the ingest run's chain head, is recorded as `assertions.corpus_manifest` on exactly the
  named stages, on every call, and on no other. It needs no constant; a stage whose only assertion
  is the link has no `constants` in its record. A `corpus_manifest` your own code writes with
  `ctx.corpus_manifest` still needs one, and its digest must be in the record's form.

**The link shows which recorded corpus the query run declared it used; it does not prove the
retriever read only that corpus.**

`onetrace localize QUERY_A QUERY_B --doc <document> --runs-root runs/` follows the link one hop
when a query run has no chunk index of its own. It finds the ingest run by its chain head one level
down in `runs/`, verifies it, and takes the chunk index from the ingest stage named as the index.
The hits still come from the query run's own retrieval output, and the view says which run each
part came from. If the ingest run isn't found or doesn't verify, or no index stage is named, the
view reads COULD NOT CHECK and says which.

### 16.14 Settings known only at run time: `ot.constant` and `ot.assertion`

A setting read from a file or an argument can't go in `ot.pkg(config=...)` when the stage is
decorated. Record it from inside the stage instead:

```python
@ot.stage("split", instrument=ot.pkg("splitter", "llama-index-core", kind="transformer"))
def split(docs, settings):
    ot.constant("chunk_size", settings.chunk_size)
    chunks = ...
    ot.assertion("chunk_count", len(chunks))
    return chunks
```

They write the running stage's constants and assertions, numbers and booleans spelled as in
`Instrument.config` (`512` as `"512"`, `False` as `"false"`). An assertion still needs a constant
beside it. Outside a run, and with `ONETRACE_DISABLE=1`, they do nothing. Inside a run but outside
any stage there is nothing to record them on, and they are refused.

### 16.15 numpy arrays, LangChain documents, LlamaIndex nodes, and index objects

- **A numpy array** passed to or returned by a stage is recorded as bytes, not as metadata: NumPy's
  own `.npy` form, which carries the dtype, the shape and the order, written from a C-ordered copy,
  media type `application/x-npy`. A returned array is stored as `return.npy`. An array of Python
  objects has no byte form and stops the stage; so does an array inside a list or dict (pass or
  return it on its own). A numpy number inside a value (`np.int64`, `np.float64`, `np.bool_`) is
  recorded as the Python number it holds.
- **LangChain's `Document` and LlamaIndex's nodes** are pydantic models, so they are recorded as
  their JSON dump, with no setup.
- **Index objects** (a FAISS index, a vector-store client) have no encoder, and passing one stops
  the stage. Pass the path of the persisted index instead, and name it in `files=`.

None of these packages is imported by onetrace itself; an encoder is looked up only for a value
whose package you have already imported.

### 16.16 Numbers and booleans: rule M for settings, rule V1 for values

A decorated pipeline records numbers and booleans in two places, each with its own rule.

**Rule M: settings and assertions** (`ot.constant`, `ot.assertion`, and an instrument's `config`
when a stage records it: `ot.pkg(config={"top_k": 4})` and `config={"top_k": "4"}` record the same
digest).
A record's constants and assertions are strings, so a value is written as its string:

- a `bool` as `"true"` or `"false"`;
- an `int` as its decimal string (`3` as `"3"`);
- a `float` in RFC 8785's number form, the shortest decimal that reads back as the same double:
  `0.1 + 0.2` as `"0.30000000000000004"`, `1e21` as `"1e+21"`, `-0.0` as `"0"`. Exponent form is
  used outside 10^-6 <= |x| < 10^21;
- NaN and Infinity have no such form, and are refused, naming the key.

No type is recorded beside the value: `0.7` and `"0.7"` give the same digest, as `3` and `"3"` do.
If the difference matters to you, say it in the key or the value.

**Rule V1: arguments and return values** recorded as artifact bytes (16.1). These are stored as
RFC 8785 JSON, media type `application/json`:

- numbers are allowed: floats in rule M's form, integers within +-(2^53 - 1); a larger integer
  stops the stage with `UnencodableValue`, whose fix is to record it as a string;
- booleans are JSON `true` and `false`;
- keys are sorted and there is no whitespace.

**The two encodings, named apart:**

- **`ctx.write_json`: the SDK's canonical form, no numbers.** The Recorder API's own form is
  unchanged: it refuses a number, so a value you write yourself is always a string you chose.
- **Decorated values: RFC 8785, numbers allowed.** Only what the decorators store for you
  (arguments and return values) uses it.

Neither changes the record's format: a receipt records an output's name, digest and media type,
not how its bytes were encoded.

### 16.17 `@ot.run`'s defaults

Everything `@ot.run` doesn't take from its arguments, it takes from these defaults:

| Option | Default |
|---|---|
| `policy` | `"fail-closed"` (5.8) |
| `manifest` | the source file of the module that defines the run function. With no source file (a REPL, a notebook cell) `@ot.run` is refused when it decorates, with `fix: pass manifest=<path to your pipeline file>` |
| topology | always on for a decorated run: its manifest carries `edges`, since a decorated pipeline may fan out, fan in or overlap, which a run in declared order can't record |
| `stages` | optional. Left out: `"intake"` (when the run function has parameters), then every `@ot.stage` name defined in the run function's module, in definition order, each once (16.3) |
| the intake stage | `"intake"`, only when the run function has parameters: each argument is recorded as an input named by its parameter, in rule V1's encoding (16.16), with the run's `trust=` (16.2). A stage of your own named `"intake"` in that module is refused |
| the return value | not recorded on its own: what a run returns is a stage's return value, recorded by that stage (16.1) |
| `run_id` | generated, recorded with `run_id_source: "generated"`; `ONETRACE_RUN_ID` gives your own (16.10) |
| `run_dir` | `"runs/{run_id}"`, with a `:` in the id written as `-` in the folder name only; the recorded `run_id` keeps its `:` |
| `sign_with` | none: the run isn't signed. A key file's path, or `onetrace.env("NAME")`, signs the run at close (17.2) |
| everything else | the `Recorder`'s own defaults (5.1) |

### 16.18 What a run says when it closes: `ONETRACE_QUIET=1`

When a decorated run closes, `@ot.run` writes two lines to stderr: the folder the run was written to,
and the `onetrace-verify` command that verifies it.

```
onetrace: run written to runs/demo
next: onetrace-verify --require-artifacts runs/demo
```

They are written once per run, after the run's record is complete, also when a stage raised and the
run ends in an error. A folder holding a space, or a character a shell would read, is shown in double
quotes, so the command can be pasted as it is; the folder is shown with `/` on every system, which PowerShell,
cmd.exe and sh all accept. stdout is never written to.

Only a decorated run (`@ot.run`) says this. A `Recorder` you open and close yourself (section 5)
writes nothing to stderr when it closes.

`ONETRACE_QUIET=1` in the environment suppresses the two lines; only the value `1` does. With
`ONETRACE_DISABLE=1` (16.8) no run is opened, so nothing is written.

The same setting also silences `onetrace-verify`'s summary line and its `fix` lines, which it writes to stderr (section 8.1). Its rows and verdict on stdout, its exit code and `--json` don't change.

## 17. Signing a run

A signature is an Ed25519 signature over a finished run's chain head, by a key you hold. It is stored as its own file, `signatures/<n>.json`, beside the run's receipts. Like an anchor, it is never part of the chain: signing changes no byte that was there before, so the chain head stays byte-identical, and a run may carry several signatures (a recorder and a reviewer, say). Signing and anchoring work together in either order.

**A signature does not show:**
- that the key wasn't stolen or misused;
- that the run's output is correct;
- when the record was signed (that is an anchor's job);
- who the person behind the key is. The verifier knows keys, not people; your trust list is how you connect a key to a name.

What it does show: the holder of that private key signed this exact record.

### 17.1 Making a key

```
mkdir -p ~/keys
onetrace keygen --out ~/keys/recorder.key
```

`onetrace keygen` writes a new private key as PEM, with owner-only permissions (0600) on Linux and macOS, and prints the public key, its `key_id` (the `sha256:` fingerprint of the public key's 32 raw bytes) and where the private key was written; it never prints the private key. It never overwrites a file, and it refuses a path inside a run folder. It doesn't create folders, so make the key's folder first, as above: a path whose folder is missing is refused, and nothing is written. On Windows it can't set owner-only permissions itself: the file inherits its folder's access list, and `keygen` says so. Keep the key in a folder only you can read.

`--test-only` adds a first line saying the key was made for tests. A test key is made for one test and never reused.

### 17.2 Signing

- **At close:** `Recorder(..., sign_with="~/keys/recorder.key")`, or `sign_with=onetrace.env("ONETRACE_SIGNING_KEY")` for a key held in an environment variable as PEM text. `@ot.run(sign_with=...)` passes it to its recorder. A key path may start with `~`. The key is checked before the run writes anything; the run is signed after its manifest is written and verified, once.
  - A run that recorded nothing writes no manifest, so there is nothing to sign: `close()` returns as it would without `sign_with`.
  - If signing fails at close (the key file was removed since the run started, say), `close()` raises `SignRefused`: the manifest stands, the run is unsigned, and the run folder is released. Sign it afterwards with `onetrace sign`. If the signature was stored but couldn't be confirmed, `close()` raises `SignNotConfirmed`, and a second `close()` doesn't sign again. Under `@ot.run` either exception comes out of the decorated call.
  - A signature says who signed the record, not that it verified: under `fail-open`, a run the verifier refused is still signed. Check it with `onetrace-verify`.
- **Afterwards:** `onetrace sign RUN --key PATH` or `onetrace sign RUN --key-env NAME`, with an optional `--signer "label"`. It exits 0 when the signature is stored and confirmed, 1 when it is refused (nothing stored), and 3 when it was stored but could not be confirmed as landed in this run.

**Key custody.** The key is never written into a run folder, never logged and never printed. A key file inside the run folder is refused before it is read, whether it is really there, reached through a link inside the folder, or a hard link to it anywhere under the folder (the refusal names that file, never the key). A key path must be a regular file of at most 64 KiB. In CI, keep the key in the CI secret store and pass it as an environment variable with `--key-env` or `onetrace.env(...)`.

`--signer` (or `signer=`) is a label the signer claims, such as "nightly CI". It is stored as a claim and only ever reported as claimed: the name the verifier shows as the signer comes from your trust list, never from the record.

Signatures are stored the way anchors are (section 15): names are allocated without overwriting, the record is linked in from beside `signatures/`, and it is reported stored only when it is confirmed in this run's folder. **Sign a run folder that nobody else is writing to.**

### 17.3 Checking signatures: `onetrace-verify RUN --trust FILE`

The trust file lists the keys you trust, each with your label for it:

```json
{"format": "onetrace-trust/0.1", "keys": [{"key_id": "sha256:<64 hex>", "label": "ci-key"}]}
```

Each file in `signatures/` gets one row, after the anchors' rows:

| Signature | Row |
|---|---|
| Valid, and the key is on your trust list | **PASS**: "signed by ci-key (sha256:…)" |
| Valid, but the key is not on your trust list (or no `--trust` was given) | **SIGNED-UNTRUSTED**: "signed by an untrusted key sha256:… -- signer not on the reader's trust list". Never a pass. |
| An `alg` this verifier doesn't implement | **NOT-RUN**, naming the algorithm |
| Without `onetrace-verify[crypto]` | **NOT-RUN**: "install onetrace-verify[crypto] to check signatures" |
| Invalid, or for another run's chain head, or malformed | **FAIL** |

A FAIL makes the verifier's result FAIL (exit 1). SIGNED-UNTRUSTED and NOT-RUN leave the result as it would be without the signature. After the summary, each count has its own line. An untrusted signature reads "records beside the chain: 1 signed by an untrusted key -- signed, and the signature is valid, but by a key not in your trust file: it shows the record is unchanged since signing, not who signed it. It leaves the result as it would be without it." `--json` gives the counts as `summary.records_signed_untrusted` and `summary.records_not_run`, each with its note. For a signed run, the text output also prints what a signature does not show, and `--json` carries the same four statements as `"non_claims"`. A run with no signature reads exactly as before. The command a run prints when it closes (`next: onetrace-verify --require-artifacts …`, section 16.18) has no `--trust`, since a run can't know its reader's trust file: add `--trust FILE` to see a trusted signature as PASS.

**The order of the checks is fixed.** The file's size and nesting caps, the record's structure and its binding to this run's chain head come first, with or without the extra and whatever the algorithm; a failure there is FAIL. Only then may a row read NOT-RUN. A malformed record, or one for another run, is never shown as NOT-RUN.

**The record:** `format`, `"stage-receipt-signature/0.1"`; `chain_head`; `alg`, `"ed25519"`; `public_key`, 64 lowercase hex; `key_id`, which must be the public key's fingerprint; `signature`, base64 of the 64-byte signature over `stage-receipt-signature/0.1:` followed by the chain head; and optionally `signer`, the claimed label. A record written as `onetrace-signature/0.1`, the name before 0.2.0, is FAIL: a development build before 0.2.0 wrote it, and it can't be made valid. The fix is to move it out of `signatures/` and sign the run again with `onetrace sign`, which writes the new one.

**onetrace's own strictness.** The approved −01 text leaves these open:
- a member the record format doesn't define is FAIL, and the row names it;
- a file in `signatures/` that isn't named `<n>.json` is FAIL;
- a `signatures/` that is a link is FAIL, and nothing in it is read.

`diff` and `localize` never change a verdict for a signature. A signed run's report carries its rows under `"signing"`, as the verifier reads them with no trust list, so a valid signature shows as SIGNED-UNTRUSTED there.
