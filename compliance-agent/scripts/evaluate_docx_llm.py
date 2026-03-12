#!/usr/bin/env python3
"""End-to-end DOCX evaluator (pilot): GDPR + NIS2-CZ → commented DOCX.

Option 1 (deterministic orchestration):
- Code controls:
  - extraction
  - rule applicability filtering
  - evidence retrieval (keyword/heading)
  - batching
  - checkpointing
  - schema validation
- LLM controls:
  - judgement of PASS/FAIL/PARTIAL/UNKNOWN
  - remediation clause suggestions

No RAG.

Models:
- Default: Anthropic Opus via API key stored in OpenClaw auth-profiles.

Usage:
  .venv/bin/python scripts/evaluate_docx_llm.py \
    --docx docs/inbox/tsa.docx \
    --profile eval/entity_profile.min.yaml \
    --outprefix outputs/tsa \
    --model anthropic/claude-opus-4-6

Outputs:
- <outprefix>.questions.yaml (if missing applicability info)
- <outprefix>.gdpr.eval.yaml
- <outprefix>.nis2.eval.yaml
- <outprefix>.annotations.yaml
- <outprefix>.commented.docx

"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

import yaml

# --- Paths ---
ROOT = Path(__file__).resolve().parents[1]
VENV_PY = ROOT / ".venv/bin/python"


def load_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text("utf-8"))


def dump_yaml(obj: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(obj, sort_keys=False, allow_unicode=True, width=1000), "utf-8")


def normalize_ws(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def extract_docx(docx: Path, out_yaml: Path) -> None:
    cmd = [str(VENV_PY), str(ROOT / "scripts/nis2cz_docx_extract.py"), "--in", str(docx), "--out", str(out_yaml)]
    subprocess.check_call(cmd)


def detect_doc_type(paragraphs: List[dict]) -> str:
    head = " ".join([p.get("text", "") for p in paragraphs[:80] if p.get("text")])
    h = head.lower()
    if any(x in h for x in ["agreement", "termination", "definitions", "service provider", "service recipient"]):
        return "contract"
    if any(x in h for x in ["policy", "politika", "směrnice"]):
        return "policy"
    if any(x in h for x in ["procedure", "postup"]):
        return "procedure"
    return "unknown"


def keyword_hits(paragraphs: List[dict], keywords: List[str], max_hits: int = 30) -> List[int]:
    kws = [k.lower() for k in (keywords or []) if k]
    if not kws:
        return []
    hits: List[int] = []
    for p in paragraphs:
        t = (p.get("text") or "")
        tl = t.lower()
        if any(k in tl for k in kws):
            hits.append(int(p["paragraph_index"]))
            if len(hits) >= max_hits:
                break
    return hits


def expand_window(indices: List[int], radius: int, max_total: int) -> List[int]:
    s = set()
    for i in indices:
        for j in range(i - radius, i + radius + 1):
            if j >= 0:
                s.add(j)
    out = sorted(s)
    if len(out) > max_total:
        return out[:max_total]
    return out


def load_auth_token(provider: str) -> str:
    """Deprecated in Option (1) cron-routed mode.

    Kept for backwards compatibility if we later re-enable direct SDK calls.
    """
    auth_path = Path("/root/.openclaw/agents/main/agent/auth-profiles.json")
    data = json.loads(auth_path.read_text("utf-8"))

    profiles = data.get("profiles") or data.get("authProfiles") or {}
    if isinstance(profiles, dict):
        for key, p in profiles.items():
            if not str(key).startswith(provider + ":"):
                continue
            if isinstance(p, dict):
                tok = p.get("token") or p.get("apiKey") or p.get("accessToken")
                if tok:
                    return tok

    raise RuntimeError(f"No token found for provider={provider} in {auth_path}")


@dataclass
class OpenClawCronClient:
    """LLM client that routes calls through OpenClaw cron (isolated run).

    This avoids direct provider HTTP auth issues and uses the Gateway's configured
    auth profiles.

    We create a one-shot cron job (scheduled far in the future) and `cron run`
    it immediately, then fetch the latest run summary.
    """

    openclaw_repo_dir: Path = Path("/opt/openclaw")

    def messages(self, *, model: str, system: str, user: str, max_tokens: int = 8000) -> str:
        # Note: max_tokens cannot be enforced via cron directly; we keep it for
        # interface parity and prompt discipline.
        prompt = (
            system.strip()
            + "\n\n"
            + "# INPUT (machine-readable JSON)\n"
            + user.strip()
            + "\n\n"
            + "# OUTPUT\nReturn raw JSON only."
        )

        add_cmd = [
            "pnpm",
            "-s",
            "openclaw",
            "cron",
            "add",
            "--json",
            "--name",
            "doc-eval-llm-call",
            "--at",
            "1h",
            "--session",
            "isolated",
            "--no-deliver",
            "--delete-after-run",
            "--model",
            model,
            "--thinking",
            "low",
            "--timeout-seconds",
            "2400",
            "--message",
            prompt,
        ]
        job_raw = subprocess.check_output(add_cmd, cwd=str(self.openclaw_repo_dir))
        job = json.loads(job_raw.decode("utf-8"))
        job_id = job["id"]

        run_cmd = [
            "pnpm",
            "-s",
            "openclaw",
            "cron",
            "run",
            "--expect-final",
            "--timeout",
            "2400000",
            job_id,
        ]
        subprocess.check_call(run_cmd, cwd=str(self.openclaw_repo_dir))

        runs_cmd = [
            "pnpm",
            "-s",
            "openclaw",
            "cron",
            "runs",
            "--id",
            job_id,
            "--limit",
            "1",
        ]
        runs_raw = subprocess.check_output(runs_cmd, cwd=str(self.openclaw_repo_dir))
        runs = json.loads(runs_raw.decode("utf-8"))
        entries = runs.get("entries") or []
        if not entries:
            raise RuntimeError("cron run produced no entries")
        summary = entries[0].get("summary")
        if not isinstance(summary, str) or not summary.strip():
            raise RuntimeError("cron run summary missing/empty")
        return summary.strip()


def build_questions(profile: dict) -> List[dict]:
    qs = []
    # NIS2
    if profile.get("in_scope_under_cz_law") in (None, "unknown"):
        qs.append({
            "id": "in_scope_under_cz_law",
            "question": "Is the assessed entity in scope under CZ-Act-264-2025 (yes/no/unknown)?",
            "choices": ["yes", "no", "unknown"],
        })
    if profile.get("duty_regime") in (None, "unknown"):
        qs.append({
            "id": "duty_regime",
            "question": "Which duty regime applies (higher=409/2025, lower=410/2025, unknown)?",
            "choices": ["higher", "lower", "unknown"],
        })
    if profile.get("entity_class") in (None, "unknown"):
        qs.append({
            "id": "entity_class",
            "question": "Is the entity essential or important (or unknown)?",
            "choices": ["essential", "important", "unknown"],
        })

    # GDPR
    if profile.get("gdpr_role") in (None, "unknown"):
        qs.append({
            "id": "gdpr_role",
            "question": "In this TSA context, is the service provider a GDPR processor, controller, or both?",
            "choices": ["processor", "controller", "both", "unknown"],
        })
    return qs


def validate_eval_output(doc: dict, expected_ruleset: str) -> None:
    if not isinstance(doc, dict):
        raise ValueError("evaluator output is not a mapping")
    result = doc.get("result")
    if not isinstance(result, dict):
        raise ValueError("missing result")
    if result.get("status") not in ("questions", "completed"):
        raise ValueError("result.status must be questions|completed")
    if result.get("status") == "completed" and result.get("ruleset") != expected_ruleset:
        raise ValueError(f"expected ruleset={expected_ruleset} got {result.get('ruleset')}")
    if result.get("status") == "completed":
        if "findings" not in doc:
            raise ValueError("completed output must include findings")


def _extract_json_block(text: str) -> str:
    """Extract JSON from a model response.

    Handles cases where the model returns markdown fences or preamble.
    """
    cleaned = text.strip()
    # Remove markdown fences
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z0-9_-]*\n", "", cleaned)
        cleaned = re.sub(r"\n```\s*$", "", cleaned)
        cleaned = cleaned.strip()

    # Find the first '{' and last '}' to extract JSON
    start = cleaned.find("{")
    if start == -1:
        raise ValueError("No JSON object found in response")
    
    end = cleaned.rfind("}")
    if end == -1 or end < start:
        raise ValueError("Incomplete JSON object in response")
    
    return cleaned[start:end+1]


def call_regulus(client: AnthropicClient, *, system_prompt: str, user_payload: str, model: str, max_tokens: int = 8000) -> dict:
    text = client.messages(model=model, system=system_prompt, user=user_payload, max_tokens=max_tokens)
    json_str = _extract_json_block(text)

    try:
        parsed = json.loads(json_str)
    except Exception as e:
        raise ValueError(f"Failed to parse JSON from model: {e}\nRaw:\n{json_str[:2000]}")
    return parsed


def make_user_payload(paragraphs: List[dict], profile: dict, ruleset_rules: List[dict], doc_type: str, batch_items: List[Tuple[dict, dict]]) -> str:
    """Create a user payload for a batch of checklist items.

    batch_items: list of (rule, item)
    """
    # Build a compact paragraph map
    para_map = {int(p["paragraph_index"]): p.get("text", "") for p in paragraphs}

    # Pre-retrieve candidate paragraphs per item
    item_blocks = []
    used_indices = set()
    for rule, item in batch_items:
        kw = (item.get("keywords_cs", []) or []) + (item.get("keywords_en", []) or [])
        hits = keyword_hits(paragraphs, kw, max_hits=20)
        expanded = expand_window(hits, radius=1, max_total=40)
        # If none, fallback: empty; evaluator should mark FAIL/UNKNOWN accordingly
        for idx in expanded:
            used_indices.add(idx)
        item_blocks.append({
            "rule_id": rule.get("id"),
            "checklist_item_id": item.get("id"),
            "title_en": item.get("title_en"),
            "title_cs": item.get("title_cs"),
            "acceptance_criteria": item.get("acceptance_criteria", []),
            "red_flags": item.get("red_flags", []),
            "candidate_paragraph_indices": expanded,
        })

    used = sorted(used_indices)
    paragraphs_block = []
    for idx in used:
        txt = para_map.get(idx, "")
        if txt:
            paragraphs_block.append({"paragraph_index": idx, "text": txt})

    payload = {
        "doc_type": doc_type,
        "entity_profile": profile,
        "rules": [
            {
                "rule_id": r.get("id"),
                "title": r.get("title"),
                "severity": r.get("severity"),
                "sources": r.get("sources", []),
            }
            for r, _ in batch_items
        ],
        "checklist_items": item_blocks,
        "paragraphs": paragraphs_block,
        "instructions": [
            "Evaluate ONLY the provided checklist_items.",
            "Use provided paragraphs; if required evidence is missing (e.g., schedules), return UNKNOWN and list missing inputs.",
            "Return YAML in the required schema with findings+annotations for these items.",
        ],
    }

    return json.dumps(payload, ensure_ascii=False)


def iter_checklist_items(rules: List[dict]) -> List[Tuple[dict, dict]]:
    out = []
    for r in rules:
        req = r.get("requirement", {}) or {}
        if req.get("type") not in ("checklist", "annex_checklist"):
            continue
        for item in (req.get("checklist") or []):
            out.append((r, item))
    return out


def findings_to_annotations(findings: List[dict], regulation: str) -> List[dict]:
    """Generate DOCX annotations from compact findings.

    Because cron summaries truncate, we keep model outputs compact and generate
    annotation text deterministically.
    """
    ann = []
    for f in findings or []:
        rid = f.get("rule_id")
        cid = f.get("checklist_item_id")
        status = f.get("status", "UNKNOWN")
        notes = normalize_ws(f.get("notes", ""))
        idxs = f.get("evidence_paragraph_indices") or []
        pidx = int(idxs[0]) if idxs else 0

        if regulation == "gdpr":
            tag = f"[GDPR][{rid}][{status}]"
        else:
            tag = f"[NIS2-CZ][{rid}][{cid}][{status}]"

        text = tag
        if idxs:
            text += f" evidence_paragraphs={idxs}."
        if notes:
            text += " " + notes

        ann.append({"paragraph_index": pidx, "text": text})
    return ann


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--docx", required=True)
    ap.add_argument("--profile", required=True)
    ap.add_argument("--outprefix", required=True)
    ap.add_argument("--model", default="anthropic/claude-opus-4-6")
    ap.add_argument("--batch-size", type=int, default=3)
    args = ap.parse_args()

    docx = Path(args.docx)
    profile_doc = load_yaml(Path(args.profile))
    profile = profile_doc.get("profile", profile_doc)

    extracted_path = ROOT / "docs/processed" / f"{docx.stem}.yaml"
    extract_docx(docx, extracted_path)
    extracted = load_yaml(extracted_path)
    paragraphs = extracted.get("paragraphs", [])
    paragraphs = [{**p, "text": normalize_ws(p.get("text", ""))} for p in paragraphs]
    doc_type = detect_doc_type(paragraphs)

    outprefix = Path(args.outprefix)

    qs = build_questions(profile)
    if qs:
        dump_yaml({"result": {"status": "questions"}, "questions": qs}, outprefix.with_suffix(".questions.yaml"))
        return

    # Load rulesets
    gdpr_rules = load_yaml(ROOT / "rules/gdpr/gdpr.rules.yaml").get("rules", [])
    nis2_rules = load_yaml(ROOT / "rules/nis2-cz/nis2-cz.rules.yaml").get("rules", [])

    # VERY simple applicability filter by doc_type
    # (Further filtering by entity_profile can be added here)
    def apply_contract_filter(r: dict) -> bool:
        scope = r.get("scope", {}) or {}
        applies = scope.get("applies_to") or []
        if doc_type == "contract":
            return ("contracts" in applies) or ("contract" in applies) or ("org" in applies) or (not applies)
        return True

    gdpr_app = [r for r in gdpr_rules if apply_contract_filter(r)]
    nis2_app = [r for r in nis2_rules if apply_contract_filter(r)]

    # Setup LLM client (route via OpenClaw cron to use Gateway auth)
    client = OpenClawCronClient()

    # Load system prompts
    sys_gdpr = (ROOT / "prompts/evaluator_gdpr_system_prompt.md").read_text("utf-8")
    sys_nis2 = (ROOT / "prompts/evaluator_nis2cz_system_prompt.md").read_text("utf-8")

    # Evaluate GDPR in batches
    gdpr_items = iter_checklist_items(gdpr_app)
    gdpr_findings = []
    missing_inputs = set()

    for i in range(0, len(gdpr_items), args.batch_size):
        batch = gdpr_items[i : i + args.batch_size]
        user_payload = make_user_payload(paragraphs, profile, gdpr_app, doc_type, batch)
        try:
            parsed = call_regulus(client, system_prompt=sys_gdpr, user_payload=user_payload, model=args.model)
        except ValueError as e:
            # If JSON parsing fails, log and skip (return UNKNOWN for items in this batch)
            print(f"Warning: GDPR batch {i//args.batch_size} failed to parse: {str(e)[:200]}", file=sys.stderr)
            for rule, item in batch:
                gdpr_findings.append({
                    "rule_id": rule.get("id"),
                    "checklist_item_id": item.get("id"),
                    "status": "UNKNOWN",
                    "evidence": [],
                    "notes": "Evaluation failed due to LLM output parsing error (response too long or malformed)",
                })
            continue
        validate_eval_output(parsed, "gdpr")
        if parsed.get("result", {}).get("status") == "questions":
            dump_yaml(parsed, outprefix.with_suffix(".gdpr.questions.yaml"))
            return
        gdpr_findings.extend(parsed.get("findings", []) or [])
        for x in (parsed.get("summary", {}) or {}).get("missing_inputs", []) or []:
            missing_inputs.add(str(x))

    gdpr_annotations = findings_to_annotations(gdpr_findings, regulation="gdpr")
    dump_yaml({"result": {"status": "completed", "ruleset": "gdpr"}, "findings": gdpr_findings, "annotations": gdpr_annotations, "summary": {"missing_inputs": sorted(missing_inputs)}}, outprefix.with_suffix(".gdpr.eval.yaml"))

    # Evaluate NIS2 in batches
    nis2_items = iter_checklist_items(nis2_app)
    nis2_findings = []
    missing_inputs2 = set()

    for i in range(0, len(nis2_items), args.batch_size):
        batch = nis2_items[i : i + args.batch_size]
        user_payload = make_user_payload(paragraphs, profile, nis2_app, doc_type, batch)
        try:
            parsed = call_regulus(client, system_prompt=sys_nis2, user_payload=user_payload, model=args.model)
        except ValueError as e:
            # If JSON parsing fails, log and skip (return UNKNOWN for items in this batch)
            print(f"Warning: NIS2-CZ batch {i//args.batch_size} failed to parse: {str(e)[:200]}", file=sys.stderr)
            for rule, item in batch:
                nis2_findings.append({
                    "rule_id": rule.get("id"),
                    "checklist_item_id": item.get("id"),
                    "status": "UNKNOWN",
                    "evidence": [],
                    "notes": "Evaluation failed due to LLM output parsing error (response too long or malformed)",
                })
            continue
        validate_eval_output(parsed, "nis2-cz")
        if parsed.get("result", {}).get("status") == "questions":
            dump_yaml(parsed, outprefix.with_suffix(".nis2.questions.yaml"))
            return
        nis2_findings.extend(parsed.get("findings", []) or [])
        for x in (parsed.get("summary", {}) or {}).get("missing_inputs", []) or []:
            missing_inputs2.add(str(x))

    nis2_annotations = findings_to_annotations(nis2_findings, regulation="nis2")
    dump_yaml({"result": {"status": "completed", "ruleset": "nis2-cz"}, "findings": nis2_findings, "annotations": nis2_annotations, "summary": {"missing_inputs": sorted(missing_inputs2)}}, outprefix.with_suffix(".nis2.eval.yaml"))

    # Merge annotations
    merge_cmd = [sys.executable, str(ROOT / "scripts/merge_annotations.py"), "--gdpr", str(outprefix.with_suffix(".gdpr.eval.yaml")), "--nis2", str(outprefix.with_suffix(".nis2.eval.yaml")), "--out", str(outprefix.with_suffix(".annotations.yaml"))]
    subprocess.check_call(merge_cmd)

    # Render commented docx
    annotate_cmd = [str(VENV_PY), str(ROOT / "scripts/nis2cz_docx_annotate.py"), "--in", str(docx), "--annotations", str(outprefix.with_suffix(".annotations.yaml")), "--out", str(outprefix.with_suffix(".commented.docx"))]
    subprocess.check_call(annotate_cmd)


if __name__ == "__main__":
    main()
