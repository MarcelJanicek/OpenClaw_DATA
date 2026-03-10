#!/usr/bin/env python3
"""Generate sha256 checksum file for a merged ruleset.

Usage:
  python3 scripts/ruleset_checksum.py nis2-cz

Writes:
  rules/<ruleset>/<ruleset>.rules.sha256
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit('Usage: ruleset_checksum.py <ruleset>')
    ruleset = sys.argv[1].strip()
    rules_path = ROOT / f'rules/{ruleset}/{ruleset}.rules.yaml'
    out_path = ROOT / f'rules/{ruleset}/{ruleset}.rules.sha256'

    digest = sha256_file(rules_path)
    out_path.write_text(f"{digest}  {rules_path.name}\n", 'utf-8')


if __name__ == '__main__':
    main()
