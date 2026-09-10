#!/bin/sh
# Reference check runner - PREVIEW ARTIFACT.
# No network, no keys, no accounts. Python 3 and sha256sum are all it needs.
set -e
echo "== 1. digests, with a standard tool (no code of ours involved) =="
sha256sum receipts/*.json MANIFEST.json
echo
echo "== 2. canonical form of every receipt =="
python3 canonicalize.py receipts/*.json
echo
echo "== 3. the chain, verified offline =="
python3 verify.py MANIFEST.json
echo
echo "== 4. rejection vectors - every one MUST be refused =="
python3 check_rejections.py
