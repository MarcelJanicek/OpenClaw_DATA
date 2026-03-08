# Compliance sub-agent (scaffold)

This folder is a starter scaffold for a compliance-focused sub-agent that:
- maintains a **canonical rule set** (structured)
- ingests **source legal documents** (PDF/DOCX/etc.)
- runs **compliance checks** against arbitrary documents you share
- produces outputs with **citations** back to sources/rules

## Folder layout
- `docs/inbox/` — drop new documents to be checked
- `docs/sources/` — legal/regulatory source docs (laws, policies, contracts)
- `docs/processed/` — normalized text extracts (generated)
- `rules/` — structured rules (YAML/JSON)
- `prompts/` — system prompts for the compliance agent and helper roles
- `outputs/` — compliance reports
- `scripts/` — ingestion + checking scripts

## Recommended workflow
1) Put source material in `docs/sources/`
2) Run ingestion to create text extracts + (optional) embeddings index
3) Write/curate rules in `rules/` (or have the agent propose them, then you approve)
4) Put a document to check in `docs/inbox/`
5) Run check to generate a report in `outputs/`

This scaffold is tool-agnostic: you can implement as pure LLM + rules, or add RAG for retrieval/citations.
