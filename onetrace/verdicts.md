# The five verdicts

Every stage in a two-run comparison (`diff`, or `localize` given two runs) gets exactly one of
five verdicts. There is no sixth.

- **same** — the stage's output digest matches on both sides.
- **FIRST DIFFERENCE** — the first stage, in chain order, whose output digest does not match.
  There is at most one of these per comparison.
- **downstream** — comes after the first difference and is still different. The divergence
  propagated forward, which is the ordinary case: a stage that consumes a changed input usually
  produces a changed output.
- **reconverged** — comes after the first difference, but matches again. Different work
  happened to produce the same result. This is reported honestly rather than hidden, because it
  happens in real pipelines (a reranker that recovers the same top document from a differently
  ordered candidate set, say) and silently folding it into "same" would erase real information
  about what actually ran.
- **COULD NOT CHECK** — the stage can't be evaluated: a format version the verifier doesn't
  implement (a major other than 0, or a minor that isn't ASCII decimal digits), a declared boundary
  placed at or before it, a file the verifier can't read. This is not a pass,
  and it never gets silently treated as one.

## What a verdict is about

A verdict is always about a stage's **output** — specifically, `outputs_root` for a per-document
stage (see [the format page](format.md#two-roots-for-a-per-document-stage)), or the output
digest directly for a run-scoped one. A difference in the **instrument** that produced the
output (its name, version, or configuration digest), or in the **constants** a stage asserts,
never changes a verdict by itself. It shows up as an **annotation** alongside the ladder instead
— naming exactly what differs — so a `same` verdict never hides that *how* an output was
produced changed even when the bytes it produced didn't.

## The overall result, separately

Each verb also reports one word for the whole comparison, with its own exit code:

| Verb | Result words | Exit codes |
|---|---|---|
| `diff` | `identical`, `diverged`, `not comparable`, `refused`, `could not check` | 0, 1, 2, 3, 4 |
| `localize` (two runs) | same five words as `diff` | same five codes |
| `localize` (one run) | `clean`, `located` (plus `refused`/`could not check`) | 0, 1 (3, 4) |
| `reproduce` | each stage is `REPRODUCED`, `DIVERGED`, or `COULD NOT CHECK` | 0 all reproduced, 1 any diverged, 4 any could-not-check and none diverged, 3 refused |

`reproduce`'s own three outcomes are a different question from the five verdicts above: they
answer "if I re-run this stage's own code right now, does it produce what the receipt says it
produced," not "do two already-recorded runs match." `rederivable` is measured by actually
re-executing the stage, never declared; a stage that isn't rederivable keeps its originally
recorded outputs rather than being treated as broken.

## A run's verdict against a reference (onetrace 0.6)

A [reference](references.md) is a sealed record of a known-good run. `onetrace verdict RUN
--reference FILE` reads a finished run against one and gives each step one word, and the run its
own. A verdict is derived from the record and the reference's declared rule; nothing is inferred.

A re-run is never counted (0.7). On a run whose receipts carry the re-run mark `rerun`, the verdict's
first line says so, `re-run: reproduce of <run id>; not counted`, and the words below it are the same
words as for any run. The verdict JSON keeps the mark as `rerun`.

**The run's word** is one of four, with the same exit codes the other verbs use:

| word | means | exit |
|---|---|---|
| `identical` | every step matched | 0 |
| `diverged` | a step's output, setting or input differs from the reference; the verdict names the first such step | 1 |
| `refused` | the run is refused (it does not verify, or a step was held) | 3 |
| `could not check` | the verifier could not check the run, or the reference names a step the run does not record | 4 |

**Each step's word** is one of seven, each with the record item it rests on:

- **same output** — the step's output digests match the reference.
- **output differs** — they do not.
- **setting differs** — the instrument's configuration digest, or a constant the rule counts,
  differs.
- **input differs** — a data input's digest differs.
- **slower than its range** — the step matched on output, setting and input but ran longer than the
  reference's timing range. Timing is a **view**: a step slower than its range is never a divergence
  and never fails a verdict.
- **no output recorded** — the step records no outputs, in the run and in the reference alike, so
  there was no output to compare; its settings and inputs matched. A decorated run's `intake` step,
  whose arguments are inputs, reads this. It never makes a run diverge. A step with outputs on one
  side and none on the other reads **output differs**, naming the side that records none.
- **could not check** — the reference names this step; the run does not record it.

Among the first three differences the order is output, then setting, then input: a step reads the
first that holds. The run `diverged`s at the first step that reads output, setting or input differs.

**onetrace-verify** gains the same verdict over a run and a reference, as rows beside its others:
`--reference FILE` adds one row per step — PASS (same output, or slower than its range), FAIL
(output, setting or input differs), or NOT-RUN (could not check) — and a row for the reference's
seal and, where it carries one, its signature. A nested run is checked against its own reference
with `--nested-reference FILE`, given its folder with `--nested-run`; with no reference for it, the
nested run reads NOT-RUN with the reason. A run verified without `--reference` reads exactly as
before. The verifier reads the reference with its own canonicalizer and imports nothing from the
SDK.
