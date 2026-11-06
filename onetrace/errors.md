# onetrace errors

Every refusal from onetrace ends with a `fix:` line and a `see:` line naming one of the
sections below. Each section says what the refusal means and what to do about it.

This page is generated from `onetrace/errors.py`; edit the table there, not this page.

## run-declaration

The run was opened without something every record needs: a run id, a non-empty list of distinct declared stages, or an emission policy (`fail-closed` or `fail-open`).

**Fix:** Give the run its id, its declared stages and its policy. With `@ot.run`, name the stages in `stages=[...]`.

## run-bytes-cap

`max_run_bytes` is smaller than the smallest receipt this run's own declared stages could have, so a stage that crossed it couldn't even be given a receipt saying why.

**Fix:** Set `max_run_bytes` to at least the minimum the message names, or leave it unset.

## run-folder-used

The run folder already holds a run. A record is never overwritten or merged into.

**Fix:** Give the run a new run id or run folder, or move the old run away first.

## run-folder-locked

Another process holds the run folder: its lock file is present. A run is written by one process.

**Fix:** Wait for the other process to finish, or give this run its own folder. Remove a lock file only when you know no process is writing that run.

## run-manifest

`@ot.run` could not find the source file to record as the run's manifest.

**Fix:** Pass `manifest=<path to your pipeline file>` to `@ot.run`.

## folder-name

A stage name, an instance or a run id names a folder in the run, and this one can't: it is empty, reserved, too long, or holds a character a file system refuses.

**Fix:** Rename it, using letters, digits, spaces, `-`, `_` and `.`.

## intake-name

A stage uses the name the run records its own arguments under (the intake stage).

**Fix:** Rename that stage.

## no-stage-context

Something that belongs to a stage (`ot.constant`, `ot.assertion`, the stage context) was used where no stage is running.

**Fix:** Call it inside the decorated stage whose output it describes.

## decision

A step cited an onedoor decision with `ctx.decision`, but what it passed is not a decision-reference object, or the permit it passed is not a compact JWS string.

**Fix:** Pass the `onedoor-decision-ref/1` object as `ref`; pass the bound permit's compact JWS (a string) as `permit` where one was issued; pass the action object the step is about to send as `action`.

## verify-nested

A nested run does not match the head the outer run recorded for it: the inner run's own chain head differs from what the outer run recorded as that run's input, or an inner run's folder was given but its manifest cannot be read.

**Fix:** Give each nested run's folder with --nested-run; restore the outer and inner records as they were written, so the inner run's chain head equals the head the outer run recorded.

## nesting-depth

A stage was called more deeply nested than the limit onetrace records (NEST_DEPTH_LIMIT). A call past the limit is refused and named, never recorded as a silent gap, so a runaway recursion cannot fill a run folder.

**Fix:** Reduce the nesting depth, or flatten the recursion into declared stages; the limit is stated in docs/nesting.md.

## traceparent

The `TRACEPARENT` environment variable is set to something that is not a W3C traceparent, so the run or a step could not record the trace context it ran in. A trace is a view, not evidence, and a broken one is never recorded.

**Fix:** Set TRACEPARENT to `00-<32 hex trace id>-<16 hex span id>-<2 hex flags>` (neither id all zero), or unset it; a run with no active span and no TRACEPARENT records no trace context.

## keep-inputs

`keep_inputs` names something that is not a parameter of the function, or `keep_inputs_cap` is not a whole number of bytes from 1 to 65536. Checked when the stage is decorated.

**Fix:** Name the function's own parameters, spelled as in its signature, and give the cap in bytes (default 4096).

## reserved-constant

A constant's name starts with `onetrace.`, which only onetrace's own constants use (`onetrace.kept_inputs`, `onetrace.inputs_not_kept`, `onetrace.links`), whether it was set with `ctx.constant` or straight into `ctx.constants`.

**Fix:** Rename the constant without the `onetrace.` prefix.

## reserved-stage

A stage is named `onetrace.close`, the name every run's close receipt is recorded under (format 0.4), or `onetrace.check`, the name a check's run is recorded under. onetrace writes both itself, and no stage of a team's may take either.

**Fix:** Rename the stage.

## run-close

`close(ended_by=...)` was given a value that is not one of the ways a run ends: `exit`, `SIGTERM`, `unhandled exception: ` followed by the exception's class, or a re-run's stop, `re-run stopped before <node>: effect <value> (<basis>)` or `...: effect not recorded`.

**Fix:** Pass `exit` for a run that ended in the ordinary way, or leave `ended_by` out.

## not-closed

The run holds no close receipt: its record ends at its last step, and nothing in it says the run finished. The run was killed, or ended without closing, or it was written before format 0.4. A signature over it would cover a record that may be cut short, so it is not signed by default.

**Fix:** Sign it anyway with `onetrace sign --not-closed` (or `sign_run(..., not_closed=True)`): the signed statement then says the run is not closed, inside the signed bytes.

## constant-name

A stage's constants can't be read as a dict, a constant's name is not a str, or two names read as the same characters (a `str` subclass, such as a `StrEnum` member, is read as its characters; the constants themselves as `dict()` reads them, as 0.3.0 did).

**Fix:** Add constants with `ctx.constant(name, value)` or by a `str` key in `ctx.constants`, and give each constant its own name.

## stage-undeclared

A stage ran, or was named, that the run doesn't declare.

**Fix:** Add it to the run's declared stages, `@ot.run(stages=[..., 'name'])`, or call the undecorated function instead.

## stage-order

A stage ran out of the declared order. In a linear run, each stage is the next declared one.

**Fix:** Call the stages in the order the run declares them, or declare the order they really run in.

## node-repeated

A node has already written its receipt. Each node id is written once in a run.

**Fix:** Name each call of a stage that runs more than once (`.instance(name)`), or declare it `repeats=True`.

## repeated-call

A stage was called again, or by overlapping calls, in a way that wouldn't name each call the same way in every run.

**Fix:** Declare the stage `repeats=True`, which numbers its calls, or name each call with `fn.instance(name)(...)`; give overlapping calls names of their own.

## instance-name

An instance name is empty or not a string.

**Fix:** Name the instance with a non-empty string: a branch name such as `a`, or an iteration number such as `1`.

## no-run-in-thread

A decorated stage was called in a thread that doesn't carry the active run. A stage is never left out of a run silently.

**Fix:** Carry the run into the thread: `ot.pool()` for a pool, `ot.map(stage, items)` for a fan-out, `ot.carry(fn)` for a thread you start (or `pool.submit(contextvars.copy_context().run, fn, ...)`); or, when the call belongs to no run, call `fn.__wrapped__(...)`.

## fan-out-key

`ot.map` or `ot.gather` was given something that isn't a decorated stage, an item whose key is not a string or an int, or two items with the same key.

**Fix:** Pass a function decorated with `@ot.stage`, and a `key=` that gives each item its own string or int (a document id, say); left out, the key is the item's position in the list.

## run-closed

A stage was called after its run closed: a call carried into the run (`ot.carry`, `ot.pool`, a copied context) that ran after the run function returned. A finished record is never added to.

**Fix:** Wait for the carried calls before the run function returns (join the thread, leave the pool's `with` block), or call the stage inside a run that is still open.

## export-unreadable

`onetrace export otel` could not read the run well enough to export it: a manifest or receipt that doesn't parse, a chain entry outside the run folder, a chain head or time it can't read. Nothing is written; a partial trace is never exported.

**Fix:** Run `onetrace-verify` on the run: it names what is wrong with the record. Export a run it reads.

## child-process

A decorated stage was called in a child process (a fork of the run's process, as `multiprocessing` and process pools make). One process writes a run folder.

**Fix:** Call the stage in the run's own process, in threads (`ot.map`, `ot.pool`) or asyncio tasks (`ot.gather`); run the child's work undecorated (`fn.__wrapped__`) and record its result in a stage of the parent.

## stage-function

`@ot.stage` was put on something with no single return value to record: a generator, an async generator, or a lambda.

**Fix:** Decorate a plain or async function that returns its result.

## hooks-off

`@ot.stage(hooks=...)` was given a value that is not `on` or `off`. `hooks="off"` turns the automatic library hooks off inside the stage, so a hooked call there records no step of its own.

**Fix:** Pass hooks="off" to turn the hooks off inside the stage, or leave it unset (the default, "on").

## stage-effect

`@ot.stage(effect=...)` or `Recorder.stage(effect=...)` was given a value that is not `read` or `write`. The value is written as the receipt's `effect_label`, basis `declared on the stage`: whether running the stage again acts on the world outside the run.

**Fix:** Pass effect="write" for a stage that acts on the world outside the run (sends, writes, orders), effect="read" for one that does not, or leave it unset to record no label.

## keep-config

`keep_config=` (on `@ot.stage`, `@ot.run` or `Recorder`) was given a value that is not `True` or `False`, or `keep_config_except=` is not a list of configuration keys. With `keep_config=True` a step's instrument configuration is kept as `config/<receipt stem>/config.json`, named by the receipt's `config_kept`; a key in `keep_config_except` is written as `not kept`.

**Fix:** Pass keep_config=True to keep the configuration, or leave it unset; name the keys never to keep, as keep_config_except=["api_key"].

## rerun-plan

The process was given a re-run plan in `ONETRACE_RERUN_PLAN` that can't be read, or that is not as this build writes it. `onetrace reproduce` writes the plan and hands it to the pipeline it re-runs, so the produced run carries the re-run mark; a run is not recorded without the mark it was asked for.

**Fix:** Leave ONETRACE_RERUN_PLAN unset when you run the pipeline yourself; `onetrace reproduce` sets it for the re-run it starts.

## check-runner

`onetrace check` was given a runner it does not run. In 0.7 that is a JSON runner (`--runner FILE`) holding an `{input:<name>}` placeholder: `onetrace reproduce` fills it from the run's kept input, and a check does not. A check with a `onetrace-runner/0.3` runner that uses only `config.*` params, or neither, runs.

**Fix:** Write the input file's path in the runner's argv in place of its {input:...} placeholder, or re-run with onetrace reproduce, which fills it.

## expectation

An expectation given to a stage's `expect=` can't be recorded: it was not made by `ot.expect.range`, `unit`, `relation` or `member`; a bound (`lo`, `hi`, `within`) is not a decimal string; its target or `of=` names no member or JSON Pointer; or two expectations of one step share a name.

**Fix:** Build each with `ot.expect.range`, `ot.expect.unit`, `ot.expect.relation` or `ot.expect.member`; give every bound as a decimal string, as `"0"` or `"0.01"`; give two expectations of one step two names with `name=`.

## meaning-fields

A meaning field was given without the one it explains: `note=` explains a stated `rederivable=`; or `rederivable=` and `note=` were given to a run function that has no arguments to describe.

**Fix:** Pass `rederivable=` with `note=`, or drop `note=`. Meaning fields are a person's answer: leave them out rather than guess.

## clock-backwards

A stage's end time came before its start time: the clock went backwards during the stage.

**Fix:** Run on a clock that doesn't step backwards (a synchronised system clock), and run the stage again.

## value-unencodable

A value a stage takes or returns, or a constant or assertion, has no form in the record's JSON: NaN or Infinity, an integer beyond 2^53 - 1, a non-string dict key, bytes or an array inside a list or dict, or a type with no encoder.

**Fix:** Record it in a form JSON keeps (a string, for example), pass bytes and arrays as their own argument, or register an encoder with `ot.encoder(Type, fn)`.

## encoder

`ot.encoder` was given something other than a type and a callable, or an encoder raised, or returned the same type it was given.

**Fix:** Register `ot.encoder(MyType, fn)` with a function that returns a dict, list or string.

## instrument

A stage's instrument can't be recorded: it has no name, its version doesn't pin a build (empty, `latest`, a branch name), its package isn't installed, `rederivable` isn't `true` or `false`, or its configuration has no canonical form.

**Fix:** Name the instrument and pin its exact version; install its package, or build the Instrument yourself.

## instrument-declaration

The run's instruments, declared when it opened, don't match its stages: a stage with none, a stage given a second one, or an instrument for a stage the run doesn't declare.

**Fix:** Declare one Instrument for each declared stage, by stage name or node id, either when the run opens or on each stage, not both.

## trust-class

An input or output was given a trust class that isn't one of `operator-authored`, `model-generated`, `externally-sourced`.

**Fix:** Use one of the three trust classes. Which one is a person's answer: ask rather than guess.

## secret-input

An input is declared secret, and the emitter never computes a digest over a secret.

**Fix:** Leave the secret out of the stage's recorded inputs; record the name of the setting that holds it instead.

## input-unidentified

A stage read an input that has no stored artifact, so nothing identifies what it read.

**Fix:** Read the input through the stage context (`ctx.read_external`), which stores what it read.

## input-changed

An input's bytes no longer match the digest recorded for them: the file changed after it was recorded, or the digest supplied for it is wrong.

**Fix:** Don't change an input while a run reads it. Pass the digest of the bytes as they are, or let the SDK compute it.

## input-name-clash

A file named in `files=` is recorded under a name a parameter already has.

**Fix:** Rename the file or the parameter, or record one of them yourself with `ctx.read_external(path, name=...)`.

## output-name

An output's name isn't one plain file name that every system stores as written: it has a folder part, or it is a name Windows would store under another name.

**Fix:** Give the output one plain file name: letters, digits, spaces, `-`, `_` and `.`, with no folder part.

## output-name-repeated

A stage wrote a second output under a name it had already written. The second write would replace the stored file the receipt already lists, and the record would no longer verify. Different stages, and different instances of one stage, may use the same name.

**Fix:** Give each output of a stage a distinct name.

## receipt-read

A stage asked for another node's receipt that isn't in this run, or named a stage with several instances without saying which.

**Fix:** Name a node that has run, and name the instance when the stage ran more than once.

## json-output

`write_json` was given something it doesn't write: a top-level value that isn't a JSON object, or a number JSON can't keep exactly.

**Fix:** Wrap the value in an object, e.g. `{"items": [...]}`, and turn numbers it can't keep into decimal strings first.

## assertion-constants

An assertion was recorded without the constants it holds under, or `constants` or `undeclared` was used as an assertion's name (with `ctx.assertion` or straight into `ctx.assertions`).

**Fix:** Record the constants with `ot.constant` (or `ctx.constant`) alongside the assertion.

## boundary

A boundary isn't a name and kind (with an optional note), or names a stage the run doesn't declare, so a reader couldn't place it.

**Fix:** Give the boundary a declared stage's name and a kind, each a non-empty string.

## gap

A gap names a stage the run doesn't declare, or gives no reason. A gap records a receipt that was never written, and why.

**Fix:** Name a declared stage and say why its receipt is missing.

## edges

A declared or observed edge doesn't fit the run: not a from/to pair, a stage it doesn't declare, declared twice, `repeats` other than `true`, or an edge to no receipt in the run.

**Fix:** Declare each edge once, between declared stages, and give `repeats` only as `true`.

## receipt-write

A receipt couldn't be written in canonical form or at all. Under `fail-closed` the stage's result is discarded rather than left unrecorded.

**Fix:** Fix the cause the message names (often a full disk or a folder that can't be written), and run again.

## anchor-heads

The anchor block names chain heads that aren't a non-empty list of chain-head strings, or an index outside them.

**Fix:** Pass a non-empty list of chain heads and an index within it.

## chunk-index

`ot.chunks` was given something it can't index: `keep_text` that isn't True or False, an item that isn't a (doc, text) pair, a document that isn't a non-empty name, or a chunk's text that isn't a string.

**Fix:** Pass `ot.chunks` a list of (doc, text) pairs, each doc a non-empty string and each text a str, and `keep_text` as True or False.

## corpus-manifest

A corpus manifest is malformed: its digest isn't `sha256:` and 64 lower-case hex; member, preimage and proof weren't given together; or the stage wrote one as well as the run's corpus link.

**Fix:** Pass the digest as `sha256:` and 64 lower-case hex, give member, preimage and proof together, and leave the link to `ot.corpus_from`.

## corpus-link

`ot.corpus_from` can't link this query run to its ingest run: no run at the place given, a run that doesn't verify, no such index stage, or stages that aren't the run's own.

**Fix:** Pass the ingest run's folder (or its chain head) and the stages of this run that read the corpus; link only a run that verifies.

## model-link

`ot.model_from` can't link this run to its provisioning run: no run at the place given, a run that doesn't verify, no such serve stage, or stages that aren't the run's own.

**Fix:** Pass the provisioning run's folder (or its chain head) and the model steps of this run; link only a run that verifies.

## anchor-run

`onetrace anchor` can't read the run's chain head: there is no run folder at the path given (or it is a file), the run has no MANIFEST.json (it isn't finished), or the manifest can't be read, is over its size or depth cap, or names a chain head of the wrong form.

**Fix:** Anchor a finished run, by its folder, and check that onetrace-verify reads the run as intact first.

## anchor-record

The anchor record isn't one the writer accepts: malformed, or not a record of this run's chain head.

**Fix:** Let `onetrace anchor` build the record from its source; don't write anchors/ by hand.

## anchor-folder

The run's anchors/ folder can't be written safely: it is a link, not a folder, can't be prepared or listed, has no free name, or changed while the record was written. Nothing is stored or claimed.

**Fix:** Anchor a local copy of the run in a folder nobody else is writing to, and run the command again.

## anchor-tsa

The RFC 3161 time-stamp authority's answer can't be used: the [crypto] extra is missing, the authority can't be reached or refused, or its response is too large, of the wrong form, for another request, or doesn't verify against the certificate and root you pinned.

**Fix:** Install `onetrace-verify[crypto]`, check `--tsa-url`, and pin the authority's own certificate and root with `--tsa-cert` and `--tsa-root`.

## anchor-calendar

No OpenTimestamps calendar gave a usable answer: none named, one not https, none answered, or every proof still pending.

**Fix:** Name each calendar as `--calendar https://...`; a pending proof reaches a Bitcoin block after some hours, so run `--upgrade` again later.

## anchor-headers

An upgraded OpenTimestamps proof can't be checked against your block headers: the block isn't in the file, the file can't be read, or the proof would read FAIL.

**Fix:** Pass `--headers` a JSON object of height to the 80-byte header as 160 lowercase hex, including the block the message names, taken from the chain itself.

## signature-folder

The run's signatures/ folder can't be written safely: it is a link, not a folder, can't be prepared or listed, has no free name, or changed while the record was written. Nothing is stored or claimed.

**Fix:** Sign a local copy of the run in a folder nobody else is writing to, and run the command again.

## signing-key

The signing key can't be used: it isn't a key file's path or `onetrace.env("NAME")`, the variable is unset, the file can't be read, isn't a regular file or is too large, it isn't an unencrypted Ed25519 private key in PEM form, the [crypto] extra is missing, or the key file (or a hard link to it) is inside the run folder. For `onetrace keygen`: the place given for the new key is inside a run folder, already exists, or can't be written.

**Fix:** Keep signing keys outside every run folder, and sign with a key `onetrace keygen` made: its file's path, or `onetrace.env("NAME")` for its PEM text in the environment. For `onetrace keygen`, when the file already exists: choose another path; a key is never overwritten. When it can't be created: create the folder first, or choose a path you can write.

## signing-store

The run can't be signed as asked: there is no run folder at the path given (or it is a file), it isn't finished (it has no MANIFEST.json), the signer label isn't a non-empty string within its length, the record would read FAIL, or its temporary file can't be written. Nothing is stored.

**Fix:** Sign a finished run that onetrace-verify reads as intact, with a short signer label or none, and run the command again.

## verify-receipt

A receipt doesn't read as written: its file, its bytes, its form or a field the format requires. Each FAIL row names the receipt and the check.

**Fix:** Restore the receipt exactly as it was written; a record is never edited. If the recorder wrote it so, record the run again with a recorder that writes the field.

## verify-chain

The chain doesn't hold together: a receipt's link to the one before it, its digest in the manifest, the manifest's own head, or the order of the stages.

**Fix:** Restore the manifest and the receipts exactly as they were written, in their order.

## verify-artifacts

An output file a receipt names is missing from the run's artifacts/ folder, unreadable, or not the file whose digest the receipt records.

**Fix:** Restore the run's artifacts/ folder as it was written, or verify without `--require-artifacts` when the outputs were deliberately not kept.

## verify-model-call

A model-call record an output names fails its check: it doesn't parse or isn't canonical, names a format this verifier doesn't implement, is missing or has a malformed field, holds a value where it is not observed, or carries a string shaped like an authorization header. A model-call-record/1.1 record also fails when its steps.* members are not in their states and values, its steps digest names no output of the step, its steps file is not lined up with steps.count, or, at L3, its runner, engine core, executor, sampling members or ending are not as L3 writes them. Each FAIL row names the record and the check.

**Fix:** Restore the record as it was written; a record is never edited. If the writer wrote it so, record the run again with a writer that writes the field, and write no credential into any recorded field.

## verify-anchor

A record beside the chain (an anchor in anchors/) fails its check, or the file you passed to check it (`--headers`, `--tsa-cert`) can't be read.

**Fix:** Restore the record as it was written, or anchor the run again with `onetrace anchor`; pass the header or certificate files in the form `onetrace-verify --help` names.

## verify-signature

A record in signatures/ fails its check: it is malformed, has an unknown member or the format name before 0.2.0, carries a key_id that isn't its key's fingerprint, covers another chain head, or doesn't verify; or signatures/ holds a file that isn't a `<n>.json` record, or is a link. Or the trust file you passed (`--trust`) can't be read.

**Fix:** Sign the run again with `onetrace sign`; a signature is never edited. Pass the trust file in the form `onetrace-verify --help` names. For a record in the format name before 0.2.0, `onetrace-signature/0.1`: move the record out of signatures/ (a development build before 0.2.0 wrote it, and no release writes that format), then sign the run again with onetrace sign.

## verify-close

The run's close receipt is not as format 0.4 writes it: it is not the chain's last receipt, there is a second one, its onetrace.steps doesn't count the receipts before it, its onetrace.ended_by is outside its five forms, a constant is missing, or onetrace.close is not the last declared stage. Or you passed --require-closed and the run holds no close receipt.

**Fix:** Restore the receipts as they were written; a close receipt is written by the recorder, last, and a record is never edited. For a run with no close receipt, record it again and let it close (`Recorder.close()`, or a decorated run that returns); a run killed before it closed can't gain one.

## verify-auto

An auto-recorded step or run is not as format 0.4 gives it: an auto block with a member outside the format, a declared other than "false", a target of the wrong shape, no effect_label, an effect label outside its three values and six bases or not what the producer documents for the library, an onetrace. constant or value the format doesn't give, an HTTP step without its status output, a thread context other than its one value; a receipt's declared stages that drop or reorder an earlier receipt's, or add a stage of no auto step; or the run has no manifest auto block, or no open boundary.

**Fix:** Restore the receipts and the manifest as they were written; an auto-recorded run is written by onetrace-auto, and a record is never edited. Record the run again with this release's onetrace-auto.

## verify-rerun

A re-run's mark is not as format 0.4 gives it: the receipts disagree on it, the manifest's copy disagrees with them, its kind is outside the four, it lacks a member its kind requires or holds one it may not, or a counterfactual's substituted step does not hold the output its mark names.

**Fix:** Restore the receipts and the manifest as they were written; a re-run's mark is written by the re-run itself, in every receipt, and a record is never edited.

## verify-receipt-0-4

A step's format 0.4 member fails: it is labelled read and records an external effect; its config_kept.digest is not instrument.config_digest with no partial, its partial is other than "true", or its kept file is not that digest; an expectation it declared, or one an expectations file declares after the run, does not hold, or its declaration_digest does not recompute; the expectations file's seal does not recompute over its content, or it names a step the run does not record, or gives two entries the same name for one step; or an output's empty is other than "true" or "false".

**Fix:** Restore the receipt and the files beside it as they were written; a record is never edited. For an expectation that does not hold, fix the step's output or the expectation, and record the run again.

## verify-embedding

An embedding record an output names fails its check: it does not parse, its identity.digest does not recompute over the fields the format names, or its rows do not number batch.size with positions 0 to n-1 and output.count equal to it.

**Fix:** Restore the record as it was written; a record is never edited. If the writer wrote it so, record the call again with a writer that computes it.

## verify-plan

The run's edges don't match its approved plan (`declared_edges`), or the manifest's edges aren't the ones its receipts record.

**Fix:** Record the run again on the approved plan, or approve the plan it ran; restore the manifest if it was edited.

## verify-decision

An onedoor decision row fails: a declared gated step cited no decision, a reference is not an onedoor-decision-ref/1 object, a step acted on a denied or proposed decision, a permit does not cover the action the step recorded (signature, action digest or lifetime), or a cited decision is not in the export you passed. Or the --decisions or --permit-issuers file can't be read.

**Fix:** Record a decision in every declared gated step (ctx.decision), cite a permitting decision for a step that acts, and record the action a permit covers; pass the decision export as --decisions and the issuer keys as --permit-issuers, in the form onetrace-verify --help names.

## unknown-command

`onetrace` was given a subcommand it doesn't have. Verifying a run is a separate command, `onetrace-verify`.

**Fix:** Run `onetrace --help` for the subcommands; to verify a run, `onetrace-verify <run folder>`.

## s3-extra

A run destination or a sink command names an `s3://` bucket, but the S3 client the sink needs is not installed. onetrace records no credential and no endpoint; the client reads those from its own environment and credential files.

**Fix:** Install the extra: `pip install 'onetrace[s3]'` (hash-locked in requirements-s3.txt), or give a local run destination instead of an `s3://` URL.

## s3-url

An `s3://` value is not a bucket and prefix: it must read `s3://bucket/prefix`, with a non-empty bucket and an optional prefix path.

**Fix:** Write the destination as `s3://bucket` or `s3://bucket/prefix`.

## sink

A finished run could not be uploaded to its `s3://` destination, or a sink command could not reach it: the bucket was unreachable, refused the write or the read, or an object's checksum did not match on the way back. The local run folder is kept.

**Fix:** Check the bucket and the client's own credentials, then `onetrace sink retry <run folder>`; the run is already recorded locally and loses nothing by a failed upload.
