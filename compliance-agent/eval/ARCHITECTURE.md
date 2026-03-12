# Evaluation pipeline architecture (DOCX → commented DOCX)

## Goal
Given a DOCX and an entity profile, evaluate against GDPR + NIS2-CZ rulesets and return:
- a structured results file
- a commented DOCX with paragraph-anchored comments

No RAG for pilot.

---

## Components

### 1) Extractor
- Input: `.docx`
- Output: `docs/processed/<doc>.yaml`
  - `paragraph_index`, `text`, `style`

Implemented:
- `scripts/nis2cz_docx_extract.py`

### 2) Ruleset loader
- Loads merged rules YAML or index+parts.
- Applies entity_profile filters (scope: doc_type, duty_regime, entity_class, etc.).

### 3) Evidence retriever (no RAG)
For each checklist item:
- Use `keywords_cs/keywords_en` to select candidate paragraphs.
- Expand window around headings/nearby paragraphs.
- If no hits, run fallback scan (limited) and mark UNKNOWN if still not found.

### 4) LLM evaluator (Opus)
- Input: checklist item rubric + candidate paragraphs (with indices)
- Output: status + evidence + remediation clause text

### 5) Renderer
- Convert evaluator output → `annotations.yaml`.
- Create commented DOCX:
  - `scripts/nis2cz_docx_annotate.py`

---

## Execution modes

### On-demand (recommended)
- Triggered when user uploads a DOCX.
- If entity_profile is missing, evaluator returns `questions` only.
- After user answers, run full evaluation.

### Inbox-worker (optional)
- Cron watches `docs/inbox/` and processes any new docs.
- Not required for pilot.

---

## Files
- Prompt: `prompts/evaluator_system_prompt.md`
- Results schema: YAML returned by evaluator
- Outputs:
  - `outputs/<doc>.results.yaml`
  - `outputs/<doc>.annotations.yaml`
  - `outputs/<doc>.commented.docx`
