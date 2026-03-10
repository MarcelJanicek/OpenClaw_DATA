#!/usr/bin/env python3
"""Filter NIS2-CZ rules by entity_profile.

This is intentionally deterministic (no RAG, no LLM).

Convention supported:
- Rule may include optional scope filters:
  scope:
    entity_class: [essential, important]
    duty_regime: [higher, lower]
    in_scope_under_cz_law: true

If a filter key is missing on the rule, it does not constrain applicability.

Usage:
  python3 scripts/nis2cz_filter.py \
    --profile rules/nis2-cz/entity_profile.schema.yaml \
    --rules rules/nis2-cz/nis2-cz.rules.yaml
"""

from __future__ import annotations

import argparse
import yaml


def rule_applies(rule: dict, profile: dict) -> bool:
    scope = rule.get('scope', {}) or {}

    # in_scope_under_cz_law
    if 'in_scope_under_cz_law' in scope:
        if profile.get('in_scope_under_cz_law') is None:
            return False  # cannot decide
        if bool(profile.get('in_scope_under_cz_law')) != bool(scope['in_scope_under_cz_law']):
            return False

    # entity_class
    if 'entity_class' in scope:
        allowed = scope['entity_class']
        if profile.get('entity_class') not in allowed:
            return False

    # duty_regime
    if 'duty_regime' in scope:
        allowed = scope['duty_regime']
        if profile.get('duty_regime') not in allowed:
            return False

    # regulated_service_type
    if 'regulated_service_type' in scope:
        allowed = scope['regulated_service_type']
        if profile.get('regulated_service_type') not in allowed:
            return False

    return True


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--profile', required=True)
    ap.add_argument('--rules', required=True)
    args = ap.parse_args()

    profile_doc = yaml.safe_load(open(args.profile, 'r', encoding='utf-8'))
    profile = profile_doc.get('profile', profile_doc)

    rules_doc = yaml.safe_load(open(args.rules, 'r', encoding='utf-8'))
    rules = rules_doc.get('rules', [])

    applicable = [r for r in rules if rule_applies(r, profile)]

    out = {
        'meta': rules_doc.get('meta', {}),
        'applicable_rules_count': len(applicable),
        'applicable_rule_ids': [r.get('id') for r in applicable],
    }
    print(yaml.safe_dump(out, sort_keys=False, allow_unicode=True, width=1000))


if __name__ == '__main__':
    main()
