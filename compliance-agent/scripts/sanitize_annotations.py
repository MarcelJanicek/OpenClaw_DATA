#!/usr/bin/env python3
"""Sanitize + re-anchor annotations before rendering into DOCX.

Problems addressed:
- Paragraph index mismatch / front-matter noise: avoid anchoring comments to
  title page / TOC-style paragraphs.
- Empty paragraphs: move to the next real paragraph.
- Debug noise: strip evidence_paragraph_indices / internal debug tokens from
  comment text.

Usage:
  python3 scripts/sanitize_annotations.py \
    --extracted docs/processed/<doc>.yaml \
    --in outputs/<doc>.annotations.yaml \
    --out outputs/<doc>.annotations.sanitized.yaml
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any, Dict, List

import yaml


EXCLUDED_STYLE_PREFIXES = (
    "TOC",          # TOC 1, TOC 2, ...
)
EXCLUDED_STYLE_EXACT = {
    "Title",
    "Subtitle",
}


def load_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text("utf-8"))


def dump_yaml(obj: Any, path: Path) -> None:
    path.write_text(yaml.safe_dump(obj, sort_keys=False, allow_unicode=True, width=1000), "utf-8")


def is_excluded(style: str | None, text: str | None) -> bool:
    style = (style or "").strip()
    t = (text or "").strip()
    if not t:
        return True
    if style in EXCLUDED_STYLE_EXACT:
        return True
    for pref in EXCLUDED_STYLE_PREFIXES:
        if style.startswith(pref):
            return True
    # Heuristic: pure TOC-like dot leaders or page numbers
    if re.fullmatch(r"[\.\s0-9ivxlcdmIVXLCDM]+", t) and len(t) < 40:
        return True
    return False


DEBUG_PATTERNS = [
    re.compile(r"evidence_paragraph(_indices|s)?\s*=\s*\[?[^\n\]]+\]?", re.I),
    re.compile(r"evidence_paragraph_indices\s*:\s*\[?[^\n\]]+\]?", re.I),
]


def strip_debug(text: str) -> str:
    out = text
    for pat in DEBUG_PATTERNS:
        out = pat.sub("", out)
    # collapse excess blank lines/spaces
    out = re.sub(r"\n{3,}", "\n\n", out).strip()
    out = re.sub(r"\s+", " ", out) if "\n" not in out else out
    return out.strip()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--extracted", required=True)
    ap.add_argument("--in", dest="in_path", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    extracted = load_yaml(Path(args.extracted)) or {}
    paras: List[Dict[str, Any]] = extracted.get("paragraphs", []) or []

    ann_doc = load_yaml(Path(args.in_path)) or {}
    annotations = ann_doc.get("annotations", ann_doc) or []

    # Build quick access arrays
    texts = [p.get("text", "") for p in paras]
    styles = [p.get("style") for p in paras]

    def next_valid_index(start: int) -> int:
        for j in range(max(0, start), len(paras)):
            if not is_excluded(styles[j], texts[j]):
                return j
        return start

    sanitized = []
    moved = 0
    for a in annotations:
        try:
            pidx = int(a.get("paragraph_index"))
        except Exception:
            continue

        pidx2 = pidx
        if pidx < 0 or pidx >= len(paras) or is_excluded(styles[pidx], texts[pidx]):
            pidx2 = next_valid_index(pidx + 1)
            if pidx2 != pidx:
                moved += 1

        text = strip_debug(str(a.get("text", "")).strip())
        if not text:
            continue

        sanitized.append({
            **{k: v for k, v in a.items() if k not in ("paragraph_index", "text")},
            "paragraph_index": pidx2,
            "text": text,
        })

    out = {
        "annotations": sanitized,
        "meta": {
            **(ann_doc.get("meta") or {}),
            "sanitized": {
                "moved_annotations": moved,
                "excluded_styles": sorted(list(EXCLUDED_STYLE_EXACT)),
                "excluded_style_prefixes": list(EXCLUDED_STYLE_PREFIXES),
            },
        },
    }

    dump_yaml(out, Path(args.out))


if __name__ == "__main__":
    main()
