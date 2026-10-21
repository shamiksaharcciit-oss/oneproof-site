# The record format, in plain words

Full, normative detail is the Internet-Draft:
`draft/draft-saha-stage-receipts-00.txt`. This page
is an orientation, not a substitute for it.

## A receipt

One JSON file per stage a pipeline ran. Every receipt carries thirteen required members:

| Member | What it says |
|---|---|
| `format` | `stage-receipt/<major>.<minor>` — which edition of this format the receipt is written in. |
| `run_id` | Which run this receipt belongs to. |
| `stage` | The stage's own name (`retrieve`, `split`, whatever the pipeline calls it). |
| `prev` | The digest of the previous receipt in the chain, or `null` for the first. |
| `time` | `started`/`ended` timestamps, each carrying an explicit zone. |
| `coverage` | Whether this receipt's own view of the run is `complete` or `incomplete`, and which stages it declares versus which it saw emit. Since format 0.3, `optional_stages` may name declared stages the run may skip; `complete` still means every declared stage emitted. |
| `emission` | Bookkeeping about how the receipt itself was produced. |
| `anchor` | Whether the run is `anchored` (published somewhere that fixes its position in time) or `unanchored`. |
| `instrument` | What ran this stage: a name, a version, and a digest that pins its exact configuration. |
| `inputs` / `outputs` | Every artifact the stage read or wrote, each with a digest, a byte count, and a declared trust class. |
| `assertions` | Named constants the stage is asserting hold, plus values measured against them. |
| `outcome` | One of `ok`, `refused`, or `error` — never left implicit. |

A receipt is **canonical JSON**: UTF-8, no BOM, keys sorted, no incidental whitespace, no JSON
numbers (a value that looks numeric is still a decimal string — `"500.00"` and `"500"` are
different strings on purpose). The verifier checks a receipt's own bytes against its own
canonical serialization; a receipt that doesn't match its own canonical form is refused before
anything else about it is even read.

## Trust classes

Every input and output declares one of three trust classes: `operator-authored`,
`model-generated`, or `externally-sourced`. This is a claim about *provenance*, not a claim of
correctness — a `model-generated` output is not thereby untrustworthy, and an
`operator-authored` one is not thereby correct. It's what lets a reader ask "was this bit fed by
something the pipeline generated on its own, or did it come from outside?" without reading the
bytes.

## A chain

Receipts link by digest: each receipt's `prev` names the digest of the one before it, and the
manifest's own `chain_head` names the digest of the last one. A chain with a stage's receipt
missing, reordered, or altered breaks a link somewhere, and the verifier reports exactly where.

## A manifest

One `MANIFEST.json` per run, naming the chain (each entry's file and digest, in order), the
overall `chain_head`, and the run's own `format` — the manifest's format string is
`stage-receipt-chain/<major>.<minor>`, a separate version line from a receipt's own `format`. A
manifest declaring a format the verifier doesn't implement is refused outright, by name, rather
than silently accepted.

Since format 0.3 the manifest says `outputs_kept`: `"all"` (each receipt's output files are kept
beside it, under `artifacts/`) or `"none"` (the run declares it keeps none; the receipts still record
every output's digest and size). A run that keeps none also says `"outputs_kept": "none"` in every
receipt's `coverage`, under the chain and any signature. A verifier reads `"none"` as a declaration,
never as files checked, and only where the manifest and every receipt agree.

## Two roots, for a per-document stage

A stage that processes many documents in a batch (a `split` stage producing per-document chunks,
say) carries two separate digests instead of one output digest: `receipts_root` (over the
receipts' own bytes — includes timestamps, so it's never equal across two runs even of identical
work) and `outputs_root` (over document-id/output-digest pairs only — equal exactly when the
stage did the same thing to the same inputs). **Compare `outputs_root`. Never compare
`receipts_root`** for sameness — it will never agree, by design, and comparing it anyway is the
single most common way to misread this format.

## A DAG, not just a chain

A stage can declare `receipt:<node-id>` inputs naming exactly which earlier receipts it read,
turning what would otherwise be assumed as a linear sequence into an explicit graph: fan-out,
fan-in, and loops are all expressible. `receipt:` inputs are structure, not data to be
digest-compared. A node present in one run and absent in another is a difference in the shape
of the run, not something the verifier tries to explain away.

## Format 0.3, and the path to 1.0

Format 0.3 (written by onetrace 0.4.0, read in full by onetrace-verify 0.4.0) adds three members,
each designed so that a verifier that doesn't know it reads the record the same or more strictly,
never more loosely:

| Member | Where | What an earlier verifier reads |
|---|---|---|
| `coverage.optional_stages` | receipt | A run that skipped an optional stage still says `incomplete`; its `--require-complete` fails it (stricter). A run that ran every stage reads the same. |
| `refused.attempted` | receipt | The links a step held before running would have read, kept apart from `inputs`, each naming a receipt earlier in the chain with its digest. It sees a refused step and a plan the edges keep to: the same verdict, without the path. |
| `outputs_kept` | manifest; with `"none"`, every receipt's `coverage` too | `"all"` or `"none"`. With `"none"` it sees the files absent, as before: the same verdicts. onetrace-verify 0.4 reads the manifest's copy only where every receipt agrees. |

That holds for every record onetrace writes. A member written wrongly by hand (an undeclared
optional stage, `refused.attempted` on a step that ran or naming a receipt that isn't an earlier one
by its digest, an `outputs_kept` other than `all` or `none`, or receipts and the manifest that
disagree on it) is one an earlier verifier doesn't read at all, so it reads that record more loosely than
onetrace-verify 0.4, which fails it. Verify format 0.3 records with onetrace-verify 0.4.

Format 0.3's rejection vectors are in tests/rejection_0_3/: eleven runs, each changed in one of these
members and re-linked, each FAILed by onetrace-verify 0.4 on the row its INDEX.json names, with what
onetrace-verify 0.3.0 reads of it.

The path to 1.0:

1. **0.3 is the last minor that adds a required behaviour.** After it, a 0.x minor only adds
   members an earlier verifier can ignore with the same reading.
2. **1.0 when all of these hold:** the Internet-Draft's next revision carries 0.3 as written; a
   second verifier implementation, not onetrace's own, passes the vector suite; two releases pass
   with no format change; the deprecations below are done.
3. **Before 1.0:** the preview literal `0.0-preview` stops being accepted for new records (it is
   still read); the `receipts_root` / `outputs_root` naming stays, with the warning above.
4. **What 1.0 promises:** every 1.x verifier reads every 0.x record it has ever been able to read;
   required members don't change within 1.x; a change that would change a reading is 2.0.
