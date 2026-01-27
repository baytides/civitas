# Civitas Credits

Civitas integrates data and tools from numerous sources. We gratefully acknowledge their contributions to civic transparency.

## Government Data Sources (Public Domain)

All government data sources listed below are in the public domain as works of the United States Government.

### Federal

| Source | Purpose | URL |
|--------|---------|-----|
| **Congress.gov API** | Federal legislation, bills, laws, votes | https://api.congress.gov/ |
| **Federal Register** | Executive orders, regulations, agency rules | https://www.federalregister.gov/developers |
| **Supreme Court** | Slip opinions | https://www.supremecourt.gov/opinions/ |
| **House Office of Law Revision Counsel** | US Code | https://uscode.house.gov/ |
| **Government Publishing Office** | US Constitution | https://www.govinfo.gov/ |

### State

| Source | Purpose | License |
|--------|---------|---------|
| **California Legislature** | CA legislation, bills, laws | Public Domain |
| **State Archives/Legislatures** | State constitutions | Public Domain |

## Open Source Tools

### Free Law Project (BSD-2-Clause)

We gratefully acknowledge the Free Law Project for their exceptional open-source legal tools:

| Tool | Purpose | License | URL |
|------|---------|---------|-----|
| **eyecite** | Legal citation extraction | BSD-2-Clause | https://github.com/freelawproject/eyecite |
| **courts-db** | Database of all US courts | BSD-2-Clause | https://github.com/freelawproject/courts-db |
| **juriscraper** | Court website scraping | BSD-2-Clause | https://github.com/freelawproject/juriscraper |
| **Court Listener API** | Federal court opinions | AGPL-3.0 | https://www.courtlistener.com/api/ |

### @unitedstates Project (Public Domain)

| Tool | Purpose | URL |
|------|---------|-----|
| **congress-legislators** | All Congress members 1789-present | https://github.com/unitedstates/congress-legislators |
| **congress** | Bill/vote data collectors | https://github.com/unitedstates/congress |
| **congressional-record** | Floor debates parser | https://github.com/unitedstates/congressional-record |
| **districts** | Legislative district GeoJSON | https://github.com/unitedstates/districts |
| **python-us** | US state metadata | https://github.com/unitedstates/python-us |
| **citation** | Legal citation extraction | https://github.com/unitedstates/citation |
| **contact-congress** | Contact form reverse engineering | https://github.com/unitedstates/contact-congress |

### Open States Project (GPL-3.0 / CC0-1.0)

State-level legislative data for all 50 states, D.C., and Puerto Rico:

| Tool | Purpose | License | URL |
|------|---------|---------|-----|
| **openstates-scrapers** | Legislative scrapers for all states | GPL-3.0 | https://github.com/openstates/openstates-scrapers |
| **people** | State legislators & governors data | CC0-1.0 | https://github.com/openstates/people |
| **openstates-core** | Data model and scraper backend | GPL-3.0 | https://github.com/openstates/openstates-core |
| **api-v3** | Open States API v3 | MIT | https://github.com/openstates/api-v3 |
| **jurisdictions** | Jurisdiction metadata | CC0-1.0 | https://github.com/openstates/jurisdictions |
| **openstates-geo** | Legislative district map tiles | MIT | https://github.com/openstates/openstates-geo |

### Open Civic Data (BSD-3-Clause)

Standards and tools for government data:

| Tool | Purpose | License | URL |
|------|---------|---------|-----|
| **ocd-division-ids** | Standardized civic division IDs | BSD-3 | https://github.com/opencivicdata/ocd-division-ids |
| **pupa** | Legislative scraping framework | BSD-3 | https://github.com/opencivicdata/pupa |
| **python-opencivicdata** | Python utilities for OCD | BSD-3 | https://github.com/opencivicdata/python-opencivicdata |
| **scrapers-us-municipal** | US municipal scrapers | MIT | https://github.com/opencivicdata/scrapers-us-municipal |
| **python-legistar-scraper** | Legistar website scraper | BSD-3 | https://github.com/opencivicdata/python-legistar-scraper |

### State-Specific Projects

| Tool | Purpose | License | URL |
|------|---------|---------|-----|
| **OpenLegislation** | NY State Senate API | AGPL-3.0 | https://github.com/nysenate/OpenLegislation |
| **calobbysearch** | CA lobbying data API | MIT | https://github.com/middletond/calobbysearch |
| **legislature-tracker** | Open States data visualization | MIT | https://github.com/MinnPost/legislature-tracker |

### Core Dependencies

| Package | Purpose | License |
|---------|---------|---------|
| **SQLAlchemy** | Database ORM | MIT |
| **Pydantic** | Data validation | MIT |
| **httpx** | HTTP client | BSD-3 |
| **Typer** | CLI framework | MIT |
| **Rich** | Terminal formatting | MIT |
| **pdfplumber** | PDF parsing | MIT |
| **BeautifulSoup4** | HTML parsing | MIT |
| **lxml** | XML/HTML processing | BSD-3 |

## AI Infrastructure

| Service | Purpose | Provider |
|---------|---------|----------|
| **Llama 3.2** | Natural language queries | Meta AI (via Ollama) |
| **Ollama** | Local LLM serving | Self-hosted on Azure |

## Cloud Infrastructure

| Service | Purpose | Provider |
|---------|---------|----------|
| **Azure Blob Storage** | Document storage | Microsoft Azure |
| **Azure VM** | Website hosting | Microsoft Azure |
| **Cloudflare** | DNS and CDN | Cloudflare |

## Project 2025

Civitas includes capabilities for tracking policy proposals from Heritage Foundation's Project 2025 "Mandate for Leadership" document against actual legislation and executive actions. This document is analyzed for transparency purposes only.

Source: https://s3.documentcloud.org/documents/24088042/project-2025s-mandate-for-leadership-the-conservative-promise.pdf

## Domain

- **Website:** https://projectcivitas.com
- **Tor Hidden Service:** ae4maw53rtbc3um3d6zbbkbxaq2wjdllss4wtupktl4su5qsgssbidid.onion

## Contact

- **Repository:** https://github.com/steven/civitas
- **Email:** steven@baytides.org

## License

Civitas is open source software. Government data is public domain. Third-party tools are used under their respective licenses as noted above.
