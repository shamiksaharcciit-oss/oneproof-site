# Compare runs: diff, localize, reproduce

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

`--mask FILE` names release noise (settings, timestamps, ids, paths, JSON fields) not to count as a
difference; every row it changes says so. See [the manual](manual.md#release-noise---mask-file).

`--durations` adds each node's time in both runs, read from its receipts' `time.started` and
`time.ended`, and the note "slower" where the candidate took at least `--slow-factor` times as long
(default 2) and at least `--slow-min-ms` more (default 1000). Timing is a view: it never changes a
verdict, the exit code or any other part of the report. `localize` takes it too, with two runs.

## `localize`

```
onetrace localize RUN [CANDIDATE] --out OUT_DIR
```

With one run, finds the first unclean stage in it alone — `clean` if none, `located` at the
first `COULD NOT CHECK` or refused stage otherwise. With two runs (`CANDIDATE` given), it's the
same comparison `diff` performs, reported the same way — `localize` and `diff` share their
underlying ladder; the difference is intent, not mechanism.

`--for STAGE` (two-run form only) starts from one stage's output and names where the change it
shows starts: walking back through the differing stages it reads from, by the links both runs
recorded. A change that output never reads from, or one that reconverged before it, is never named
as an origin. See [the manual](manual.md#one-outputs-path-localize---for).

`--doc DOC` (two-run form only) narrows to one document's chunk set under both runs, digest by
digest, when a per-document stage's `outputs_root` differs and the question is *which* documents
moved.

## `drift`

```
onetrace drift RUN RUN [RUN ...] [--against first|previous] --out OUT_DIR
```

Many runs of one pipeline, oldest first, side by side: each compared with the first (or, with
`--against previous`, with the run before it) exactly as `diff` compares two, one column per
compared run and one row per node, each cell the verdict `diff` gave. The exit code is that of the
first comparison, in run order, whose exit code isn't 0, or 0. `--mask` and `--durations` work as
for `diff`; with `--durations`, every time slower than the run it was compared with is listed.

## `match`

```
onetrace match RUN [--runs-root DIR] --out OUT_DIR
```

Lists the runs one level down in `DIR` (default: the folder holding `RUN`) given the same recorded
inputs as `RUN`, each checked by the verifier, newest first. `diff` and `localize` point to it when
two runs were given different inputs. See [the manual](manual.md#runs-on-the-same-input-onetrace-match).

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
