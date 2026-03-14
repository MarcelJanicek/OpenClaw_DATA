# Evaluation result schema (pilot)

Evaluator returns YAML with:
- `result.status`: questions|completed
- `questions[]`: interactive questions to resolve applicability
- `findings[]`: per rule/checklist item status + evidence
- `annotations[]`: paragraph-level comments for commented DOCX
- `summary`: totals + missing inputs

This schema is implemented by the framework-specific prompts:
- `prompts/evaluator_gdpr_system_prompt.md`
- `prompts/evaluator_nis2cz_system_prompt.md`

Consumed by:
- `scripts/evaluate_docx_llm.py` (main runner — orchestrates evaluation end-to-end)
- `scripts/evaluate_docx.py` (bundle builder — produces candidate indices for external evaluator)
- `scripts/nis2cz_docx_annotate.py` (renderer — injects comments into DOCX)
