# The three verbs

Every verb calls the reference verifier first (via the installed `onetrace-verify` package,
resolved automatically — see the [quickstart](quickstart.md)). A
run or a receipt the verifier refuses is refused by the verb too; no comparison or check is
attempted against something the verifier itself won't stand behind.

## `diff`

```
onetrace diff BASELINE CANDIDATE --out OUT_DIR
```

Compares two runs stage by stage and reports the [five verdicts](verdicts.md) as a ladder, the
first point of difference (if any), and annotations for anything about *how* a stage ran that
changed without changing its output. Writes both a text report and the same information as
canonical JSON, side by side, in `OUT_DIR`.

## `localize`

```
onetrace localize RUN [CANDIDATE] --out OUT_DIR
```

With one run, finds the first unclean stage in it alone — `clean` if none, `located` at the
first `COULD NOT CHECK` or refused stage otherwise. With two runs (`CANDIDATE` given), it's the
same comparison `diff` performs, reported the same way — `localize` and `diff` share their
underlying ladder; the difference is intent, not mechanism.

`--doc DOC` (two-run form only) narrows to one document's chunk set under both runs, digest by
digest, when a per-document stage's `outputs_root` differs and the question is *which* documents
moved.

## `reproduce`

```
onetrace reproduce RUN [STAGE] --runner RUNNER.json --out OUT_DIR
```

Re-executes a recorded stage's own code, for real, and compares what comes out against what the
receipt already claims. `RUNNER.json` names the command to run and how to fill in its
parameters from the record. Each stage
comes back `REPRODUCED`, `DIVERGED`, or `COULD NOT CHECK` — never a fourth thing, and
`rederivable` is never declared, only measured by actually re-running the code.

With `STAGE` omitted, every stage in the run is attempted. A stage the runner declares
non-rederivable (an LLM call with no fixed seed, say) reports `COULD NOT CHECK` with the reason
named, and its originally recorded outputs are kept rather than treated as invalidated.

## `anchor`

```
onetrace anchor RUN --source rfc3161 --tsa-url URL --tsa-cert CERT --tsa-root ROOT
onetrace anchor RUN --source opentimestamps --calendar URL [--calendar URL ...]
onetrace anchor RUN --source opentimestamps --upgrade --headers HEADERS.json
```

Not one of the three: it compares nothing. After a run has closed, it asks a source you name to
attest the run's chain head, and stores the answer as a new record in `anchors/`, beside the chain;
the chain head doesn't change. It is the only onetrace command that contacts a network, and only
when you run it; no source is built in. Before anything is stored, the record is checked the way
the verifier will check it, and what would read `FAIL` is refused. Exit status: 0 stored (or, for
`--upgrade`, already stored, with nothing still pending: the record holding it is named and
nothing new is stored), 1 refused (nothing stored), 2 a usage error (nothing asked of any
source), 3 stored but not confirmed. See the manual's section 15.

## Common to all three

- `--verifier DIR` overrides where the reference verifier is read from; the default is the
  installed `onetrace-verify` package, resolved via `importlib.resources` — never a path
  relative to onetrace's own source location.
- `--stages STAGES.json` is needed only for the "summary" record kind (two-root form with no
  chain manifest); a `MANIFEST.json`-based run doesn't need it.
- `--quiet` suppresses the text report; the JSON report is always written.
