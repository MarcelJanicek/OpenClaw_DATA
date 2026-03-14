#!/usr/bin/env python3
"""Evaluate a DOCX against rulesets (GDPR + NIS2-CZ) — pilot runner.

This runner orchestrates the workflow without RAG:
1) Extract DOCX to paragraph YAML
2) Load entity_profile
3) Load rulesets (merged YAML)
4) Determine applicability + missing profile fields
5) Build an evaluation request bundle containing:
   - questions (if needed)
   - for each checklist item: candidate paragraph indices (via keyword anchors)

NOTE:
- This script does NOT call an LLM by itself.
- Use the produced bundle as input to the Opus evaluator agent (Regulus-Eval).
- After you obtain evaluator output, use `nis2cz_docx_annotate.py` to generate commented DOCX.

Usage:
  python3 scripts/evaluate_docx.py \
    --docx <file.docx> \
    --profile <entity_profile.yaml> \
    --out outputs/<name>.eval_bundle.yaml

"""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any

import subprocess

import yaml


def load_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text("utf-8"))


def normalize_text(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def detect_doc_type(paragraphs: list[dict]) -> str:
    head = " ".join([p.get("text", "") for p in paragraphs[:60] if p.get("text")])
    h = head.lower()
    if "agreement" in h or "terms" in h or "termination" in h or "definitions" in h:
        return "contract"
    if "policy" in h or "směrnice" in h or "politika" in h:
        return "policy"
    if "procedure" in h or "postup" in h:
        return "procedure"
    return "unknown"


def required_profile_questions(profile: dict, needs: list[str]) -> list[dict]:
    qs = []
    # NIS2-CZ core
    if "in_scope_under_cz_law" in needs and profile.get("in_scope_under_cz_law") in (None, "unknown"):
        qs.append({
            "id": "in_scope_under_cz_law",
            "question": "Is the assessed entity in scope under CZ-Act-264-2025 (yes/no/unknown)?",
            "choices": ["yes", "no", "unknown"],
        })
    if "duty_regime" in needs and profile.get("duty_regime") in (None, "unknown"):
        qs.append({
            "id": "duty_regime",
            "question": "Which duty regime applies under CZ decrees (higher=409/2025, lower=410/2025, unknown)?",
            "choices": ["higher", "lower", "unknown"],
        })
    if "entity_class" in needs and profile.get("entity_class") in (None, "unknown"):
        qs.append({
            "id": "entity_class",
            "question": "Is the entity essential or important (or unknown)?",
            "choices": ["essential", "important", "unknown"],
        })
    return qs


def rule_applies(rule: dict, doc_type: str, profile: dict) -> bool:
    scope = rule.get("scope", {}) or {}
    applies_to = scope.get("applies_to")
    if applies_to:
        # Map doc_type to applies_to tokens used in rules
        if doc_type == "contract" and "contracts" not in applies_to and "contract" not in applies_to:
            # some rules use 'contracts'
            return False
        if doc_type == "policy" and "policy" not in applies_to and "policies" not in applies_to and "org" not in applies_to:
            return False

    # Simple profile gates
    for key in ("duty_regime", "entity_class", "regulated_service_type"):
        if key in scope:
            allowed = scope[key]
            if profile.get(key) not in allowed:
                return False

    if scope.get("in_scope_under_cz_law") is True:
        if profile.get("in_scope_under_cz_law") is not True:
            return False

    return True


def keyword_retrieve(paragraphs: list[dict], keywords: list[str], max_hits: int = 20) -> list[int]:
    if not keywords:
        return []
    hits = []
    kws = [k.lower() for k in keywords if k]
    for p in paragraphs:
        t = (p.get("text") or "")
        tl = t.lower()
        if any(k in tl for k in kws):
            hits.append(int(p["paragraph_index"]))
            if len(hits) >= max_hits:
                break
    return hits


def build_bundle(doc_name: str, doc_type: str, paragraphs: list[dict], profile: dict, rules: list[dict]) -> dict:
    # Determine what profile fields we need based on rules present
    needs = ["in_scope_under_cz_law", "duty_regime", "entity_class"]
    questions = required_profile_questions(profile, needs)
    if questions:
        return {
            "result": {
                "status": "questions",
                "doc_name": doc_name,
                "doc_type": doc_type,
                "rulesets": ["gdpr", "nis2-cz"],
                "entity_profile_used": profile,
            },
            "questions": questions,
        }

    applicable = []
    for r in rules:
        if rule_applies(r, doc_type, profile):
            applicable.append(r)

    items = []
    for r in applicable:
        req = r.get("requirement", {}) or {}
        if req.get("type") not in ("checklist", "annex_checklist"):
            continue
        checklist = req.get("checklist", []) or []
        for it in checklist:
            kw_cs = it.get("keywords_cs", []) or []
            kw_en = it.get("keywords_en", []) or []
            hits = keyword_retrieve(paragraphs, kw_cs + kw_en)
            items.append({
                "rule_id": r.get("id"),
                "checklist_item_id": it.get("id"),
                "title_en": it.get("title_en"),
                "title_cs": it.get("title_cs"),
                "candidate_paragraph_indices": hits,
            })

    return {
        "result": {
            "status": "bundle",
            "doc_name": doc_name,
            "doc_type": doc_type,
            "rulesets": ["gdpr", "nis2-cz"],
            "entity_profile_used": profile,
        },
        "bundle": {
            "paragraph_count": len(paragraphs),
            "applicable_rules_count": len(applicable),
            "checklist_items": items,
            "notes": [
                "This bundle does not include full paragraph text. The evaluator should request paragraph text by index or the runner can be extended to embed it.",
                "If schedules/annexes are referenced but missing from the DOCX, evaluator should return UNKNOWN for dependent items and list missing inputs.",
            ],
        },
    }


def extract_docx(docx: Path, out_yaml: Path) -> None:
    """OOXML extractor — paragraph order matches nis2cz_docx_annotate.py (.//w:body//w:p)."""
    cmd = [
        str(Path(__file__).resolve().parents[1] / ".venv/bin/python"),
        str(Path(__file__).resolve().parent / "docx_extract_structured.py"),
        "--in", str(docx),
        "--out", str(out_yaml),
    ]
    subprocess.check_call(cmd)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--docx", required=True)
    ap.add_argument("--profile", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--rules-nis2", default=str(Path(__file__).resolve().parents[1] / "rules/nis2-cz/nis2-cz.rules.yaml"))
    ap.add_argument("--rules-gdpr", default=str(Path(__file__).resolve().parents[1] / "rules/gdpr/gdpr.rules.yaml"))
    args = ap.parse_args()

    docx = Path(args.docx)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    processed = Path(__file__).resolve().parents[1] / "docs/processed" / (docx.stem + ".yaml")
    processed.parent.mkdir(parents=True, exist_ok=True)
    extract_docx(docx, processed)

    extracted = load_yaml(processed)
    paragraphs = extracted.get("paragraphs", [])
    paragraphs = [{**p, "text": normalize_text(p.get("text", ""))} for p in paragraphs]

    doc_type = detect_doc_type(paragraphs)

    prof_doc = load_yaml(Path(args.profile))
    profile = prof_doc.get("profile", prof_doc)

    # Load rulesets (merged)
    nis2_doc = load_yaml(Path(args.rules_nis2))
    gdpr_doc = load_yaml(Path(args.rules_gdpr))

    rules = []
    rules.extend(nis2_doc.get("rules", []))
    rules.extend(gdpr_doc.get("rules", []))

    bundle = build_bundle(docx.name, doc_type, paragraphs, profile, rules)
    out.write_text(yaml.safe_dump(bundle, sort_keys=False, allow_unicode=True, width=1000), "utf-8")


if __name__ == "__main__":
    main()
