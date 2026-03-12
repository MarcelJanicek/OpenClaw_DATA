# Evaluation result schema (pilot)

Evaluator returns YAML with:
- `result.status`: questions|completed
- `questions[]`: interactive questions to resolve applicability
- `findings[]`: per rule/checklist item status + evidence
- `annotations[]`: paragraph-level comments for commented DOCX
- `summary`: totals + missing inputs

This schema is described in `prompts/evaluator_system_prompt.md` and is used by:
- `scripts/evaluate_docx.py` (runner)
- `scripts/nis2cz_docx_annotate.py` (renderer)
