#!/usr/bin/env python3
"""Extract DOCX text into a structured JSON/YAML for compliance processing.

For pilot: paragraph-level extraction with stable indices.

Usage:
  .venv/bin/python scripts/nis2cz_docx_extract.py --in input.docx --out extracted.yaml
"""

from __future__ import annotations

import argparse
from pathlib import Path

from docx import Document
import yaml


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--in', dest='in_path', required=True)
    ap.add_argument('--out', required=True)
    args = ap.parse_args()

    doc = Document(args.in_path)
    paras = []
    for i, p in enumerate(doc.paragraphs):
        text = p.text or ""
        paras.append({
            'paragraph_index': i,
            'text': text,
            'style': p.style.name if p.style else None,
        })

    out = {
        'source_file': str(Path(args.in_path).name),
        'paragraphs': paras,
    }

    Path(args.out).write_text(yaml.safe_dump(out, sort_keys=False, allow_unicode=True, width=1000), 'utf-8')


if __name__ == '__main__':
    main()
