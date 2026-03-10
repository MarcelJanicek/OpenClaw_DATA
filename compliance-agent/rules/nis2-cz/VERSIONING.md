# NIS2-CZ ruleset versioning

## Principle
- The canonical source is the YAML in `rules/nis2-cz/`.
- Each release has a **version** and an integrity **checksum**.

## Files
- `nis2-cz.index.yaml` — meta includes version/status
- `nis2-cz.rules.yaml` — merged output
- `nis2-cz.rules.sha256` — sha256 of the merged output
- `RELEASES.md` — human changelog

## Workflow
1) Update parts under `parts/`
2) Regenerate merged: `python3 scripts/ruleset_merge.py nis2-cz`
3) Update checksum: `python3 scripts/ruleset_checksum.py nis2-cz`
4) Update `RELEASES.md`
5) Commit + tag (optional)
