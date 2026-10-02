#!/usr/bin/env bash
# Download the 10 public sample P&IDs from the DiagEx reproducibility package
# (ABB Corporate Research, Apache-2.0). Puts them in data/samples/.
set -euo pipefail
mkdir -p data/samples
tmp=$(mktemp -d)
git clone --depth 1 https://github.com/hkoziolek/diagex-repro "$tmp/diagex-repro"
cp "$tmp/diagex-repro/tests/p-ids-public/"*.pdf data/samples/
rm -rf "$tmp"
ls data/samples/
