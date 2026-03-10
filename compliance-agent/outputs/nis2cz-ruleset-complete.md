# NIS2-CZ ruleset — complete (pilot)

- **Ruleset ID:** `nis2-cz`
- **Version:** `1.0-pilot`
- **Status:** complete
- **Rule count:** 28
- **Jurisdiction:** CZ

## What this deliverable contains
A pilot ruleset covering the **core CZ KB package**:
- Act **264/2025 Sb.** (Zákon o kybernetické bezpečnosti)
- Decrees **408/2025 Sb.**, **409/2025 Sb.**, **410/2025 Sb.**, **334/2025 Sb.**

Rules are organized into parts (foundations, scoping, governance, risk measures, incidents, supply chain) and merged into a single ruleset file.

Each rule includes:
- stable `id`
- `title`, `scope` and `requirement`
- `evidence_hints.required`
- `severity`
- `sources` (CZ legal citations; NIS2 directive only as reference/mapping where included)

## Files
- Merged ruleset: `rules/nis2-cz/nis2-cz.rules.yaml`
- Parts: `rules/nis2-cz/parts/nis2cz.*.yaml`
- Index: `rules/nis2-cz/nis2-cz.index.yaml`
- Entity profile schema: `rules/nis2-cz/entity_profile.schema.yaml`
- Milestones: `rules/nis2-cz/MILESTONES.md`

## How to regenerate
```bash
python3 scripts/ruleset_merge.py nis2-cz
```
