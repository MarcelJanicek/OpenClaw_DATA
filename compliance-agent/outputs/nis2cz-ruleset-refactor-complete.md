# NIS2-CZ ruleset refactor — complete (audit-grade)

Date (UTC): 2026-03-12

This file marks completion of the **NIS2-CZ ruleset audit-grade refactor** per `rules/nis2-cz/MILESTONES.md`.

## What “complete” means
- Milestones 0–5 in `rules/nis2-cz/MILESTONES.md` are checked off (foundations → governance → technical/organizational measures → incident handling & reporting → supply chain → final consistency sweep).
- Rules are structured as executable, deterministic checklists:
  - clear applicability / scoping
  - explicit pass/fail/N/A logic (with N/A justification)
  - bilingual anchors (EN/CZ) where applicable
  - red flags where appropriate
  - evidence requirements expressed via `evidence_hints.required[*].artifact_id`
- Evidence artifact IDs referenced by rules are validated to exist in `rules/nis2-cz/EVIDENCE_CATALOG.yaml`.

## Regeneration steps (performed)
- `python3 scripts/ruleset_merge.py nis2-cz`
- `python3 scripts/ruleset_checksum.py nis2-cz`

## Notes
- If any future edits are made to individual rules under `rules/nis2-cz/rules/**`, re-run the merge + checksum scripts above and commit the updated merged output + checksum.
