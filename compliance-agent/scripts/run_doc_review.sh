#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 3 ]]; then
  echo "Usage: $0 <docx_path> <entity_profile_yaml> <outprefix>" >&2
  echo "Example: $0 docs/inbox/tsa.docx eval/entity_profile.min.yaml outputs/tsa" >&2
  exit 2
fi

DOCX="$1"
PROFILE="$2"
OUTPREFIX="$3"  # e.g., outputs/tsa1
MODEL_OPUS="anthropic/claude-opus-4-6"

BASE_DIR="${COMPLIANCE_AGENT_DIR:-/root/.openclaw/workspace/compliance-agent}"
cd "$BASE_DIR"

# 1) Extract (OOXML-based; preserves exact paragraph order used by annotator)
EXTRACTED="docs/processed/$(basename "${DOCX%.*}").yaml"
.venv/bin/python scripts/docx_extract_structured.py --in "$DOCX" --out "$EXTRACTED"

# 2) Build job message (the isolated agent will read files directly)
MSG_FILE=$(mktemp)
cat > "$MSG_FILE" <<EOF
You are running an on-demand DOCX compliance evaluation job.

Inputs (paths are relative to $BASE_DIR):
- DOCX: $DOCX
- Extracted paragraphs: $EXTRACTED
- Entity profile: $PROFILE
- Rulesets:
  - GDPR merged: rules/gdpr/gdpr.rules.yaml
  - NIS2-CZ merged: rules/nis2-cz/nis2-cz.rules.yaml
- Prompts:
  - GDPR evaluator: prompts/evaluator_gdpr_system_prompt.md
  - NIS2-CZ evaluator: prompts/evaluator_nis2cz_system_prompt.md

Task:
A) If entity profile is missing required fields, write ${OUTPREFIX}.questions.yaml with questions and STOP.
B) Otherwise:
  1) Run GDPR evaluation and write: ${OUTPREFIX}.gdpr.eval.yaml
  2) Run NIS2-CZ evaluation and write: ${OUTPREFIX}.nis2.eval.yaml
  3) Merge annotations:
     python3 scripts/merge_annotations.py --gdpr ${OUTPREFIX}.gdpr.eval.yaml --nis2 ${OUTPREFIX}.nis2.eval.yaml --out ${OUTPREFIX}.annotations.yaml
  4) Render commented DOCX:
     .venv/bin/python scripts/nis2cz_docx_annotate.py --in $DOCX --annotations ${OUTPREFIX}.annotations.yaml --out ${OUTPREFIX}.commented.docx

Rules:
- Do not guess. Missing schedules/annexes => UNKNOWN + list missing inputs.
- Each finding must cite paragraph_index + quote.
- Comments MUST be prefixed:
  - [GDPR][rule_id][status]
  - [NIS2-CZ][rule_id][checklist_item_id][status]
EOF

# JSON-escape message
ESCAPED_MSG=$(python3 - <<'PY'
import json,sys
print(json.dumps(open(sys.argv[1]).read()))
PY
"$MSG_FILE")

# 3) Create a one-shot job that deletes itself after run
JOB_JSON=$(cd /opt/openclaw && pnpm -s openclaw cron add --json \
  --name "DOCX review job (one-shot)" \
  --at "+1s" \
  --delete-after-run \
  --session isolated \
  --no-deliver \
  --model "$MODEL_OPUS" \
  --thinking low \
  --timeout-seconds 2400 \
  --message "${ESCAPED_MSG:1:-1}")

JOB_ID=$(python3 - <<'PY'
import json,sys
j=json.load(sys.stdin)
print(j.get('id') or j.get('jobId'))
PY
<<<"$JOB_JSON")

# 4) Run now (extend gateway timeout)
cd /opt/openclaw
pnpm -s openclaw cron run "$JOB_ID" --timeout 300000

echo "Started job: $JOB_ID"
echo "Outputs expected: ${OUTPREFIX}.*"
