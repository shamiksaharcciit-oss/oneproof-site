# Recipe for coding agents: instrument an existing Python pipeline with onetrace

You are adding onetrace to a codebase you did not write. Your job is to add **recording**, not to change **behaviour**. When you finish, the pipeline must produce exactly the same results as before, and every run must leave a record that `onetrace-verify` accepts.

Read all of this before editing. The rules in "Never" are hard rules. Fetch this file itself, as raw text, from https://oneproof.dev/onetrace/agents/instrument.md, and work from it, not from a summary of it.

**The rules, in short** (each is explained below):

1. Add recording. Change nothing the pipeline computes: no signature, output or logic changes.
2. Leave out `trust=`, `output_trust=`, `rederivable=` and `note=`, and ask the human about each.
3. No secret, token or key in a decorator, `config=`, `ot.constant` or a decorated function's arguments: a step that takes a client holding a key gets a thin wrapper (§3).
4. Never turn on signing, decorate library code, add network calls, anchoring or telemetry, or edit CI files unasked.
5. List in `@ot.run(stages=[...])` every stage the run's own module doesn't define when it is imported.
6. A literal setting goes in `config=`; a setting from a flag, an argument or a variable goes in `ot.constant`.
7. Use the real services. A stubbed run says so in its run id (`ONETRACE_RUN_ID=stub-…`), and isn't proof.
8. Run every run in full, verify it with `onetrace-verify --require-artifacts`, and compare two runs.
9. End with the report in §7, including your questions for the human.

## 0. Before you start

- Confirm Python ≥ 3.10 and that the project's tests pass **before** any change. Record the test command and its result. If the tests don't pass, stop and tell the human.
- Install: `pip install onetrace` (add it to the project's dependency file the way the project already does it: `pyproject.toml`, `requirements.txt`, lock file).
- **This needs onetrace 0.2.0 or later.** Check which onetrace Python actually imports:
  ```
  python -c "import onetrace, onetrace_verify; print(onetrace.__version__, onetrace.__file__)"
  ```
  If the version is below 0.2.0, or the path isn't in the environment the project runs in, make a fresh virtual environment and install onetrace there.
- Run `onetrace doctor`. Fix what it reports before going on.
- **Your own code needs an installed distribution.** `ot.pkg` reads the version of the package you name from its installed metadata. For a project that isn't installed, `ot.pkg` is refused when the stage is decorated, which for a stage at module level is when its module is imported (`package 'my-pipeline' is not installed, so its version can't be read`). For a project of scripts with no `pyproject.toml`, add a minimal one, then run `pip install -e .`, and tell the human you added it:
  <!-- not executed: a file to save, not a command; tests/test_agent_recipe_examples.py builds it -->
  ```toml
  [build-system]
  requires = ["setuptools>=77"]
  build-backend = "setuptools.build_meta"

  [project]
  name = "my-pipeline"
  version = "0.1.0"

  [tool.setuptools]
  py-modules = []
  ```

## 1. Find the run

A **run** is one call of one function that does the whole job once: answers one question, processes one document batch, handles one request. Find that function (often `main`, `run`, `handle`, `answer`, or the function the CLI or API route calls).

- If there are two kinds of run (for example an **ingest** job that builds an index, and a **query** that uses it), each gets its own `@ot.run`.
- **Link the query run to what it reads.** If the query reads an index that an ingest run built:
  - when the index is built before the run, by the project's own code, record that build as an **ingest run** (its own `@ot.run`, with its own stages), and link each query run to it with `@ot.run(corpus=ot.corpus_from(<ingest run folder>, stages=[<the stages that read it>]))`. The ingest run is verified when the query run starts. Keep the ingest runs in the same folder as the query runs: `onetrace diff A B --follow-corpus` then follows a changed link one hop into the two ingest runs and names the stage where they first differ, and why (manual, section 16.13);
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

- **`stages=[...]`:** by default a run records the stages its own module defines when it is imported. List every stage in the run's order, `@ot.run(run_dir="runs/{run_id}", stages=["retrieve", "generate"])`, when any stage is not one of those: a stage defined in another module, or a stage decorated inside a function while the run is running (a thin wrapper, below). A stage the run calls without that is refused, and the message names both fixes.
- **One import** per file you touch: `import onetrace as ot`. Change nothing else in the file: no reformatting, no renames, no signature changes, no logic changes. The thin wrappers and the folder digest below add code without changing what the pipeline computes.
- **`ot.pkg(id, package, kind=..., config=...)`**: `package` is the installed distribution that does the work (its version is read from its installed metadata; never type a version). `id` is a short stable name for the tool. For a stage that is your own code, `package` is your project's own distribution, as its `pyproject.toml` names it, installed (§0).
- **`config=` or `ot.constant`:** `config` is recorded as one digest, so when it changes a comparison says the stage's config changed, not which key. Put a setting in `config=` when it is a **literal value in the code**, copied exactly. A setting whose value comes from a flag, an argument, a settings file or a variable goes in `ot.constant("chunk_size", chunk_size)` inside the function, and a comparison then names it by its key (`constant chunk_size differs`). **Never record the value of an environment variable that holds a key or token.**
- **Model settings:** record the settings the code actually sends with the call: the model name, and whatever else it passes, each from where the code takes it. Don't add a setting the code doesn't send, to the call or to the record: a model can reject a parameter it doesn't support.
- **`files=[...]`**: files the stage reads from disk (corpus, index, prompt templates). Write each path as the code opens it: a relative path is read from the directory the pipeline runs in, not from the repository root.
- **A folder of documents:** `files=` records each file by its name, so two files with the same name in different subfolders are refused when the stage is decorated. For a folder, record one digest over its files' sorted relative paths and bytes, with `ot.constant`:
  ```python
  import hashlib
  from pathlib import Path

  import onetrace as ot

  def folder_sha256(root) -> str:
      root = Path(root)
      h = hashlib.sha256()
      for p in sorted((q for q in root.rglob("*") if q.is_file()),
                      key=lambda q: q.relative_to(root).as_posix()):
          h.update(p.relative_to(root).as_posix().encode("utf-8") + b"\0")
          h.update(hashlib.sha256(p.read_bytes()).digest())
      return h.hexdigest()

  @ot.stage("load", instrument=ot.pkg("loader", "my-pipeline", kind="reader"))
  def load(docs_dir: str) -> list[str]:
      ot.constant("docs_sha256", folder_sha256(docs_dir))
      ...
  ```
  A comparison then names the change as `constant docs_sha256 differs`.
- **A step that is a method on an object, or that receives an SDK client holding a key** (a retriever index's `search`, a function given `client`): don't decorate it. Add a **thin wrapper**: a small inner function that takes only plain values, uses the object or client from the enclosing scope, and is the decorated stage. The key never passes through a decorated function, and what the pipeline computes doesn't change. List the stages in `stages=[...]`, since they're decorated while the run is running:
  ```python
  import onetrace as ot

  MODEL = "your-model-name"

  def retrieve(index, question, k=2):
      @ot.stage("retrieve", instrument=ot.pkg("bm25", "my-pipeline", kind="retriever"))
      def search(question: str, k: int) -> list[str]:
          return index.search(question, k)
      return search(question, k)

  def generate(client, question, passages):
      @ot.stage("generate", instrument=ot.pkg("model-call", "my-pipeline", kind="model-call",
                                              config={"model": MODEL}))
      def call(question: str, passages: list[str]) -> str:
          return client.complete(MODEL, question + "\n\n" + "\n".join(passages))
      return call(question, passages)

  @ot.run(run_dir="runs/{run_id}", stages=["retrieve", "generate"])
  def answer(question: str) -> str:
      client = Client()        # the project's own client, holding its key
      return generate(client, question, retrieve(Index(), question))
  ```
  The object itself isn't recorded. Record what identifies it: the ingest run that built the index (`ot.corpus_from`, §1), or its name and version with `ot.constant`.
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
2. **Use the real services.** If a service the pipeline needs is down (a vector database, a model API), stop and tell the human. Never substitute stubs or mocks silently. A run made with stubs must say so in its run id, and it doesn't count as proof. If the human agrees to stub a model API, do it on the command line, with no mock code inside the pipeline: start a local fake endpoint, point the client library at it with its base-URL environment variable, and give the run a stub id, in one line:
   <!-- not executed: needs a fake endpoint listening on that port, and the project's own entry point -->
   ```
   ONETRACE_RUN_ID=stub-query-1 OPENAI_BASE_URL=http://127.0.0.1:8000/v1 python -m app "a question"
   ```
   `OPENAI_BASE_URL` is the `openai` package's variable; other client libraries name their own. Each run needs a new id: a run folder that already holds anything is refused.
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
  | the model, or a setting the code sends with it | … | … |
  | the model simply answered differently | … | … |

  Add rows for anything specific to this pipeline. Where a row says "no", say what would fix it: a setting to record, or a link to add.
- the test result before and after, the `onetrace-verify` result, and the `onetrace diff` of two runs (§5).

## Never

- Never change what the pipeline computes, its function signatures, or its outputs.
- Never set `trust`, `output_trust`, `rederivable` or `note` yourself. That includes calls to hosted models and external services: describe what you saw, and ask.
  - If your onetrace version makes you pass a trust class, pick the most cautious one, and list every choice in your report as a question.
  - Never mark text a user typed as `operator-authored`.
- Never put a secret, token, key or password into a decorator argument, `config`, `ot.constant`, or a stage's arguments. If a function receives an API key, or a client holding one, as an argument, don't decorate it: decorate a thin wrapper inside it (§3), or tell the human.
- Never create a `Recorder` at module level, and never decorate library code.
- Never turn on signing: no `sign_with=` on `@ot.run` or `Recorder`, and no `onetrace keygen` or `onetrace sign`. Signing is the human's choice, with the human's key.
- Never add network calls, anchoring, or telemetry.
- Never edit CI workflow files unless the human asked, and then only through `onetrace-ci init-ci`.
- Never claim the record shows the output is correct. It shows what each decorated stage received and produced, and that the record hasn't been altered since.
