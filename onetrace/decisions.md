# Recording which onedoor decision allowed an action

A step that takes an action can record which [onedoor](https://onedoor.example) decision allowed
it, and the record proves it: anyone can check, with no network calls, that the decision exists
unaltered, that it permitted this step, and, where a bound permit was used, that the permit covered
exactly the action the step recorded. onetrace never imports onedoor — the small, stable pieces it
needs are vendored as standard-library code (`onetrace.onedoor_ref`) and tested against onedoor's
own published vectors.

## Declaring the gated steps

A run declares which of its steps must be gated:

```python
@ot.run(stages=["approve_payment"], gated_stages=["approve_payment"])
def main():
    ...
```

`Recorder(..., gated_stages=[...])` does the same. Each gated stage must be a declared stage. The
declaration is written into the run's manifest. A gated step that records no decision is a finding
the verifier names, not a silence. A step not declared gated may still cite a decision.

## Recording the decision inside the step

Inside a decorated step, after onedoor answers and before the action:

```python
ot.decision(ref, permit=None, action=None)
```

- `ref`: the `onedoor-decision-ref/1` object onedoor returns (`request_id`, `decision_digest`,
  `verdict`, `issuer`), recorded verbatim. A step may record more than one — a proposal, then its
  resumption — and they are kept in call order.
- `permit`: optional, the bound permit's compact JWS, where one was issued. It is recorded verbatim
  so its signature can be re-checked later.
- `action`: optional, the action object the step is about to send. It is recorded **by digest
  only** — the digest the bound-permit profile uses (domain tag `aadp:action:v1`, one zero byte,
  the JCS form of the object, SHA-256, base64) — never the object itself. An action object's numbers
  are **decimal strings**, as onedoor's vectors have them (`"amount_eur": "40.00"`); a float in an
  action is refused and named, never canonicalised.

These go in the receipt's optional `authorization` block. A run that records no decision writes
receipts byte-identical to 0.4.0.

## What onetrace-verify checks

Five rows, each PASS, FAIL or NOT-RUN, never guessed. They appear only when a run declares gated
stages or cites a decision; a run verified without any is read exactly as before.

| row | PASS | FAIL | NOT-RUN |
|---|---|---|---|
| gated steps cite a decision | every declared gated step cited one | a gated step cited none | no `gated_stages` declared |
| references are well formed | each is `onedoor-decision-ref/1` | one is malformed | no references |
| a step that acted cites a permitting decision | its last reference's verdict is `permit` | it acted on a `deny` or `propose` | no references on an acting step |
| the permit covers the recorded action | the signature is valid for an issuer in `--permit-issuers`, the action digest equals the step's recorded action, and the step ran within the permit's lifetime | any of these fails | no permit recorded, or no issuer key given |
| the decision is in the export | `--decisions <export.jsonl>` (with its `.sha256` sidecar) given, and every reference matches a row by digest | a digest mismatch, not in the export, or the export is damaged | no export given |

The last row reuses onedoor's own five outcomes. With no export and no permit, the record can still
show that a gated step cited a permitting decision; the rows that need more read NOT-RUN, so nothing
reads as checked that was not.

```
onetrace-verify --decisions decisions.jsonl --permit-issuers issuers.json runs/<run_id>
```

The permit issuer's Ed25519 public key is read from `--permit-issuers`, an `onedoor-issuer-trust/1`
file, separate from the run-signing `--trust` file: the permit issuer is a different trust domain
from the run's signer, and the `onetrace-trust/0.1` file carries key fingerprints, not public keys.
The run-signing `--trust` file is never read for an issuer, and an issuer key is never read from the
run. The file names each issuer and its 64-hex Ed25519 public key:

```json
{
  "format": "onedoor-issuer-trust/1",
  "issuers": [
    {"issuer": "https://onedoor.example/payments-issuer",
     "alg": "ed25519",
     "public_key": "03a107bff3ce10be1d70dd18e74bc09967e4d6309ba50d5f1ddc866412553..."}
  ]
}
```

When `--decisions` is given without `--permit-issuers`, the permit row reads NOT-RUN, naming the
missing `--permit-issuers` file, so a permit is never read as checked when its issuer key is absent.

## What this does not claim

- A citation shows that the run names an existing, unaltered decision. It does not show that every
  action was gated, only that every declared gated step cited one.
- A permit check shows the decision covered the action object the step recorded. It does not show
  that the receiving system received exactly that object; that is the recipient's own check.
- Nothing here says a decision was right.
