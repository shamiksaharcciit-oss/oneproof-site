# The record format, in plain words

Full, normative detail is the Internet-Draft:
`draft/draft-saha-stage-receipts-02.txt`, which describes the members through format 0.4, the re-run
mark, the step's effect label, step expectations, the kept configuration and the check run among them.
Its earlier revision -01, beside it, is kept as it was, and revision -00 describes format 0.1. This page
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

onetrace 0.5 stays in format 0.3: its optional blocks — `authorization` (onedoor decisions), the
span context (`trace`, `traceparent`) and the nesting fields (`parent`, `children`, `parent_run`,
`parent_stage`) — are optional members a 0.4.0 verifier reads unchanged, ignoring the blocks it does
not know, so a 0.5 receipt verifies exactly as a 0.4.0 one does and a run that records none of them
is byte-identical to 0.4.0.

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

## Format 0.4: every run ends with a close receipt

Format 0.4 is written by onetrace 0.7, and it is that release's one minor. Everything onetrace 0.7
adds under it is optional members only: nothing removes a required member, changes a type or
changes a canonical form.

**What this build writes.** Of the members below, this build writes:
- the close receipt, and the not-closed signature record;
- the model-call record 1.1 in its self-hosted form, with the members the table marks;
- with onetrace-auto, the members of an auto-recorded run that the table marks;
- `effect_label` on a declared stage, and on a step a check or a counterfactual puts in place;
- the re-run mark of all four kinds, `reproduce`, `twin`, `counterfactual` and `check`, with
  `writes_allowed`, `config_of_*`, `substituted` and `from_stage` where the kind has them, and the two
  `re-run stopped` forms of `onetrace.ended_by`;
- a check's run (`onetrace.check`);
- `config_kept`, the kept configuration;
- step expectations: `expectations` in a receipt, and the `onetrace-expectations/1` file
  `onetrace expect write` writes.

The members the table below marks "not yet" are specified here and in the Internet-Draft's revision
-02, and no onetrace build writes them yet. Each line names its row of the table, then what in it is
not written:
- manifest, `auto`: `boundary` `request`, and `key`;
- receipt, `effect_label`: the value `unknown`, and the basis `not classified`;
- receipt, `outputs[].empty`: the member;
- receipt, `return_holds`: the member;
- reference, `steps.<node>.reads`: the member;
- reference, `steps.<node>.empty_outputs`: the member;
- model-call record 1.1, `steps.level`, `steps.method`: in a hosted record;
- model-call record 1.1, `steps.k_requested`, `steps.k_returned_min`, `steps.k_returned_max`, `steps.count`, `steps.logprobs`: in a hosted record, and `steps.logprobs` in a self-hosted one;
- model-call record 1.1, the steps file, hosted form: the file;
- model-call record 1.1, `identity.digest`, `call.kind`: `identity.digest`, and the call kind `endpoint`;
- embedding record 1.0, the members it shares with the model-call record: the record;
- embedding record 1.0, `embedding.*`: the members;
- embedding record 1.0, `output.*`, `usage.tokens`, `batch.size`, `rows`: the members;
- embedding record 1.0, `fingerprints[].quantity`: the member.

### The version lines

| Version line | Before | Format 0.4 | Written by this build |
|---|---|---|---|
| receipt `format` | `stage-receipt/0.3` | `stage-receipt/0.4` | yes |
| manifest `format` | `stage-receipt-chain/0.3` | `stage-receipt-chain/0.4` | yes |
| signature record | `stage-receipt-signature/0.1` | `0.1` kept for a closed run; `0.2`, written only for a run signed not closed | yes |
| model-call record | `model-call-record/1.0` | `model-call-record/1.1` | self-hosted: yes; hosted: not yet |
| embedding record | none | `embedding-call-record/1.0`, new | not yet |
| reference | `onetrace-reference/1` | `onetrace-reference/1`, unchanged: optional members only | not yet |
| expectations file | none | `onetrace-expectations/1`, new | yes |
| runner | `onetrace-runner/0.2` | `onetrace-runner/0.3`: `{input:<name>}` and `config.*` params | yes |
| runner table | none | `[[runner]]` in onetrace-explain's configuration file: `code`, `command` (`{stage}` and `{run}` only), `cwd`, `timeout_seconds`; read by the SDK on Python 3.11 and later | yes, by `onetrace check` |

The receipt and manifest members below are all under `0.4`, and the model-call record's under `1.1`.
The signature record, the model-call and embedding records, the reference and the runner are outside
the Internet-Draft. The expectations file is specified in its revision -02, section 4.15.

### The close receipt

**What it is for.** A run killed before it closed (`SIGKILL`, `os._exit`, out of memory, power lost)
leaves a folder whose chain verifies to the last receipt written, with a manifest that agrees with
it. That is exactly the shape of a closed run with fewer steps, and nothing else in the record
tells the two apart. onetrace-verify 0.6.1 reads such a run PASS.

**What is written.** When a run closes, before its final manifest, its verify hook and any
signature, the recorder writes one more receipt, the **close receipt**:

- stage `onetrace.close`. Every run declares it as its last stage, after its own stages and any
  intake. The name is reserved: a stage of a team's may not take it, and the recorder refuses one
  that does;
- instrument `onetrace.close`, kind `close`, at onetrace's own version, `rederivable: "false"`;
- no inputs and no outputs, outcome `ok`;
- three constants, under the prefix onetrace keeps for its own: `onetrace.closed: "true"`,
  `onetrace.steps` (how many receipts come before it) and `onetrace.ended_by`:
  `exit`, `unhandled exception: <class>` (a decorated run whose function raised) or `SIGTERM`.
  Every reader leaves `onetrace.` constants out of a step's settings, and a team's constant of
  that form is refused. So a reference made from a closed run, read by onetrace 0.6.1's `verdict`
  or by onetrace-verify 0.6.1's `--reference`, doesn't fail a run that closed another way or after
  another number of steps;
- in a re-run, the re-run mark `rerun`, as every receipt of a re-run carries (below).

`onetrace.ended_by` has five forms in format 0.4. Beside the three above, a re-run stopped by the
replay rule writes `re-run stopped before <node>: effect <value> (<basis>)` at a step with a label,
or `re-run stopped before <node>: effect not recorded` at a step with none. This build writes all
five: the last two in the run `onetrace reproduce` produces, where the replay rule stops it before a
step, with a boundary of kind `re-run stopped` whose note holds the same words. An auto-recorded run that reaches its store bound closes with `exit` (below): that is
not a sixth form, and there is none.

**`exit` says the interpreter exited normally.** An app's own signal handler that ends the process
through `sys.exit` writes `exit` too, so `exit` does not say the work ran to its end.

Its digest is the chain head, so a signature, which is over the chain head, covers it.
`onetrace.close` is declared, so no receipt before it can read `complete`, the last step included:
**only the close receipt can read `complete`**, and only when every declared stage emitted and no
boundary stands. A run in which nothing happened writes no close receipt, as it writes no
manifest. `max_run_bytes` bounds a run's steps: the close receipt counts toward it but is never
refused by it, so a run that reached its bound still closes. A close receipt that cannot be written
is recorded as a gap, like any other receipt, and the run then has no close receipt.

**A run with no close receipt** was killed, ended without closing, or was written before format
0.4. Its chain verifies to its last receipt, and in a 0.4 run that last receipt reads `incomplete`.
onetrace-verify 0.6.1 reads such a run as it reads any run, PASS when what was written is intact.
This release's onetrace-verify gives every run a row of its own, `the close receipt`: PASS, `closed: by
<onetrace.ended_by>`, for a run whose chain ends with its close receipt; NOT-RUN, `not closed: the record
ends at <last step> and holds no close`, for a run with none, which `--require-closed` makes a FAIL; and
FAIL for a close receipt that is not last, a second one, an `onetrace.steps` that does not count the
receipts before it, an `onetrace.ended_by` outside its five forms, a constant missing, or
`onetrace.close` not the last declared stage. The NOT-RUN row cannot tell a run stopped before its
close from a run written before format 0.4, and says only that the record holds none.

**The close receipt is optional for every reader,** so the promise of the path to 1.0 above holds
unchanged. A reader never fails a run for lacking one. Every run written before format 0.4 verifies
exactly as it did. A writer from onetrace 0.7 always writes one, as its own choice, not as a
requirement on any record a reader is given. Two reading rules keep it so:

1. **A receipt is a close receipt only when its own `format` is `stage-receipt/0.4` or later and
   its instrument is `onetrace.close` of kind `close`.** Before 0.4 the name was not reserved, so a
   run written then can hold an ordinary stage named `onetrace.close`, with any instrument. Such a
   receipt is read as the ordinary step it is.
2. **Completeness is read off the last receipt, as before.** The writer is what makes the close
   receipt the only one that can read `complete`, so a reader adds no rule, and a run written
   before 0.4 that reads `complete` still does.

**How onetrace-verify 0.6.1 reads a 0.4 run.** It accepts any minor of major 0, so it reads a 0.4
run's close receipt as an ordinary receipt: a closed run reads PASS, and a killed 0.4 run reads
PASS, as a killed 0.3 run does.

**The verbs read the close receipt as what it is, not as a step.** `onetrace diff`, `localize`
and `reproduce` set it aside before they compare, so the steps they compare are the same with
and without it, and the search for a first difference never lands on it. When one run closed and
the other did not, or both closed with different endings, a comparison says so in a line of its
own, before any step difference:

```
close: run A closed (exit); run B not closed, its record ends at answer
```

The line changes no verdict and no exit code. `onetrace reference make` leaves the close receipt
out of a reference. Where a reference made earlier holds it as a step, `onetrace verdict` skips it
and names it, under `set_aside`, as not a step. It skips a step only on both sides: the run set its
close receipt aside, and the reference's entry has a close receipt's exact shape (no outputs, no
data inputs, no constants of its own, and the empty configuration's digest). The same reading rule
applies: a stage named `onetrace.close` in a run written before 0.4 is a step, and is compared as
one.

**A gap: an empty stage of that name is still skipped.** A reference records neither the
receipt's format nor its instrument's kind, so the verdict reads the entry's shape. A stage named
`onetrace.close` in a run written before 0.4 with no outputs, no data inputs, no constants of its
own and an empty configuration has exactly that shape, and against a closed run it is skipped, not
compared. Recording both parts in a reference is not in this release.

**Only a closed run is signed by default.** `onetrace sign` refuses a run with no close receipt.
`--not-closed` signs it anyway, in format `stage-receipt-signature/0.2`, with `closed: "false"`,
over `stage-receipt-signature/0.2:not-closed:` followed by the chain head, so the statement can't
be removed without the signature failing. A closed run's signature is unchanged:
`stage-receipt-signature/0.1`, over the chain head, which is the close receipt's. onetrace-verify
0.6.1 FAILs a 0.2 record (it names the member `closed`, which it does not know), the stricter
reading: under no verifier does a signature make an interrupted run look finished. This release's
onetrace-verify reads a 0.2 record: on a run that is not closed it is checked over its own statement,
and its row says `signed as not closed`; on a closed run it FAILs, `a not-closed record on a closed run`.

**Byte-identity with 0.6.1 ends at 0.7.** A 0.7 run is never byte-identical to a 0.6.1 run of the
same pipeline: its format strings say 0.4, every receipt declares `onetrace.close`, and its chain
ends with the close receipt.

### An auto-recorded step

**Every HTTP step's `status` output.** A step onetrace-auto records from an HTTP call
(`httpx.send`, `requests.send`) has two outputs: `status`, the canonical JSON object
`{"status": "<code>"}`, and `response`, the response body's bytes. A `requests` call that followed
redirects is one step: its `status` is the final response's, with the number of hops,
`{"redirects": "<n>", "status": "<code>"}`, and its `response` is the final body. An `httpx` step's
`status` never carries `redirects`. A streamed response has `status` alone: its body is not read.
So a status that differs is an output that differs, whatever the body.

**A model step's `auto.target` is `{"host": "<host>"}` alone:** the host the client's request went
to, read through the client's public `post` while the call runs. It has no `method`, `path_digest`,
`path` or `query_names`. A model step whose hook did not see the client's request has no `target`.

**The boundaries an auto-recorded run declares.** When it opens, one boundary over its first
declared stage, of `kind` `not observed` with the `note` `steps outside the hooked libraries`, so its
coverage never reads `complete`. When it reaches its store bound, it declares the boundary of `kind`
`store bound reached`, with the `note` `nothing after this point is recorded`, at the step that
reached it, and closes, with `onetrace.ended_by` `exit`: the five forms above stand, with no sixth.
That boundary's `name` is the step, its node id `<stage>#<instance>` (`httpx.send#2`): a boundary's
`name` is a declared stage, or a step: the step that reached the store bound, or, for the `re-run
stopped` boundary, the step the re-run stopped before. The step that reached the
bound is recorded as a gap at its own index, the index its receipt would have had, in the next
receipt written and in the manifest, as the draft's section 9 records an absence. Every later hooked
call in that process goes ahead unrecorded. **A decorated run's own auto step** that reaches that run's
store bound, a top-level auto step or a stage's child, records the same gap at its index and the same
boundary naming it, and its call goes ahead; but the run is not closed. Recording goes on, and `@ot.run`
closes the run at its end.

**The constants an auto-recorded step carries.** Each is under the `onetrace.` prefix, which
onetrace keeps for its own, as the close receipt's are: every reader leaves `onetrace.` constants
out of a step's settings, and a team's constant of that form is refused. So none of them ever reads
as a setting that differs.

| Constant | Value | On |
|---|---|---|
| `onetrace.http.body` | `not observed: streamed` | an HTTP step whose response was streamed: it has no `response` output |
| `onetrace.http.request` | `not observed: streamed` | an HTTP step whose request body was streamed (an iterator): it has no `request` input |
| `onetrace.http.request` | `not observed: the text cannot be encoded as it will be sent` | a `requests` step whose text body the installed urllib3 would send as ISO-8859-1, and which that cannot encode: no digest is taken, and it has no `request` input |
| `onetrace.model_call` | `not written: the hook did not see the client's request` | a model step on a client made before onetrace-auto's boot, or a model step whose call failed before it reached the client's `post`: no model-call record, no credential, no host |
| `onetrace.model_call` | `not written: embeddings have no record format in this release` | an embeddings call: no model-call record |

**How this release's onetrace-verify reads an auto-recorded run.** Each receipt with an `auto` block gets
its rows: the block's members and its `target`'s shape (an HTTP step's, or a model step's `host` alone);
`declared` is `"false"`; the step carries `effect_label`, its value one of the three and its basis one of
the six, as the producer documents it for the library (the table below); an HTTP step's `status` output
in its form, read where the output was kept; and its `onetrace.` constants, each one the format gives.
A run onetrace-auto opened itself, the process run or a request run, gets two: the manifest's `auto` block,
and the open boundary. A decorated `@ot.run` that holds auto steps gets neither: its auto steps get their
rows, and the run keeps its own declared coverage, so its close may read `complete`. onetrace-verify knows
a run onetrace-auto opened by the manifest's `auto` block or by the open boundary, in the manifest or in any
receipt's coverage; it makes no claim about a process run rewritten without both and re-linked, which reads as a
decorated run, nor about a decorated run whose team declares that exact boundary, which reads as one onetrace-auto
opened. The summary line ends `auto-recorded: N steps, not declared`. An auto step's thread `context`, where present, is read: `thread
without the run's context` is its one value, and any other FAILs. A run whose receipts declare stage lists that
differ gets one row, `declared stages grow only by auto stages`: a later list may add only the stages of the chain's
auto steps, every earlier name in its place, and a removal, a reorder or another added name FAILs. A run whose
receipts all declare one list, a straight decorated run among them, gets no such row.

**The effect labels the producer documents, by library.** At minor 4 an `effect_label`'s basis is one of
six: `declared on the stage`, `model call`, `model call stored by the provider`, `http method`, `not
classified` and `substituted, not executed`. A record holding any other basis is outside the format, and
its row FAILs, naming the basis. For an auto-recorded step, onetrace-verify reads the label against what
the producer documents for the step's library:

| Library | Value | Basis | On |
|---|---|---|---|
| `httpx`, `requests` | `read` | `http method` | a `GET` or `HEAD` |
| `httpx`, `requests` | `write` | `http method` | any other method |
| `openai` | `write` | `model call stored by the provider` | a `responses.create` call without `store=False` |
| `openai` | `read` | `model call` | any other call |
| any | `unknown` | `not classified` | a call the hook cannot classify |

A label outside its library's rows FAILs. On a `responses.create` step either `openai` label reads as
documented: the receipt does not hold `store`. A library the producer does not document reads NOT-RUN,
`<library>: no documented bases`; its value is still checked against the three, and its basis against
the six. `onetrace.sdk_verify`, the SDK's own verifier, has none of the rows this release's
onetrace-verify adds for format 0.4.

### Every member format 0.4 adds

Every scalar is a string, and every member is optional: a record that does not hold one reads as a
record written before 0.4 does.

| Record | Member | Values | Written by this build |
|---|---|---|---|
| close receipt | `stage.name`, `instrument` | `onetrace.close`, reserved; instrument `onetrace.close`, kind `close`, onetrace's version | yes |
| close receipt | constants `onetrace.closed`, `onetrace.steps`, `onetrace.ended_by` | `true`; the number of receipts before it; the five forms above | yes |
| signature record | `closed` | `false`, in `stage-receipt-signature/0.2` only, inside the signed bytes; `--not-closed` is refused on a closed run | yes |
| receipt | `auto` | `declared` (`false`), `call`, `library`; for an HTTP call `target`: `host`, `method`, `query_names` and one of `path_digest` (the default) or `path` (only with `ONETRACE_AUTO_HTTP_PATH=plain`); for a model call `target`: `host` alone; and on a step recorded from a thread that did not carry the run's context, `context`: `thread without the run's context` | with onetrace-auto: yes |
| manifest | `auto` | `boundary` (`process`, `request`), `hooks` (each `library`, `status`, `version`), `key` | with onetrace-auto: `boundary` `process` and `hooks`; `request` and `key` not yet |
| receipt | `rerun` | `kind` (`twin`, `counterfactual`, `reproduce`, `check`), `of_run`, `of_chain_head`; a twin, and a check under the baseline's settings: `config_of_run`, `config_of_chain_head`; a counterfactual: `substituted`; a check: `from_stage`. In every receipt of a re-run, the intake and close receipts included | kind `reproduce`, in the run `onetrace reproduce` produces, kind `twin`, in the run `onetrace reproduce --config-of` produces, kind `counterfactual`, in the run `onetrace reproduce --substitute` produces, and kind `check`, in the run a check of `reproduce` produces: yes |
| receipt | `rerun.from_stage` | the node id a check started from: required for `check`, absent for every other kind | yes |
| receipt | `rerun.writes_allowed` | plain `reproduce` only, and required there: `true` when `--allow-writes` was given, `false` otherwise | yes |
| receipt | `rerun.substituted` | `step`, `from_run`, `from_chain_head`, `from_receipt`, `output`, `output_digest` | yes |
| manifest | `rerun` | a copy of the receipts' `rerun` (below) | kinds `reproduce`, `twin`, `counterfactual` and `check`: yes |
| check run | stage `onetrace.check` | reserved; instrument `onetrace.check`, kind `check`. Its constants (`verb`, `argv`, `runner_digest`, `rerun_plan`, `timeout_seconds`, `baseline`, `candidate`, `stage`, `claim`, `predicted`) and assertions (`exit`, `result`, `came_back`: `as predicted`, `otherwise`, `did not run: <reason>`) are ordinary constants and assertions | yes, by `onetrace check`; the constants `baseline` and `stage` only where the verb has them, and `runner_digest` and `rerun_plan` for `reproduce` only |
| receipt | `effect_label` | `value` (`read`, `write`, `unknown`) and `basis` (`declared on the stage`, `model call`, `model call stored by the provider`, `http method`, `not classified`, `substituted, not executed`). Required on a receipt with an `auto` block; absent on an unmarked declared stage and on the recorder's own receipts (intake, close) | on a declared stage marked `effect="read"` or `"write"`: yes, basis `declared on the stage`; with onetrace-auto: `read` and `write`, basis `http method`, `model call` and `model call stored by the provider`; on a step a check or a counterfactual puts in place: `read`, basis `substituted, not executed`: yes; the others not yet |
| receipt | `config_kept` | `name` (`config.json`), `digest` (equal to `instrument.config_digest`), `bytes`; the file under `config/<receipt stem>/`, the receipt stem being the receipt file's name without its `.json`, for example `03-answer`. Where keys were left out of the kept file, `partial`: `true`, and `digest` is the kept bytes' digest; the next verifier then reads the equality as NOT-RUN, `configuration kept in part`, never FAIL | yes |
| receipt | `expectations` | each `name`, `kind` (`range`, `unit`, `relation`, `member`), `target`, `declaration`, `declaration_digest`, `declared` (`with the run`). A `relation`'s `declaration` is `op` (`difference`, `sum` or `ratio`), `of` (two JSON Pointers into the target's own output, joined by one space, as `/raw /offset`) and `within`: the target's value is within `within` of the first value less the second, the two added, or the first divided by the second. An expectation that holds shows the declared rule held, not that the output was right | yes |
| expectations file | entries | as `expectations`, with `declared`: `after the run`; the file sealed as a reference is. An expectation declared after the run says nothing about what was expected when the run was made, and one that holds shows the declared rule held, not that the output was right | yes |
| receipt | `outputs[].empty` | `true`, `false` | not yet |
| receipt | `return_holds` | each `at`, `child`, `child_at`, `digest`: a part of a child's return held, as the same object, in the caller's return | not yet |
| reference | `steps.<node>.reads` | stage names, sorted, unique; `[]` for none | not yet |
| reference | `steps.<node>.empty_outputs` | beside `outputs`, never inside an entry: the outputs the run marked empty, sorted, unique; `[]` for none; absent where any of the step's outputs carries no mark | not yet |
| model-call record 1.1 | `steps.level`, `steps.method` | `L1-hosted`, `L2-hosted`, and self-hosted `L1`, `L2`, `L3`; `provider-text`, and self-hosted `token-ids`, `top-k-ids`, `sha256-tree-512/v0` | self-hosted: yes; hosted: not yet |
| model-call record 1.1 | `steps.k_requested`, `steps.k_returned_min`, `steps.k_returned_max`, `steps.count`, `steps.logprobs` | decimal strings (`k_requested` `declared, not observed`, `k_returned_min` and `k_returned_max` and `steps.count` `observed`; all three k members `not applicable` at `L1-hosted`, as at self-hosted `L1`); `logprobs`: `none` (the default), `rounded-2`, `as-returned` | self-hosted, all but `steps.logprobs`: yes; hosted: not yet |
| model-call record 1.1 | the steps file, hosted form | `level`, `method`, `steps[]`, each `{chosen, candidates}`, each token `{text, bytes, provider_token_id, logprob}`, the last three where present | not yet |
| model-call record 1.1 | the self-hosted members | the steps file at L1, L2 and L3, `steps.surplus`, `engine.settings.model_runner`, the self-hosted `output.finish`, and the refusal at L3 with its `sampling.*` members and `engine.settings.logits_processors`: given once, in `docs/model-call-record.md`'s 1.1 section | yes |
| model-call record 1.1 | `identity.digest`, `call.kind` | `sha256:<hex>`; `call.kind` adds `endpoint` | not yet |
| embedding record 1.0 | the members it shares with the model-call record | `format`, `call.kind`, `call.api`, `credential`, `model.*`, `tokenizer.digest`, `engine.*`, `runtime.*`, `dtype`, `input.request_digest`, `input.token_ids_digest`, `engine.settings.*`, `identity.digest` | not yet |
| embedding record 1.0 | `embedding.*` | `pooling` (`mean`, `cls`, `max`, `last-token`, or the module's own name), `normalize`, `max_length`, `truncation` (`end`, `start`, `none`, `error`), `dimensions`, `input_type`, `encoding` (`float`, `base64`, `int8`, `uint8`, `binary`, `ubinary`) | not yet |
| embedding record 1.0 | `output.*`, `usage.tokens`, `batch.size`, `rows` | `vectors_digest`, `vectors_form` (`raw-<dtype>-le`, `json-decimal`, `base64-bytes`), `count`, `dimensions`, `norms` (`unit`, `not unit`); tokens or `not observed`; the batch size; each row `{position, input_digest, vector_digest, tokens}` | not yet |
| embedding record 1.0 | `fingerprints[].quantity` | adds `embedding-vectors`, in the embedding record only | not yet |

### Reading the new members

- **Absent is not `unknown`.** A missing `effect_label` says no label was recorded; `unknown` says
  a hook could not classify the call. Every reader's words for a missing label are `effect not
  recorded`, never `unknown`. The next verifier fails a receipt with an `auto` block and no
  `effect_label`. A substituted step's label is `read`, basis `substituted, not executed`: nothing
  ran.
- **The manifest's `rerun` copy marks nothing by itself.** It is read only where every receipt
  carries the same mark, and a tool that reads the manifest alone does not take it as one. The intake
  and close receipts of a re-run carry the mark like every other receipt.
- **`return_holds`:** `[]` means checked, nothing held; absent means not checked. `digest` is the
  sha256 of the held part's canonical bytes, as an output's digest is.
- **A check's run may hold local paths and output.** Its `argv` constant holds the filled `{run}`,
  and its outputs keep `stdout.txt` and a tail of stderr. The record's credential rule covers its
  constants and kept outputs like any other run's.
- **`identity.digest`** hashes a field's `status` alone where the field has no value, so two
  `not observed` fields whose reasons differ give one identity.
- **Reserved names.** A stage named `onetrace.close` or `onetrace.check` in a run written before
  0.4 is an ordinary step, in every reader. A receipt is a close or check receipt only when its own
  `format` is `stage-receipt/0.4` or later and its instrument is the reserved one of its kind.
- **The meanings of "declared".** The format uses the word in eight places:
  - `auto.declared: "false"`: the step was not declared in code;
  - `effect_label.basis: "declared on the stage"`: the label was declared in code;
  - `expectations[].declared`: `with the run` or `after the run`;
  - `coverage.declared_stages`: the stages the run declared;
  - `declared_edges`: the plan's edges, declared by the team;
  - the model-call state `declared, not observed`: given by the caller, not read back;
  - `reproduce`'s `COULD NOT CHECK` category `declared`;
  - "a declared step with no `effect_label`": a decorated stage the team named.

  Two meet on one receipt: an auto-recorded step's stage is in `coverage.declared_stages` (an auto
  run declares the stage names of its hooks), while its `auto.declared` is `"false"`.
- **A decorated run's declared stages may grow while it runs.** A decorated `@ot.run` gains an auto
  stage name the first time a hooked call inside it fires that stage: the name is added before the
  close stage, and no name is ever removed or reordered. Each receipt's `coverage.declared_stages` is
  the list as known when it was written, so an earlier receipt may declare fewer names than a later
  one. The close receipt's list is the run's whole list. A decorated run that fires no hooked call
  declares its team's stages and its close alone.

**How this release's onetrace-verify reads them.** Each has rows of its own, PASS, FAIL or NOT-RUN:
- **the re-run mark**, on a run whose record holds one: `a <kind> of <run> (<chain head>)`, or FAIL where
  the receipts disagree, the manifest's copy disagrees with them, `kind` is outside the four, or a member
  its kind requires is missing or one it may not hold is there; and `substituted output`, a
  counterfactual's substituted step holding the output its mark names. An original run gains no row. On a
  re-run every `--reference` row reads NOT-RUN, `a re-run is not checked against a reference`, and the
  summary line begins `re-run (<kind> of <run>):`;
- **an effect label** of `read` on a receipt whose `effects` holds an entry: FAIL;
- **`config_kept`**: its digest against `instrument.config_digest` (NOT-RUN `configuration kept in part`,
  naming the keys left out, where `partial` is `"true"`; FAIL for a `partial` other than `"true"`), and the
  kept file against its digest;
- **each expectation**, `expect <step>.<name>`: its `declaration_digest` recomputed, and `range`, `unit`,
  `relation` and `member` read against the kept output, PASS or FAIL. A member absent is a FAIL; it reads
  NOT-RUN only where the output was not kept, its target or one of a relation's two values names no value,
  or a value is not a decimal. A ratio over a zero is a FAIL. A relation is computed to 100 significant
  digits;
- **`outputs[].empty`**: `"true"` or `"false"`;
- **an embedding record**: its format, its `identity.digest` recomputed, and its `rows` against
  `batch.size`. Its vectors read NOT-RUN: the receipt does not name the vectors output.

Not checked yet: the `identity.digest` of a model-call record 1.1, and `return_holds`.

**How onetrace 0.6.1 and onetrace-verify 0.6.1 read the new members.** Each member was read under
0.6.1 on a test copy: none of them makes 0.6.1 read a record more loosely, with one limit only
onetrace 0.7 closes. **onetrace 0.6.1's `reference make` accepts a run carrying the re-run mark,
accepts a check run (stage `onetrace.check`, which carries no mark), and keeps the reserved stages
`onetrace.check` and `onetrace.close` as steps.** Two members, as first written, made 0.6.1 FAIL a
record that should pass, and both now have a form measured to read as without them: the reference's
empty mark, `steps.<node>.empty_outputs` beside the outputs, and the close receipt's constants,
under the `onetrace.` prefix.

**The model-call record 1.1 and the embedding record.** onetrace-verify before 0.7 does not check a
`model-call-record/1.1` record's content, or an embedding record at all, its credential row
included. A gate that relies on those rows should move to onetrace-verify 0.7.
