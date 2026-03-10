#!/usr/bin/env python3
"""Generic ruleset merge utility.

Merges parts listed in a ruleset index into a single <ruleset>.rules.yaml file.

Usage:
  python3 scripts/ruleset_merge.py gdpr
  python3 scripts/ruleset_merge.py dora

Index path convention:
  rules/<ruleset>/<ruleset>.index.yaml

Output path convention:
  rules/<ruleset>/<ruleset>.rules.yaml
"""

from __future__ import annotations

import sys
import yaml
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: ruleset_merge.py <ruleset> (e.g., gdpr, dora)")

    ruleset = sys.argv[1].strip()
    index_path = ROOT / f"rules/{ruleset}/{ruleset}.index.yaml"
    out_path = ROOT / f"rules/{ruleset}/{ruleset}.rules.yaml"

    index = yaml.safe_load(index_path.read_text("utf-8"))
    includes = index.get("includes", [])

    merged_rules = []
    meta = None

    for rel in includes:
        p = ROOT / f"rules/{ruleset}" / rel
        doc = yaml.safe_load(p.read_text("utf-8"))
        if meta is None:
            meta = doc.get("meta", {})
        merged_rules.extend(doc.get("rules", []))

    out_doc = {"meta": meta or index.get("meta", {}), "rules": merged_rules}
    out_path.write_text(
        yaml.safe_dump(out_doc, sort_keys=False, allow_unicode=True, width=1000),
        "utf-8",
    )


if __name__ == "__main__":
    main()
