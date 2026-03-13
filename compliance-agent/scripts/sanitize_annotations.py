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

    texts = [p.get("text", "") for p in paras]
    styles = [p.get("style") for p in paras]
    is_heading_flags = [bool(p.get("is_heading")) for p in paras]

    def next_valid_index(start: int) -> int:
        for j in range(max(0, start), len(paras)):
            if not is_excluded(styles[j], texts[j]):
                return j
        return start

    def heading_anchor(idx: int) -> int:
        j = min(max(idx, 0), len(paras) - 1)
        for k in range(j, -1, -1):
            if is_heading_flags[k] and not is_excluded(styles[k], texts[k]):
                return k
        return idx

    def find_schedule_ref_anchor(missing_inputs: List[str]) -> int | None:
        needles = [str(x).strip() for x in (missing_inputs or []) if str(x).strip()]
        for i, t in enumerate(texts):
            tl = (t or "").lower()
            for n in needles:
                if n and n.lower() in tl:
                    return i
        for i, t in enumerate(texts):
            tl = (t or "").lower()
            if any(w in tl for w in ["schedule", "annex", "appendix", "příloha", "priloha"]):
                return i
        return None

    sanitized = []
    moved = 0
    reanchored_unknown = 0
    reanchored_to_heading = 0

    for a in annotations:
        try:
            pidx = int(a.get("paragraph_index"))
        except Exception:
            continue

        status = str(a.get("status") or "").upper()
        missing_inputs = a.get("missing_inputs") or []

        pidx2 = pidx

        # Step 3: UNKNOWN → anchor to schedule/annex reference (if possible)
        if status == "UNKNOWN" and missing_inputs:
            ref = find_schedule_ref_anchor(missing_inputs)
            if ref is not None:
                pidx2 = ref
                reanchored_unknown += 1

        # PASS/PARTIAL/FAIL → anchor to nearest heading above
        if status in ("PASS", "PARTIAL", "FAIL"):
            h = heading_anchor(pidx2)
            if h != pidx2:
                pidx2 = h
                reanchored_to_heading += 1

        # Exclusions / empty paragraphs
        if pidx2 < 0 or pidx2 >= len(paras) or is_excluded(styles[pidx2], texts[pidx2]):
            pidx3 = next_valid_index(pidx2 + 1)
            if pidx3 != pidx2:
                moved += 1
            pidx2 = pidx3

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
                "reanchored_unknown": reanchored_unknown,
                "reanchored_to_heading": reanchored_to_heading,
                "excluded_styles": sorted(list(EXCLUDED_STYLE_EXACT)),
                "excluded_style_prefixes": list(EXCLUDED_STYLE_PREFIXES),
            },
        },
    }

    dump_yaml(out, Path(args.out))


if __name__ == "__main__":
    main()
