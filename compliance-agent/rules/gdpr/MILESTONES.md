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

Target: finish the remaining GDPR coverage within ~**8 hours** using 20-minute cron slices.
Rule of thumb: each milestone should fit in **<= 20 minutes** and change only one chapter part file.

### Completed
1) Ch I–IV: Arts. 1–22 ✅ (completed 2026-03-09)
   - Includes foundations, transparency (Arts. 12–14), and rights (Arts. 15–22)

### Remaining (chapter-by-chapter)
2) **Chapter V (Arts. 23–31)** — controller/processor obligations
   2.1) Art. 23 (restrictions) — tag as conditional + evidence needed
   2.2) Art. 24–25 (controller responsibility; DP by design/default)
   2.3) Art. 26–27 (joint controllers; EU representative)
   2.4) Art. 28–29 (processor clauses; acting on instructions)
   2.5) Art. 30–31 (ROPA; cooperation with SA)

3) **Chapter VI (Arts. 32–34)** — security & breaches
   3.1) Art. 32 (security of processing)
   3.2) Art. 33 (breach notification to SA)
   3.3) Art. 34 (breach communication to data subjects)

4) **Chapter VII (Arts. 35–43)** — DPIA/DPO/certification
   4.1) Arts. 35–36 (DPIA; prior consultation)
   4.2) Arts. 37–39 (DPO designation/position/tasks)
   4.3) Arts. 40–43 (codes of conduct; certification) — tag + evidence

5) **Chapter VIII (Arts. 44–50)** — transfers
   5.1) Arts. 44–46 (principle; adequacy; safeguards overview)
   5.2) Arts. 47–49 (BCR; derogations)
   5.3) Art. 50 (international cooperation) — tag + evidence

6) **Chapters IX–X (Arts. 51–76)** — supervisory authorities & consistency
   6.1) Arts. 51–59 (SA establishment/powers) — tag + evidence
   6.2) Arts. 60–67 (cooperation/one-stop-shop) — tag + evidence
   6.3) Arts. 68–76 (EDPB/consistency mechanisms) — tag + evidence

7) **Chapter XI (Arts. 77–84)** — remedies/liability/penalties
   7.1) Arts. 77–82 (complaints; judicial remedies; liability) — tag + evidence
   7.2) Arts. 83–84 (penalties) — tag + evidence

8) **Chapters XII–XV (Arts. 85–99)** — derogations/special cases
   8.1) Arts. 85–91 (freedom of expression; access to documents; national IDs; employment) — conditional
   8.2) Arts. 92–96 (delegation; committee procedure; repeals; relationship to earlier directive)
   8.3) Arts. 97–99 (reports; entry into force; addresses) — tag

## Changelog
- 2026-03-09: Milestone 3 complete — expanded rights rules for Arts. 15–22 with Art. 12-aligned intake/timelines/verification/fees; added granular access response requirements (content/copy/rights-of-others), restriction workflow details, Art. 19 recipient notification rule, and Art. 22 safeguards/exception documentation; extended entity_profile with portability/ADM/recipient-sharing flags.
- 2026-03-09: Milestone 2 complete — expanded Art. 13/14 notice content requirements; added explicit timing rules for Art. 13 (at collection) and Art. 14(3) (within 1 month / first communication / first disclosure); added conditional rule for Art. 14(5) exemptions with required documentation; extended entity_profile with direct/indirect collection and Art. 14(5) exemption flags.
- 2026-03-08: Milestone 1 complete — added rules for Arts. 1–4 and 7–11; expanded Art. 12 to include facilitation, timelines, and fees; added required-evidence lists; extended entity_profile with applicability/scope flags.

## Review cadence
- Commit at the end of each milestone with a changelog summary.
