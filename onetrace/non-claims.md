# What onetrace does not claim

This list exists because every one of these is an easy thing to assume onetrace does, and it
doesn't.

- **onetrace does not check whether a pipeline's output is true.** It checks what was recorded,
  and whether an independent verifier can confirm that record is internally consistent and its
  chain unbroken. A pipeline that faithfully records a wrong answer produces a record that
  verifies cleanly — verification is not a truth oracle.

- **A trust class is not a correctness claim.** `operator-authored`, `model-generated`, and
  `externally-sourced` describe *provenance* — where a byte came from — not whether it's right.
  `model-generated` doesn't mean "less trustworthy"; `operator-authored` doesn't mean "correct."

- **`same` does not mean "nothing changed."** It means a stage's output digest matched. The
  instrument that produced it, its configuration, or an asserted constant can all have changed
  without moving the verdict — that's reported as an annotation, deliberately kept separate from
  the verdict itself (see [the verdicts page](verdicts.md)).

- **`reconverged` is not a bug in the comparison.** Two different computations landing on the
  same output is a real thing that happens; onetrace reports it as its own verdict rather than
  either hiding it inside `same` or forcing it to read as a difference.

- **An unanchored run's `originality` check reporting `NOT-RUN` is not a failure.** It means
  exactly what it says: this verifier can establish that a record is internally consistent, not
  that it was first published by whoever holds it. Anchoring (`onetrace anchor`: a timestamp
  proof over the chain head, from a party outside the recorder) is a separate record beside the
  chain; without it, originality is a question onetrace is honest about not answering, not one it
  answers `PASS` on a technicality.

- **An anchor does not show when the run happened, that its output was correct, or who wrote
  the record.** An anchor is a timestamp proof over a run's chain head, from a party outside the
  recorder. It establishes that this exact record existed no later than time T, as attested by
  the anchor's source, under that source's trust assumptions. It does not show:
  - when the run happened (only that the record existed by T);
  - that the output was correct;
  - who wrote the record (that is a signature's job, below).

  An RFC 3161 anchor is only as good as the time-stamp authority's certificate and root you
  pin: the verifier checks a token against those, never against a certificate the token carries.
  An OpenTimestamps anchor checked against block headers you supply is only as good as the source
  of those headers: the verifier trusts the heights in your header file, and checks each header
  only for its own proof-of-work target, not that it is on the chain everyone else follows. The verifier reads each anchor file once and checks and reports from
  those bytes, but a folder someone else is writing to can hold something else the next moment:
  verify a copy you control, not a folder someone else is writing to.

  When `onetrace anchor` can't store a record, its reason can be wrong in one case. On a system
  without `/proc/self/fd` (macOS, for example), if someone moves the run folder away and puts an
  empty folder, or a link to somewhere else, at its old name just as the record is being linked,
  the reason says the temporary file's name was moved, though the file is intact in the moved
  folder. What it says about the outcome stays true: nothing is stored. Anchor a run folder nobody
  else is writing to.

- **A signature does not show that the key wasn't stolen or misused, that the run's output is
  correct, when the record was signed, or who the person behind the key is.** A signature is an
  Ed25519 signature over a run's chain head, by a recorder's key: it shows that the holder of that
  private key signed this exact record. A signature does not show:
  - that the key wasn't stolen or misused;
  - that the run's output is correct;
  - when the record was signed (that is an anchor's job);
  - who the person behind the key is. The verifier knows keys, not people; your trust list is how
    you connect a key to a name, and a valid signature by a key not on it is never a pass.

  The `signer` label in a signature record is the signer's own claim, and is only ever reported
  as claimed.

- **`reproduce` does not mean every stage is infinitely re-runnable.** A stage that calls a model
  with no fixed seed, or reads from a source that's since changed, is legitimately not
  rederivable — that's `COULD NOT CHECK`, with the reason named, and the stage's originally
  recorded outputs are kept rather than discarded.

- **onetrace does not protect against a write-access attacker who can also recompute every
  downstream digest and chain link.** Rewriting history undetected requires forging or replaying
  bytes past the verifier's own checks; closing the remaining gap (an attacker with full write
  access to storage, patient enough to recompute everything downstream) is what anchoring is
  for (manual, section 15): a rewrite changes the chain head, and an anchor made before it no longer
  binds to the record. An anchor is not part of the chain, though: the same attacker can delete
  `anchors/`, and the run still passes. Anchoring closes the gap only for a reader who expects an
  anchor, or holds one independently of the run's own storage.

- **The format is not finished.** Format major version `0` (the current `stage-receipt/0.2`) is
  specified by an Internet-Draft that hasn't reached RFC status. Required members, canonical-form
  rules, and the rejection vectors may still change before major version `1`. Format major
  version is carried in every record and checked explicitly — a verifier that doesn't implement a
  record's version (a major other than 0, or a minor that isn't ASCII decimal digits) says so, by
  name, rather than guessing.

- **`reproduce` does not claim bit-exact floating-point reproduction on every machine.** A stage
  whose own code depends on numpy/BLAS (an embedding step, say) is claimed rederivable only on
  the environment recorded in the run — a different machine's BLAS build can legitimately produce
  different bytes for the identical code and inputs, which `reproduce` reports honestly rather
  than asserting past.

- **onetrace does not claim identical test behavior across every Python patch version on every
  OS.** CPython 3.10.11's own random-number-generator initialization on Windows is known to fail
  outright on some current runner images, unrelated to onetrace — which fixtures reproduce there
  is a property of that Python build, not of the format or the SDK.

- **The ingest-r1 PDF stage requires poppler's `pdftotext`, and refuses any other build by
  design.** `pdftotext` from a different vendor (xpdf, say) is not silently accepted as
  equivalent, even when it runs and produces text — ring 4's own emission checks the reported
  converter identity before writing a single receipt and refuses to run at all if it isn't
  poppler's. This is not a portability gap to be worked around; the converter's identity is part
  of the recorded configuration, and a different vendor is a different, unconfirmed instrument.

- **The text diff does not say why recorded outputs changed, or that either version was
  correct.** `diff --text` shows what the two runs' recorded outputs contained, read only after
  each run verified and each file matched its receipt.

- **`diff --text` never shows an input's content.** Inputs are fingerprinted, not stored, so a
  changed input is named, with its trust class and digests, and nothing more.

## onetrace 0.5: onedoor decisions, span context, nesting

- **A citation shows that the run names an existing, unaltered decision.** It does not show that
  every action was gated, only that every declared gated step cited one.

- **A permit check shows the decision covered the action object the step recorded.** It does not
  show that the receiving system received exactly that object; that is the recipient's own check.

- **Nothing here says a decision was right.** onetrace records which onedoor decision allowed an
  action and lets anyone re-check it offline; it does not judge the policy, the decision or the
  action.

- **A trace is a view, not evidence.** It may be sampled, dropped, rewritten or re-timed by a
  collector. The span context a receipt records (a W3C trace id and span id) and the run's
  `traceparent` say which trace the run and its steps ran in; only the record proves the step's
  inputs and outputs.

- **Nesting is recorded for calls through decorated stages only.** A call that bypasses the
  decorator is not in the record, as today. `parent`, `children`, `parent_run` and `parent_stage`
  name the calls that went through `@ot.stage` and `@ot.run`, and nothing else.

- **A 0.5 receipt is not a new format.** onetrace 0.5 stays in format 0.3: a 0.4.0 verifier reads a
  0.5 receipt unchanged, ignoring the `authorization`, span-context and nesting blocks it does not
  know, and a run that records none of them is byte-identical to 0.4.0.

## onetrace 0.6: references and verdicts, variation, streaming

- **A verdict is derived from the record and a declared rule.** The rules are declared per step —
  exact digest by default, a mask where one is given — never inferred. A verdict names where a run
  parts from its reference; it does not say why, or that either run was right.

- **A step matching its reference shows it did what the known-good run did, not that either was
  right.** A reference is a statement that a run is the one to compare against, not that it is
  correct.

- **Timing is a view, never part of a verdict.** A step slower than its range is reported, but it is
  never a divergence and never fails a verdict.

- **A profile describes the repeats recorded, not every future run.** Matching in N repeats does not
  prove a step is deterministic. A step declared `may_vary` is shown as declared; the declaration is
  never used to hide a difference.

- **A before/after profile names the setting that changed between the sets; it does not say the
  change made the difference.** It is a comparison, as the others are.

- **Streaming shares the record as it grows; it is not the record.** Only the written run folder,
  read and verified, is the record; a receipt that reached a console is provisional until the run
  closes and its whole chain verifies. A failed stream changes no receipt.

- **A 0.6 record is not a new format.** onetrace 0.6 stays in format 0.3: a 0.5.0 verifier reads a
  0.6 run unchanged, ignoring the `repeat_of` and `stream` members in the manifest and the
  `may_vary` member on a receipt, and a run that records none of them is byte-identical to 0.5.0. A
  reference is its own file (`onetrace-reference/1`), sealed and signed as a run is, never a
  receipt.

## onetrace 0.6: the run sink

- **A bucket verifies nothing; the reader verifies on every read.** Storage location does not change
  what a record proves. A tampered object is caught when a reader verifies the run, not at rest.

- **A delivered run is the same record as the local one.** The sink uploads the sealed folder and
  changes no receipt; the only addition is the manifest's optional `sink` member, which names no
  endpoint and no credential.

- **An object's checksum guards the transfer, not the record.** The chain, the digests and the
  signature are what prove the run; the per-object sha256 only catches an object damaged in the
  bucket, on the way back.

## onetrace 0.6: the model-call record

The [model-call record](model-call-record.md) is evidence beside a stage receipt; it never changes the
reading of a run's receipts — its own verifier rows read as every other row does, and a FAIL on one
fails the run like any other FAIL. What it does not claim:

- **A record is not a correctness claim.** It holds no hidden reasoning, and does not check whether an
  answer is semantically correct. A differing value names no cause, and `same` covers only the
  compared fields. Record equivalence is not correctness.

- **A record does not reproduce across machines.** It claims no reproducibility across GPUs, versions
  or engines, and says nothing about a hosted provider's internals, which are `not observed`.

- **A digest is not a commitment.** A digest in the record names a value; it does not bind the writer
  to anything, and is not a proof of what was served. In particular, `model.files_digest` is the
  digest of the directory given to the adapter, not read from the engine: it does not show that the
  served weights are the hashed ones.

- **The comparator's not-repeatable condition rests on one measurement** and fits no tolerance. vLLM
  with batch-invariant mode not observed on, at a submitted batch size over 1, is not compared; the
  reason claims no property of such a configuration.

- **The tolerant fingerprint is not a detector of small numeric changes.** It is built to miss them; a
  small numeric change can leave it unchanged. The exact form is the full row for a transformers
  prefill, and the top 16 unrounded for a vLLM call — not the full vLLM distribution.

- **The companion result was measured at one arrangement.** That a filler request changed a target's
  answer was measured at batch 4 only, with the target first, companions no longer than the target,
  and no fillers beyond the companions; it is not a claim about other batch sizes or arrangements.

- **The per-step capture holds the model's token ids.** It is `model-generated`, kept in a separate
  output (`model_call.<n>.steps.json`), and the record names only its digest — the record itself
  holds no token id and no text at any level. A prefix-digest chain over token ids reveals the tokens
  to anyone with the vocabulary; it hides nothing. The cost of taking L1 or L2 is not measured, and L3
  is not measured.

- **The verifier does not check that a record's `steps` digest names the steps output.** The steps
  file is an ordinary model-generated output the chain covers; a verifier does not add a row checking
  that the record's `steps` digest is that output's digest.
