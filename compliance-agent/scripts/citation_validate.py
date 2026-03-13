#!/usr/bin/env python3
"""Validate that model evidence quotes actually appear in the referenced paragraphs.

Used by the evaluator runner to prevent hallucinated citations.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple


def _norm(s: str) -> str:
    s = (s or "").strip()
    s = re.sub(r"\s+", " ", s)
    return s


def validate_citations(model_out: Dict[str, Any], paragraphs: List[Dict[str, Any]]) -> List[str]:
    """Return list of validation error strings."""

    para_map = {int(p["paragraph_index"]): _norm(p.get("text", "")) for p in paragraphs if "paragraph_index" in p}

    errs: List[str] = []
    res = (model_out or {}).get("result") or {}
    if res.get("status") != "completed":
        return errs

    findings = model_out.get("findings") or []
    for i, f in enumerate(findings):
        status = (f or {}).get("status")
        ev = f.get("evidence") if isinstance(f, dict) else None
        miss = f.get("missing_inputs") if isinstance(f, dict) else None

        if status in ("PASS", "PARTIAL", "FAIL"):
            if not isinstance(ev, list) or not ev:
                errs.append(f"finding[{i}] status={status} missing evidence[]")
                continue
            for j, e in enumerate(ev):
                try:
                    pidx = int(e.get("paragraph_index"))
                except Exception:
                    errs.append(f"finding[{i}].evidence[{j}] missing/invalid paragraph_index")
                    continue
                quote = _norm(str(e.get("quote", "")))
                if not quote:
                    errs.append(f"finding[{i}].evidence[{j}] empty quote")
                    continue
                ptxt = para_map.get(pidx)
                if ptxt is None:
                    errs.append(f"finding[{i}].evidence[{j}] paragraph_index {pidx} not in payload")
                    continue
                if quote not in ptxt:
                    errs.append(f"finding[{i}].evidence[{j}] quote not found in paragraph {pidx}")

        if status == "UNKNOWN":
            if not isinstance(miss, list) or not miss or not all(str(x).strip() for x in miss):
                errs.append(f"finding[{i}] status=UNKNOWN missing missing_inputs[]")

    # annotations: if quote provided, validate too
    anns = model_out.get("annotations") or []
    for i, a in enumerate(anns):
        if not isinstance(a, dict):
            continue
        if "quote" not in a:
            continue
        try:
            pidx = int(a.get("paragraph_index"))
        except Exception:
            errs.append(f"annotation[{i}] invalid paragraph_index")
            continue
        quote = _norm(str(a.get("quote", "")))
        if not quote:
            continue
        ptxt = para_map.get(pidx)
        if ptxt is None:
            errs.append(f"annotation[{i}] paragraph_index {pidx} not in payload")
            continue
        if quote not in ptxt:
            errs.append(f"annotation[{i}] quote not found in paragraph {pidx}")

    return errs
