# Compliance Agent — Architecture (AI‑readable)

Status: **active / evolving**

This document is the canonical overview of the `compliance-agent/` system: folder layout, end‑to‑end pipeline, file formats, invariants, and operational practices.

---

## 0) Goals & Non‑negotiables

### Primary goals
1) Extract DOCX structure deterministically from OOXML, preserving **exact paragraph order** used by the annotator.
2) Evaluate the document against **NIS2‑CZ** and **GDPR** rule sets with **citation‑grounded** findings.
3) Produce:
   - machine‑auditable findings YAML
   - Word document annotated with comments anchored to the correct paragraphs

### Non‑negotiables
- **No hallucinated citations**: every `quote` must be a verbatim substring of the referenced paragraph.
- **Deterministic indexing** end‑to‑end:
  - extraction uses XPath: `.//w:body//w:p`
  - annotation renderer anchors to the same paragraph stream
- **Local‑first, auditable**: rules-as-code, outputs preserved.
- **Missing required content ⇒ FAIL** (policy): if required referenced inputs are missing, mark impacted items `FAIL` and populate `missing_inputs`.
- **Do not review TOC / navigation text**.

---

## 1) Repository layout

Top-level folder: `compliance-agent/`

### Core folders
- `docs/inbox/` — input documents to review (`*.docx`)
- `docs/processed/` — extracted OOXML paragraph stream (`*.yaml`)
- `rules/` — rulesets:
  - `rules/nis2-cz/nis2-cz.rules.yaml`
  - `rules/gdpr/gdpr.rules.yaml`
- `prompts/` — evaluator system prompts
  - `prompts/evaluator_nis2cz_system_prompt.md`
  - `prompts/evaluator_gdpr_system_prompt.md`
- `scripts/` — pipeline code
- `outputs/` — evaluation results + intermediate artifacts

### Key documents
- `README.md` — scaffold overview
- `README_docx_pilot.md` — basic DOCX annotate workflow
- `PROCESS.md` — ruleset build process notes (GDPR oriented)
- `LOCKING.md` — operational locking conventions (if used by cron)

---

## 2) Data model (files & schemas)

### 2.1 Extracted document: `docs/processed/<doc>.yaml`
Produced by: `scripts/docx_extract_structured.py`

Key fields:
- `paragraphs[]` — list of paragraph objects in **OOXML order**
  - `paragraph_index` (int): index in `.//w:body//w:p`
  - `text` (str)
  - `style` (str|None): resolved style name (if available)
  - `is_heading` (bool)
  - `heading_level` (int|None)
  - `section_path` (list[str]): heading stack above paragraph
  - `clause_number` (str|None)
  - `clause_title` (str|None)
- `definitions` — best effort term → definition mapping with source paragraph_index

### 2.2 Evaluation output (per framework)
Produced by: `scripts/evaluate_docx_llm.py`

Files:
- `outputs/<outprefix>.nis2.eval.yaml`
- `outputs/<outprefix>.gdpr.eval.yaml`

Schema (core):
- `findings[]` with:
  - `rule_id`
  - `checklist_item_id`
  - `status`: `PASS|PARTIAL|FAIL|UNKNOWN`
  - `evidence[]`: `[{paragraph_index, quote}]`
  - `missing_inputs[]`
  - `notes`
  - `remediation` (optional)
- `annotations[]` (generated from findings):
  - `paragraph_index`
  - `text` (comment text)
  - `rule_id`, `checklist_item_id`, `status`, `regulation`, `missing_inputs`

### 2.3 Merged annotations
Produced by: `scripts/merge_annotations.py`

- `outputs/<outprefix>.annotations.yaml`

### 2.4 Sanitized / anchored annotations
Produced by: `scripts/sanitize_annotations.py`

- `outputs/<outprefix>.annotations.sanitized.yaml`

Adds `meta.sanitized` counters (reanchoring, exclusions, dedup).

### 2.5 Final annotated document
Produced by: `scripts/nis2cz_docx_annotate.py`

- `outputs/<outprefix>.commented.docx`

---

## 3) End‑to‑end pipeline

Main entrypoint:
- `scripts/evaluate_docx_llm.py`

### Step A — Extract (OOXML)
- Script: `scripts/docx_extract_structured.py`
- Invariant: paragraph stream order matches annotator order: `.//w:body//w:p`

**Important**: do NOT use python-docx for indexing; it can drop/merge paragraphs and causes anchor drift.

### Step B — Retrieval / context selection (no embeddings)
Implemented in `evaluate_docx_llm.py`:
- `retrieve_candidate_indices()`

Strategy:
1) Clause-span selection based on matching headings.
2) One-hop reference expansion:
   - `Clause/Section X.Y`
   - `Schedule N.N`
   - `Annex X`
3) Fallback keyword hits.

Hard filters:
- exclude `Title`, `Subtitle`, `TOC*` styles
- exclude TOC-like dot-leader paragraphs (heuristic)

### Step C — LLM evaluation (batched)
- Orchestrator: `evaluate_docx_llm.py`
- Transport: `OpenClawCronClient` (cron isolated runs)

Batching:
- checklist items evaluated in batches (`--batch-size`)

Fallback chain:
- `call_regulus()` tries models in order.
- Cooldown handling: per-model wait timeout (Anthropic 5 min) triggers fallback.

### Step D — Citation validation + retry
- `scripts/citation_validate.py` validates:
  - each quote is verbatim in the paragraph text
  - `FAIL/PARTIAL` without evidence must include `missing_inputs`

If validation fails:
- re-ask the model with explicit validation errors (retry path in `evaluate_docx_llm.py`).

### Step E — Findings → annotations
- `findings_to_annotations()` builds DOCX comment text.

Comment header format:
- `[NIS2-CZ][<rule_id>][<checklist_item_id>][<status>] REF: <CZ citations> ...`

Legal references:
- For NIS2, prefer `CZ-*` citations (Act/Decree). Avoid Directive references.

### Step F — Merge, sanitize, re-anchor
- `merge_annotations.py` merges GDPR+NIS2 or single-framework.
- `sanitize_annotations.py`:
  - excludes TOC/title/navigation
  - re-anchors by `missing_inputs` (schedule/annex refs)
  - optionally anchors PASS/PARTIAL/FAIL to headings (if heading metadata exists)
  - deduplicates by rule/checklist/status/missing_inputs/text
    - duplicates can be converted to “reference comments” pointing to the primary paragraph

### Step G — Render Word comments
- `nis2cz_docx_annotate.py` injects comments into the DOCX at the anchor paragraph indices.

---

## 4) Operational behavior

### 4.1 Checkpointing / resume
To avoid losing work on long runs:
- after each batch, a partial checkpoint is written:
  - `<outprefix>.nis2.eval.partial.yaml`
  - `<outprefix>.gdpr.eval.partial.yaml`
- on restart, already completed `(rule_id, checklist_item_id)` are skipped.

Cleanup policy:
- partial checkpoints are deleted **only after** the final `*.eval.yaml` is written.

### 4.2 Common failure modes
- **Misplaced comments / “random” anchors**
  - root cause: extractor mismatch (python-docx) vs annotator (OOXML)
  - mitigation: always use `docx_extract_structured.py`
- **Comments appear in TOC**
  - root cause: TOC paragraphs not styled `TOC*`
  - mitigation: TOC-like heuristic exclusion (dot leaders + page number)
- **Cooldown hangs**
  - root cause: provider waits without throwing error
  - mitigation: per-model wait timeout triggers fallback

---

## 5) How to run

### NIS2 only
```bash
.venv/bin/python scripts/evaluate_docx_llm.py \
  --docx docs/inbox/<doc>.docx \
  --profile /tmp/profile_run.yaml \
  --outprefix outputs/<name> \
  --framework nis2 \
  --model anthropic/claude-sonnet-4-6
```

### Choose GPT as primary (avoid Anthropic cooldown)
```bash
.venv/bin/python scripts/evaluate_docx_llm.py \
  --docx docs/inbox/<doc>.docx \
  --profile /tmp/profile_run.yaml \
  --outprefix outputs/<name> \
  --framework nis2 \
  --model openai-codex/gpt-5.2 \
  --model-fallback anthropic/claude-sonnet-4-6
```

---

## 6) Notes / TODOs

- Improve heading detection for documents with custom styles (non-Heading1/2).
- Consider enforcing “definitions cannot be evidence” for non-definition checklist items.
- Consider stronger dedup: group similar issues across items (beyond strict text equality).
