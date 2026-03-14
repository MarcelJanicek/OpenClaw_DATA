# DOCX pilot: extract + commented DOCX output

This pilot supports **DOCX only**.

## Setup
A local venv is located at:
- `compliance-agent/.venv/`

## Extract
```bash
cd /root/.openclaw/workspace/compliance-agent
.venv/bin/python scripts/docx_extract_structured.py --in <input.docx> --out docs/processed/<name>.yaml
```

## Annotate (add Word comments)
Create `annotations.yaml`:
```yaml
annotations:
  - paragraph_index: 12
    author: ComplianceAgent
    text: "Compliance note..."
```

Run:
```bash
.venv/bin/python scripts/nis2cz_docx_annotate.py --in <input.docx> --annotations annotations.yaml --out outputs/<name>.commented.docx
```

## Next step
Hook `nis2cz_local_run.py` + a future LLM-based checker to generate `annotations.yaml` automatically.
