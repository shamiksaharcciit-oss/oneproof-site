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

**Fix:** Carry the run into the thread, `pool.submit(contextvars.copy_context().run, fn, ...)`; or, when the call belongs to no run, call `fn.__wrapped__(...)`.

## stage-function

`@ot.stage` was put on something with no single return value to record: a generator, an async generator, or a lambda.

**Fix:** Decorate a plain or async function that returns its result.

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

An assertion was recorded without the constants it holds under, or `constants` was used as an assertion's name.

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

## anchor-run

`onetrace anchor` can't read the run's chain head: the run has no MANIFEST.json (it isn't finished), or the manifest can't be read, is over its size or depth cap, or names a chain head of the wrong form.

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

The run can't be signed as asked: it isn't finished (it has no MANIFEST.json), the signer label isn't a non-empty string within its length, the record would read FAIL, or its temporary file can't be written. Nothing is stored.

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

## verify-anchor

A record beside the chain (an anchor in anchors/) fails its check, or the file you passed to check it (`--headers`, `--tsa-cert`) can't be read.

**Fix:** Restore the record as it was written, or anchor the run again with `onetrace anchor`; pass the header or certificate files in the form `onetrace-verify --help` names.

## verify-signature

A record in signatures/ fails its check: it is malformed, has an unknown member or the format name before 0.2.0, carries a key_id that isn't its key's fingerprint, covers another chain head, or doesn't verify; or signatures/ holds a file that isn't a `<n>.json` record, or is a link. Or the trust file you passed (`--trust`) can't be read.

**Fix:** Sign the run again with `onetrace sign`; a signature is never edited. Pass the trust file in the form `onetrace-verify --help` names. For a record in the format name before 0.2.0, `onetrace-signature/0.1`: move the record out of signatures/ (a development build before 0.2.0 wrote it, and no release writes that format), then sign the run again with onetrace sign.

## verify-plan

The run's edges don't match its approved plan (`declared_edges`), or the manifest's edges aren't the ones its receipts record.

**Fix:** Record the run again on the approved plan, or approve the plan it ran; restore the manifest if it was edited.

## unknown-command

`onetrace` was given a subcommand it doesn't have. Verifying a run is a separate command, `onetrace-verify`.

**Fix:** Run `onetrace --help` for the subcommands; to verify a run, `onetrace-verify <run folder>`.
