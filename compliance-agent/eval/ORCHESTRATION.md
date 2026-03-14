# Orchestration: two sub-agents (GDPR + NIS2-CZ)

## Why two evaluators
- Separate applicability questions and rubrics per regulation.
- Cleaner prompts and more consistent scoring.

## Workflow

1) Extract DOCX
```bash
.venv/bin/python scripts/docx_extract_structured.py --in <doc.docx> --out docs/processed/<doc>.yaml
```

2) Run bundler (questions-first)
```bash
.venv/bin/python scripts/evaluate_docx.py --docx <doc.docx> --profile <entity_profile.yaml> --out outputs/<doc>.eval_bundle.yaml
```

- If bundle status is `questions`, answer them and re-run.

3) Run **GDPR** evaluator (Opus)
- Use `prompts/evaluator_gdpr_system_prompt.md`
- Provide extracted paragraphs + gdpr profile + GDPR ruleset
- Save output as: `outputs/<doc>.gdpr.eval.yaml`

4) Run **NIS2-CZ** evaluator (Opus)
- Use `prompts/evaluator_nis2cz_system_prompt.md`
- Provide extracted paragraphs + nis2 profile + NIS2-CZ ruleset
- Save output as: `outputs/<doc>.nis2.eval.yaml`

5) Merge annotations
```bash
python3 scripts/merge_annotations.py \
  --gdpr outputs/<doc>.gdpr.eval.yaml \
  --nis2 outputs/<doc>.nis2.eval.yaml \
  --out  outputs/<doc>.annotations.yaml
```

6) Render commented DOCX
```bash
.venv/bin/python scripts/nis2cz_docx_annotate.py --in <doc.docx> --annotations outputs/<doc>.annotations.yaml --out outputs/<doc>.commented.docx
```

## Comment format
Each comment should be prefixed:
- `[GDPR][<rule_id>][<status>] ...`
- `[NIS2-CZ][<rule_id>][<checklist_item_id>][<status>] ...`
