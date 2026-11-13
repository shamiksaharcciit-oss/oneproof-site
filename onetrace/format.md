# The record format, in plain words

Full, normative detail is the Internet-Draft:
`draft/draft-saha-stage-receipts-04.txt`, prepared and not posted, which describes the members through
format 0.5; revision -03, beside it, describes the same format, and -04 states checks -03 left to the reference
implementation. Revision -02 describes them through format 0.4, the re-run mark, the step's effect label, step
expectations, the kept configuration and the check run among them. Its earlier revision -01 is kept as it was, and
revision -00 describes format 0.1. This page is an orientation, not a substitute for it.

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

No digest and no signature covers a manifest member other than the chain and its head, so where a record must be
signed with the run, it goes in a receipt, and the manifest holds a copy. Since format 0.5 the manifest holds these
copies: `state_at_open` and `code`, of the first receipt's; `agent`, of every receipt's `run_agent`; `rerun_from`, of
every receipt's, as `rerun` has since format 0.4; and on a callee of another service, `parent_run`, `parent_stage` and
`origin_run`, of the first receipt's `parent_link`. A reader reads each copy only where it equals the receipts'. A
copy that differs FAILs, and so does a copy with nothing beside it in the receipts: `state_at_open`, `agent`,
`rerun_from`, `code`, `thread_id` and `origin_run` in a manifest whose receipts hold no such member each FAIL on their
member's row. A manifest's `parent_run` and `parent_stage` with no `parent_link` in the first receipt name in-process
nesting, as in onetrace 0.5.

Since format 0.5 the writer rewrites the manifest at most once per `manifest_interval` seconds (default `1.0`), and
always at close and at recovery. While a run is in progress, its manifest may be up to `manifest_interval` behind its
receipts. The journal and the receipts are current.

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

## Across services: the cross-service link

Since format 0.5, a run in one service that calls another can name the call, and the run the call started can name
its caller. Two HTTP fields carry the link, and two signed records hold it, one on each side. Where a reader is given
both runs' folders, it checks that the two agree. Every run the request reached also carries the **origin**: the run
id where the whole request started, copied unchanged to every hop, so the runs that came from one request can be
gathered without walking the links back one hop at a time.

### What a caller sends

```
onetrace-parent: 1.<run>.<stage>.<head>.<origin>
```

| Field | Form |
|---|---|
| `1` | the version, exactly the one byte `1` |
| `<run>` | the caller's run id's UTF-8, in base64url with no padding (RFC 4648 section 5) |
| `<stage>` | the calling step's node id's UTF-8, the same way |
| `<head>` | the caller's chain head at this moment, its 64 lowercase hex characters, without `sha256:`; or the one byte `-` where the run has no receipt yet |
| `<origin>` | the origin run id's UTF-8, the same way as `<run>` |

A run id holds `:` and `.`, and a node id may hold almost anything, so both go encoded; the separator `.` is not in
the base64url alphabet. For run `r-1`, step `approve_payment#2`, head `ab…ab` (64 hex characters), on a first hop:

```
onetrace-parent: 1.ci0x.YXBwcm92ZV9wYXltZW50IzI.abab…abab.ci0x
```

**The origin a run sends.** A run sends the origin it was given, where its own `parent_link` holds one. A run nested
in-process (onetrace 0.5's nesting: `parent_run` in its manifest, no `parent_link`) takes its in-process parent's
origin: that parent's `parent_link.origin`, or else the parent's own origin by the same rule, up to the outermost run.
A run with no parent of either kind is its own origin, and sends its own run id. Nothing in the record's form changes
for a nested run; only the value it sends does.

**Who sends it.** Inside a step, `ot.outgoing_headers()` gives `{"onetrace-parent": …, "traceparent": …}`, the
second where a context is recorded, and needs no list. The httpx, requests and openai hooks add the header only to a
host on `ONETRACE_PROPAGATE`, a comma-separated list of exact hosts, **empty by default**: the header names the run and
the step to whoever receives it, and a model provider or a third party is not told either unless someone asked. A
field value is at most 1024 bytes; a header that would be longer is left out.

### What the callee records

A callee reads the header with `ot.incoming(headers)`, for `@ot.run(parent=…)` or `Recorder(parent=…)`, or through
`ot.asgi(app)` or `ot.wsgi(app)`, which wrap an app. A hand-made `parent=` without an origin is refused, naming the
field.

| Record | Member | Values |
|---|---|---|
| callee's first receipt | `parent_link` | `run`, `stage`, `head`, `origin`, and `traceparent` where well formed; or `status` alone |
| callee's manifest | `parent_run`, `parent_stage` | copies of `parent_link.run` and `.stage` |
| callee's manifest | `origin_run` | a copy of `parent_link.origin` |

- **In the record, a head is a chain digest:** `sha256:<64 hex>`, the wire's 64 hex with `sha256:` added, so it
  compares with chain digests as a string. The wire's `-` is recorded as `-`.
- **The receipt holds the link; the manifest holds copies.** No signature covers a manifest member, so the link is in
  the first receipt, under the chain. The manifest's `parent_run`, `parent_stage` and `origin_run` are read as a
  cross-service link only where they equal the first receipt's `parent_link`. A manifest with `parent_run` and
  `parent_stage` and no `parent_link` is a nested run, as in onetrace 0.5. A run with no `parent_link` writes no
  `origin_run`: its origin is its own run id.
- **A header that does not parse** gives `parent_link` with `status` alone, `unreadable: <the rule's words>`, and no
  origin. The rules, in order: `more than one value`; `longer than 1024 bytes` (counted in UTF-8 bytes after the
  field's bytes are read as Latin-1, as HTTP/1.1 and ASGI carry them, so a byte of 0x80 or above counts two); `version
  <the first 8 bytes, escaped>` (escaped: a printable ASCII byte other than the backslash as itself, every other byte
  as `\xNN`, two lowercase hexadecimal digits; a later version is unread, not an error); `not its form` (not exactly
  five parts, or three for `onetrace-child`); `not canonical base64url`; `not text` (a decoded part that is empty, is
  not UTF-8, or holds a control character: a code point below 32, or 127); `not a head`. **A parse failure never raises and never fails
  a request.**
- **A header is a claim from whoever sent the request.** Its values go only into `parent_link`. They name no file, no
  folder and no run id of the callee's.

### What the callee answers, and what the caller records

```
onetrace-child: 1.<run>.<head>
```

The callee's run id and its chain head, in the same forms. The callee sets it when the response starts, and only on
a request that sent `onetrace-parent`, so a run id is not given to every caller. A response's headers go out before a
streamed body ends and before the callee's run closes, so **the head a caller receives is usually an earlier receipt
of the callee's, not its final head.**

The caller records each call on the calling step, in call order, in `calls` (`ctx.child(headers)`, or a hook):

| `calls[].status` | When |
|---|---|
| `head returned` | the response held a readable `onetrace-child`; the only status with `child_run` and `child_head` |
| `called, head not returned` | the request went, and the response held no such field |
| `unreadable: <reason>` | the response's field did not parse, by the rules above |
| `not sent: <reason>` | no header went: `longer than 1024 bytes`, or `host not on ONETRACE_PROPAGATE` |

Each entry adds `traceparent` where one was sent. **A call never guesses a head.** `calls` is not an input: a callee's
run id and head differ on every call, so as an input they would make the calling step read `inputs differ` in every
comparison. `onetrace-parent` and `onetrace-child` are not recorded among a step's HTTP inputs either.

### How onetrace-verify reads a link

One row, `linked runs match`, per linked run the reader holds: `--linked-run DIR`, repeatable, or `--linked-runs DIR`
for a folder of several services' runs. It reads from the caller's side and from a callee's. A run with no link and no
`--linked-run` gains no row.

| Result | Words |
|---|---|
| PASS | `<child run>: names <caller run> at <step>, and its head is the head returned, origin <origin run>` |
| PASS | `<child run>: names <caller run> at <step>; the head returned is its receipt <n> of <m>, origin <origin run>`, where the callee wrote more after the response started |
| PASS | `<child run>: names <caller run> at <step>; it held no receipt when the response started, origin <origin run>`, where `child_head` is `-` |
| FAIL | `<child run> names <run> at <stage>, not <caller run> at <step>` |
| FAIL | `the head returned is not in <child run>'s chain` |
| FAIL | `the head <caller run> gave is not in its own chain`, on `parent_link.head` where both are held and it is not `-` |
| FAIL | `<child run> names origin <x>, but <caller run>'s origin is <y>`, where both folders are held. A caller's origin is its `parent_link.origin`, or, where it has none, the origin the rule above gives it, read for a nested caller as below |
| FAIL | `<child run> names <caller run> at <step>, and <caller run> holds no call to it`, read from the callee's side where the caller's folder is held and holds no `calls` entry at that step |
| FAIL | `the first receipt's parent_link holds no origin`, on a `parent_link` that holds `run`, `stage` and `head`; `parent_link.origin <value> is not a run id`, where it is not one: a run id is any non-empty string |
| FAIL | the receipts' `parent_link` and the manifest's copies disagree, `origin_run` among them (`the manifest's origin_run differs from the first receipt's parent_link.origin`); a `calls` entry out of form: a status outside the four, `child_run` or `child_head` on any status but the first, or missing on it, a head neither `sha256:<64 hex>` nor `-` |
| NOT-RUN | `<child run>: its folder was not given` |
| NOT-RUN | `<step>: called, head not returned` |
| NOT-RUN | `<step>: unreadable: <reason>`, a `parent_link` with `status` alone among them: it has no origin to check |
| NOT-RUN | `<step>: not sent: <reason>` |
| NOT-RUN | `no link recorded`, only where `--linked-run` was given |
| NOT-RUN | `<child run>: <caller run>'s origin is its outer run's, and <outer run>'s folder was not given`, for a nested caller (below) |

**The origin of a nested caller.** Where the caller is a run nested in-process and holds no `parent_link`, a verifier
reads its origin in this order:

1. from the outer run's folder, where the check is given it, by the rule above;
2. otherwise the origin's check reads NOT-RUN,
   `<child run>: <caller run>'s origin is its outer run's, and <outer run>'s folder was not given`.

A nested run's manifest does not carry its origin: `origin_run` is written only with a `parent_link`.

**A comparison follows the link** where both runs' callee folders are given, as it descends into a nested run:
`inside billing-agent, called from approve_payment, at price_lookup`. Otherwise it says which folder it would have
needed. **The OpenTelemetry export** gives a span whose receipt recorded `trace` a link to the app's
`{trace_id, span_id}` and the attributes `onetrace.app.trace_id` and `onetrace.app.span_id`; its own trace id does
not change.

**How onetrace-verify 0.7.0 and 0.7.1 read a link.** `parent_link`, its `head` in either form, `parent_link` with
`status` alone, the manifest's `parent_run` and `parent_stage`, and `calls` with each of its four statuses read as a
run without them. A callee's manifest `parent_run` reads as onetrace 0.5's in-process nesting. The origin's members,
`parent_link.origin` and `origin_run`, are held to the same rule.

### What a link does not show

- A cross-service link shows that two signed records agree on their parent and child. It does not show the services
  ran as recorded, or that the network delivered the request unaltered.
- The parent link is a claim from the request's sender until the caller's record is held and agrees.
- A head returned is one receipt of the callee's chain at the response's start. It is not the callee's final head,
  and it says nothing about what the callee did after.
- A service that does not record, or a proxy that strips a header, is a gap the record shows as a gap: `called, head
  not returned`.
- A link and a recorded trace id are equality of recorded values. They say nothing of how one service's work affected
  the other's.
- The origin is what the chain of callers sent. Where every folder is held and agrees, the records agree on where the
  request started. That does not show the origin run was not itself called by a service that does not record.

**What this build writes.** `parent_link` with `run`, `stage`, `head`, `origin`, `traceparent` or `status`; the
manifest's `parent_run`, `parent_stage` and `origin_run`; `onetrace-parent` in its five parts,
`1.<run>.<stage>.<head>.<origin>`; `calls`, through `ctx.child(headers)` and from onetrace-auto's `httpx` and
`requests` hooks, which send the header to a host on `ONETRACE_PROPAGATE` and record `not sent: host not on
ONETRACE_PROPAGATE` for any other; and the helpers `ot.outgoing_headers()`, `ot.incoming(headers)`,
`ot.response_headers()`, `ot.asgi(app)` and `ot.wsgi(app)`. The server side: onetrace-auto with
`ONETRACE_AUTO_PER=request` records a run per request under Starlette and Flask; the launcher's `onetrace-run --per
request` is refused.

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
- with onetrace-auto, the members of an auto-recorded run that the table marks, the request boundary and its `key`
  among them (`ONETRACE_AUTO_PER=request`), and the embedding record 1.0 of a hosted embeddings call through the
  `openai` hook;
- `effect_label` on a declared stage, on a step a check or a counterfactual puts in place, and from onetrace-auto's
  hooks, the framework hooks' `unknown` and `not classified` among them;
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
- receipt, `outputs[].empty`: the member;
- receipt, `return_holds`: the member;
- reference, `steps.<node>.reads`: the member;
- reference, `steps.<node>.empty_outputs`: the member;
- model-call record 1.1, `steps.level`, `steps.method`: in a hosted record;
- model-call record 1.1, `steps.k_requested`, `steps.k_returned_min`, `steps.k_returned_max`, `steps.count`, `steps.logprobs`: in a hosted record, and `steps.logprobs` in a self-hosted one;
- model-call record 1.1, the steps file, hosted form: the file;
- model-call record 1.1, `identity.digest`, `call.kind`: `identity.digest`, and the call kind `endpoint`;
- embedding record 1.0, the members it shares with the model-call record: in a self-hosted record (a hosted call's is written, through onetrace-auto's `openai` hook);
- embedding record 1.0, `embedding.*`: in a self-hosted record (a hosted call's is written, through onetrace-auto's `openai` hook);
- embedding record 1.0, `output.*`, `usage.tokens`, `batch.size`, `rows`: in a self-hosted record (a hosted call's is written, through onetrace-auto's `openai` hook);
- embedding record 1.0, `fingerprints[].quantity`: in a self-hosted record.

### The version lines

| Version line | Before | Format 0.4 | Written by this build |
|---|---|---|---|
| receipt `format` | `stage-receipt/0.3` | `stage-receipt/0.4` | no: this build writes `stage-receipt/0.5` (format 0.5, below) |
| manifest `format` | `stage-receipt-chain/0.3` | `stage-receipt-chain/0.4` | no: this build writes `stage-receipt-chain/0.5` |
| signature record | `stage-receipt-signature/0.1` | `0.1` kept for a closed run; `0.2`, written only for a run signed not closed | yes |
| model-call record | `model-call-record/1.0` | `model-call-record/1.1` | self-hosted: yes; hosted: not yet |
| embedding record | none | `embedding-call-record/1.0`, new | with onetrace-auto: a hosted embeddings call; self-hosted: not yet |
| reference | `onetrace-reference/1` | `onetrace-reference/1`, unchanged: optional members only | yes; its optional members `reads` and `empty_outputs` not yet |
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
not a sixth form, and there is none. Format 0.5 adds none either. A run an expectation stopped (format 0.5, below)
writes `unhandled exception: ExpectationStopped at <node>: expect <name>: <detail>`: the `unhandled exception:` form,
with its text fixed. A recovered close receipt holds no `onetrace.ended_by` at all.

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

**A recovered close receipt (format 0.5).** A run killed before it closed may be recovered by a later process,
which writes a close receipt of instrument kind `close-recovered`, with the constants `onetrace.recovered` (`true`),
`onetrace.last_confirmed` and `onetrace.steps`, and no `onetrace.ended_by`. Its coverage reads `incomplete`. A
verifier that reads format 0.5 gives it the row `the close receipt`, PASS `recovered: last confirmed <node>`, never
`closed:`, and `--require-closed` FAILs it, `not closed by its own process: recovered`. It FAILs a `close-recovered`
that is not last, one holding `onetrace.closed` or `onetrace.ended_by`, an `onetrace.steps` other than the receipts
before it, and a `complete` on it. onetrace-verify 0.7 reads it as an ordinary step and the run as it reads any killed
one: `not closed: the record ends at onetrace.close and holds no close`.

**The close receipt is optional for every reader,** so the promise of the path to 1.0 above holds
unchanged. A reader never fails a run for lacking one. Every run written before format 0.4 verifies
exactly as it did. A writer from onetrace 0.7 always writes one, as its own choice, not as a
requirement on any record a reader is given. Two reading rules keep it so:

1. **A receipt is a close receipt only when its own `format` is `stage-receipt/0.4` or later and
   its instrument is `onetrace.close` of kind `close`.** Before 0.4 the name was not reserved, so a
   run written then can hold an ordinary stage named `onetrace.close`, with any instrument. Such a
   receipt is read as the ordinary step it is. The kind is `close` only: a recovered close, of kind
   `close-recovered`, is not a close receipt by this rule, and nothing reads a recovered run as closed
   by its own hand.
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

**Only a closed run is signed by default.** `onetrace sign` refuses a run with no close receipt, and
treats a run whose chain ends with a recovered close receipt as not closed.
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
classified` and `substituted, not executed`, and minor 5 keeps the six: a vector query's or change's own
basis is beside the label, in `step.effect_basis`. A record holding any other basis is outside the format, and
its row FAILs, naming the basis. For an auto-recorded step, onetrace-verify reads the label against what
the producer documents for the step's library:

| Library | Value | Basis | On |
|---|---|---|---|
| `httpx`, `httpx2`, `requests` | `read` | `http method` | a `GET` or `HEAD` |
| `httpx`, `httpx2`, `requests` | `write` | `http method` | any other method |
| `openai` | `write` | `model call stored by the provider` | a `responses.create` call without `store=False` |
| `openai` | `read` | `model call` | any other call |
| `anthropic` | `read` | `model call` | any call |
| `langchain` | `read` | `model call` | a chat model or completion model step (`auto.call` `chat_model`, `llm`) |
| `langchain` | `read` | `not classified` | a retriever step, with `step.effect_basis` `vector query` (format 0.5) |
| `langchain`, `langgraph` | `read` | `declared on the stage` | a tool or node that declares its effect `read` in the framework's own metadata |
| `langchain`, `langgraph` | `write` | `declared on the stage` | a tool or node that declares its effect `write` in the framework's own metadata |
| any | `unknown` | `not classified` | a call the hook cannot classify |

A label outside its library's rows FAILs. On a `responses.create` step either `openai` label reads as
documented: the receipt does not hold `store`. A library the producer does not document reads NOT-RUN,
`<library>: no documented bases`; its value is still checked against the three, and its basis against
the six. `onetrace.sdk_verify`, the SDK's own verifier, reads these format 0.4 members by the same
row names: the close receipt, the re-run mark and a counterfactual's substituted output, the effect
label (its value and basis, and `read` against `effects`), an auto step's `effect_label`, `declared` and
`context`, `outputs[].empty`, `config_kept`, each expectation a receipt declares, `return_holds`, the
embedding record, the manifest's `auto` block and the open boundary, the declared stage lists, and the
labels the producer documents by library (a step is a `responses.create` call where its `auto.call` and
its stage both say so), a model-call record of either version, and an expectations file, given as
`python -m onetrace.sdk_verify --expectations FILE MANIFEST`. It reads no signature: the not-closed
signature's row is onetrace-verify's alone. A manifest declares no stages of its own, so it places a boundary the manifest holds against
the stages the chain's last receipt declares.

### Every member format 0.4 adds

Every scalar is a string, and every member is optional: a record that does not hold one reads as a
record written before 0.4 does.

| Record | Member | Values | Written by this build |
|---|---|---|---|
| close receipt | `stage.name`, `instrument` | `onetrace.close`, reserved; instrument `onetrace.close`, kind `close`, onetrace's version | yes |
| close receipt | constants `onetrace.closed`, `onetrace.steps`, `onetrace.ended_by` | `true`; the number of receipts before it; the five forms above | yes |
| signature record | `closed` | `false`, in `stage-receipt-signature/0.2` only, inside the signed bytes; `--not-closed` is refused on a closed run | yes |
| receipt | `auto` | `declared` (`false`), `call`, `library`; for an HTTP call `target`: `host`, `method`, `query_names` and one of `path_digest` (the default) or `path` (only with `ONETRACE_AUTO_HTTP_PATH=plain`); for a model call `target`: `host` alone; and on a step recorded from a thread that did not carry the run's context, `context`: `thread without the run's context` | with onetrace-auto: yes |
| manifest | `auto` | `boundary` (`process`, `request`), `hooks` (each `library`, `status`, `version`), `key` | with onetrace-auto: `boundary` `process` and `hooks`; `request` and `key` with `ONETRACE_AUTO_PER=request` |
| receipt | `rerun` | `kind` (`twin`, `counterfactual`, `reproduce`, `check`), `of_run`, `of_chain_head`; a twin, and a check under the baseline's settings: `config_of_run`, `config_of_chain_head`; a counterfactual: `substituted`; a check: `from_stage`. In every receipt of a re-run, the intake and close receipts included | kind `reproduce`, in the run `onetrace reproduce` produces, kind `twin`, in the run `onetrace reproduce --config-of` produces, kind `counterfactual`, in the run `onetrace reproduce --substitute` produces, and kind `check`, in the run a check of `reproduce` produces: yes |
| receipt | `rerun.from_stage` | the node id a check started from: required for `check`, absent for every other kind | yes |
| receipt | `rerun.writes_allowed` | plain `reproduce` only, and required there: `true` when `--allow-writes` was given, `false` otherwise | yes |
| receipt | `rerun.substituted` | `step`, `from_run`, `from_chain_head`, `from_receipt`, `output`, `output_digest` | yes |
| manifest | `rerun` | a copy of the receipts' `rerun` (below) | kinds `reproduce`, `twin`, `counterfactual` and `check`: yes |
| check run | stage `onetrace.check` | reserved; instrument `onetrace.check`, kind `check`. Its constants (`verb`, `argv`, `runner_digest`, `rerun_plan`, `timeout_seconds`, `baseline`, `candidate`, `stage`, `claim`, `predicted`) and assertions (`exit`, `result`, `came_back`: `as predicted`, `otherwise`, `did not run: <reason>`) are ordinary constants and assertions | yes, by `onetrace check`; the constants `baseline` and `stage` only where the verb has them, and `runner_digest` and `rerun_plan` for `reproduce` only |
| receipt | `effect_label` | `value` (`read`, `write`, `unknown`) and `basis` (`declared on the stage`, `model call`, `model call stored by the provider`, `http method`, `not classified`, `substituted, not executed`). Required on a receipt with an `auto` block; absent on an unmarked declared stage and on the recorder's own receipts (intake, close) | on a declared stage marked `effect="read"` or `"write"`: yes, basis `declared on the stage`; with onetrace-auto: `read` and `write`, basis `http method`, `model call` and `model call stored by the provider`; on a step a check or a counterfactual puts in place: `read`, basis `substituted, not executed`: yes; from the framework hooks: `unknown` and `read`, basis `not classified` |
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
| embedding record 1.0 | the members it shares with the model-call record | `format`, `call.kind`, `call.api`, `credential`, `model.*`, `tokenizer.digest`, `engine.*`, `runtime.*`, `dtype`, `input.request_digest`, `input.token_ids_digest`, `engine.settings.*`, `identity.digest` | with onetrace-auto, a hosted call: yes; self-hosted: not yet |
| embedding record 1.0 | `embedding.*` | `pooling` (`mean`, `cls`, `max`, `last-token`, or the module's own name), `normalize`, `max_length`, `truncation` (`end`, `start`, `none`, `error`), `dimensions`, `input_type`, `encoding` (`float`, `base64`, `int8`, `uint8`, `binary`, `ubinary`) | with onetrace-auto, a hosted call: yes; self-hosted: not yet |
| embedding record 1.0 | `output.*`, `usage.tokens`, `batch.size`, `rows` | `vectors_digest`, `vectors_form` (`raw-<dtype>-le`, `json-decimal`, `base64-bytes`), `count`, `dimensions`, `norms` (`unit`, `not unit`); tokens or `not observed`; the batch size; each row `{position, input_digest, vector_digest, tokens}` | with onetrace-auto, a hosted call: yes; self-hosted: not yet |
| embedding record 1.0 | `fingerprints[].quantity` | adds `embedding-vectors`, in the embedding record only | with onetrace-auto, a hosted call: yes; self-hosted: not yet |

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
- **an embedding record**: its format; the model-call record's rows under its own format (it parses and is
  canonical, its fields are complete and well formed, no field holds a value where it is not observed, no
  string is shaped like an authorization header); its fingerprints, each `embedding-vectors`, an `exact`
  one equal to `output.vectors_digest`; its `identity.digest` recomputed; and its `rows` against
  `batch.size`. Its vectors read NOT-RUN: the receipt does not name the vectors output;
- **a model-call record 1.1's `identity.digest`**, where the record holds it: recomputed over the shared
  fields, PASS or FAIL, NOT-RUN where a field it is computed over is missing;
- **`return_holds`**, where a receipt holds it: `[]` reads PASS; each entry is four strings, its `child`
  one of the step's `children`, and the part at `at` in the caller's kept return and at `child_at` in the
  child's each digest to `digest`, PASS or FAIL. NOT-RUN where either return was not kept.

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

## Format 0.5: what a run touched outside itself, and who did it

Format 0.5 is the format of onetrace 0.8. Like 0.4, it adds optional members only: nothing removes a required
member, changes a type or changes a canonical form. Its members say what a run touched outside itself (store data,
other services, other agents, a recipient's confirmation) and who did it (a step's kind, its agent, the code it ran).

**A 0.7 verifier reads a 0.5 run as it reads a 0.4 run.** onetrace-verify 0.7.0 and 0.7.1 (0.7.1 changes no row)
read a 0.5 run with the same exit as a 0.4 run, and no row that PASSes on a 0.4 run reads with another outcome. Its
words may quote other recorded values, and it may add rows for a receipt 0.7 would not write. Each member below was
measured that way under 0.7.0: a committed 0.4 vector, its format strings set to minor 5, the member added, the chain
re-linked. There are two stated exceptions:

- **A library 0.7 does not document.** A step of a library onetrace-verify 0.7 does not document reads NOT-RUN on
  that one row, `<library>: no documented bases`, as for any undocumented library. The exit does not change. This
  applies to `anthropic` and `httpx2` (below), and to `langchain` and `langgraph`.
- **An output kept only as a digest.** An output 0.5 keeps only as a digest leaves `outputs`, so under 0.7 its two
  rows, `output artifact '<name>' matches` and `outputs/<name> declares a trust class`, are absent, as for a step that
  wrote no such output. A 0.7 reader of a capped run is not told an output was held back.

Two consequences outside the verifier, read from the design and the 0.7.0 code and not run:

- A 0.7 comparison and a 0.7 console's index see none of the new members, so a capped output is a missing output to
  a 0.7 comparison.
- A callee's manifest `parent_run` reads under 0.7 as onetrace 0.5's in-process nesting.

**The Internet-Draft describes format 0.5 in its revision -04,** `draft/draft-saha-stage-receipts-04.txt`, prepared
and not posted, started from -03, which describes the same format. Revision -02 describes the members through format
0.4.

**What this build writes.** Of the members below, this build writes:
- store state a step declares through `ot.state.read` and `ot.state.write`, with
  `state_cut`, `step.effect_basis`, a kept state value and `state_at_open`;
- `step.kind`, from a decorated stage and from onetrace-auto's `openai`, `httpx` and `requests` hooks; `tool_call`;
  `agent` and `run_agent`, with the manifest's `agent`;
- `messages` and `messages_received`, from `ctx.message`, `ot.message` and `ctx.received`, with kept bytes;
- store state onetrace-auto's store hooks fill: LangGraph checkpoints, psycopg, the vector clients, boto3 and the
  cloud object clients, Iceberg and Delta;
- the cross-service link's `parent_link` with its `origin`, its manifest copies with `origin_run`, the five-part
  `onetrace-parent`, and `calls`, through `ot.outgoing_headers()`, `ot.incoming(headers)`, `ot.response_headers()`,
  `ctx.child(headers)`, `ot.asgi(app)` and `ot.wsgi(app)`, and from onetrace-auto's `httpx` and `requests` hooks with
  `not sent: host not on ONETRACE_PROPAGATE`; a run per request under Starlette and Flask with
  `ONETRACE_AUTO_PER=request`;
- the writer's `emission.queue`, a dropped step's gap and its `queue full` boundary, `outputs_digest_only`, the
  journal, and the recovered close receipt;
- `expectations[].checked`, `expectations_batch` and the stop's form of `onetrace.ended_by`;
- the recipient confirmation's `authorization` members and its kept file;
- `code` and `rerun_from`;
- from onetrace-auto's `openai` hook, `model_usage`, `model_call_attempts`, `model_call_failed`, and the `/1.1`
  record of a call that failed after `post`;
- the `anthropic` and `httpx2` hooks, `auto.library` `anthropic` and `httpx2`.

The members the table below marks "not yet" are specified here, and no onetrace build writes them yet. Each line
names its row of the table, then what in it is not written:
- receipt, `model_usage`: `cost`;
- receipt, `tokenizer_digest_method`: the member (no hook writes it).

### The version lines

| Version line | Format 0.4 | Format 0.5 | Written by this build |
|---|---|---|---|
| receipt `format` | `stage-receipt/0.4` | `stage-receipt/0.5` | yes |
| manifest `format` | `stage-receipt-chain/0.4` | `stage-receipt-chain/0.5` | yes |
| signature record | `stage-receipt-signature/0.1`, `0.2` | unchanged. A recovered run is not closed: it is signed only with `--not-closed`, in `0.2` | yes |
| model-call record | `model-call-record/1.1` | unchanged, `/1.1` or `/1.0` byte for byte: what a model call adds is a receipt member beside it | yes |
| embedding record | `embedding-call-record/1.0` | unchanged | with onetrace-auto, a hosted call, as at 0.4 |
| reference | `onetrace-reference/1` | unchanged | yes |
| expectations file | `onetrace-expectations/1` | unchanged | yes |
| HTTP field `onetrace-parent` | none | version `1`: `1.<run>.<stage>.<head>.<origin>` | yes |
| HTTP field `onetrace-child` | none | version `1`: `1.<run>.<head>` | yes |
| recipients' file | none | `onetrace-recipient-trust/1`, new: the file `onetrace-verify --recipients FILE` reads | read by this build's onetrace-verify; a person writes it |
| journal | none | `onetrace-journal/1`, new: local, not part of the record | yes |

The receipt and manifest members below are all under `0.5`. The HTTP fields, the recipients' file and the journal are
outside the Internet-Draft; the draft's next revision is to register the two HTTP fields or say they are not.

### Store data a step touched

A step records the store data it read or wrote as **state**, apart from its inputs and outputs: what it read or
wrote and at what version, which earlier run wrote what this run read, and what state the store was in when the run
started.

- `state_reads` and `state_writes`: one entry per read or write. An entry names the `store` as the team declares it
  (`orders_db.orders`), its `store_kind`, the key (by default `key_digest`, a `sha256:` over the key's bytes; `key` in
  plain only with `ONETRACE_STATE_KEYS=plain` or `key_plain=True`), the store's own `version` with its
  `version_kind`, and exactly one of `digest` (with its `digest_form`), `digest_status` (`not observed: <reason>`) or
  `found: "false"`. It may add `as_of` (`newest`, `oldest`: the store's own `last modified`, never the local clock),
  `ids_digest` on a vector query, and `kept`. `[]` says recorded, nothing read; absent says not recorded.
- **Where a store has no revision, `version` is the literal `not observed`,** with no `version_kind`. onetrace never
  makes one up: no counter, no hash of what was read, no clock. A team that keeps its own revision passes `version=`
  and `version_kind="declared"`.
- `state_cut`: a step keeps its first 1000 entries on each side and counts the rest here. A step with a cut never
  reads as having told the whole of its state.
- `state_at_open`, in the first receipt (each `{store, version, version_kind}`), with a manifest copy read only where
  it equals the first receipt's. It is written only from a store that gives a cheap whole-store revision: onetrace
  never reads a store whole to compute one.
- **A kept state value** is the exact bytes `digest` is over, under `state/<receipt stem>/reads/<n>` or
  `.../writes/<n>`, beside `artifacts/`, so it never reads as an output. Only where asked (`keep=True` on
  `ot.state.read` or `ot.state.write`, or `@ot.run(keep_state=True)`), never on a run with `outputs_kept` `none`.
- **The digest forms:** `sql-rows/1` (rows sorted, so a row order the query never fixed is not a difference),
  `sql-rows-ordered/1` (`ordered=True`), `bytes/1`, `json/1`, `docs/1`, `vector-query/1` (ids and scores, in returned
  order), `vector-change/1`, and `checkpoint/1` (no digest by default: the checkpoint id is the version).
- **A step with a write is a write.** A step holding an entry in `state_writes` reads as `write` to every re-run,
  whatever its label, as a step with `effects` does.
- **A vector query or change keeps `effect_label` to its six bases.** A vector query is `read`, `not classified`,
  and a change `write`, `not classified`, each with the real basis beside it in `step.effect_basis`: `vector query` or
  `vector change`. A 0.5 reader reads `step.effect_basis` first. `step` is a closed list of three members, `kind`,
  `effect_basis` and `lower_hook`.

**What a 0.7 verifier reads.** Every state member reads as 0.4. A vector query reads `read`, `not classified`, and a
vector change `write`, `not classified`: the label stays true, and a change never reads `read`.

**What it does not show.** Lineage is equality of recorded digests or versions: it says run B read what run A
wrote, not that the data made B behave as it did. A version is the store's own report, and onetrace does not check
that a store's versions are consistent. At Postgres, a read's version is the LSN at the read, not a snapshot the read
is proved to have used. A store reached without a hook or a declaration is not seen. Source age is the store's own
`last modified`, not when the data was true. A sorted `sql-rows/1` says which rows came back, not in what order.
`state_at_open` is a revision the store reported at open, not a statement of the store's content.

### What kind of step this is, and which agent ran it

- `step.kind`: exactly one of `model call`, `tool call`, `retrieval`, `decision`, `state read`, `state write`,
  `transform`, `other`. The list is fixed: a new kind needs a new minor. A decorated stage sets it with `kind=`, and
  a value outside the list is refused at decoration. The `openai` hook writes `model call` (an embeddings call
  included), and the `httpx` and `requests` hooks `other`: a hook sees a method and a host, not what the call is
  for. The recorder's own receipts carry none. **Absent is not `other`:** it says no kind was recorded.
- `tool_call`, only on a step of kind `tool call`: `name`, `arguments_digest` or `arguments_status`, `result_digest`
  or `result_status`, `call_id`, and `requested_by` (`{step, call_id}`: the model step that asked for it). The
  model-call record holds no tool request, so a reader finds the request in that step's kept `response`.
- `agent`, on a step: `name`, and `role` and `runs_on` (`{kind: model or framework, name, version}`) where given. A
  step's `agent` is absent where it equals the run's.
- `run_agent`: the run's agent, equal in every receipt of the run, the recorder's own included, with the manifest's
  `agent` a copy read only where every receipt carries the same. The manifest is not signed, so the run's agent goes
  in every receipt, as `rerun` does.

A comparison names the agent with the step, and a changed kind or agent is an annotation, never a verdict word.

**What a 0.7 verifier reads.** Each reads as 0.4, a kind outside the list among them.

**What it does not show.** A step's kind and an agent's identity are what the code declares, or what a hook read of
the call. They are bound by the signature to the key that signed them, not a proof of which model or tool answered.
`requested_by` shows the record names a request with that id, not that the tool ran with what the model asked for,
unless a reader that holds both compares the arguments. An absent kind says nothing about the step.

### Messages between agents

`ctx.message(to, kind, body)` (or `ot.message`, the current stage's) records a message a step sent;
`ctx.received(ref_or_digest)` records one it took in.

- `messages`: what the step sent, in call order, each `seq` (from `1`), `from`, `to`, `kind`, `digest` (`sha256:`
  over the body's bytes), `bytes`, and `media_type` and `kept` where they apply. A message's id is `<node id>:<seq>`.
- `messages_received`: each `{from_step, seq, digest}`, or `{digest}` alone where no sending step is known.
- **The body goes by digest.** Its bytes are kept only where the run keeps outputs, under
  `messages/<receipt stem>/<seq>`, outside `artifacts/`, so a kept message never reads as an output.
- **A message is not an output.** It is not among a step's settings or outputs and changes no verdict. A comparison
  names the first message that differs, apart from the steps.

**What a 0.7 verifier reads.** `messages`, `messages_received` and the `messages/` folder read as 0.4.

**What it does not show.** A message record shows what was sent, not that the receiver acted on it.
`messages_received` shows the receiving step's code said it took the message in, or that a framework's state held it
when the node started, not that the node read it. `to` is what the code declared; under LangGraph it is a channel,
not a route. A message passed with no helper and no adapter is not seen.

### The cross-service link

A step that calls another service sends `onetrace-parent`; the callee records `parent_link` in its first receipt,
with the manifest's `parent_run`, `parent_stage` and `origin_run` as copies; it answers with `onetrace-child`, and the
caller records the call in `calls`. The section "Across services: the cross-service link" above gives the headers,
the members, the readings and the non-claims.

**What a 0.7 verifier reads.** `parent_link`, its `head` in either form, `parent_link` with `status` alone, the
manifest's `parent_run` and `parent_stage`, and `calls` with each of its four statuses read as 0.4. A callee's
manifest `parent_run` reads under 0.7 as onetrace 0.5's in-process nesting.

### What a model call adds beside its record

**The record does not change.** A hosted or self-hosted record stays `/1.1`, or `/1.0`, byte for byte: a new member
inside a `/1.1` record FAILs onetrace-verify 0.7.0, and a new format line turns its content rows, its credential row
among them, from PASS to NOT-RUN. So these are receipt members, each entry naming its record by its output's name
(`model_call.json`, `model_call.2.json`): a step can hold more than one.

- `model_usage`: each `{record, input_tokens, output_tokens, total_tokens, cost}`, the last four as the provider's
  response gives them: decimal strings, `observed`, or `not observed` where it gives none. `cost` is `{value,
  currency}` as the provider reports it, **never computed from a price list**.
- `model_call_attempts`: each `{record, retries, attempts}`. `retries` counts the attempts past the first the client
  made within this call; `attempts` lists each `{status, request_digest}`, `status` the HTTP status or `no response`.
- `model_call_failed`: each `{record, failed}`, where a call fails after `post`: `failed` is the exception's class,
  `observed`, source `the call failed after post`. Such a call still writes a `/1.1` record, under the step whose
  outcome stays `error`, with `input.request_digest` and `output.*` `not observed`.
- `tokenizer_digest_method`: each `{record, form, keys, files}`, saying how the record's `tokenizer.digest` was made
  (`form` `sha256-of-canonical-name-map/1`), so a reader can rebuild it from named files. Names of files are recorded,
  never their contents; where the digest was given by a caller, no entry is written.

Budgets stay with onedoor, as a policy; onetrace records its decision.

**Two more hooks.** onetrace-auto's `anthropic` hook records library `anthropic`, `target` `{host}`, kind `model
call`; the `httpx2` hook records an HTTP call through `httpx2.Client.send` and `httpx2.AsyncClient.send`, stage
`httpx2.send`, for httpx2 >=2,<3, as the `httpx` hook records one, and a model call made over `httpx2`, as openai 3.x
makes one, is the model step's own and no step of the `httpx2` hook. Their rows join the labels table under "An
auto-recorded step".

**`localize`'s JSON key stays.** Its text report heads the block `FIRST DIFFERENCE at …`. Its JSON report keeps the
key `cause` (`frontier_causes` on a topology) at format 0.5: the key names the first difference, not a cause.

**What a 0.7 verifier reads.** `model_usage`, `model_call_attempts`, `tokenizer_digest_method`, and
`model_call_failed` with the `/1.1` record a failed call writes, read as 0.4: the record's rows run as on any `/1.1`
record, its credential row included. A step of library `anthropic` or `httpx2` reads NOT-RUN on its label row,
`anthropic: no documented bases` or `httpx2: no documented bases`, with the exit unchanged.

**What it does not show.** Usage and cost are what the provider reported; onetrace does not check them against a bill
or a tokenizer. `retries` counts the attempts the hook saw through the client's public `post`: a retry below that,
in a transport, is not seen. A failed call's record shows what the hook saw go out, not what the provider did with
it. `tokenizer_digest_method` says how the digest was made, not that those files were what the model loaded.

### LangChain and LangGraph

onetrace-auto's `langchain` and `langgraph` hooks record a step at the framework's own callbacks, with `auto.library`
`langchain` or `langgraph` and no `target`. An auto-recorded run declares a fixed list of stage names, so two runs
compare cleanly; a node's own name is an instance, not a stage name, its `<n>` counting from 1 within the name in the
run:

| Stage | `auto.call` | Instance | The step |
|---|---|---|---|
| `langgraph.node` | `node` | `<node name>.<n>`, as the node id `langgraph.node#agent.1` | a graph node |
| `langchain.chat_model` | `chat_model` | `<n>`, as `langchain.chat_model#2` | a chat model call, with its model-call record, `step.kind` `model call` |
| `langchain.llm` | `llm` | `<n>` | a completion model call, with its model-call record, `step.kind` `model call` |
| `langchain.tool` | `tool` | `<tool name>.<n>`, as `langchain.tool#add.1` | a tool call, with `tool_call`, `step.kind` `tool call` |
| `langchain.retriever` | `retriever` | `<n>` | a retrieval, `step.kind` `retrieval` |

A call that is not a graph node and not a subgraph opens no step: its calls nest under the enclosing step. A call
that ends in error closes its step with `outcome.class` `error`. A subgraph is a nested run, told apart by the depth of
its namespace, and its head is an input of the enclosing node. Nodes that run in one superstep are chained in the
order they finished, so two runs of the same work may differ in that order. A graph invocation at the top level of a
process is one run. A node's `step.kind` is the one it declares, or `other`. The labels the hooks write are the
`langchain` and `langgraph` rows of the labels table.

- **A call is never recorded twice.** While a framework model step is open, a lower hook (an HTTP or model client
  hook) records no step for the call it sees, and adds to the framework step `step.lower_hook`: `library`, the lower
  hook's library, and `note`, `already recorded by the framework hook`. A call a node or a tool makes outside a
  framework model step is recorded by the lower hook as format 0.4 records it, nested under the node or the tool.
- **`framework_error`:** a framework step whose callback could not finish recording carries `framework_error`, the
  string `not recorded: ` followed by what was not recorded; the pipeline's own call goes on.
- **`thread_id`:** a graph run's first receipt may carry the framework's thread id, as its metadata gives it, and the
  manifest a copy.
- **The hooks and the state:** the manifest's `auto.hooks` gains entries for `langchain-core` and `langgraph`, each
  with `library`, `status` and `version`. Checkpoints are recorded as state, of `store_kind` `langgraph`.

**How this build's onetrace-verify reads them.** A framework step's label is read against the labels table, and a
label outside its library's rows FAILs. `<receipt>: step.lower_hook` FAILs a member other than its two, a `note`
other than its one value, or a `lower_hook` on a step whose kind is not `model call`; `<receipt>: framework_error`
FAILs one not of its form; each prints only on a FAIL. On a run with framework steps, `framework steps nest` FAILs a
framework step whose `parent` names a step that ended before it began (every framework step's parent is an open node
or the run); `no call recorded twice` FAILs two steps under one node with the same request digest (the digest of the step's
input named `request`), one carrying
`step.lower_hook` naming a library and the other an auto-recorded step of that library; and `thread id` FAILs a
manifest `thread_id` that differs from the first receipt's.

**What it does not show.** A framework-recorded run is complete only for the events the framework's callbacks
deliver, at the versions in `auto.hooks`. Code a node runs outside the framework's calls is seen only through the lower
hooks, or a declared stage. A model step's request is what the callback delivered, not the bytes sent:
`step.lower_hook` shows a lower hook saw a call during that step, and does not compare the two. A node's agent identity
is the graph's own name for it. A subgraph told apart by namespace depth reads what the framework reports there.

### Recording on the hot path

The writer queues receipts and writes them in batches. With the default, `block`, no member changes: a run's
receipts are the same bytes in the same order, queued or not; only when and how they reach the disk differ.

- `emission.queue`: `drop`, in every receipt of a run that declared `@ot.run(queue="drop")`, `Recorder(queue=…)` or
  `ONETRACE_QUEUE`. Absent reads `block`. `drop` with `policy="fail-closed"` is refused at open: a dropped step keeps
  its result with no receipt, which fail-closed rules out.
- **A dropped step** is a gap at its own index, reason `dropped: the writer's queue was full at <node>`, with a
  boundary of `kind` `queue full`, `name` its stage, `note` `receipt not written: <the gap's reason>`. `prev` does
  not move, so the chain has no hole, and **a run with a drop never reads `complete`**. It still closes.
- `outputs_digest_only`: an output past `keep_cap_bytes`, kept only as its digest. The entry leaves `outputs` for
  this list, with `name`, `digest`, `bytes`, `media_type`, `trust_class` and `kept` (`digest only: over the cap of
  <n> bytes`), and no file. A 0.5 reference and comparison read both lists. `ctx.write_stream` and `ctx.write_file`
  hash by chunks and give the same digest as a whole write.
- **The manifest on a timer.** The writer rewrites the manifest at most once per `manifest_interval` seconds (default
  `1.0`; set on `Recorder` and `@ot.run`, or by `ONETRACE_MANIFEST_INTERVAL`), after the run's first batch, and always
  at close and at recovery. `0` rewrites it after every batch.
- **The journal.** `.journal`, in the run's folder, beginning `onetrace-journal/1 <host digest> <pid> <process start
  time>`, holds each receipt's bytes as it is built, and an entry named `gap` for each gap the writer knows of: a
  dropped step, a receipt that could not be written, a gap the producer declared. It is local, like `.lock`: never in
  the chain, never uploaded by the sink, and removed when the run closes. On a system with no `/proc` (Windows and
  macOS among them) the start time is `-`, and a recovery reads by pid alone; a pid a live process has taken then
  leaves the journal unrecovered.
- **A recovered close receipt.** On a recorder's next start (or by `onetrace recover RUN`; `ONETRACE_RECOVER=0`
  turns the scan off), a folder whose journal names a process that is gone is recovered: the confirmed receipts are
  written byte for byte, a gap is recorded for each later whole entry, a boundary of `kind` `recovered`, `name`
  `onetrace.close`, `note` `recovered by a later process` is added, and a close receipt of instrument `kind`
  `close-recovered` is written, with the constants `onetrace.recovered` (`true`), `onetrace.last_confirmed` (a node id,
  or `none`) and `onetrace.steps`, and never `onetrace.ended_by`. Its coverage reads `incomplete`.
- **A journal with nothing to close.** One that holds no whole entry gives no receipt and no manifest: it is kept as
  `.journal.empty`. One that holds entries and confirms none gives no close (a close chained after none would FAIL
  every verifier): the folder is renamed `<run>.unrecoverable`, with `UNRECOVERABLE.txt`, and `onetrace recover`
  exits 1.

**What a 0.7 verifier reads.** `emission.queue` and a drop's gap and boundary read as 0.4, as a `Recorder` run with
a gap does. A digest-only output reads by the second exception. A recovered close is an ordinary step to it, by the
close receipt's two-part rule: it reads the run as it reads any killed one, `not closed: the record ends at
onetrace.close and holds no close`, with rows added for that receipt, and `--require-closed` FAILs it. `.journal`,
`.journal.empty` and `.lock` left in a folder read as 0.4.

**What it does not show.** A dropped step ran with no receipt: what it did is not in the record, beyond its stage
name and its place. `block` under `fail-open` returns before the receipt is durable: power loss can lose the batch in
flight, and the record then ends earlier, as a killed run's does. A recovered close receipt shows a later process
found the journal. It was not written by the run, and does not show how the run ended or what happened after the
last confirmed step: `onetrace.recovered` is the record's whole statement. A journal is as trusted as the folder it
is in. `.journal.empty` shows what its first line says: a host's digest, a pid and a start time. A benchmark's number
holds on its runner, for its payloads. A digest-only output cannot be checked against its bytes, and a reference that
compares it compares digests. While a run is in progress, its manifest may be up to `manifest_interval` behind its
receipts. The journal and the receipts are current.

### Expectations checked during the run

Off by default. `@ot.run(expect_mode=…)`, `@ot.stage(expect_mode=…)` or one expectation's `mode=` asks for an
expectation to be checked as its step returns, over the bytes about to be recorded; the narrowest wins. `off`
writes nothing.

- `expectations[].checked`: `when` (`during the run`), `mode` (`record` or `stop`), `outcome` (`PASS`, `FAIL`,
  `NOT-RUN`), `detail` (the reading's own words) and `reader` (`onetrace-verify <version>`). It sits beside
  `declaration`, so `declaration_digest` does not change.
- `expectations_batch`: an expectation with a batch threshold, `batch` `{"over": "/docs/*", "more_than": "3"}`, with
  `failed` and `of` in its `checked`. The target's JSON Pointer holds one `*` segment, not its last, naming each
  document of an array, with the member read in each document after it, as `/docs/*/score`; `over` is the pointer
  through the `*`. Each document's result is not written, only the count.
- **The stop.** In `stop`, a FAIL raises `ExpectationStopped` (a `BaseException`) at the step's return, and every
  later stage call in the run raises it again before its body. The close's `onetrace.ended_by` is
  `unhandled exception: ExpectationStopped at <node>: expect <name>: <detail>`: one of the five forms, with its text
  fixed. A `NOT-RUN` never stops. A hooked call is never stopped by an expectation.
- **On a run that keeps no outputs,** `checked.detail` and `ended_by` read `<the value is not kept> is outside
  <rule>`: no value appears in plain.

The verifier re-reads each such expectation and compares `outcome`, not `detail`. A FAIL in `record` fails the run
like any other FAIL, and a batch over its threshold FAILs its `batch` row in `record` too.

**What a 0.7 verifier reads.** `checked` and `expectations_batch` read as 0.4, and the stop's `ended_by` reads as any
`unhandled exception:` ending does: its close row prints it.

**What it does not show.** A run that was not stopped shows that no `stop` expectation failed at a step's return, not
that the outputs were right. A stop guards the steps after it, never the step that failed. It is not a policy check
before an action. `checked` says what the reading gave over the bytes recorded at that moment, under `reader`'s
version. Code the app runs after catching `ExpectationStopped`, or outside any stage, is not stopped. On a run that
keeps no outputs, the result written during the run cannot be re-read: it is the SDK's word, under the run's
signature. A batch's count is written, not which documents failed.

### The recipient's confirmation

At a gated step, beside `ot.decision(...)`, `ot.permit_presented(permit_token, request={...})` records the permit
the step presented, and `ot.confirmation(token)` the token the recipient returned, however it came back. One
presentation per step.

- `authorization.permit_digest` (`sha-256=:…:` over the token's bytes as given), `permit_iss`, `permit_jti`,
  `permit_aud`, `permit_exp`, and `permit_status` `could not be read` where the token did not parse.
- `authorization.request`: `content_digest`, `signature_base_digest` (`sha-256=:…:`) and `keyid`. No request body and
  no key is recorded.
- `authorization.confirmation_digest` (`sha256:`), and the token itself, always kept, in
  `authorization/<receipt stem>/confirmation.jwt`, beside `artifacts/`.
- The permit token is not kept by default. `ot.decision(ref, permit=token)` still records it verbatim, as in
  onetrace 0.7.

onetrace-verify reads five rows, `confirmation: request`, `permit`, `recipient key`, `single use` and `outcome`,
each on its own, only for a step that presented a permit, against a recipients' file given with `--recipients`.

**What a 0.7 verifier reads.** `authorization`'s new members, with or without `decisions`, `permit_status` and the
`authorization/` folder read as 0.4.

**What it does not show.** A confirmation shows the recipient said it acted, not that the effect happened in the
world: that is the recipient's word, signed. A `refused` confirmation is likewise the recipient's word that it did not
act. A trusted key means the key is on the list you gave: onetrace does not decide whom to trust. The rows other than
the Key row compare what a confirmation says whether or not its signature verified: a Request or Permit PASS beside a
Key FAIL or NOT-RUN is a match with an unauthenticated statement. The request digests are the ones the step wrote when
it sent the request: a match shows the recipient confirmed what the step says it sent, not what went on the wire, and
the presenter's own request signature is not checked (no body or key is kept). In a refusal at step 2, the permit's
issuer and id are what the recipient read, not what it authenticated. Single use is checked across the records you
give one verifier run, not across every record that exists; a byte-identical repeat is counted once, so a second
effect behind a reused token cannot be seen. A confirmation's `iat` is the recipient's own clock; `mandate_verdict` is
recorded, not checked; unknown members are named, not checked. The rows read the record as onetrace wrote it:
recording a confirmation's digest in a step does not discharge the Bound Permits draft's `present_bound` obligation,
which onedoor implements; that is the presenter's own report. The rows make no network calls and ask no recipient
anything. **A reservation that never completes:** with a durable store, a recipient's open reservation holds for good,
and onedoor's in-memory store, `InMemoryConsumeStore`, loses it on restart. That is the recipient's store, and no row
reads it.

### Re-runs with parts chosen separately

- `code`, in the first receipt, with a manifest copy read only where it equals it: `commit` (the 40 or 64 hex of
  `HEAD`, or `not observed: <reason>`), `dirty` (`true`, `false`), and `lock_name` and `lock_digest` (the first of
  `uv.lock`, `poetry.lock`, `requirements.txt`). Opt-in: `@ot.run(record_code=True)`, `Recorder(record_code=True)` or
  `ONETRACE_RECORD_CODE=1`. A run that does not ask writes the same receipts as before, and `--code-of` refuses a run
  with none.
- `rerun_from`, beside `rerun`, never inside it, in every receipt of such a re-run, with a manifest copy: what
  `onetrace reproduce --config-of REF --only …`/`--except …`, `--code-of B` or `--substitute … --config-of …` took:
  `config_parts`, `code_of_run`, `code_of_chain_head`, `code_commit`, `environment` (`today`, always), `lock_differs`,
  and `config_of_run` and `config_of_chain_head` on a kind that may not hold them in `rerun`. `rerun.kind` stays one
  of the four.

**What a 0.7 verifier reads.** `code` reads as 0.4, with a lock or none; `rerun_from` reads as 0.4 on a twin, a
reproduce and a counterfactual, and the run shows its re-run mark.

**What it does not show.** It shows what that combination does today, with today's services and model. Code from B
with today's environment is not B's run. A recorded commit is what `git` reported when the run opened, and
`manifest_digest` covers the code file the run names, not every file that commit holds. `dirty` `false` says tracked
files matched; untracked files are not read. `lock_differs` compares two files' digests, not which package differs.
A part named and taken is a value handed to the code through a parameter, not shown to be used.

### Every member format 0.5 adds

Every scalar is a string, and every member is optional: a record that does not hold one reads as a record written
before 0.5 does.

| Record | Member | Values | Written by this build |
|---|---|---|---|
| receipt | `state_reads`, `state_writes` | each entry `store`, `store_kind`, `key_digest` or `key`, `version`, `version_kind`, one of `digest` with `digest_form`, `digest_status` or `found` (`false`), and `as_of`, `ids_digest`, `kept` where they apply; `[]` for none | declared through `ot.state.read` or `ot.state.write`: yes; by a store hook: yes |
| receipt | `state_cut` | the count of entries past the step's 1000 | yes |
| receipt | `step` | a closed list: `kind`, `effect_basis`, `lower_hook` | yes |
| receipt | `step.effect_basis` | `vector query` beside `read`, `not classified`; `vector change` beside `write`, `not classified` | yes |
| first receipt; manifest copy | `state_at_open` | each `{store, version, version_kind}` | declared, and by a store hook: yes |
| kept file | `state/<receipt stem>/reads/<n>`, `.../writes/<n>` | the bytes `digest` is over | yes |
| receipt | `step.kind` | `model call`, `tool call`, `retrieval`, `decision`, `state read`, `state write`, `transform`, `other` | a decorated stage: yes; the `openai`, `httpx` and `requests` hooks: yes |
| receipt | `tool_call` | `name`, `arguments_digest` or `arguments_status`, `result_digest` or `result_status`, `call_id`, `requested_by` (`{step, call_id}`) | yes |
| receipt | `agent` | `name`; `role`, `runs_on` (`{kind, name, version}`) where given | yes |
| every receipt; manifest `agent` | `run_agent` | as `agent`, equal in every receipt | yes |
| receipt | `messages` | each `seq`, `from`, `to`, `kind`, `digest`, `bytes`, `media_type`, `kept` | yes |
| receipt | `messages_received` | each `{from_step, seq, digest}`, or `{digest}` | yes |
| kept file | `messages/<receipt stem>/<seq>` | a message's bytes | yes |
| callee's first receipt | `parent_link` | `run`, `stage`, `head` (`sha256:<64 hex>` or `-`), `origin`; `traceparent` where well formed; or `status` alone (`unreadable: <reason>`) | yes |
| callee's first receipt | `parent_link.origin` | the origin run id, as received | yes |
| callee's manifest | `parent_run`, `parent_stage` | copies of `parent_link.run` and `.stage` | yes |
| callee's manifest | `origin_run` | a copy of `parent_link.origin` | yes |
| caller's receipt | `calls` | each `{child_run, child_head, status}`, `traceparent` where sent; `status` `head returned`, `called, head not returned`, `unreadable: <reason>`, `not sent: <reason>` | through `ctx.child`, and from the `httpx` and `requests` hooks: yes |
| receipt | `model_usage` | each `{record, input_tokens, output_tokens, total_tokens, cost}` | from the `openai` hook: yes; `cost`: not yet |
| receipt | `model_call_attempts` | each `{record, retries, attempts}`, each attempt `{status, request_digest}` | from the `openai` hook: yes |
| receipt | `model_call_failed` | each `{record, failed}` | from the `openai` hook: yes |
| receipt | `tokenizer_digest_method` | each `{record, form, keys, files}`, `form` `sha256-of-canonical-name-map/1` | not yet |
| receipt | `auto.library` | adds `anthropic`, `httpx2`, `langchain`, `langgraph` | yes |
| receipt | `step.lower_hook` | `library`, the lower hook's; `note`, `already recorded by the framework hook`; on a framework model step | with the framework hooks: yes |
| receipt | `framework_error` | `not recorded: <what was not recorded>` | with the framework hooks: yes |
| first receipt; manifest copy | `thread_id` | the framework's thread id, as its metadata gives it | with the `langgraph` hook: yes |
| receipt | `emission.queue` | `drop`; absent reads `block` | yes |
| receipt, manifest | `emission.gaps[]`, `gaps[]` | a dropped step: reason `dropped: the writer's queue was full at <node>`; a recovery's: `recovered: its outputs did not hold`, `recovered: an earlier entry did not hold` | yes |
| receipt, manifest | `coverage.boundaries[]`, `boundaries[]` | adds `kind` `queue full` and `kind` `recovered` | yes |
| receipt | `outputs_digest_only` | each as an `outputs` entry, `kept` `digest only: over the cap of <n> bytes` | yes |
| recovered close receipt | instrument `kind`; constants `onetrace.recovered`, `onetrace.last_confirmed`, `onetrace.steps` | `close-recovered`; `true`; a node id or `none`; the receipts before it, gaps not counted. Never `onetrace.ended_by` | yes |
| local, not part of the record | `.journal`, `.journal.empty`, `<run>.unrecoverable` with `UNRECOVERABLE.txt` | `onetrace-journal/1` | yes |
| receipt | `expectations[].checked` | `when`, `mode`, `outcome`, `detail`, `reader` | yes |
| receipt | `expectations_batch` | entries as `expectations`, with `batch` `{over, more_than}`; `checked` adds `failed`, `of` | yes |
| close receipt | `onetrace.ended_by` | the stop's text inside `unhandled exception:` | yes |
| receipt | `authorization.permit_digest`, `permit_iss`, `permit_jti`, `permit_aud`, `permit_exp`, `permit_status` | the presented permit's digest and claims; `could not be read` | yes |
| receipt | `authorization.request` | `content_digest`, `signature_base_digest`, `keyid` | yes |
| receipt | `authorization.confirmation_digest` | `sha256:` over the token | yes |
| kept file | `authorization/<receipt stem>/confirmation.jwt` | the token | yes |
| first receipt; manifest copy | `code` | `commit`, `dirty`, `lock_name`, `lock_digest` | with `record_code`: yes |
| every receipt; manifest copy | `rerun_from` | `config_parts`, `code_of_run`, `code_of_chain_head`, `code_commit`, `environment`, `lock_differs` (with `lock_name`, `lock_digest`), `config_of_run`, `config_of_chain_head` | yes |

### Reading the new members

- **Absent reads as not recorded.** No state member says nothing was read or written; `[]` says recorded, nothing
  there. No `step.kind` is not `other`. No `code` is not a commit `not observed`.
- **Read `step.effect_basis` before `effect_label`.** A vector query's label is `read`, `not classified`, and a
  vector change's `write`, `not classified`, so a 0.7 reader sees a true label; the real basis is beside it.
- **A write is a write.** A step with an entry in `state_writes` reads as `write` to every re-run, whatever its
  label.
- **A manifest copy is read only where it equals the receipts'.** `state_at_open`, `agent`, `parent_run` and
  `parent_stage`, `origin_run`, `code`, `rerun_from` and `thread_id` in a manifest are read only where they equal the
  receipts', as `rerun` is; a copy that differs FAILs, and a copy with nothing beside it in the receipts FAILs too. A
  manifest's `parent_run` with no `parent_link` in the first receipt is in-process nesting, as in onetrace 0.5
  (format 0.3).
- **A message, a kept state value and a confirmation are not outputs.** Each is kept beside `artifacts/`, never in
  it, and none changes a verdict.
- **A capped output is in `outputs_digest_only`,** never in `outputs` with its file gone. Expectations on it read
  NOT-RUN, `the output was not kept`.
- **A recovered close is not a close.** Only kind `close` is a close receipt; `close-recovered` says a later process
  wrote it. Nothing reads a recovered run as closed by its own hand. `onetrace sign` treats it as not closed.
- **`onetrace.ended_by` still has five forms.** The stop's text is the `unhandled exception:` form with its text
  fixed.
- **`checked` is compared by `outcome`, not `detail`,** so a wording change between verifier versions is not a
  difference.
- **`rerun_from` sits beside `rerun`.** `rerun.kind` is still one of the four, and `--config-of` with `--substitute`
  is a `counterfactual` whose `rerun_from` holds the configuration.

**How this build's onetrace-verify reads them.** Each has rows of its own, PASS, FAIL or NOT-RUN, shown only on a
record that holds the member:
- **state:** `<receipt>: state entries` (each entry in form; FAIL `state_cut <value> is not a decimal count`),
  `<receipt>: step`, `<receipt>: state_writes against
  effect_label` (FAIL `labelled read and records a state write`), `<receipt>: state kept` (the kept value recomputes),
  and `state at open` (the manifest's copy against the first receipt's);
- **kind and agent:** `<receipt>: step kind` (FAIL `'<value>' is outside the eight`; a kind on the list is counted in
  the summary), `<receipt>: step kind against its record`, `<receipt>: tool_call`, `<receipt>: tool_call
  requested_by`, `<receipt>: agent` and `run agent`;
- **messages:** `<receipt>: messages`, PASS `N messages, in order, each in form`, FAIL naming each entry out of form,
  `messages[<n>]: <what>`: a member outside the table, a missing member, `seq` not `1..N` in order, a digest out of
  form, `bytes` not a decimal, `from`, `to`, `kind` or `media_type` not a non-empty string (`kind` 1 to 64
  characters, no control character); `<receipt>: messages kept`; and `<receipt>: messages_received`, FAIL on an entry
  out of form (`{from_step, seq, digest}`, or `{digest}` alone), a `from_step` that is not an earlier step, no
  message at that `seq`, and a digest that differs from the sender's;
- **the cross-service link:** `linked runs match`, in "Across services" above;
- **the writer:** `writer: queue`, `writer: gaps`, `<receipt>: outputs_digest_only`, the close receipt's row
  `recovered: last confirmed <node>`, and with `--require-closed`, FAIL `not closed by its own process: recovered`;
- **expectations during the run:** `<step>.<name> as checked during the run`, `<step>.<name> checked`,
  `<step>.<name> batch` and `the run's stop`;
- **the confirmation:** `confirmation: request`, `confirmation: permit`, `confirmation: recipient key`,
  `confirmation: single use` and `confirmation: outcome`, with the recipients' keys from `--recipients FILE`;
- **re-runs:** `re-run from`, PASS `<parts> from <run>; code from <run> at <commit>, environment today`, or `no part
  named` where it names none, and FAIL on receipts that disagree, a manifest copy that differs, `a rerun_from on a run
  with no rerun`, `rerun_from is not an object`, `config_parts with no config_of_run and config_of_chain_head in
  rerun or rerun_from` (it needs both), `code_commit <value> is not 40 or 64 hex characters` (lowercase), and
  `environment <value> is not 'today'`; `code`; and `the code matches its commit` (NOT-RUN unless `--repo DIR` is
  given).

- **the model call's members:** `<receipt>: model_usage`, `<receipt>: model_call_attempts`, `<receipt>:
  model_call_failed` and `<receipt>: tokenizer_digest_method`; and the labels of `anthropic` and `httpx2` are read as
  the labels table gives them.

**How onetrace-verify 0.7.0 and 0.7.1 read the new members.** As above, under each part: every member reads as 0.4,
but for the two exceptions, an undocumented library's one NOT-RUN row and a digest-only output's absent rows. Rows
read against another base are a capped output, a drop's gap, a recovered close and the stop's form. **Forms that
would not read as 0.4 are not used:** a new `onetrace.ended_by` form, a basis outside the six or a third member in
`effect_label`, a new member inside `rerun`, a new member or a new format line in a `/1.1` record, an output left in
`outputs` with its file gone, a `more_than` inside a `declaration`, and an `onetrace.` constant of a new name on an
auto step. A gate that relies on the new rows needs a verifier that reads format 0.5.

**How onetrace-verify 0.6.1 reads a 0.5 run.** As 0.7.0 and 0.7.1 do, with one pass row fewer: the same exit, the
same FAIL rows and the same NOT-RUN rows, and a summary of one PASS less. Measured on the golden example (137 pass
against 0.7's 138), the quickstart page's two runs (78 against 79, and 104 against 105) and the origin's vectors
(R317: 76 against 77), each with no FAIL row.
