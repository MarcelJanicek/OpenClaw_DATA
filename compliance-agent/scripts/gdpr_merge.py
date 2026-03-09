#!/usr/bin/env python3
"""Merge GDPR ruleset parts into a single gdpr.rules.yaml.

Why:
- Keep human-edits small (parts/*)
- Still offer a single-file ruleset for consumers

Usage:
  python3 scripts/gdpr_merge.py
"""

from __future__ import annotations

import yaml
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "rules/gdpr/gdpr.index.yaml"
OUT = ROOT / "rules/gdpr/gdpr.rules.yaml"


def main() -> None:
    index = yaml.safe_load(INDEX.read_text("utf-8"))
    includes = index.get("includes", [])

    merged_rules = []
    meta = None

    for rel in includes:
        p = ROOT / "rules/gdpr" / rel.replace("parts/", "parts/")
        doc = yaml.safe_load(p.read_text("utf-8"))
        if meta is None:
            meta = doc.get("meta", {})
        merged_rules.extend(doc.get("rules", []))

    out_doc = {"meta": meta or index.get("meta", {}), "rules": merged_rules}
    OUT.write_text(
        yaml.safe_dump(out_doc, sort_keys=False, allow_unicode=True, width=1000),
        "utf-8",
    )


if __name__ == "__main__":
    main()
