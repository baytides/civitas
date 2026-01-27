# Civitas Resistance Framework

## Vision

Transform Civitas from a passive data platform into an **active resistance toolkit** that:
1. Tracks Project 2025 implementation in real-time
2. Identifies legal vulnerabilities in each action
3. Recommends counter-strategies based on current political reality
4. Provides actionable guidance for citizens, attorneys, and legislators

## Three-Tier Resistance Strategy

### Tier 1: Immediate Actions (Now - November 2026)
**Tools Available:** Courts, 10th Amendment, State Governments

Actions that can be taken NOW regardless of federal political control:

#### 1.1 Legal Challenges
- **Constitutional violations** - 1st, 4th, 5th, 14th Amendment challenges
- **Administrative Procedure Act (APA)** - Challenge rules without proper notice/comment
- **Ultra vires actions** - Executive overreach beyond statutory authority
- **Equal Protection** - Discriminatory enforcement
- **Due Process** - Arbitrary/capricious agency actions

#### 1.2 State-Level Resistance (10th Amendment)
- **Sanctuary policies** - Refuse state cooperation with federal enforcement
- **State constitutional protections** - Enshrine rights at state level
- **State AG lawsuits** - Coordinate multi-state legal challenges
- **Regulatory divergence** - Maintain state standards above federal rollbacks
- **Economic leverage** - State contracts, pension fund divestment

#### 1.3 Citizen Actions
- **FOIA requests** - Document decision-making processes
- **Public comment** - Flood dockets during rulemaking
- **Whistleblower support** - Protect federal employees exposing misconduct
- **Organizing** - Build coalitions for specific issue areas

### Tier 2: Congressional Restoration (2027-2028)
**If Democrats win House/Senate majorities in November 2026**

#### 2.1 Oversight Powers
- **Subpoena authority** - Compel testimony and documents
- **Defund implementation** - Appropriations riders blocking enforcement
- **Confirmation blocking** - Prevent extremist appointments
- **Inspector General investigations** - Expose waste, fraud, abuse

#### 2.2 Legislative Countermeasures
- **Statutory reversal** - Pass laws undoing executive actions
- **Codification** - Enshrine protections in statute (Roe, voting rights, etc.)
- **Agency restructuring** - Prevent Schedule F, protect civil service
- **Judicial reform** - Court expansion, jurisdiction stripping, ethics

#### 2.3 Messaging Platform
- **Public hearings** - Televised exposure of P2025 harms
- **Report generation** - Congressional reports documenting damage
- **Veto fights** - Force presidential vetoes on popular measures

### Tier 3: Full Restoration (2029+)
**If Democrat wins presidency in 2028**

#### 3.1 Executive Reversal
- **Day One orders** - Reverse EOs, proclamations, memos
- **Agency guidance** - Rescind harmful interpretations
- **Personnel** - Remove political appointees, restore career staff
- **Regulatory restoration** - Repropose rolled-back rules

#### 3.2 Structural Reforms
- **Inspector General independence** - Prevent future purges
- **Civil service protection** - Codify Schedule F prohibition
- **Pardon limitations** - Self-dealing restrictions
- **Emergency powers reform** - Prevent abuse of national emergencies

#### 3.3 Constitutional Amendments (Long-term)
- **Voting rights** - Automatic registration, election day holiday
- **Judicial term limits** - 18-year SCOTUS terms
- **Anti-corruption** - Emoluments enforcement
- **Democratic representation** - DC/PR statehood, Electoral College reform

---

## Data Model: Tracking Implementation & Resistance

### P2025 Objective
```
- id
- mandate_section (page range in PDF)
- agency
- category (environment, immigration, health, etc.)
- objective_text (what they want to do)
- rationale (their stated justification)
- status: not_started | in_progress | completed | blocked | reversed
- implementation_date
- evidence_urls[]
- related_eos[] (Executive Order IDs)
- related_rules[] (Federal Register document IDs)
- court_challenges[] (Case IDs)
```

### Legal Challenge
```
- id
- p2025_objective_id
- challenge_type: constitutional | apa | ultra_vires | equal_protection | due_process
- legal_basis (specific clause/statute)
- court_level: district | circuit | scotus
- case_citation
- status: filed | pending | won | lost | appealed
- outcome_summary
- precedent_citations[]
- lead_plaintiffs
- representing_orgs
```

### State Resistance Action
```
- id
- state_code
- action_type: sanctuary | lawsuit | legislation | executive_order | constitutional_amendment
- p2025_objectives_countered[]
- status: proposed | enacted | enjoined | effective
- legal_citation
- text_summary
- model_legislation_url (for replication)
```

### Resistance Recommendation
```
- id
- p2025_objective_id
- tier: 1_immediate | 2_congressional | 3_presidential
- action_type
- description
- prerequisites (what must happen first)
- likelihood_of_success: high | medium | low
- resources_required
- model_language (draft text)
- successful_examples[]
```

---

## Website Structure

### Homepage
- **P2025 Progress Dashboard** - Visual tracker showing implementation status
- **Resistance Scorecard** - Wins/losses in courts, states
- **Action Alerts** - Time-sensitive opportunities
- **Search** - Find specific policies, cases, or actions

### By Category
- Environment & Climate
- Immigration & Border
- Healthcare & Reproductive Rights
- LGBTQ+ Rights
- Education
- Labor & Workers
- Voting & Democracy
- Civil Rights
- Economic Policy
- Foreign Policy
- Government Structure

### By Action Type
- Court Challenges (filterable by status, jurisdiction)
- State Actions (map view)
- Federal Register Actions (rules, notices)
- Executive Orders
- Congressional Activity

### Resources
- **Legal Toolkit** - Model complaints, FOIA templates, amicus briefs
- **State Advocacy** - Model legislation by category
- **Citizen Guide** - How to comment, organize, support
- **Attorney Network** - Pro bono coordination
- **Data API** - For researchers and journalists

### About
- Methodology
- Data Sources (with Civitas credits)
- Team
- Donate/Support

---

## Technical Implementation

### Data Pipeline
1. **Ingest P2025 PDF** → Extract objectives by agency/category
2. **Monitor Federal Register** → Match new rules/notices to objectives
3. **Track Court Cases** → Link challenges to specific objectives
4. **Scrape State Legislatures** → Identify resistance actions
5. **AI Matching** → Use Llama to classify new actions against P2025 goals

### Resistance Scoring Algorithm

For each P2025 objective, calculate:
```
threat_level =
  (implementation_status * 0.4) +
  (constitutional_vulnerability * -0.3) +
  (state_resistance_coverage * -0.2) +
  (active_litigation_strength * -0.1)

Where:
  implementation_status: 0 (not started) to 1 (completed)
  constitutional_vulnerability: 0 (solid) to 1 (clearly unconstitutional)
  state_resistance_coverage: 0 (no states) to 1 (all states)
  active_litigation_strength: 0 (no cases) to 1 (strong precedent)
```

### API Endpoints
```
GET /api/objectives - List all P2025 objectives
GET /api/objectives/{id} - Single objective with all linked data
GET /api/objectives/by-agency/{agency} - Filter by agency
GET /api/objectives/by-category/{category} - Filter by category
GET /api/challenges - All legal challenges
GET /api/state-actions - All state resistance actions
GET /api/recommendations/{objective_id} - Resistance recommendations
POST /api/track - Report new implementation evidence (moderated)
```

---

## Data Sources Integration

### Already in Civitas
- Federal Register (EOs, rules, notices)
- Congress.gov (legislation)
- SCOTUS opinions
- Court Listener (federal courts)
- US Code
- State constitutions

### To Add
- Project2025.observer (via scraping/API)
- State legislature trackers (50 states)
- PACER/RECAP (federal court filings)
- Ballotpedia (state ballot measures)
- State AG press releases
- News API (implementation reporting)

---

## Implementation Priority

### Phase 1: Foundation (Current Sprint)
1. Complete P2025 PDF parsing with detailed extraction
2. Build objective-to-action matching
3. Create legal challenge database schema
4. Deploy basic tracking dashboard

### Phase 2: Intelligence (Next Sprint)
1. AI-powered matching of new Federal Register docs to P2025
2. Automated court case tracking
3. State action aggregation
4. Resistance recommendation engine

### Phase 3: Action Platform (Following Sprint)
1. Public website with search and filtering
2. Alert system for time-sensitive actions
3. Legal toolkit resources
4. API for researchers/journalists

### Phase 4: Community (Future)
1. User accounts for tracking issues
2. Comment/discussion on objectives
3. Volunteer coordination
4. Attorney matching for pro bono work
