# GDPR ruleset milestones

Status: complete

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

Target: finish the remaining GDPR coverage within ~**8 hours** using 20-minute cron slices.
Rule of thumb: each milestone should fit in **<= 20 minutes** and change only one chapter part file.

### Completed
1) Ch I–IV: Arts. 1–22 ✅ (completed 2026-03-09)
   - Includes foundations, transparency (Arts. 12–14), and rights (Arts. 15–22)

### Completed
2) Chapter V (Arts. 23–31) ✅
3) Chapter VI (Arts. 32–34) ✅
4) Chapter VII (Arts. 35–43) ✅
5) Chapter VIII (Arts. 44–50) ✅
6) Chapters IX–X (Arts. 51–76) ✅
7) Chapter XI (Arts. 77–84) ✅
8) Chapters XII–XV (Arts. 85–99) ✅

## Changelog
- 2026-03-09: Milestone 3 complete — expanded rights rules for Arts. 15–22 with Art. 12-aligned intake/timelines/verification/fees; added granular access response requirements (content/copy/rights-of-others), restriction workflow details, Art. 19 recipient notification rule, and Art. 22 safeguards/exception documentation; extended entity_profile with portability/ADM/recipient-sharing flags.
- 2026-03-09: Milestone 2 complete — expanded Art. 13/14 notice content requirements; added explicit timing rules for Art. 13 (at collection) and Art. 14(3) (within 1 month / first communication / first disclosure); added conditional rule for Art. 14(5) exemptions with required documentation; extended entity_profile with direct/indirect collection and Art. 14(5) exemption flags.
- 2026-03-08: Milestone 1 complete — added rules for Arts. 1–4 and 7–11; expanded Art. 12 to include facilitation, timelines, and fees; added required-evidence lists; extended entity_profile with applicability/scope flags.

## Review cadence
- Commit at the end of each milestone with a changelog summary.
