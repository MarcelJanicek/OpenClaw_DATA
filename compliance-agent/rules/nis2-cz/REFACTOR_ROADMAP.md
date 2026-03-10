# NIS2-CZ Ruleset Refactor Roadmap

Status: **in-progress**
Created: 2026-03-10

## Problem Statement

The NIS2-CZ ruleset was built incrementally across multiple milestones. This created
several inconsistencies that hurt machine-readability and auditability:

1. **Evidence catalog is incomplete** — `EVIDENCE_CATALOG.yaml` only covers supply-chain
   (ch05) artifacts. Parts 00–04 reference ~40+ evidence items as bare strings with no
   catalog entries, descriptions, or format hints.
2. **Inconsistent evidence_hints format** — ch05 uses structured `artifact_id:` references;
   ch00–ch04 use bare string lists under `required:` and `artifacts:`.
3. **No not-applicable mechanism** — rules have no schema for marking a rule or checklist
   item as not-applicable with justification (critical for audit).
4. **Merged rules file drift** — `nis2-cz.rules.yaml` is a flat merge that may diverge
   from the authoritative `parts/` files.
5. **Scope conditions inconsistency** — some rules use `conditions:` blocks, others use
   top-level `duty_regime:` / `in_scope_under_cz_law:` directly.

## Milestones (each ≤40 min)

### M0 — Schema & catalog normalization (this run)
- [x] Define `not_applicable` mechanism schema (add to rules schema docs)
- [x] Create full evidence artifact catalog covering ALL parts (00–05)
- [x] Normalize all part files to use `artifact_id:` references in `evidence_hints`
- [x] Regenerate merged `nis2-cz.rules.yaml`
- [x] Commit

### M1 — Scope & applicability normalization (~30 min)
- [x] Unify scope/conditions format across all parts
- [ ] Add `not_applicable_if:` conditions where appropriate (e.g., code ownership
      clause only when supplier develops software)
- [x] Validate all `duty_regime` conditions are consistent
- [x] Regenerate merged file + commit

### M2 — Incident & reporting completeness (~30 min)
- [ ] ch04 currently has only 2 rules (classification + register) — needs reporting
      workflow, timelines, post-incident review rules per MILESTONES.md items 3.2–3.3
- [ ] Add evidence catalog entries for incident artifacts
- [ ] Commit

### M3 — Risk measures deep pass (~40 min)
- [ ] ch03 has 12 rules but evidence hints are bare strings — verify all map to catalog
- [ ] Add missing rules for BCP/DR, secure development, change management
- [ ] Validate severity assignments against decree sections
- [ ] Commit

### M4 — Cross-references & validation (~30 min)
- [ ] Add `cross_references:` linking related rules across parts
- [ ] Build/run validation script: every `artifact_id` in rules exists in catalog,
      every catalog entry has at least one `referenced_by`
- [ ] Final consistency sweep
- [ ] Commit + update MILESTONES.md

### M5 — Oversight tagging & finalization (~20 min)
- [ ] Populate ch99 with oversight/tagging rules
- [ ] Version bump to 2.0
- [ ] Update NIS2-CZ.md, RELEASES.md
- [ ] Final merged file generation + checksum
