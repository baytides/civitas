# Project Civitas

Civic empowerment platform for referencing Supreme Court rulings and enacted legislation to support political strategy, checks on power, and legislative drafting.

## Vision

Democratize access to legal and legislative intelligence - giving campaigns and citizens the same analytical capabilities that well-funded lobbying firms have.

### Core Purposes

- **Prevent abuse** - Reference precedents to identify and challenge governmental overreach
- **Check power** - Understand the legal landscape for accountability
- **Draft legislation** - Learn from laws that survived judicial review
- **Inform strategy** - Support electoral, advocacy, and litigation efforts

## Data Sources

### Supreme Court

| Source | Description | Status |
|--------|-------------|--------|
| [Library of Congress - US Reports](https://www.loc.gov/collections/united-states-reports/) | Official bound volumes of Supreme Court decisions | Planned |
| [supremecourt.gov Slip Opinions](https://www.supremecourt.gov/opinions/slipopinion/25) | Recent decisions (2018-present) | Planned |
| [US Reports Archive](https://www.supremecourt.gov/opinions/USReports.aspx) | Historical bound volumes | Planned |

### Congress

| Source | Description | Status |
|--------|-------------|--------|
| [Congress.gov API](https://github.com/LibraryOfCongress/api.congress.gov) | Official API for bills, laws, votes, members | Planned |
| [Enacted Legislation](https://www.congress.gov/search?q=%7B%22source%22%3A%22legislation%22%2C%22bill-status%22%3A%22law%22%7D) | Public laws | Planned |

## Roadmap

### Phase 1: Data Ingestion
- [ ] Congress.gov API integration
- [ ] Supreme Court opinion scraper
- [ ] Citation parser (link cases <-> laws)
- [ ] Local database storage

### Phase 2: Search & Reference
- [ ] Full-text search across cases and laws
- [ ] Citation lookup
- [ ] Topic/keyword filtering
- [ ] CLI interface

### Phase 3: Analysis Layer
- [ ] Pattern detection (what makes laws survive challenges)
- [ ] Network analysis (sponsor coalitions, citing patterns)
- [ ] Timeline/trend visualization

### Phase 4: AI-Powered Features
- [ ] Natural language queries
- [ ] Draft assistance from precedents
- [ ] Legal risk assessment

## Development Approach

**Current Phase:** Private development with [Bay Tides](https://github.com/baytides) as test user for conservation advocacy use cases.

**Future:** Broader public release for campaigns and citizens.

## Project Structure

```
civitas/
├── src/
│   └── civitas/
│       ├── __init__.py
│       ├── congress/       # Congress.gov API integration
│       ├── scotus/         # Supreme Court data ingestion
│       ├── db/             # Database models and storage
│       ├── search/         # Search functionality
│       └── analysis/       # Analysis tools
├── tests/
├── data/                   # Local data storage (gitignored)
├── docs/                   # Documentation
└── scripts/                # Utility scripts
```

## Development

### Backend

- Create/activate the Python venv and install deps as needed.
- Run tests:

```
./venv/bin/python -m pytest -q
```

### Web App

```
cd web
npm ci
npm run dev
```

## Deployment (Cloudflare Pages)

This project deploys the Next.js app to Cloudflare Pages via GitHub Actions:

- Workflow: `.github/workflows/deploy.yml`
- Build: `npm run build` in `web/`
- Cache cleanup: `.next/cache` removed before deploy to avoid the 25 MiB file limit
- Deploy command: `wrangler pages deploy web/.next --project-name=civitas`

Required secrets/vars:
- `CLOUDFLARE_API_TOKEN`
- `CLOUDFLARE_ACCOUNT_ID`
- `NEXT_PUBLIC_API_URL`

## Accessibility

Target: WCAG 2.2 AA.

Implemented practices include:
- Skip link to main content
- Programmatic labels for form inputs
- Button groups with `aria-pressed` state
- Decorative icons marked `aria-hidden`
- Reduced motion support for animated UI elements

Recommended checks:
- Keyboard-only navigation and focus visibility
- Screen reader smoke test (NVDA/VoiceOver)
- Color contrast review on badge/status colors

## License

TBD

## Contributing

Currently in private development. Contribution guidelines will be added for public release.
