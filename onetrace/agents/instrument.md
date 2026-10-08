# Recipe for coding agents: instrument an existing Python pipeline with onetrace

You are adding onetrace to a codebase you did not write. Your job is to add **recording**, not to change **behaviour**. When you finish, the pipeline must produce exactly the same results as before, and every run must leave a record that `onetrace-verify` accepts.

Read all of this before editing. The rules in "Never" are hard rules.

## 0. Before you start

- Confirm Python ≥ 3.10 and that the project's tests pass **before** any change. Record the test command and its result. If the tests don't pass, stop and tell the human.
- Install: `pip install onetrace` (add it to the project's dependency file the way the project already does it: `pyproject.toml`, `requirements.txt`, lock file).
- Run `onetrace doctor`. Fix what it reports before going on.

## 1. Find the run

A **run** is one call of one function that does the whole job once: answers one question, processes one document batch, handles one request. Find that function (often `main`, `run`, `handle`, `answer`, or the function the CLI or API route calls).

- If there are two kinds of run (for example an **ingest** job that builds an index, and a **query** that uses it), each gets its own `@ot.run`.
- **Link the query run to what it reads.** If the query reads an index that an ingest run built:
  - when the ingest run is recorded with onetrace, link it with `@ot.run(corpus=ot.corpus_from(<ingest run folder>, stages=[<the stages that read it>]))`;
  - when the index lives in an **external service** (Qdrant, Pinecone, Weaviate, a database), record its identity on the stage that reads it with `ot.constant(...)`: the collection or index name, and the ingest run id or version that built it, if the code knows it. Then list the service as a question for the human ("retrieve reads collection X in Qdrant, outside the run: how should it be treated?").

  Without a link, a later comparison can say *that* the retrieved chunks changed, but not that the index behind them changed.
- If you can't tell which function is one run, stop and ask the human. Do not guess.

## 2. Find the stages

A **stage** is a function the run calls that does one distinct step whose result matters. Typical stages in AI pipelines:

| Step | Typical `kind` |
|---|---|
| load / read documents | `reader` |
| clean, convert, normalise | `transformer` |
| split into chunks | `transformer` |
| embed | `embedder` |
| build or update an index | `indexer` |
| retrieve | `retriever` |
| build the prompt | `formatter` |
| call a model | `model-call` |
| parse the model's output | `parser` |
| act on it (write a file, call an API) | `actuator` |

Rules for choosing:

- Only functions **defined in this repository**. Never decorate a library function. If a single library call does several steps (for example `VectorStoreIndex.from_documents(docs)`), it is **one** stage, unless the human asks you to split it into small functions of the project's own.
- Prefer **fewer, meaningful stages** over many tiny ones. Five to ten is typical. Starting with just one stage is fine.
- A decorated stage must not call another decorated stage. Decorate the outer one or the inner ones, not both.

## 3. Add the decorators

```python
import onetrace as ot

@ot.run(run_dir="runs/{run_id}")
def answer_question(question: str) -> str:
    docs = retrieve(question)
    return generate(question, docs)

@ot.stage("retrieve",
          instrument=ot.pkg("bm25-retriever", "rank_bm25", kind="retriever",
                            config={"top_k": 4}),
          files=["data/corpus.json"])
def retrieve(question: str) -> list[str]:
    ...

@ot.stage("generate",
          instrument=ot.pkg("model-call", "openai", kind="model-call",
                            config={"model": "gpt-4.1-mini"}))
def generate(question: str, docs: list[str]) -> str:
    ...
```

- **Stages in another module:** by default a run records the stages defined in its own module. When a stage is defined in a different module from the `@ot.run` function, list every stage in the run's order: `@ot.run(run_dir="runs/{run_id}", stages=["retrieve", "generate"])`. A stage the run calls without that is refused, and the message names both fixes.
- **One import** per file you touch: `import onetrace as ot`. Change nothing else in the file: no reformatting, no renames, no signature changes, no logic changes.
- **`ot.pkg(id, package, kind=..., config=...)`**: `package` is the installed distribution that does the work (its version is read at run time; never type a version). `id` is a short stable name for the tool. For a stage that is your own code, `package` is your project's own distribution, as its `pyproject.toml` names it; its installed version is read the same way.
- **`config`**: only settings you can see as **literal values in the code** (chunk size, overlap, top-k, model name, temperature). Copy them exactly. If a setting comes from a variable, a settings file or an environment variable, use `ot.constant("chunk_size", chunk_size)` inside the function instead, and **never record the value of an environment variable that holds a key or token**.
- Record with `ot.constant` every setting you'd want named when two runs are compared, such as a model name or a chunk size.
- **`files=[...]`**: files the stage reads from disk (corpus, index, prompt templates). Write each path as the code opens it: a relative path is read from the directory the pipeline runs in, not from the repository root.
- **Values between stages** must be plain data: strings, bytes, ints, lists and dicts of these, pydantic models, dataclasses, numpy arrays. If a stage returns an object onetrace can't encode (an index object, a database client), don't change the function. Tell the human, and suggest either returning the saved index path or registering an encoder with `ot.encoder`.
- **A stage called more than once in a run:** by default a stage runs once per run, and a second call is refused. For sequential repeats (a loop, a retry), declare the stage `repeats=True`: each call is numbered #1, #2, …. For calls that overlap (`asyncio.gather`, a thread pool), name each call with a stable name per branch instead, for example `retrieve.instance("en")(question)` and `retrieve.instance("fr")(question)`.

- **What a stage depends on, but its code doesn't show:** for example, a prompt template in another module, or a settings file. Record its version or content hash with `ot.constant`, so a change to it is named as the reason.
- **Everything a stage uses must reach it in a way the record sees:** as an argument, a `files=` entry, or `ot.constant`. A value the stage takes from a global, an enclosing function or `self` (the user's question, a settings object) is not recorded, and a comparison will then show the stage's output changing while none of its inputs changed. Don't restructure the code to fix this. Record the value with `ot.constant` (for text, its SHA-256, never the text itself), and tell the human.
- **A stage that groups several steps** (for example `retrieve` = embed the query + search the index) stays one stage. Don't refactor to split it. Instead, **record the settings of every hidden step on that stage**: the embedding model, top-k, the collection name, and any filters. That's what lets a comparison say *why* the stage's output changed.

## 4. Leave the meaning to the human

These fields say what a stage *means*, and only a person may set them:

- `trust=`: where the values a stage reads come from (`operator-authored`, `externally-sourced`, …);
- `output_trust=`: the same, for what the stage returns. The trust class covers outputs too: a decorated stage's output with no stated class is recorded with the most cautious one and listed as undeclared, like an input's;
- `rederivable=` and `note=`: whether running the stage again gives the same output (a hosted model usually doesn't).

**Do not set these.** Leave them out. onetrace then records the most cautious value (`externally-sourced`; not re-derivable) and lists the field as `undeclared` on that stage, so everyone can see nobody stated it. At the end, list them as questions for the human (step 7), with what you observed, for example: *"`generate` calls a hosted model: is it re-derivable? (usually no)"*.

## 5. Check behaviour is unchanged

1. Run the project's test command. The same tests must pass as in step 0, with the same results. If anything differs, undo your change to that function and report it.
2. **Use the real services.** If a service the pipeline needs is down (a vector database, a model API), stop and tell the human. Never substitute stubs or mocks silently. A run made with stubs must say so in its run id (set `ONETRACE_RUN_ID=stub-query-1` for that run), and it doesn't count as proof.
3. Run **every run function in full** (for a RAG pipeline, the whole ingest run *and* the whole query run, all stages), the way the project normally runs it or through the test that exercises it. A folder appears under `runs/` for each, and when each run closes it prints that folder and the command that verifies it, on stderr. A shortened demo run that skips stages doesn't count.
4. Verify it:
   <!-- not executed: <run_id> stands for the folder your run wrote -->
   ```
   onetrace-verify --require-artifacts runs/<run_id>
   ```
   Exit code 0 means the record is intact. The verifier's first line, on stderr, says so (`record intact: …`), or names the first failing row (`record NOT intact: …`), and under it a `fix (…)` line for each failing row says what to change and which section of the errors page explains it. Don't set `ONETRACE_QUIET=1` while you check: it silences those lines. Anything else: read that row and its `fix (…)` line; the errors page explains each one. `onetrace doctor` checks the setup and says whether the most recent run verifies, not why a row failed. Fix the instrumentation, not the pipeline.
5. **Run it a second time with nothing changed, and compare:** `onetrace diff runs/<first> runs/<second>`. Every stage should read `same`, except stages that call a hosted model, or read a service that changes by itself.
   - If any other stage differs, **stop and find out why before anything else.** The usual causes are ids generated fresh each run (uuid), timestamps written into outputs, absolute paths, and unordered sets or dict iteration.
   - Report it to the human with the stage and the field.
   - Until it's fixed, every comparison will blame that stage first and hide the real change.
6. Only then make one deliberate change (for example chunk size) and compare again. The first difference must be the stage you changed. `onetrace diff` and `onetrace localize` name a setting recorded with `ot.constant` by its key ("constant chunk_size differs"); for a setting in `config=` they say the stage's config changed, not which key. To have the key named, record the setting with `ot.constant`.
7. For a query pipeline, also compare two **different** questions. `retrieve` and the model's answer should normally differ. If they don't, report it: it usually means something was stubbed or cached. Also check that every stage that uses the question (retrieve, prompt building) lists it among its inputs.

## 6. Optional, only if the human asks

- CI gate: `pip install onetrace-ci`, then `onetrace-ci init-ci` (writes one workflow file and a minimal plan with a question for the human), then `onetrace-ci baseline propose --from runs/<run_id> --out baselines/golden`.
- Signing: **not yours to turn on.** If the human wants runs signed, they make the key (`onetrace keygen`), keep it, and add `sign_with=` themselves; the manual's section 17 explains it. **Never create, print, copy or commit a private key yourself.**
- Add the onetrace section to the repository's `AGENTS.md` (see the AGENTS.md section page), so later edits keep the instrumentation consistent.

## 7. Report to the human

End with a short report:

- the run function(s) and the stages you decorated, file and line;
- the settings recorded per stage, and any you saw but could not record;
- **questions**: every `trust`, `output_trust` and `rederivable` you left undeclared, each with what you observed;
  - whether runs should be signed, and with whose key: signing is the human's choice, with a key the human holds (`sign_with=`, `onetrace keygen`, `onetrace sign`);
  - if a stage splits documents into chunks: onetrace can record a chunk index (`ot.chunks`) so a comparison can show which chunk changed, and with `keep_text=True` its text. That changes the function's return value and stores the corpus text in run folders, so it is the human's choice; ask;
- what is **not** covered: steps inside library calls, files read but not listed, code you did not decorate, external services the run reads or writes;
- **what changes the record can and can't explain.** Don't report coverage as "n of n stages": you chose the stages, so that number is always complete. Instead, list the likely changes and say, for each, whether a comparison of two runs would name the stage **and** the reason:

  | Likely change | Explained? | Why or why not |
  |---|---|---|
  | a source document edited | … | … |
  | chunk size or overlap | … | … |
  | the embedding model (at ingest, and at query time) | … | … |
  | top-k or retrieval filters | … | … |
  | the external index changed (re-indexed or edited by hand) | … | … |
  | the prompt template | … | … |
  | the model, or its temperature and other settings | … | … |
  | the model simply answered differently | … | … |

  Add rows for anything specific to this pipeline. Where a row says "no", say what would fix it: a setting to record, or a link to add.
- the test result before and after, the `onetrace-verify` result, and the `onetrace diff` of two runs (§5).

## Never

- Never change what the pipeline computes, its function signatures, or its outputs.
- Never set `trust`, `output_trust`, `rederivable` or `note` yourself. That includes calls to hosted models and external services: describe what you saw, and ask.
  - If your onetrace version makes you pass a trust class, pick the most cautious one, and list every choice in your report as a question.
  - Never mark text a user typed as `operator-authored`.
- Never put a secret, token, key or password into a decorator argument, `config`, `ot.constant`, or a stage's arguments. If a stage function receives an API key as an argument, don't decorate it; tell the human.
- Never create a `Recorder` at module level, and never decorate library code.
- Never turn on signing: no `sign_with=` on `@ot.run` or `Recorder`, and no `onetrace keygen` or `onetrace sign`. Signing is the human's choice, with the human's key.
- Never add network calls, anchoring, or telemetry.
- Never edit CI workflow files unless the human asked, and then only through `onetrace-ci init-ci`.
- Never claim the record shows the output is correct. It shows what each decorated stage received and produced, and that the record hasn't been altered since.
