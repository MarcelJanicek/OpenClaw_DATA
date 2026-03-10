# NIS2 — Czech Republic pilot ruleset

This ruleset targets **Czech Republic implementation** of the EU NIS2 framework.

## Scope (pilot)
Core only:
- **Zákon č. 264/2025 Sb., o kybernetické bezpečnosti**
- Implementing decrees listed on NÚKIB portal page (core KB package):
  - Vyhláška č. 408/2025 Sb. (regulované služby)
  - Vyhláška č. 409/2025 Sb. (vyšší povinnosti)
  - Vyhláška č. 410/2025 Sb. (nižší povinnosti)
  - Vyhláška č. 334/2025 Sb. (Portál NÚKIB + úkony)

NIS2 Directive itself is used as a **reference mapping layer**, but compliance checks must follow Czech law + decrees.

## Sources (official)
- NÚKIB portal: https://portal.nukib.gov.cz/informacni-servis/legislativa/aktualne-platne-predpisy-v-kyberneticke-bezpecnosti
- e‑Sbírka / Open data (ELI-based): typically via `opendata.eselpoint.cz/esel-esb/eli/...`
- NIS2 directive (CZ PDF): https://eur-lex.europa.eu/legal-content/CS/TXT/PDF/?uri=CELEX:32022L2555&from=CS

## Design choices
- Rules are canonical YAML.
- Conditions depend on `entity_profile` (sector, size, essential/important, regulated service type, higher/lower regime).
- Each rule must include `evidence_hints.required` for audit-ready checks.
