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
  record's version says so, by name, rather than guessing.

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
