# When you want RAG (recommended for real regulatory work)

Add Retrieval-Augmented Generation when:
- source regulations are long (hundreds of pages)
- you need **traceable citations** to specific sections
- rules evolve and you want the agent to re-derive or validate rules

Pattern:
- Keep `rules/` as the canonical, reviewable requirements.
- Use RAG over `docs/sources/` to:
  - cite why a rule exists
  - resolve interpretation questions
  - detect updates/changes in new source docs
- Optionally use RAG over the target document to find relevant clauses faster.

Note: RAG does not replace rules; it supports them.
