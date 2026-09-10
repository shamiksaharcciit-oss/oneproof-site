# Watch this file

**PREVIEW ARTIFACT, 11 September 2026.**

There is no mailing list, no "notify me" form, and nothing that collects your
address. Instead there is `STATUS.json`: the machine-readable state of every
open requirement, every battery ring, and every artifact we have committed to,
with a date.

## How to watch

- **Watch the repository.** Any change to `STATUS.json` is a change to the
  commitments.
- **Or poll the raw file** on whatever schedule suits you, and diff it:

```sh
python3 whatchanged.py old-STATUS.json new-STATUS.json
```

It prints only what moved: which requirement changed state, which battery ring
advanced, which artifact shipped — and, deliberately, **any commitment that was
removed**, flagged as something to ask about.

## Why a file instead of a form

A roadmap in a blog post is a promise. A roadmap in a diffable file is a record
you can hold us to, and it costs you nothing to keep — no account, no address,
no relationship with us at all.

It also means slippage is visible. If a requirement sits at `not-started` for
four months, `whatchanged.py` will show you four months of nothing moving. That
is the intended behaviour.

## Reading the states

`not-started` → `specified` → `implemented` → `tested` → `shipped`

Only `shipped` describes something that exists. Everything else is a
commitment, and `battery_coverage` on each requirement says honestly whether
the Validation Battery can even test it — two of the thirteen carry more of the
product's weight than the rest, and the battery reaches neither fully. Those
two are marked `LOAD-BEARING` in their notes.
