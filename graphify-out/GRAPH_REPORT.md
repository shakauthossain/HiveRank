# Graph Report - .  (2026-08-23)

## Corpus Check
- Corpus is ~25,487 words - fits in a single context window. You may not need a graph.

## Summary
- 363 nodes · 654 edges · 27 communities (13 shown, 14 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 40 edges (avg confidence: 0.85)
- Token cost: 0 input · 107,220 output

## Community Hubs (Navigation)
- Auth & Session Backend
- Backend Deps & Business Rules
- Frontend Package Config
- Frontend Auth UI
- SEO Snapshot Scoring Engine
- Snapshot API Endpoints
- DataForSEO API Client
- TypeScript Compiler Config
- Deck Builder Script
- HTML Report Generation
- Deck Builder Package Config
- Report Template Rationale
- aiofiles Dependency
- openpyxl Dependency
- psycopg2-binary Dependency
- pydantic Dependency
- python-dotenv Dependency
- python-multipart Dependency
- uvicorn Dependency
- Excluded Tool: Ahrefs/Semrush
- Excluded Tool: Google Analytics
- Excluded Tool: Search Console
- Excluded Tool: Screaming Frog
- Estimated-Label Rule
- Referring-Domains-Only Rule

## God Nodes (most connected - your core abstractions)
1. `process_snapshot()` - 24 edges
2. `User` - 19 edges
3. `analyze_website()` - 15 edges
4. `compilerOptions` - 15 edges
5. `DataForSeoClient` - 14 edges
6. `create_snapshot()` - 13 edges
7. `process_bulk_audit()` - 13 edges
8. `DataForSEO API` - 10 edges
9. `Snapshot` - 9 edges
10. `approve_snapshot()` - 9 edges

## Surprising Connections (you probably didn't know these)
- `Thin-Data Fallback (drop slides 3, 4, 7)` --semantically_similar_to--> `Thin-Data Fallback Rule`  [INFERRED] [semantically similar]
  SEO_Snapshot_Tool_Implementation_Brief.md → CEO_SEO_Snapshot_Brief.md
- `Daily Spend Cap (dashboard + env var)` --semantically_similar_to--> `Daily Spend Cap`  [INFERRED] [semantically similar]
  SEO_Snapshot_Feature_Tool_Map.md → CEO_SEO_Snapshot_Brief.md
- `Thin-Data Fallback (drop slides 3, 4, 7)` --semantically_similar_to--> `Thin-Data Rule`  [INFERRED] [semantically similar]
  SEO_Snapshot_Tool_Implementation_Brief.md → SEO_Snapshot_Feature_Tool_Map.md
- `Daily Spend Limit` --semantically_similar_to--> `Daily Spend Cap (dashboard + env var)`  [INFERRED] [semantically similar]
  SEO_Snapshot_Tool_Implementation_Brief.md → SEO_Snapshot_Feature_Tool_Map.md
- `pandas` --conceptually_related_to--> `Scorecard (visibility/technical/content/authority)`  [INFERRED]
  backend/requirements.txt → SEO_Snapshot_Feature_Tool_Map.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **DataForSEO Labs endpoint family** — seo_snapshot_feature_tool_map_dataforseo_labs_domain_rank_overview, seo_snapshot_feature_tool_map_dataforseo_labs_ranked_keywords, seo_snapshot_feature_tool_map_dataforseo_labs_competitors_domain, seo_snapshot_feature_tool_map_dataforseo_labs_domain_intersection [INFERRED 0.85]
- **Human-in-the-loop review gate across specs** — ceo_seo_snapshot_brief_human_review_gate, seo_snapshot_feature_tool_map_priorities_cta, seo_snapshot_tool_implementation_brief_pipeline [INFERRED 0.85]
- **Thin-data fallback rule restated across specs** — ceo_seo_snapshot_brief_thin_data_fallback, seo_snapshot_feature_tool_map_thin_data_rule, seo_snapshot_tool_implementation_brief_thin_data_fallback [INFERRED 0.95]

## Communities (27 total, 14 thin omitted)

### Community 0 - "Auth & Session Backend"
Cohesion: 0.07
Nodes (57): create_access_token(), get_current_user(), get_optional_user(), get_password_hash(), get_super_admin(), Session, verify_password(), get_db() (+49 more)

### Community 1 - "Backend Deps & Business Rules"
Cohesion: 0.06
Nodes (52): bcrypt==3.2.0, fastapi, httpx, pandas, passlib, playwright, python-jose[jwt], requests (+44 more)

### Community 2 - "Frontend Package Config"
Cohesion: 0.04
Nodes (48): autoprefixer, axios, express, dependencies, axios, dotenv, express, @google/genai (+40 more)

### Community 3 - "Frontend Auth UI"
Cohesion: 0.09
Nodes (33): api, isAuthenticated(), logout(), setAuthToken(), App(), AuthModal(), AuthModalProps, CircularProgress() (+25 more)

### Community 4 - "SEO Snapshot Scoring Engine"
Cohesion: 0.16
Nodes (29): first_result(), authority_score(), clamp_score(), content_score(), draft_top_fixes(), is_thin_labs(), _log_scale(), Scorecard and draft-priority helpers. Narrative is template-based, not AI. (+21 more)

### Community 5 - "Snapshot API Endpoints"
Cohesion: 0.17
Nodes (28): Snapshot, User, approve_snapshot(), create_snapshot(), download_snapshot(), get_snapshot(), list_snapshots(), _owned() (+20 more)

### Community 6 - "DataForSEO API Client"
Cohesion: 0.14
Nodes (11): AsyncClient, _credentials(), DataForSeoClient, DataForSeoError, DataForSEO v3 REST client. Credentials come from env, never from the repo., task_ok(), build_pptx(), _node_bin() (+3 more)

### Community 7 - "TypeScript Compiler Config"
Cohesion: 0.11
Nodes (18): compilerOptions, allowImportingTsExtensions, allowJs, experimentalDecorators, isolatedModules, jsx, lib, module (+10 more)

### Community 8 - "Deck Builder Script"
Cohesion: 0.26
Nodes (12): addFooter(), build(), dash(), estimatedNote(), fs, kicker(), main(), path (+4 more)

### Community 9 - "HTML Report Generation"
Cohesion: 0.28
Nodes (5): generate_seo_html(), score_color(), status_meta(), generate_html(), Generates the premium Slide-Deck HTML report for SEO (no Jinja2 â pure inline…

### Community 10 - "Deck Builder Package Config"
Cohesion: 0.22
Nodes (8): dependencies, pptxgenjs, description, main, name, private, version, pptxgenjs

## Ambiguous Edges - Review These
- `5-Step Build Pipeline` → `AI Studio App (Gemini boilerplate)`  [AMBIGUOUS]
  frontend/README.md · relation: conceptually_related_to
- `Slide 5: Technical Health` → `playwright`  [AMBIGUOUS]
  backend/requirements.txt · relation: conceptually_related_to

## Knowledge Gaps
- **84 isolated node(s):** `fs`, `path`, `PptxGenJS`, `name`, `private` (+79 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **14 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `5-Step Build Pipeline` and `AI Studio App (Gemini boilerplate)`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `Slide 5: Technical Health` and `playwright`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **Why does `dotenv` connect `Auth & Session Backend` to `Frontend Package Config`?**
  _High betweenness centrality (0.119) - this node is a cross-community bridge._
- **Why does `dotenv` connect `Frontend Package Config` to `Auth & Session Backend`?**
  _High betweenness centrality (0.118) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `process_snapshot()` (e.g. with `create_snapshot()` and `fetch_pagespeed_data_sync()`) actually correct?**
  _`process_snapshot()` has 2 INFERRED edges - model-reasoned connections that need verification._
- **What connects `fs`, `path`, `PptxGenJS` to the rest of the system?**
  _84 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Auth & Session Backend` be split into smaller, more focused modules?**
  _Cohesion score 0.07307692307692308 - nodes in this community are weakly interconnected._