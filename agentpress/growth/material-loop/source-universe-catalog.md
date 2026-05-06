# AgentPress Source Universe Catalog

Generated: 2026-05-06T04:59:42Z

Purpose: list document types and where to get them for AI-unoptimized, high-demand sources agents need.

## Acquisition methods
- **sitemaps** — /sitemap.xml, /sitemap_index.xml, robots.txt Sitemap lines (best for company/docs/help centers)
- **llms.txt / ai manifests** — /llms.txt, /.well-known/ai-plugin.json, /.well-known/agentpress.json (best AI-optimized seed; also identifies gaps)
- **open APIs** — CKAN, Socrata, EDGAR, eCFR, Federal Register, CourtListener, OpenAlex, Crossref, PubMed, PatentsView (millions)
- **GitHub/GitLab repos** — docs/ folders, README, markdown, OpenAPI specs, typedoc/sphinx outputs (millions)
- **package registries** — npm, PyPI, crates.io, pkg.go.dev, Maven, RubyGems docs/readmes (millions)
- **public PDFs** — filings, laws, RFPs, research, standards, guidance PDFs (millions but needs PDF extraction)
- **RSS/changelog/status** — blogs, docs changelogs, status pages, release feeds (freshness and agent pain signals)

## Source categories

### Technical — API references / SDK refs (P0, millions)
- Why: agents implement integrations and need exact params/errors
- Where: OpenAPI specs: APIs.guru, provider /openapi.json, developer portals, GitHub repos; SDK docs sitemaps: Stripe, Twilio, Slack, Discord, Notion, Linear, Shopify, Plaid, GitHub, GitLab, Cloudflare; Package docs: npm/PyPI/RubyGems/Crates docs, typedoc/sphinx/rustdoc/go pkg pages
- AgentPress use: Wrap into llms.txt/RUN_THIS/material-manifest/proof-receipt; prefer citation-ready, task-specific slices.

### Technical — Framework docs (P0, hundreds-thousands)
- Why: agents constantly build apps and need compact recipes
- Where: React/Next/Vue/Svelte/Angular/Astro/Nuxt/Remix/TanStack docs sitemaps; Django/FastAPI/Flask/Rails/Spring/.NET/Laravel/Phoenix docs; Mobile/desktop: React Native, Expo, Android, Apple Developer, Electron, Tauri
- AgentPress use: Wrap into llms.txt/RUN_THIS/material-manifest/proof-receipt; prefer citation-ready, task-specific slices.

### Technical — Infra / DevOps docs (P0, millions)
- Why: agents debug deployments and config
- Where: Docker/Kubernetes/Terraform/Helm/Ansible/Nix docs; AWS/GCP/Azure/Cloudflare/Vercel/Netlify/Fly/Render/Railway docs; GitHub Actions/GitLab CI/CircleCI/Buildkite docs
- AgentPress use: Wrap into llms.txt/RUN_THIS/material-manifest/proof-receipt; prefer citation-ready, task-specific slices.

### Technical — Database/search/vector docs (P0, hundreds-thousands)
- Why: agents build persistence/RAG and need query/config examples
- Where: Postgres/MySQL/SQLite/MongoDB/Redis/Elasticsearch/OpenSearch docs; Prisma/Drizzle/SQLAlchemy/TypeORM/Sequelize docs; Pinecone/Qdrant/Weaviate/Chroma/Milvus/LanceDB docs
- AgentPress use: Wrap into llms.txt/RUN_THIS/material-manifest/proof-receipt; prefer citation-ready, task-specific slices.

### Technical — Error/troubleshooting docs (P0, millions)
- Why: agents waste time resolving opaque failures
- Where: Provider error docs, status docs, troubleshooting pages, GitHub issues tagged error/bug; StackOverflow canonical Q&A dumps, GitHub Discussions, release notes/changelogs; Sentry/Datadog/OpenTelemetry/Grafana/Prometheus docs
- AgentPress use: Wrap into llms.txt/RUN_THIS/material-manifest/proof-receipt; prefer citation-ready, task-specific slices.

### Technical — Security/auth docs (P0, hundreds-thousands)
- Why: agents implement auth incorrectly without compact instructions
- Where: OAuth/OIDC/SAML specs and vendor docs: Auth0, Clerk, Okta, WorkOS, Cognito, Firebase Auth, Supabase Auth; OWASP cheat sheets, NIST docs, CIS benchmarks, cloud IAM docs; Webhook signing/security docs for Stripe/GitHub/Slack/Shopify/Twilio
- AgentPress use: Wrap into llms.txt/RUN_THIS/material-manifest/proof-receipt; prefer citation-ready, task-specific slices.

### Technical — AI/agent docs (P0, hundreds-thousands)
- Why: first-user wedge: agents use docs to build agents
- Where: MCP registries/docs, OpenAI/Anthropic/Google/Groq/Mistral/Cohere docs; LangChain/LangGraph/LlamaIndex/CrewAI/AutoGen/Haystack/DSPy docs; Agent platform docs: Cline/Roo/OpenHands/Cursor/Windsurf/Replit/StackBlitz/Bolt
- AgentPress use: Wrap into llms.txt/RUN_THIS/material-manifest/proof-receipt; prefer citation-ready, task-specific slices.

### Government/Law — Statutes, regulations, administrative codes (P0, millions)
- Why: agents/legal ops need structured legal answers and compliance mapping
- Where: US: congress.gov bulk, GovInfo bulkdata, eCFR XML/API, Federal Register API, state legislature APIs; EU: EUR-Lex, EBA/ESMA/EIOPA, national gazettes; UK legislation.gov.uk, Canada Justice Laws, Australia Federal Register, UN/OECD/World Bank docs
- AgentPress use: Wrap into llms.txt/RUN_THIS/material-manifest/proof-receipt; prefer citation-ready, task-specific slices.

### Government/Law — Court opinions/dockets/filings (P0, millions)
- Why: agents research precedent and risk signals
- Where: CourtListener/RECAP API, Justia, Google Scholar legal, state court portals where permitted; SEC litigation releases, DOJ/FTC/CFPB enforcement releases; Bankruptcy/RECAP filings and docket PDFs
- AgentPress use: Wrap into llms.txt/RUN_THIS/material-manifest/proof-receipt; prefer citation-ready, task-specific slices.

### Government/Law — Regulatory guidance / supervisory manuals (P0, hundreds-thousands)
- Why: finance/compliance agents need exact citations
- Where: SEC/FINRA/CFTC/FDIC/OCC/Fed/CFPB/FCA/MAS/HKMA/ADGM/VARA/ESMA/BIS/IOSCO sites; Examination manuals, no-action letters, enforcement orders, consultation papers; Crypto-specific guidance from regulators and FATF/OFAC
- AgentPress use: Wrap into llms.txt/RUN_THIS/material-manifest/proof-receipt; prefer citation-ready, task-specific slices.

### Government/Law — Procurement/RFP/grants notices (P1, millions)
- Why: BD agents need opportunity discovery and proposal prep
- Where: SAM.gov API, Grants.gov, EU TED, state procurement portals, World Bank procurement; Municipal RFP portals, university procurement portals; Award databases and contract documents
- AgentPress use: Wrap into llms.txt/RUN_THIS/material-manifest/proof-receipt; prefer citation-ready, task-specific slices.

### Government/Law — Permits, zoning, municipal codes, land records (P2, millions)
- Why: agents need local compliance/business intel
- Where: Municode, city/county planning portals, zoning PDFs, GIS open data portals; Recorder/property tax portals, building permit APIs; State/local open data CKAN/Socrata endpoints
- AgentPress use: Wrap into llms.txt/RUN_THIS/material-manifest/proof-receipt; prefer citation-ready, task-specific slices.

### Company/Finance — Public company filings and transcripts (P0, millions)
- Why: finance agents need precise, structured business facts
- Where: SEC EDGAR submissions/companyfacts APIs, XBRL, 10-K/10-Q/8-K/S-1/DEF14A exhibits; Sedar+/Companies House/ASX/SGX/HKEX filings; Earnings call transcripts, investor day PDFs, investor relations sitemaps
- AgentPress use: Wrap into llms.txt/RUN_THIS/material-manifest/proof-receipt; prefer citation-ready, task-specific slices.

### Company/Finance — Private-company docs / startup surfaces (P0, millions)
- Why: growth agents need target/account intelligence
- Where: Company websites sitemaps, docs pages, pricing pages, changelogs, status pages, API docs; Crunchbase/Wellfound/Product Hunt/G2/Capterra where allowed, GitHub org repos; Job postings (Greenhouse/Lever/Ashby), help centers, support docs
- AgentPress use: Wrap into llms.txt/RUN_THIS/material-manifest/proof-receipt; prefer citation-ready, task-specific slices.

### Company/Finance — Market/industry reports (P1, hundreds-thousands)
- Why: strategy agents need cited context
- Where: IMF/World Bank/OECD/BIS/FRED/BLS/BEA/Eurostat data/docs; Consulting/industry PDFs, trade association reports, standards bodies; Central bank speeches/minutes/reports, rating agency methodology PDFs
- AgentPress use: Wrap into llms.txt/RUN_THIS/material-manifest/proof-receipt; prefer citation-ready, task-specific slices.

### Company/Finance — Credit/risk/counterparty docs (P0, hundreds-thousands)
- Why: Nexio-adjacent agents need risk intel
- Where: Exchange proof-of-reserves pages, custodian docs, protocol docs, governance forums; Bank call reports, FDIC data, FFIEC, NCUA, broker/dealer filings; Audits, attestations, SOC reports landing pages, insurance docs
- AgentPress use: Wrap into llms.txt/RUN_THIS/material-manifest/proof-receipt; prefer citation-ready, task-specific slices.

### Research — Papers, preprints, datasets (P1, millions)
- Why: research agents need compressed literature maps
- Where: arXiv, bioRxiv, SSRN, RePEc, PubMed/PMC, Semantic Scholar/OpenAlex/Crossref APIs; Papers with Code, Hugging Face papers/models/datasets, Kaggle datasets; University lab pages, conference proceedings, NBER/CEPR/Bank papers
- AgentPress use: Wrap into llms.txt/RUN_THIS/material-manifest/proof-receipt; prefer citation-ready, task-specific slices.

### Research — Standards/specifications/RFCs (P0, hundreds-thousands)
- Why: agents implement protocols and need exact clauses
- Where: IETF RFCs/datatracker, W3C, WHATWG, TC39, ISO landing pages where public; Kubernetes Enhancement Proposals, Python PEPs, Rust RFCs, OpenAPI/JSON Schema specs; Payments/finance standards: FIX, ISO 20022 public guides, NACHA public docs
- AgentPress use: Wrap into llms.txt/RUN_THIS/material-manifest/proof-receipt; prefer citation-ready, task-specific slices.

### Research — Patents and technical disclosures (P2, millions)
- Why: agents find invention/competitive intelligence
- Where: USPTO PatentsView, Google Patents, EPO Espacenet, WIPO Patentscope; Patent PDFs, claims, citations, assignees, classifications; Defensive publications and standards contributions
- AgentPress use: Wrap into llms.txt/RUN_THIS/material-manifest/proof-receipt; prefer citation-ready, task-specific slices.

### Public Data — Open data portals and data dictionaries (P1, millions)
- Why: agents need schema-aware datasets not human pages
- Where: data.gov CKAN, Socrata portals, EU data portal, World Bank, OECD, IMF, FRED, BLS, Census APIs; City/state CKAN/Socrata portals, NOAA/NASA/USGS/EPA/CDC/FDA data docs; Dataset metadata, schemas, codebooks, API docs
- AgentPress use: Wrap into llms.txt/RUN_THIS/material-manifest/proof-receipt; prefer citation-ready, task-specific slices.

### Health/Science — Clinical/medical/public health docs (P2, millions)
- Why: agents need cited medical/science context, not advice
- Where: FDA labels/Orange Book/Drugs@FDA, ClinicalTrials.gov, PubMed/PMC, CDC/WHO/NIH docs; EMA/Health Canada/MHRA docs, adverse event docs, drug labels; Hospital guideline PDFs and clinical society guidelines where public
- AgentPress use: Wrap into llms.txt/RUN_THIS/material-manifest/proof-receipt; prefer citation-ready, task-specific slices.

### Education — Courses, textbooks, tutorials (P2, millions)
- Why: agents need learning/curriculum compression
- Where: MIT OCW, OpenStax, university course pages, lecture notes, syllabi; Khan/DeepLearning.AI/Fast.ai docs where public, GitHub course repos; Problem sets, rubrics, lab manuals
- AgentPress use: Wrap into llms.txt/RUN_THIS/material-manifest/proof-receipt; prefer citation-ready, task-specific slices.

### Support/Help Centers — Customer-support KBs (P0, millions)
- Why: agents solving user problems need exact support steps
- Where: Zendesk/Intercom/HelpScout/ReadMe/GitBook/Docusaurus/Mintlify/Nextra help centers; Status pages, changelogs, incident postmortems; Community forums, GitHub Discussions, Discord/Slack docs where public
- AgentPress use: Wrap into llms.txt/RUN_THIS/material-manifest/proof-receipt; prefer citation-ready, task-specific slices.

### Sales/Marketing — Product/pricing/integration pages (P1, millions)
- Why: growth agents need targetable pain and current claims
- Where: Company sitemaps, pricing pages, docs, changelogs, integrations directories, marketplace listings; G2/Capterra/Product Hunt/marketplaces where allowed; Case studies, whitepapers, webinars, partner directories
- AgentPress use: Wrap into llms.txt/RUN_THIS/material-manifest/proof-receipt; prefer citation-ready, task-specific slices.

### Media/News — Newsletters, blogs, transcripts (P2, millions)
- Why: agents need timely context and summaries
- Where: RSS feeds, Substack/public newsletters, company blogs, YouTube transcripts where allowed; Podcasts transcripts, earnings/news transcripts, press releases; GDELT/news APIs and archive pages
- AgentPress use: Wrap into llms.txt/RUN_THIS/material-manifest/proof-receipt; prefer citation-ready, task-specific slices.
