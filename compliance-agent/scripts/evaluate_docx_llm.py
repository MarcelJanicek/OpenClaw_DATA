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
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

import yaml

# Allow running as a script (no package install)
# (ROOT is defined just below; we temporarily compute it here too)
_THIS_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_THIS_ROOT))
from scripts.citation_validate import validate_citations

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


def heading_indices(paragraphs: List[dict]) -> List[int]:
    return [int(p["paragraph_index"]) for p in paragraphs if p.get("is_heading")]


def section_span(paragraphs: List[dict], heading_idx: int, max_len: int = 80) -> List[int]:
    """Return indices from heading until next heading of same/higher level."""
    n = len(paragraphs)
    if heading_idx < 0 or heading_idx >= n:
        return []
    lvl = paragraphs[heading_idx].get("heading_level")
    if lvl is None:
        lvl = 9
    out = [heading_idx]
    for j in range(heading_idx + 1, n):
        if len(out) >= max_len:
            break
        if paragraphs[j].get("is_heading"):
            lvl2 = paragraphs[j].get("heading_level")
            lvl2 = lvl2 if lvl2 is not None else 9
            if lvl2 <= lvl:
                break
        out.append(j)
    return out


def match_heading(p: dict, needles: List[str]) -> bool:
    if not p.get("is_heading"):
        return False
    t = (p.get("text") or "").lower()
    return any(n in t for n in needles if n)


def retrieve_candidate_indices(paragraphs: List[dict], item: dict, *, max_total: int = 80) -> List[int]:
    """Step 4 (no embeddings): structure-aware retrieval.

    Sources of candidates:
    - keyword hits (full text)
    - headings that match keywords/title
    - schedule/annex reference paragraphs when missing inputs likely
    """
    needles = []
    for x in (item.get("keywords_cs") or []) + (item.get("keywords_en") or []):
        if x and len(x) >= 3:
            needles.append(x.lower())
    for x in [item.get("title_en"), item.get("title_cs")] :
        if x:
            needles.extend([w.lower() for w in re.findall(r"[A-Za-zÁ-ž]{4,}", x)])
    needles = sorted(set(needles))

    # 1) keyword hits in body
    hits = keyword_hits(paragraphs, needles, max_hits=30)
    cand = set(expand_window(hits, radius=1, max_total=max_total))

    # 2) heading matches → include their section spans
    for i, p in enumerate(paragraphs):
        if match_heading(p, needles):
            for idx in section_span(paragraphs, i, max_len=60):
                cand.add(idx)

    # 3) schedule/annex references
    sched_needles = ["schedule", "annex", "appendix", "příloha", "priloha"]
    if any(n in needles for n in ["schedule", "annex", "appendix", "příloha", "priloha"]):
        for i, p in enumerate(paragraphs):
            tl = (p.get("text") or "").lower()
            if any(s in tl for s in sched_needles):
                cand.add(i)

    out = sorted(cand)
    if len(out) > max_total:
        out = out[:max_total]
    return out


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

    Critical: we do NOT use the cron `summary` as the model output, because summary
    can be truncated. Instead we read the full assistant message from the cron run's
    persisted session JSONL file (sessionId is returned by `openclaw cron runs`).
    """

    openclaw_repo_dir: Path = Path("/opt/openclaw")
    session_store_dir: Path = Path("/root/.openclaw/agents/main/sessions")

    def _read_assistant_text_from_session(self, session_id: str, wait_s: float = 3.0) -> str:
        path = self.session_store_dir / f"{session_id}.jsonl"
        t0 = time.time()
        while not path.exists() and time.time() - t0 < wait_s:
            time.sleep(0.05)
        if not path.exists():
            raise RuntimeError(f"Session JSONL not found: {path}")

        last_text = None
        for line in path.read_text("utf-8").splitlines():
            try:
                rec = json.loads(line)
            except Exception:
                continue
            if rec.get("type") != "message":
                continue
            msg = rec.get("message") or {}
            if msg.get("role") != "assistant":
                continue
            parts = []
            for block in (msg.get("content") or []):
                if block.get("type") == "text":
                    parts.append(block.get("text") or "")
            last_text = "".join(parts).strip()

        if not last_text:
            raise RuntimeError("No assistant message text found in session JSONL")
        return last_text

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

        job_name = f"doc-eval-llm-call-{uuid.uuid4().hex[:8]}"

        add_cmd = [
            "pnpm",
            "-s",
            "openclaw",
            "cron",
            "add",
            "--json",
            "--name",
            job_name,
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
        session_id = entries[0].get("sessionId")
        if not session_id:
            raise RuntimeError("cron run entry missing sessionId")

        return self._read_assistant_text_from_session(session_id)


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


def call_regulus(
    client: OpenClawCronClient,
    *,
    system_prompt: str,
    user_payload: str,
    models: List[str],
    max_tokens: int = 8000,
) -> dict:
    """Call evaluator with model fallback chain.

    `models` is tried in order until one returns parseable JSON.
    """
    last_err: Exception | None = None
    for m in models:
        try:
            text = client.messages(model=m, system=system_prompt, user=user_payload, max_tokens=max_tokens)
            json_str = _extract_json_block(text)
            return json.loads(json_str)
        except Exception as e:
            last_err = e
            print(f"Warning: model {m} failed ({type(e).__name__}): {str(e)[:200]}", file=sys.stderr)
            continue
    raise ValueError(f"All models failed. Last error: {last_err}")


def make_user_payload(paragraphs: List[dict], profile: dict, ruleset_rules: List[dict], doc_type: str, batch_items: List[Tuple[dict, dict]]) -> tuple[str, list[dict]]:
    """Create a user payload for a batch of checklist items.

    Returns (payload_json, paragraphs_block) so we can validate citations against
    the exact text sent to the model.
    """
    para_map = {int(p["paragraph_index"]): p.get("text", "") for p in paragraphs}

    item_blocks = []
    used_indices = set()
    for rule, item in batch_items:
        expanded = retrieve_candidate_indices(paragraphs, item, max_total=80)
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
        "checklist_items": item_blocks,
        "paragraphs": paragraphs_block,
        "instructions": [
            "Evaluate ONLY the provided checklist_items.",
            "CITATION RULE: any quote MUST be copied verbatim from the provided paragraphs.",
            "If required inputs are missing, set status UNKNOWN and populate missing_inputs[].",
            "Return RAW JSON only in the required schema.",
        ],
    }

    return json.dumps(payload, ensure_ascii=False), paragraphs_block


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
    """Generate DOCX annotations from findings.

    Step 2 changed the finding schema to be citation-grounded:
      evidence: [{paragraph_index, quote}]

    Anchoring policy (v1):
    - If evidence exists: anchor to the first evidence paragraph.
    - Else: anchor to paragraph 1 (avoid title/TOC 0); sanitizer may further move.
    """
    ann = []
    for f in findings or []:
        rid = f.get("rule_id")
        cid = f.get("checklist_item_id")
        status = f.get("status", "UNKNOWN")
        notes = normalize_ws(f.get("notes", ""))
        missing_inputs = f.get("missing_inputs") or []

        evidence = f.get("evidence") or []
        pidx = 1
        quote = None
        if isinstance(evidence, list) and evidence:
            e0 = evidence[0] or {}
            try:
                pidx = int(e0.get("paragraph_index"))
            except Exception:
                pidx = 1
            q = e0.get("quote")
            if isinstance(q, str) and q.strip():
                quote = q.strip()

        if regulation == "gdpr":
            tag = f"[GDPR][{rid}][{status}]"
        else:
            tag = f"[NIS2-CZ][{rid}][{cid}][{status}]"

        text = tag
        if quote:
            text += f" QUOTE: {normalize_ws(quote)}"
        if notes:
            text += f" ISSUE: {notes}"
        if status == "UNKNOWN" and missing_inputs:
            text += f" MISSING: {', '.join(map(str, missing_inputs))}"

        ann.append({
            "paragraph_index": pidx,
            "author": "ComplianceAgent",
            "text": text,
            "quote": quote,
            "status": status,
            "rule_id": rid,
            "checklist_item_id": cid,
            "regulation": regulation,
            "missing_inputs": missing_inputs,
        })

    return ann


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--docx", required=True)
    ap.add_argument("--profile", required=True)
    ap.add_argument("--outprefix", required=True)
    ap.add_argument(
        "--model",
        default="anthropic/claude-opus-4-6",
        help="Primary model for evaluation calls (will fall back if configured)",
    )
    ap.add_argument(
        "--model-fallback",
        action="append",
        default=[],
        help="Fallback model (repeatable). Default chain: sonnet then openai-codex/gpt-5.2",
    )
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

    # Model chain
    fallbacks = args.model_fallback or ["anthropic/claude-sonnet-4-6", "openai-codex/gpt-5.2"]
    model_chain = [args.model, *fallbacks]

    # Evaluate GDPR in batches
    gdpr_items = iter_checklist_items(gdpr_app)
    gdpr_findings = []
    missing_inputs = set()

    for i in range(0, len(gdpr_items), args.batch_size):
        batch = gdpr_items[i : i + args.batch_size]
        user_payload, payload_paras = make_user_payload(paragraphs, profile, gdpr_app, doc_type, batch)
        try:
            parsed = call_regulus(client, system_prompt=sys_gdpr, user_payload=user_payload, models=model_chain)
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

        cit_errs = validate_citations(parsed, payload_paras)
        if cit_errs:
            retry_payload = json.loads(user_payload)
            retry_payload["validation_errors"] = cit_errs[:20]
            retry_payload["instructions"].append(
                "VALIDATION FAILED: Fix evidence quotes so each quote is a verbatim substring of the referenced paragraph."
            )
            parsed = call_regulus(
                client,
                system_prompt=sys_gdpr,
                user_payload=json.dumps(retry_payload, ensure_ascii=False),
                models=model_chain,
            )
            validate_eval_output(parsed, "gdpr")

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
        user_payload, payload_paras = make_user_payload(paragraphs, profile, nis2_app, doc_type, batch)
        try:
            parsed = call_regulus(client, system_prompt=sys_nis2, user_payload=user_payload, models=model_chain)
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

        cit_errs = validate_citations(parsed, payload_paras)
        if cit_errs:
            retry_payload = json.loads(user_payload)
            retry_payload["validation_errors"] = cit_errs[:20]
            retry_payload["instructions"].append(
                "VALIDATION FAILED: Fix evidence quotes so each quote is a verbatim substring of the referenced paragraph."
            )
            parsed = call_regulus(
                client,
                system_prompt=sys_nis2,
                user_payload=json.dumps(retry_payload, ensure_ascii=False),
                models=model_chain,
            )
            validate_eval_output(parsed, "nis2-cz")

        nis2_findings.extend(parsed.get("findings", []) or [])
        for x in (parsed.get("summary", {}) or {}).get("missing_inputs", []) or []:
            missing_inputs2.add(str(x))

    nis2_annotations = findings_to_annotations(nis2_findings, regulation="nis2")
    dump_yaml({"result": {"status": "completed", "ruleset": "nis2-cz"}, "findings": nis2_findings, "annotations": nis2_annotations, "summary": {"missing_inputs": sorted(missing_inputs2)}}, outprefix.with_suffix(".nis2.eval.yaml"))

    # Merge annotations
    merge_cmd = [sys.executable, str(ROOT / "scripts/merge_annotations.py"), "--gdpr", str(outprefix.with_suffix(".gdpr.eval.yaml")), "--nis2", str(outprefix.with_suffix(".nis2.eval.yaml")), "--out", str(outprefix.with_suffix(".annotations.yaml"))]
    subprocess.check_call(merge_cmd)

    # Sanitize + re-anchor annotations (avoid title/TOC noise)
    sanitized_path = outprefix.with_suffix(".annotations.sanitized.yaml")
    sanitize_cmd = [
        sys.executable,
        str(ROOT / "scripts/sanitize_annotations.py"),
        "--extracted",
        str(extracted_path),
        "--in",
        str(outprefix.with_suffix(".annotations.yaml")),
        "--out",
        str(sanitized_path),
    ]
    subprocess.check_call(sanitize_cmd)

    # Render commented docx
    annotate_cmd = [
        str(VENV_PY),
        str(ROOT / "scripts/nis2cz_docx_annotate.py"),
        "--in",
        str(docx),
        "--annotations",
        str(sanitized_path),
        "--out",
        str(outprefix.with_suffix(".commented.docx")),
    ]
    subprocess.check_call(annotate_cmd)


if __name__ == "__main__":
    main()
