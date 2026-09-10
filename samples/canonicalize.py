#!/usr/bin/env python3
"""Reference canonicalizer for stage-receipt/0.0-preview.

PREVIEW ARTIFACT. The format is forthcoming; this file exists so the sample
receipts published beside it can be checked by anyone, today, with no trust in
the publisher.

Canonical form, in full:
  1. UTF-8, no byte-order mark.
  2. JSON with object keys sorted by Unicode code point.
  3. No whitespace outside string literals.
  4. NO JSON NUMBERS. Every numeric value is a decimal string. A format that
     serializes 500.00 as a float has already lost the distinction between
     '500.00' and '500', and that distinction has cost us a defect before.
  5. No NaN, no Infinity, no -0.
  6. The file contains exactly the canonical bytes and nothing else - no
     trailing newline.
  7. A receipt NEVER contains its own digest. A record cannot contain the proof
     of its own final state; the digest lives in the chain manifest and in the
     next receipt's `prev` field.
"""
import hashlib, json, sys


def _no_numbers(node, path="$"):
    if isinstance(node, bool):
        return
    if isinstance(node, (int, float)):
        raise ValueError(f"JSON number at {path}: use a decimal string")
    if isinstance(node, dict):
        for k, v in node.items():
            if not isinstance(k, str):
                raise ValueError(f"non-string key at {path}")
            _no_numbers(v, f"{path}.{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            _no_numbers(v, f"{path}[{i}]")


def canonicalize(obj: dict) -> bytes:
    _no_numbers(obj)
    if "receipt_digest" in obj or "receipt_id" in obj:
        raise ValueError("a receipt may not carry its own digest")
    return json.dumps(
        obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def digest(obj: dict) -> str:
    return hashlib.sha256(canonicalize(obj)).hexdigest()


if __name__ == "__main__":
    for path in sys.argv[1:]:
        raw = open(path, "rb").read()
        obj = json.loads(raw.decode("utf-8"))
        canon = canonicalize(obj)
        status = "CANONICAL" if canon == raw else "NOT CANONICAL"
        print(f"{hashlib.sha256(canon).hexdigest()}  {status}  {path}")
