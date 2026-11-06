# References: a sealed record of a known-good run

A **reference** is a sealed record of a run you vouch for, or of selected steps of it: per step,
the output digests, the settings, the data inputs and a timing range, with the rule for the step.
A later run is checked against it with [`onetrace verdict`](verdicts.md), which gives each step one
word and the run its own. A reference is its own file, format `onetrace-reference/1`; it is never a
receipt and never part of a run's chain.

## Making one

```
onetrace reference make RUN… --out FILE [--steps NODE …] [--mask FILE] [--sign FILE | --sign-env NAME]
```

- `RUN…` is one or more finished runs that verify. A run that is refused, or that the verifier
  could not check, is not a known-good run: making a reference from it is refused, naming it.
- A re-run is not an original run (0.7). A run whose receipts carry the re-run mark `rerun`, such as
  the run `onetrace reproduce` produces, is refused, naming it: `<RUN> is a re-run (reproduce of
  <run id>): a reference is made from an original run`. The manifest's copy of the mark alone marks
  nothing. onetrace 0.6.1's `reference make` accepted a marked run.
- The output digests, the settings and the data inputs are taken from the first run; the **timing
  range** is taken across every run given (a range needs more than one run — a single run gives a
  point, not a range, so a reference made from one run carries no timing).
- `--steps NODE` keeps only the named steps (by node id, `name` or `name#instance`); the default is
  every step of the first run.
- The reference is **sealed** as a receipt is: its `seal` is the SHA-256 content digest over its
  canonical bytes. `--sign FILE` or `--sign-env NAME` signs the seal with an Ed25519 key, the way a
  run's chain head is signed; a reader checks the signature as they check a run's.

```
onetrace reference show FILE
```

prints a reference as text: its seal, its signature, the runs it was made from, and per step the
outputs, inputs, settings and timing range.

## What a step holds

| field | what it is |
|---|---|
| `outputs` | the step's output digests, by name |
| `inputs` | the step's **data** inputs by digest (not the `receipt:` links to earlier steps, which are the run's structure) |
| `settings` | the instrument's configuration digest and the stage's own constants (onetrace's own `onetrace.*` constants are not settings) |
| `timing_ms` | the range `{min, max}` across the runs given, when more than one gave a readable time |
| `rule` | `exact` (the default), or a mask |

## The rule

The default rule is **exact**: a step's output digests, its settings and its data inputs must match
the reference. `--mask FILE` (an [`onetrace-mask/0.1`](verbs.md) file) names settings not to count
as a difference; the reference records the rule in full, so a reader sees exactly what was not
counted. Outputs are always compared by digest — a reference holds digests, which a value mask has
nothing to act on — so a tolerance on a numeric output waits for the per-step values a later
release records, not this one.

## A pipeline may hold several

A pipeline's golden set is its references — one per release, say. Each is a separate file; a run is
checked against whichever one you name.

## What a reference does not claim

- A step matching its reference shows it did what the known-good run did, not that either was right.
- A reference is a statement that this run is the one to compare against, not that it is correct.
- The seal shows the reference was not changed after it was made; the signature shows who made it,
  under the trust the reader places in the key. Neither shows the run it was made from was correct.
