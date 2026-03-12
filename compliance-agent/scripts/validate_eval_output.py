#!/usr/bin/env python3
"""Validate evaluator YAML output schema.

Usage:
  python3 scripts/validate_eval_output.py outputs/doc.gdpr.eval.yaml --ruleset gdpr
"""

from __future__ import annotations

import argparse
from pathlib import Path
import yaml


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('file')
    ap.add_argument('--ruleset', required=True, choices=['gdpr', 'nis2-cz'])
    args = ap.parse_args()

    doc = yaml.safe_load(Path(args.file).read_text('utf-8'))
    if not isinstance(doc, dict):
        raise SystemExit('Not a YAML mapping')

    result = doc.get('result')
    if not isinstance(result, dict):
        raise SystemExit('Missing result')

    status = result.get('status')
    if status not in ('questions', 'completed'):
        raise SystemExit('result.status must be questions|completed')

    if result.get('ruleset') != args.ruleset and status == 'completed':
        raise SystemExit(f"Expected ruleset {args.ruleset} got {result.get('ruleset')}")

    if status == 'completed':
        if not isinstance(doc.get('findings'), list):
            raise SystemExit('Missing findings list')
        if not isinstance(doc.get('annotations'), list):
            raise SystemExit('Missing annotations list')

        # basic checks
        for a in doc['annotations'][:50]:
            if 'paragraph_index' not in a or 'text' not in a:
                raise SystemExit('Annotation missing paragraph_index/text')

    print('OK')


if __name__ == '__main__':
    main()
