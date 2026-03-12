# RUNBOOK — Evaluating a DOCX (pilot)

## 0) Prepare inputs
- DOCX to evaluate
- `entity_profile.yaml` (if unknown, start with unknowns and answer questions)

## 1) Extract
```bash
cd /root/.openclaw/workspace/compliance-agent
.venv/bin/python scripts/nis2cz_docx_extract.py --in <doc.docx> --out docs/processed/<doc>.yaml
```

## 2) Run evaluator (LLM, Opus)
This runs end-to-end (GDPR + NIS2-CZ) and produces a commented DOCX.

```bash
.venv/bin/python scripts/evaluate_docx_llm.py \
  --docx <doc.docx> \
  --profile <entity_profile.yaml> \
  --outprefix outputs/<doc>
```

## 3) If questions returned
If `outputs/<doc>.questions.yaml` is produced, answer those questions by updating the profile YAML (or provide answers in chat), then rerun.

## Outputs
- `outputs/<doc>.results.yaml`
- `outputs/<doc>.annotations.yaml`
- `outputs/<doc>.commented.docx`
