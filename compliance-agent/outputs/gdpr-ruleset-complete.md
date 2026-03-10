# GDPR ruleset — complete

Status: complete

This repository contains end-to-end, chapter-by-chapter GDPR coverage for Arts. 1–99 as a practical product/compliance check ruleset.

## Primary outputs

- **Merged ruleset:** `rules/gdpr/gdpr.rules.yaml`
- **Index:** `rules/gdpr/gdpr.index.yaml`
- **Entity/profile schema:** `rules/gdpr/entity_profile.schema.yaml`
- **Chapter parts (source-of-truth):** `rules/gdpr/parts/` (merged by script)

## Completion notes

- Chapters I–XV have explicit rule coverage (including conditional/tagged institutional/national-derogation articles).
- Every rule includes:
  - `evidence_hints.required`
  - `severity`
  - `sources` citations

## Build

Regenerate the merged ruleset:

```bash
python3 scripts/gdpr_merge.py
```

## Snapshot

- Total merged rules: **79**
- Last verified build: **2026-03-10 06:09 UTC**
