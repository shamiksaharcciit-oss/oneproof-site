<!-- Paste this section into your repository's AGENTS.md (or CLAUDE.md, .cursorrules, copilot-instructions.md). Edit the bracketed lines. -->

## onetrace (run records)

This repository records each pipeline run with onetrace: one verifiable receipt per stage, written under `runs/`.

- **Run functions:** [e.g. `app/pipeline.py:answer_question`] carries `@ot.run`. **Stages:** functions decorated with `@ot.stage`.
- **When you change a decorated stage:** keep the decorator. If you change a setting recorded in `config=` or `ot.constant(...)` (chunk size, top-k, the model and the settings the code sends with it), update the recorded value in the same edit. A literal in the code goes in `config=`; a value from a flag, an argument or a variable goes in `ot.constant`, so a comparison names it by its key. A setting that changes without being recorded makes a later comparison say *that* the stage changed, but not *why*.
- **When you change how an index is built, or which collection or index a query reads:** update the recorded link or constants (`ot.corpus_from(...)`, or the collection name and ingest version recorded with `ot.constant`) in the same edit.
- **When you add a step that matters to the result:** add `@ot.stage` following the recipe at https://oneproof.dev/onetrace/agents/instrument.md. Only functions defined in this repository; never library functions; a decorated stage must not call another decorated stage. A stage defined in another module, or decorated inside a function while the run is running, is listed in `@ot.run(stages=[...])`.
- **Do not set** `trust=`, `output_trust=`, `rederivable=` or `note=`. A person decides those. Leave them out and mention them in your summary as questions.
- **Never** put secrets, tokens or keys into decorator arguments, `config`, `ot.constant`, or a decorated function's arguments: a step that receives a client holding a key gets a thin wrapper, as the recipe shows. Don't add or change `sign_with=`, and never create or commit signing keys: signing is a person's choice, with their own key.
- **Do not edit or delete** anything under `runs/` or `baselines/`. A baseline changes only in a pull request a person approves.
- **After changing pipeline code, check:**
  <!-- not executed: the bracketed line is the project's own test command, filled in when pasted -->
  ```
  [project test command]
  onetrace-verify --require-artifacts runs/<latest run>
  ```
  If CI runs `onetrace-ci gate` and it reports **review**, the summary names the first stage that changed; explain in the pull request whether that change was intended. Don't regenerate the baseline to make the gate pass unless a person asked.
- **To switch recording off locally:** `ONETRACE_DISABLE=1`. Don't remove decorators to silence an error; fix the cause or ask.
