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

Rule of thumb: each milestone should fit in **<= 20 minutes** (one cron run).

A) Core scope + transparency + rights (already done)
1) Foundations: Art. 1–12 (+ key recitals) + definitions constraints ✅ (completed 2026-03-08)
2) Notices: Art. 13–14 ✅ (completed 2026-03-09)
3) Rights: Art. 15–22 (+ Art. 12 timelines/fees) ✅ (completed 2026-03-09)

B) Controller/processor obligations (split)
4) Controller responsibility (Art. 24)
5) Data protection by design/default (Art. 25)
6) Joint controllers (Art. 26)
7) EU representative (Art. 27)
8) Processor clauses (Art. 28)
9) Processor acting on instructions (Art. 29)

C) Security & breaches (split)
10) Security of processing (Art. 32)
11) Breach notification to SA (Art. 33)
12) Breach communication to data subjects (Art. 34)

D) Accountability docs & org (split)
13) ROPA (Art. 30)
14) DPIA (Art. 35)
15) Prior consultation (Art. 36)
16) DPO designation (Art. 37)
17) DPO position/tasks (Arts. 38–39)

E) Transfers (split)
18) Transfers principle (Art. 44)
19) Adequacy (Art. 45)
20) Safeguards (Arts. 46–47)
21) Derogations (Art. 49)

F) Authorities / enforcement / remedies (product-check focus; mostly evidence/tagging)
22) Supervisory authorities basics (Arts. 51–59)
23) Cooperation/consistency (Arts. 60–76)
24) Remedies/liability (Arts. 77–82)
25) Penalties (Arts. 83–84)

G) Special processing + derogations
26) Special cases/derogations (Arts. 85–99)

## Changelog
- 2026-03-09: Milestone 3 complete — expanded rights rules for Arts. 15–22 with Art. 12-aligned intake/timelines/verification/fees; added granular access response requirements (content/copy/rights-of-others), restriction workflow details, Art. 19 recipient notification rule, and Art. 22 safeguards/exception documentation; extended entity_profile with portability/ADM/recipient-sharing flags.
- 2026-03-09: Milestone 2 complete — expanded Art. 13/14 notice content requirements; added explicit timing rules for Art. 13 (at collection) and Art. 14(3) (within 1 month / first communication / first disclosure); added conditional rule for Art. 14(5) exemptions with required documentation; extended entity_profile with direct/indirect collection and Art. 14(5) exemption flags.
- 2026-03-08: Milestone 1 complete — added rules for Arts. 1–4 and 7–11; expanded Art. 12 to include facilitation, timelines, and fees; added required-evidence lists; extended entity_profile with applicability/scope flags.

## Review cadence
- Commit at the end of each milestone with a changelog summary.
