# GDPR ruleset milestones

Status: in progress

## Target definition of done
- Covers GDPR obligations end-to-end (Arts. 1–99), with practical product-check focus
- Rules are parameterized by `entity_profile` (controller/processor etc.)
- Each rule includes:
  - id, title
  - scope (role, applies_to)
  - requirement (test type + acceptance criteria)
  - evidence_hints (including **required evidence list**)
  - severity
  - sources (article/recital citations)

## Milestones
1) Foundations: Art. 1–12 (+ key recitals) + definitions constraints ✅ (completed 2026-03-08)
2) Notices: Art. 13–14 ✅ (completed 2026-03-09)
3) Rights: Art. 15–22 (+ Art. 12 timelines/fees) ✅ (completed 2026-03-09)
4) Governance roles: Art. 24–29, 26–28
5) Security & breaches: Art. 32–34
6) Accountability docs: Art. 30, 35–39
7) Transfers: Art. 44–49
8) Supervisory authorities & cooperation: Art. 51–76 (encode what the product can check)
9) Remedies & liability & penalties: Art. 77–84 (encode obligations/expectations)
10) Sector-specific/derogations: Art. 85–99 (tag as conditional/needs legal input)

## Changelog
- 2026-03-09: Milestone 3 complete — expanded rights rules for Arts. 15–22 with Art. 12-aligned intake/timelines/verification/fees; added granular access response requirements (content/copy/rights-of-others), restriction workflow details, Art. 19 recipient notification rule, and Art. 22 safeguards/exception documentation; extended entity_profile with portability/ADM/recipient-sharing flags.
- 2026-03-09: Milestone 2 complete — expanded Art. 13/14 notice content requirements; added explicit timing rules for Art. 13 (at collection) and Art. 14(3) (within 1 month / first communication / first disclosure); added conditional rule for Art. 14(5) exemptions with required documentation; extended entity_profile with direct/indirect collection and Art. 14(5) exemption flags.
- 2026-03-08: Milestone 1 complete — added rules for Arts. 1–4 and 7–11; expanded Art. 12 to include facilitation, timelines, and fees; added required-evidence lists; extended entity_profile with applicability/scope flags.

## Review cadence
- Commit at the end of each milestone with a changelog summary.
