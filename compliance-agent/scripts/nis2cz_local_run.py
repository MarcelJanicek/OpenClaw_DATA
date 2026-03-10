#!/usr/bin/env python3
"""Local pilot runner for NIS2-CZ.

- No RAG
- No LLM
- Generates a *skeleton* report:
  - lists applicable rules
  - per-rule required evidence list
  - marks findings as UNKNOWN until evidence is provided/parsed

Usage:
  python3 scripts/nis2cz_local_run.py \
    --profile <entity_profile.yaml> \
    --rules rules/nis2-cz/nis2-cz.rules.yaml \
    --out outputs/nis2cz-report.md
"""

from __future__ import annotations

import argparse
import datetime as dt
import yaml

from pathlib import Path


def rule_applies(rule: dict, profile: dict) -> bool:
    scope = rule.get('scope', {}) or {}

    if 'in_scope_under_cz_law' in scope:
        if profile.get('in_scope_under_cz_law') is None:
            return False
        if bool(profile.get('in_scope_under_cz_law')) != bool(scope['in_scope_under_cz_law']):
            return False

    for key in ('entity_class', 'duty_regime', 'regulated_service_type'):
        if key in scope:
            allowed = scope[key]
            if profile.get(key) not in allowed:
                return False

    return True


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--profile', required=True)
    ap.add_argument('--rules', required=True)
    ap.add_argument('--out', required=True)
    args = ap.parse_args()

    prof_doc = yaml.safe_load(open(args.profile, 'r', encoding='utf-8'))
    profile = prof_doc.get('profile', prof_doc)

    rules_doc = yaml.safe_load(open(args.rules, 'r', encoding='utf-8'))
    meta = rules_doc.get('meta', {})
    rules = rules_doc.get('rules', [])

    applicable = [r for r in rules if rule_applies(r, profile)]

    now = dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat() + 'Z'

    lines = []
    lines.append(f"# NIS2-CZ Compliance Report (pilot)")
    lines.append("")
    lines.append(f"- Generated: {now}")
    lines.append(f"- Ruleset: {meta.get('ruleset_id')} {meta.get('version')} ({meta.get('status')})")
    lines.append(f"- Applicable rules: {len(applicable)} / {len(rules)}")
    lines.append("")

    lines.append("## Entity profile")
    lines.append("```yaml")
    lines.append(yaml.safe_dump(profile, sort_keys=False, allow_unicode=True, width=1000).strip())
    lines.append("```")
    lines.append("")

    lines.append("## Findings (initial)")
    lines.append("All findings are **UNKNOWN** until the required evidence artifacts are provided and evaluated.")
    lines.append("")

    for r in applicable:
        rid = r.get('id')
        title = r.get('title', '')
        severity = r.get('severity', 'unknown')
        required = (r.get('evidence_hints', {}) or {}).get('required', [])
        sources = [s.get('citation') for s in (r.get('sources', []) or []) if s.get('citation')]

        lines.append(f"### {rid} — {title}")
        lines.append(f"- Severity: **{severity}**")
        lines.append(f"- Status: **UNKNOWN**")
        if required:
            lines.append("- Required evidence:")
            for x in required:
                lines.append(f"  - {x}")
        if sources:
            lines.append("- Sources:")
            for s in sources:
                lines.append(f"  - {s}")
        lines.append("")

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines).rstrip() + "\n", 'utf-8')


if __name__ == '__main__':
    main()
