# GDPR ruleset — complete

Status: complete

This repository now contains end-to-end, chapter-by-chapter GDPR coverage for Arts. 1–99 as a practical product/compliance check ruleset.

## Primary outputs

- **Merged ruleset:** `rules/gdpr/gdpr.rules.yaml`
- **Index:** `rules/gdpr/gdpr.index.yaml`
- **Entity/profile schema:** `rules/gdpr/entity_profile.schema.yaml`
- **Chapter parts:** `rules/gdpr/parts/` (source-of-truth, merged by script)

## Completion notes

- Chapters I–XV have explicit rule coverage (including conditional/tagged institutional/national-derogation articles).
- All rules include:
  - `evidence_hints.required`
  - `severity`
  - `sources` citations

## Build

To regenerate the merged ruleset:

```bash
python3 scripts/gdpr_merge.py
```

## Snapshot

- Total merged rules: **79**
- Last milestone addressed: **Arts. 97–99** (monitoring + applicability tagging)
