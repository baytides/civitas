# Data Sources

Detailed documentation of data sources for Project Civitas.

## Supreme Court

### Official Sources

#### 1. Library of Congress - United States Reports
- **URL:** https://www.loc.gov/collections/united-states-reports/
- **Coverage:** Complete historical archive of bound Supreme Court decisions
- **Format:** PDF volumes, searchable
- **Access:** Public, free
- **Notes:** Official published opinions after they're finalized

#### 2. supremecourt.gov - Slip Opinions
- **URL Pattern:** `https://www.supremecourt.gov/opinions/slipopinion/{term}`
- **Available Terms:** 18-25 (October 2018 - present)
- **Format:** PDF files linked from HTML pages
- **Access:** Public, free
- **Notes:** Recent decisions before bound into US Reports
- **Update Frequency:** As decisions are issued

**Term URLs:**
- https://www.supremecourt.gov/opinions/slipopinion/25 (2025 term)
- https://www.supremecourt.gov/opinions/slipopinion/24 (2024 term)
- https://www.supremecourt.gov/opinions/slipopinion/23 (2023 term)
- https://www.supremecourt.gov/opinions/slipopinion/22 (2022 term)
- https://www.supremecourt.gov/opinions/slipopinion/21 (2021 term)
- https://www.supremecourt.gov/opinions/slipopinion/20 (2020 term)
- https://www.supremecourt.gov/opinions/slipopinion/19 (2019 term)
- https://www.supremecourt.gov/opinions/slipopinion/18 (2018 term)

#### 3. supremecourt.gov - US Reports Archive
- **URL:** https://www.supremecourt.gov/opinions/USReports.aspx
- **Coverage:** Historical bound volumes
- **Format:** PDF
- **Access:** Public, free

#### 4. Dates of Decisions
- **URL:** https://www.supremecourt.gov/opinions/datesofdecisions.pdf
- **Format:** PDF calendar
- **Use:** Reference for when decisions were issued

### Data to Extract

For each case:
- Citation (e.g., "598 U.S. 651")
- Case name (e.g., "Sackett v. EPA")
- Docket number
- Decision date
- Vote breakdown (e.g., 5-4)
- Opinion author
- Concurrences (author, joined by)
- Dissents (author, joined by)
- Full text (majority, concurrence, dissent)
- Holding/summary
- Laws/statutes referenced
- Prior cases cited

---

## Congress

### Congress.gov API

- **Documentation:** https://github.com/LibraryOfCongress/api.congress.gov
- **Base URL:** `https://api.congress.gov/v3`
- **Authentication:** API key required (free)
- **Rate Limits:** 5,000 requests/day
- **Format:** JSON

#### Key Endpoints

| Endpoint | Description |
|----------|-------------|
| `/bill` | Bills and resolutions |
| `/law` | Enacted public and private laws |
| `/member` | Members of Congress |
| `/committee` | Congressional committees |
| `/nomination` | Presidential nominations |
| `/treaty` | Treaties |

#### Enacted Laws Search
- **URL:** https://www.congress.gov/search?q=%7B%22source%22%3A%22legislation%22%2C%22bill-status%22%3A%22law%22%7D
- **Filter:** `bill-status: law`
- **Pagination:** Up to 250 per page

### Data to Extract

For each law:
- Public Law number (e.g., "P.L. 117-58")
- Bill origin (e.g., "H.R. 3684")
- Short title
- Full text
- Enacted date
- Sponsors/cosponsors
- Committee(s)
- Vote records (House and Senate)
- Related bills
- Amendments
- Subjects/topics
- CRS summaries

---

## Secondary Sources (Future)

### CourtListener (Free Law Project)
- **URL:** https://www.courtlistener.com/
- **API:** https://www.courtlistener.com/api/
- **Coverage:** Federal and state courts
- **Notes:** Good for cross-referencing, has citation network

### Justia
- **URL:** https://supreme.justia.com/
- **Notes:** Free case law, good for verification

### Google Scholar
- **URL:** https://scholar.google.com/
- **Notes:** Case law search, citation tracking

---

## Data Relationships

```
┌─────────────┐         ┌─────────────┐
│   SCOTUS    │         │  CONGRESS   │
│   CASE      │         │    LAW      │
└──────┬──────┘         └──────┬──────┘
       │                       │
       │    ┌─────────────┐    │
       ├───►│   CITES     │◄───┤
       │    └─────────────┘    │
       │                       │
       │    ┌─────────────┐    │
       └───►│  INTERPRETS │◄───┘
            │  / STRIKES  │
            └─────────────┘
```

Key relationships to track:
1. **Case cites Law** - Court references specific statute
2. **Case upholds Law** - Court finds law constitutional
3. **Case strikes Law** - Court finds law unconstitutional
4. **Case interprets Law** - Court clarifies law's meaning
5. **Case cites Case** - Precedent chain
6. **Law amends Law** - Legislative history
