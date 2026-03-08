# Minimal compliance checking approach (no RAG)

Use this when:
- the rule set is stable and short
- you primarily check a small number of recurring document types

Steps:
1) Normalize target doc -> text (`docs/processed/<doc>.txt`)
2) For each rule in `rules/*.yaml`, run:
   - exact/regex search for required elements
   - simple structural checks (headings, presence of clauses)
3) Produce report with:
   - PASS/FAIL/UNKNOWN
   - snippet evidence from the target doc

Limits:
- weak for long/complex legal sources
- harder to cite the *exact* basis in source regulations
