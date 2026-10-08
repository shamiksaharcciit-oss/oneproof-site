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
- **COULD NOT CHECK** — the stage can't be evaluated: an unimplemented format major version, a
  declared boundary placed at or before it, a file the verifier can't read. This is not a pass,
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
