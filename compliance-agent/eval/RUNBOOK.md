# RUNBOOK — Evaluating a DOCX (pilot)

## 0) Prepare inputs
- DOCX to evaluate
- `entity_profile.yaml` (if unknown, start with unknowns and answer questions)

## 1) Extract
```bash
cd /root/.openclaw/workspace/compliance-agent
.venv/bin/python scripts/nis2cz_docx_extract.py --in <doc.docx> --out docs/processed/<doc>.yaml
```

## 2) Run evaluator (LLM)
- Send to Regulus-Eval (Opus) with:
  - extracted paragraphs
  - entity_profile
  - relevant ruleset parts

## 3) If questions returned
- Answer questions and re-run evaluation.

## 4) Render commented DOCX
```bash
.venv/bin/python scripts/nis2cz_docx_annotate.py --in <doc.docx> --annotations outputs/<doc>.annotations.yaml --out outputs/<doc>.commented.docx
```

## Outputs
- `outputs/<doc>.results.yaml`
- `outputs/<doc>.annotations.yaml`
- `outputs/<doc>.commented.docx`
