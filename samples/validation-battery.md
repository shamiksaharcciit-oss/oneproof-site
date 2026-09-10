# The Validation Battery
### The acceptance tests that `draft-saha-stage-receipts` and its reference SDK will be held to

**Battery version 1.0 · published before the code · 11 September 2026**

> **PREVIEW.** Everything below describes tests for implementations that **do not exist**.
> The format is an Internet-Draft (`draft-saha-stage-receipts-00`, posted
> 8 September 2026, <https://datatracker.ietf.org/doc/draft-saha-stage-receipts/>) — a draft, not a
> standard. The SDK is forthcoming. The verifier is forthcoming. This document is the exam;
> the candidates have not been written.

---

## Why this is published first

The ordinary sequence is: build a thing, then decide how to evaluate it. That
sequence lets the evaluation drift toward whatever the thing turned out to do.

So we are publishing the exam before the candidate exists. Every test below was
written before a line of the format or the SDK, and the release condition is
fixed now, in public, where it cannot be quietly relaxed later:

> **The reference implementation ships with this battery's results attached,
> uncurated — every test, including the ones it fails, with the failure text as
> emitted.** A battery that publishes only its passes is marketing with a test
> runner attached.

Anyone may run this battery against any implementation, including ours. That is
the point: if the checker has to be trusted, nothing has been checked.

---

## 0. What a conforming implementation is claimed to be

The battery tests one contract and no more. A conforming implementation
produces records of pipeline execution that are:

- **Well-formed** — canonically serialized, byte-identically, on any platform.
- **Self-describing** — every record names the instrument that produced it, the
  transform constants its assertions depend on, and the profile level it claims.
- **Honest about absence** — absent, declared-none, and recorded are three
  distinct states, and nothing may collapse them.
- **Re-derivable** — every quantity a record asserts can be recomputed from the
  records it summarizes, by a third party, offline, with no access to the
  operator's systems.

**Scope of the claim, stated plainly.** These records are *tamper-evident and
re-derivable*. They are not, on their own, proof of originality: a hash proves a
record is consistent with itself, never that it is the record that was made. An
operator holding every copy can rewrite a record and recompute every downstream
link. Resistance to that requires anchoring to a commitment the operator cannot
rewrite — requirement #2 — and §6 states exactly how far this battery can and
cannot test it.

---

## 1. How the battery is scored

Every test returns one of exactly three outcomes. There is no fourth, and there
is no silence:

| Outcome | Meaning |
|---|---|
| **PASS** | The behaviour was observed. |
| **FAIL** | The behaviour was not observed. The emitted output is published verbatim. |
| **NOT RUN — with reason** | The test could not execute. The reason is published, and an unexplained skip is itself a battery failure. |

Two scoring rules follow from the house's own scars:

1. **A test with no failing case is not a test.** Every test below ships with a
   known-negative fixture alongside its known-positive. A probe that returns
   perfection is measuring its own leniency.
2. **Counts are re-derived, never asserted.** The battery's own summary figures
   are recomputed from its per-test records; the runner emits both, and a
   mismatch between them fails the run.

---

## 2. Ring one — the pathology zoo

Fixtures written before the code, each encoding a failure that actually
happened. This ring is not hypothetical: every entry names the incident that
made it necessary, because a test whose motivating failure cannot be stated is
usually a test of something nobody got wrong.

### 2.1 Recording failures honestly

**P-01 · The silent zero.** A measurement subsystem fails and returns a
plausible number. *Scar: a memory measurement reported a peak of 0 MB while its
collection call was failing.*
**Required:** the record carries the measurement's error, not a value. A failed
measurement and a measured zero are different states.

**P-02 · The status code wearing an explanation.** A transport error is recorded
under the label of a semantic outcome. *Scar: an HTTP 403 from a network edge
was recorded as a model refusal.*
**Required:** an error outcome records status, body, and origin. Refusal and
transport failure are distinct outcome classes and may not collapse into one.

**P-03 · The failing-open guard.** A check silently degrades to a pass. *Scar: a
leak-detection guard whose normalization mismatch reduced its examined
population from 265 fragments to 1, and reported clean.*
**Required:** a guard records the population it examined. A check whose
denominator is unknown FAILS; it does not pass.

**P-09 · The register backfilled by generation.** A record is missing and the
implementation supplies a plausible substitute. *Scar: an unarchived measurement
log, which was left recorded as missing rather than reconstructed.*
**Required:** a gap is recorded as a gap. No conforming implementation may
synthesize a record it did not observe, and the battery's negative fixture
checks that it does not.

### 2.2 Naming the instrument and its constants

**P-04 · The unpinned instrument.** A record is produced against a component
that cannot be identified. *Scar: a scoring server reporting a null model
identity — a campaign refused to run against it.*
**Required:** refusal, not a blank field. A record whose instrument cannot be
named is invalid.

**P-05 · The unstated constant.** A relation holds only under a transform
nobody declared. *Scar: a containment relation that verified 934/934 under
blank-line joining and 606/934 under single-newline joining — the constant was
doing the work.*
**Required:** any relation a record asserts names the transform constants it
depends on. A relation that holds only under an unstated constant tests the
constant, not the relation.

**P-07 · The declaration that outran the code.** The specification claims a
field the implementation never emits. *Scar: a spec asserting character offsets
where the code recorded none.*
**Required:** conformance is checked against emitted bytes and never against
documentation. Every declared field must be produced by the code path that
emits it.

### 2.3 Quantities, states, and time

**P-08 · The half timestamp.** A time with no zone. *Scar: a teardown recorded
at 22:16, which was two possible durations.*
**Required:** every temporal field carries its zone. Ordering under disagreeing
clocks is declared separately (see §6, requirement #7).

**P-10 · The count that was testimony.** An aggregate that cannot be recomputed
from what it aggregates. *Scar: a green-run count adopted from a summary rather
than re-derived, and wrong by one.*
**Required:** every count is re-derivable from the records it counts, and the
derivation is stated in the record.

**P-11 · The unequalized comparison.** Two instruments compared under different
input handling. *Scar: a candidate that would have been "rescued" by giving it
batch-size-1 treatment its competitors did not receive.*
**Required:** a comparison record declares the input handling of each side.
Unequal handling invalidates the comparison and the record says so — an
instrument comparison that does not equalize input handling measures the
rejection policy, not the instrument.

**P-12 · The three states.** A field that may legitimately be empty.
**Required:** absent, declared-none, and recorded serialize distinguishably and
round-trip distinguishably. No profile may collapse them.

### 2.4 The byte-level zoo

**P-13 · Awkward transforms.** Fixtures a canonical serializer must survive
without silently normalizing away meaning:

- Unicode normalization forms (NFC/NFD/NFKC/NFKD) on the same logical content
- CRLF, LF, and mixed line endings; leading and trailing whitespace
- Byte-order marks; zero-width characters; combining marks
- Right-to-left and bidirectional text; surrogate pairs and lone surrogates
- Very long single fields; deeply nested structures; duplicate keys
- **Numeric edge cases: decimal strings versus floats**, leading zeros, negative
  zero, integers beyond double precision, and the `'500.00'` / `'500'`
  distinction. *Scar: a numeric field where decimal-string handling was the
  difference between two different values, caught by its own impossibility test.*
- Empty string versus null versus absent

Each fixture ships with its expected canonical form and expected digest.

---

## 3. Ring two — golden conformance vectors

**Shipped inside the Internet-Draft itself**, so the standard carries its own
tests and no implementer has to trust a repository.

| Vector class | What it fixes |
|---|---|
| **V-1 Canonical form** | For each fixture: the input, its expected canonical serialization, its expected digest — byte for byte |
| **V-2 Cross-platform identity** | The same fixture serialized on Windows, macOS and Linux must be byte-identical. Line endings and long-path handling are named traps, not discovered ones |
| **V-3 Round-trip** | Parse → re-serialize → byte-identical to the input's canonical form |
| **V-4 Profile levels** | One vector per declared conformance profile, and a vector that conforms at a lower level and correctly declares it |
| **V-5 Rejection vectors** | Malformed inputs a conforming parser must refuse, each with the refusal it must produce. **A format with no rejection vectors has not specified anything** |
| **V-6 Chain vectors** | A multi-record chain, its links, and the digest at each step — plus a tampered variant that must fail, and must fail at the identified link |

---

## 4. Ring three — the framework matrix

The strongest test in the battery, and the one whose failure would matter most.

Four pipelines producing equivalent work, at pinned versions:

1. A **plain-Python control** — no framework, the reference path
2. **LangChain**
3. **Langflow**
4. **LlamaIndex**

**One verifier checks all four, blind.** The pass condition is not merely that
each set of records validates. It is that:

- the verifier requires no framework-specific handling, and
- **the verifier cannot tell from the records which framework produced them**,
  except where the instrument declaration deliberately says so.

This is what separates a format from one implementation's output shape. If the
verifier needs to know its source, we have four dialects and no standard, and
the honest conclusion is that the format is not ready — which the battery would
report as a FAIL, publicly, with the divergence shown.

---

## 5. Ring four — the dogfood

The house's own forensic retrieval pipeline, re-expressed through the SDK.

**Pass condition:** every claim previously made from that pipeline's records is
re-derivable from the SDK-emitted versions — the same numbers, the same
citations, the same refusals, including the results that were unflattering. If
the SDK cannot carry records this house already produced by hand, it is not
finished, whatever the other three rings say.

This ring is deliberately the least glamorous and the hardest to fake.

---

## 6. What the battery can and cannot test, requirement by requirement

The format carries **thirteen open requirements**. Honesty about which of them
a test can reach is itself part of the exam.

| # | Requirement | Battery coverage |
|---|---|---|
| 1 | Merkle corpus manifest | **Testable** — manifest construction, inclusion proofs, and a tampered-member rejection vector |
| 2 | **Epoch anchoring** | **Partial, and this is the honest limit.** The battery can test that a record *declares* its anchor target, its cadence, and the unanchored state. It **cannot** test that the anchor is unrewritable — that is a property of an external witness, not of our code. **The battery measures tamper-evidence; it does not and cannot measure tamper-resistance.** |
| 3 | Tenant isolation | **Partial** — format-level separation is testable; deployment isolation is not |
| 4 | Signature envelope | **Not yet** — sequenced behind actor identity; vectors are reserved, not written |
| 5 | Dependency record | **Testable** — presence, structure, and the three-state network-access declaration |
| 6 | Signing-key lifecycle | **Not yet** — follows #4. A vector for "record signed by a since-revoked key" is reserved |
| 7 | **Topology / DAG** | **Not yet specified, therefore not yet testable — the battery's largest hole.** Fan-out, fan-in, retries as distinct attempts, branches, loops, compensation, exactly-once versus at-least-once, and out-of-order arrival all need fixtures that cannot be written until the requirement is. Named here rather than omitted |
| 8 | Disclosure layer | **Partial** — that a record can be *checked without being fully read* is testable once the mechanism exists |
| 9 | Coverage attestation | **Testable, and required** — declared expected topology, which stages emitted valid records, boundary declarations, and INCOMPLETE as a first-class state. A conforming interpreter may not assert a root cause across an undeclared boundary |
| 10 | Content trust class | **Testable** — every recorded value declares operator-authored, model-generated, or externally sourced |
| 11 | Emission failure semantics | **Testable** — declared fail-open or fail-closed, with the resulting absence recorded as a declared gap |
| 12 | Schema evolution | **Testable** — a current verifier reading an earlier-version record must produce a declared outcome, never a silent one |
| 13 | External effect records | **Testable** — attempted, returned-a-response, and confirmed-by-the-external-system are three states, and a verifier may not read the first as the third |

**Two requirements (#7 and #2) carry more of the product's weight than the rest,
and the battery reaches neither fully.** Publishing that here, before anyone
asks, is the only version of this document worth publishing.

---

## 7. What this battery deliberately does not test

Stated so nobody reads a passing run as more than it is:

- **It does not test that the pipeline was correct.** A well-formed record of a
  wrong answer passes every test in this document.
- **It does not test that a model was good**, that retrieval was relevant, or
  that an answer was true.
- **It does not test performance.** Throughput and overhead are a separate
  commitment with its own published numbers; no claim about scale is made or
  implied here.
- **It does not test tamper-resistance** (see §6, #2).
- **It does not certify a deployment.** It tests an implementation against a
  format.

---

## 8. Running it, and contributing to it

The battery will ship as a repository: fixtures, expected outputs, a runner, and the
result format. It is open, and its licence matches the format's.

**Implementers are invited to do three things**, and this invitation is the
other half of this package:

1. **Run it against your implementation** and publish your results — including
   your failures. We will link to any published run, passing or not.
2. **Contribute a pathology fixture.** The most valuable contribution to this
   battery is a case that breaks it: a transform, an encoding, a topology, or a
   failure mode we did not anticipate. Ring one grows by other people's scars,
   not only ours.
3. **Write a second verifier.** One verifier checking one format is a claim; two
   independent verifiers agreeing on the same records is evidence.

---

## 9. The battery's own versioning

The battery is versioned and additive. Tests are added; a test is never quietly
removed or loosened. If a test is retired, the retirement is recorded with its
reason and the version in which it last ran — the same discipline the records
themselves are held to, applied to the thing that judges them.

**Version 1.0 · 11 September 2026 · published before the code it will judge.**
