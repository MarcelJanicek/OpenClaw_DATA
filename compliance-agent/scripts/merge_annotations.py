#!/usr/bin/env python3
"""Merge two evaluator YAML outputs (GDPR + NIS2-CZ) into one annotations.yaml.

Usage:
  python3 scripts/merge_annotations.py \
    --gdpr outputs/<doc>.gdpr.eval.yaml \
    --nis2 outputs/<doc>.nis2.eval.yaml \
    --out  outputs/<doc>.annotations.yaml

Notes:
- Simply concatenates annotations and sorts by paragraph_index.
- Also merges missing_inputs into a header note (optional).
"""

from __future__ import annotations

import argparse
from pathlib import Path
import yaml


def load(p: Path) -> dict:
    return yaml.safe_load(p.read_text('utf-8')) or {}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--gdpr', required=True)
    ap.add_argument('--nis2', required=True)
    ap.add_argument('--out', required=True)
    args = ap.parse_args()

    gdpr = load(Path(args.gdpr))
    nis2 = load(Path(args.nis2))

    ann = []
    ann.extend(gdpr.get('annotations', []) or [])
    ann.extend(nis2.get('annotations', []) or [])

    # sort by paragraph_index then author
    def key(a: dict):
        return (int(a.get('paragraph_index', 10**9)), str(a.get('author','')))

    ann_sorted = sorted(ann, key=key)

    out = {
        'annotations': ann_sorted,
        'meta': {
            'sources': [
                {'ruleset': 'gdpr', 'file': Path(args.gdpr).name},
                {'ruleset': 'nis2-cz', 'file': Path(args.nis2).name},
            ]
        }
    }

    Path(args.out).write_text(yaml.safe_dump(out, sort_keys=False, allow_unicode=True, width=1000), 'utf-8')


if __name__ == '__main__':
    main()
