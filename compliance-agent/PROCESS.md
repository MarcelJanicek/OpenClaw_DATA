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
1) **Pick a GDPR slice** (e.g., Art. 5–6, Art. 12–14, security, breaches, DPA, international transfers)
2) I propose rules in `rules/gdpr/gdpr.rules.yaml` with:
   - stable IDs
   - acceptance criteria
   - evidence hints
   - severity
3) You review and approve/adjust (we keep diffs small)
4) We add automated checks where feasible (presence/section checks)

## Definition of “complete”
A ruleset is "complete" when:
- all GDPR obligations relevant to typical SaaS/AI products are represented
- rules are grouped by lifecycle: collection -> processing -> storage -> sharing -> rights -> incident response -> governance
- each rule has at least one suggested evidence artifact
- unclear items are explicitly flagged as needing human/legal interpretation

## Output expectations
- Human reports initially (markdown)
- Later: add JSON output + issue list integration if you want
