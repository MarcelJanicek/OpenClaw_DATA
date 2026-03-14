# GDPR ruleset milestones

Status: audit-grade-partial (v0.2-audit)

## Audit-Grade Quality Bar (mirrors NIS2-CZ v2.0)

For a rule to be considered **audit-grade**, it must have:
- `requirement.type: checklist` with explicit `logic` (ALL/ANY) and `na_mechanism`
- Per-item `acceptance_criteria` list (what the auditor must confirm to pass)
- Per-item `red_flags` list (automatic findings if present)
- `evidence_hints` referencing `artifact_id` keys from `EVIDENCE_CATALOG.yaml` (not free-text strings)

Rules still using `multi_obligation`, `document_required`, or `mapping_required` types are **draft-grade** and must be upgraded in subsequent milestones.

---

## MUST DO NEXT (high priority — blocks audit readiness)

### Milestone A — Core lawful-basis rules (Art. 6 + Art. 9)
- Upgrade `GDPR-ART6-LAWFUL-BASIS` and `GDPR-ART9-SPECIAL-CATEGORIES` to checklist structure
- These are the highest-traffic rules in evaluations; free-text evidence hints cause inconsistent scoring
- Add artifact IDs: `GDPR-LAWFUL-BASIS-REGISTER`, `GDPR-ROPA`, `GDPR-LIA` (already in catalog)
- **Estimate:** 30–45 min

### Milestone B — Data subject rights cluster (Arts. 12–22)
- Upgrade `GDPR-ART12-TRANSPARENT-COMMUNICATION`, `GDPR-ART15-ACCESS`, `GDPR-ART17-ERASURE`
- Add `GDPR-DSR-PROCEDURE` and `GDPR-DSR-REGISTER` artifact hints
- These are the most frequently disputed rules in DPA investigations
- **Estimate:** 60–90 min (6–8 rules)

### Milestone C — Breach notification (Arts. 33–34)
- Upgrade `GDPR-ART33-BREACH-SUPERVISORY` and `GDPR-ART34-BREACH-DATA-SUBJECT` to checklist
- 72-hour timer item, supervisory authority notification, data subject communication
- Artifact IDs already in catalog: `GDPR-BREACH-REGISTER`, `GDPR-BREACH-RESPONSE-PLAN`, `GDPR-SA-NOTIFICATION-TEMPLATE`
- **Estimate:** 30 min

### Milestone D — DPA and processor obligations (Art. 28)
- Upgrade `GDPR-ART28-PROCESSOR` to checklist with sub-processor chain, DPA clause checklist
- Add `GDPR-DPA-TEMPLATE` artifact hints
- Critical for SaaS/AI products that operate as processors
- **Estimate:** 30 min

---

## CAN WAIT (lower priority)

### Milestone E — DPIA and DPO (Arts. 35–39)
- Upgrade to checklist; add `GDPR-DPIA-SCREENING`, `GDPR-DPIA-REPORTS`, `GDPR-DPO-APPOINTMENT`
- Important but less frequently triggered by entity profile flags
- **Estimate:** 45 min

### Milestone F — International transfers (Arts. 44–50)
- Upgrade to checklist; add `GDPR-TRANSFER-MECHANISMS` artifact hints
- High importance for global SaaS but can be deferred if entity is EU-only
- **Estimate:** 30 min

### Milestone G — Remaining Arts. 7–11 (consent, children, special categories detail)
- `GDPR-ART7-CONSENT-CONDITIONS`, `GDPR-ART8-CHILD-CONSENT-ISS` — add checklist + red_flags
- **Estimate:** 30 min

### Milestone H — Supervision and remedies (Arts. 51–84)
- Primarily supervisory authority obligations; lower day-to-day evaluation frequency
- Upgrade key rules (Art. 58 supervisory powers, Art. 77 right to lodge complaint)
- **Estimate:** 45 min

### Milestone I — Evidence catalog completeness pass
- Review all existing `evidence_hints` in ch03–ch05, ch07–ch15 and replace free-text with
  `artifact_id` references; add any missing artifact IDs to EVIDENCE_CATALOG.yaml
- **Estimate:** 60 min

---

## Completed

### v0.2-audit (2026-03-14) — Audit refactor bootstrap
- Created `EVIDENCE_CATALOG.yaml` with 30+ canonical artifact IDs for GDPR rules
- Refactored `GDPR-ART5-PRINCIPLES` (ch02) to checklist structure: 7 checklist items
  (ART5-01 through ART5-07), each with acceptance_criteria and red_flags
- Refactored `GDPR-ART32-SECURITY` (ch06) to checklist structure: 7 checklist items
  (ART32-01 through ART32-07), each with acceptance_criteria and red_flags
- Both rules now reference EVIDENCE_CATALOG artifact IDs instead of free-text strings
- Bumped gdpr.index.yaml version to `0.2-audit`, status to `audit-grade-partial`
- Added changelog entry in gdpr.index.yaml

### v0.1 (2026-03-08 to 2026-03-09) — Initial GDPR coverage Arts. 1–99
1) Ch I–IV: Arts. 1–22 ✅ (completed 2026-03-09)
2) Chapter V (Arts. 23–31) ✅
3) Chapter VI (Arts. 32–34) ✅
4) Chapter VII (Arts. 35–43) ✅
5) Chapter VIII (Arts. 44–50) ✅
6) Chapters IX–X (Arts. 51–76) ✅
7) Chapter XI (Arts. 77–84) ✅
8) Chapters XII–XV (Arts. 85–99) ✅

---

## Changelog
- 2026-03-14: v0.2-audit — Audit-grade refactor of Art. 5 and Art. 32; EVIDENCE_CATALOG.yaml created.
- 2026-03-09: Milestone 3 complete — expanded rights rules for Arts. 15–22.
- 2026-03-09: Milestone 2 complete — expanded Art. 13/14 notice content requirements.
- 2026-03-08: Milestone 1 complete — added rules for Arts. 1–4 and 7–11.
