# The record format, in plain words

Full, normative detail is the Internet-Draft:
[`draft/draft-saha-stage-receipts-00.txt`](../draft/draft-saha-stage-receipts-00.txt). This page
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
| `coverage` | Whether this receipt's own view of the run is `complete` or `incomplete`, and which stages it declares versus which it saw emit. |
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
