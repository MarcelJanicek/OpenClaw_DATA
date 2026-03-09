# GDPR ruleset build process (step-by-step)

Goal: build a **thorough, reviewable** GDPR ruleset for an AI compliance agent.

## Core design choices
- **Rules (YAML) are canonical** for checks.
- **Sources (EUR-Lex text) support citations** and interpretation.
- Each rule must be:
  - scoped (who/what it applies to)
  - testable (what evidence would satisfy it)
  - actionable (remediation)
  - citeable (article/recital)

## Iteration loop
1) **Pick a GDPR slice** (small milestone)
2) Add/update rules in the appropriate **part file** under `rules/gdpr/parts/`.
3) Update `rules/gdpr/gdpr.index.yaml` if a new part file is added.
4) Run merge script to regenerate the single-file ruleset:
   - `python3 scripts/gdpr_merge.py`
5) Commit and push.

## Definition of “complete”
A ruleset is "complete" when:
- all GDPR obligations relevant to typical SaaS/AI products are represented
- rules are grouped by lifecycle: collection -> processing -> storage -> sharing -> rights -> incident response -> governance
- each rule has at least one suggested evidence artifact
- unclear items are explicitly flagged as needing human/legal interpretation

## Output expectations
- Human reports initially (markdown)
- Later: add JSON output + issue list integration if you want
