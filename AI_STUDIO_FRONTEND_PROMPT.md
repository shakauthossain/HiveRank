# HiveBrief operator app — Google AI Studio prompt

How to use
1. Open Google AI Studio → Build (or Apps) → new app from prompt.
2. Paste EVERYTHING below the line “PROMPT START”.
3. Attach `brand/hivebrief-brand-kit.png` and `brand/hivebrief-mark.svg` as visual references if the UI allows files.
4. Turn OFF any Gemini / Generate Content API. This app does not call Gemini. It only calls our FastAPI backend.
5. After generate: set `VITE_API_URL` to the FastAPI base (example `http://localhost:8003`). Export and drop the files over `frontend/` (keep backend untouched).

Do not paste this how-to section into AI Studio. Paste from PROMPT START only.

---

PROMPT START

Build a complete production-ready React + TypeScript + Vite + Tailwind v4 operator web app named HiveBrief.

This is NOT a public SaaS, NOT a landing page, NOT a Semrush clone, NOT a Gemini chatbot, NOT an AI writer. Do not import `@google/genai`. Do not add a chat panel. Do not invent features.

It is an internal Notionhive staff tool. Sales operators paste a URL, pull public SEO/speed data from an existing FastAPI backend, review numbers, approve, and download a branded PPTX. Prospects never log in.

Wire every screen to the real REST API below. Use axios. Base URL from `import.meta.env.VITE_API_URL`. JWT in localStorage key `token`, sent as `Authorization: Bearer <token>`. Timeout 120000ms. On 401, clear the token.

============================================================
BRAND (non-negotiable)
============================================================

Name: HiveBrief (capital H, capital B). Never Hivebrief, Hive Brief, HIVEBRIEF, NH SEO Tools, SEO Snapshot (in prospect-facing copy). Internal route `/snapshot` may stay.

Tagline: Reviewed before it leaves the hive.

Parent brand: Notionhive. App chrome says HiveBrief. Deck/cover copy may say “HiveBrief by Notionhive”.

Metaphor: a signed brief. Logo mark: custom HB ligature in Hive Blue. The H is two stems and a crossbar (a bound report spine). The B shares the right stem; its lower bowl has a small folded-page triangle (the sign-off). Not a font. No hexagon, no bee, no honeycomb, no magnifying glass, no clipboard clipart, no outlined mark, no drop shadow. Horizontal lockup in the header: ligature + wordmark “HiveBrief” (tracking -0.02em). Import the mark from `brand/hivebrief-mark.svg` as component `LigatureMark`.

Personality: precise, calm, specialist, paper-like. A studio desk, not a glowing cockpit.

Visual mode: light operator UI. Paper canvas, white surfaces, one blue accent.

Colors (CSS tokens, use exactly):
--hive: #1158E5          primary CTA, links, mark, focus ring
--hive-dark: #0B3FA8     primary hover/pressed
--ink: #0B1220           body text, wordmark
--paper: #F4F6F9         app background
--white: #FFFFFF         cards, inputs, slides-in-app
--wash: #F1F6FE          selected rows, health cards
--line: #E2E8F0          1px borders
--muted: #64748B         captions only, never body text
--pass: #059669
--warn: #D97706
--fail: #DC2626
--takeaway: #FBF3D5
--takeaway-ink: #7A5B00

Type: DM Sans only (Google font, weights 400/500/600). Never Inter. Never a second display face. Scores and timings use font-variant-numeric: tabular-nums. Scale: 12 caption, 14 body, 16 control, 20 section, 28 page title. Never weight 800.

Shape: controls 8px radius (not pills). App cards 12px. No box-shadows. Elevation = white surface on paper + 1px --line border. Focus: 2px --hive ring, 2px offset.

Buttons:
- Primary: --hive bg, white text. Labels: Analyze, Approve, Download deck, Start batch.
- Ghost: ink on white, 1px --line. Labels: Edit fixes, Sign out, New HiveBrief.
One label per intent. Approve is not Publish.

Icons: @phosphor-icons/react, stroke 1.5. Do not use lucide-react.

Motion: 160ms color/opacity on state change only. Skeleton loaders that match the scorecard grid. Honor prefers-reduced-motion. No marquees, no gradient text, no custom cursors, no glassmorphism, no purple glow, no black Inter-on-zinc chrome.

First viewport of every tool page: a field and one primary action. Not a marketing hero. No “Trusted by”. No feature grid.

Voice (use these strings):
- App title: HiveBrief
- Analyze idle: Paste a URL. Technical SEO and Core Web Vitals.
- Snapshot idle: Pull a HiveBrief. A person approves it before it goes out.
- Thin data: Little keyword data. Technical and authority slides still go out.
- Error: Could not pull this site. Check the URL and try again.
Banned copy: unleash, seamless, next-gen, AI-powered, intelligence platform, auto-send, Search Engine Intelligence, premium RankMath engine, Welcome Back (use Sign in).

Always label traffic and keyword counts “Estimated”. Show referring domains, never total backlink counts as the headline metric. Status is never color-only: Pass / Warn / Fail chips with text.

============================================================
TECH
============================================================

- React 19, TypeScript, Vite, react-router-dom v7, Tailwind v4, axios, motion (optional, keep subtle).
- File layout: src/App.tsx, src/api.ts, src/pages/{AnalyzePage,SnapshotPage,BulkAuditPage,AdminPage}.tsx, src/components/{AuthModal,HistoryPanel,LigatureMark}.tsx, src/index.css with @theme tokens.
- Env: VITE_API_URL, VITE_APP_TITLE="HiveBrief".
- Responsive: desktop-first operator tool, usable at 768px. Header nav collapses under md to a compact row or menu. Header height ≤ 72px.

============================================================
APP SHELL
============================================================

Full-height paper canvas. Header: LigatureMark + “HiveBrief” (click → reset Analyze and go /). Nav links: Analyze, Snapshot, Bulk, Admin. Right: history icon (opens Audit History drawer), Sign in OR Sign out.

Routes:
- / and /analyze/:domain/:reportId → AnalyzePage
- /snapshot and /snapshot/:id → SnapshotPage (login required to run)
- /bulk-audit and /bulk-audit/:jobId → BulkAuditPage (login required)
- /admin → AdminPage (separate super-admin HTTP Basic auth, not JWT)

Auth modal: email + password. POST `/token?email={email}&password={password}` → { access_token, token_type }. Store token. Copy: “Sign in to run HiveBriefs, bulk jobs, and history.”

History drawer (JWT users): GET `/me/audits` → list of { report_id, url, seo_score, speed_score, created_at }. Click → `/analyze/{domain}/{report_id}`. Empty: “No audits yet.”

============================================================
SCREEN 1 — ANALYZE (/)
============================================================

Staff (guest allowed). POST `/analyze` body { url, report_type: "seo" | "speed" | "both" }. Default both. Segmented control: SEO | Full | Speed.

States: idle, analyzing, complete, error.

Idle: page title is not a marketing headline. Use “Analyze” as H1. Sub: “Paste a URL. Technical SEO and Core Web Vitals.” Combined URL field + Analyze button. If logged in, show recent audits (max 6) with SEO and Speed scores.

Analyzing: five steps, not a spinner-only void:
1 Connecting to server
2 Fetching performance metrics
3 Analyzing Core Web Vitals
4 Evaluating content structure
5 Compiling report
Animate step index every ~1.8s while waiting; complete when the POST returns.

Complete: two cards (SEO and Speed if present).
SEO card: large tabular seo_score, bar, up to 3 failed tests (title + content), links:
- Open report → `{VITE_API_URL}/reports/{id}_seo.html`
- PDF → `{VITE_API_URL}/reports/{id}_seo.pdf`
Speed card: mobile perf_score and desktop perf_score, FCP/LCP/CLS from speed.mobile or speed.metrics. Same HTML/PDF pattern with `_speed`.
Reset ghost button returns to idle and navigates to /.

Load existing: GET `/audits/{reportId}` when route is /analyze/:domain/:reportId.

Analyze response shape (use defensively):
{
  id, url?,
  seo: { seo_score, seo_tests: [{ title, status, content }], categories? },
  speed: {
    perf_score, perf_score_desktop?,
    mobile: { perf_score, fcp, lcp, cls, categories? },
    desktop: { perf_score },
    metrics: { fcp, lcp, cls, tbt, si, tti },
    speed_tests: [{ title, status, content }]
  },
  seo_report_url, speed_report_url
}
Test status: pass | warning | fail | check.

============================================================
SCREEN 2 — SNAPSHOT (/snapshot)  [flagship]
============================================================

Login required to create. This is the sales leave-behind pipeline. H1: “HiveBrief”. Sub: “Pull a HiveBrief. A person approves it before it goes out.”

Create: label “Prospect website” above input. POST `/snapshots` { prospect_url }. Optional later fields exist on the API (competitor_url, location_code default 2840, language_code default "en") but the current product does not ask for a competitor. Navigate to `/snapshot/{id}`.

Poll GET `/snapshots/{id}` every 3s while status is pending or running. Show snapshot.progress text. Typical wait: a few minutes (100-page crawl).

Statuses: pending | running | review | approved | failed.

Review/approved layout (operator desk, not a fake slide deck):
1. Header: prospect_domain, thin_data warning if true (use the thin-data copy), API cost `$x.xxxx`.
2. Health grid: payload.health.cards (usually 8). Each card: large value, label, subtext, tone pass|warn|fail|neutral. Wash background. Fallback if health.cards missing: derive from payload.scores / organic / technical / authority as in the existing app (authority, estimated traffic, ranking keywords, referring domains, site health, AI search, CWV, AI-cited).
3. Takeaway band: payload.health.takeaway on --takeaway background.
4. Authority section: payload.authority_slide.cards, peers (bold the is_you row), reading notes.
5. If NOT thin_data: rankings_slide (cards, buckets, top_keywords table). No separate all-markets organic slide — rankings carries traffic and keyword counts.
6. If thin_data: expanded crawl table from technical.worst_pages (url, status_code, onpage_score). Hide rankings/quick-wins.
7. Performance: payload.performance_slide.cards + rows table (metric, mobile, desktop, lab) with tone colors. Fallback LCP/INP/CLS from technical.
8. On-page: payload.onpage_slide.cards + takeaway.
9. GEO: payload.geo_slide
10. AI Visibility & Citations: payload.citations_slide
11. Site Audit — Crawl & Links: payload.site_audit_slide (OnPage — not Semrush)
12. Crawlability: payload.crawlability_slide (robots / llms / sitemap probes)
13. Quick wins table if !thin_data && quick_wins (keyword, position, volume_display). Positions 4–15. Moved after the crawl slides.
14. Crawl findings list: technical.issues.
15. Edit desk (the product’s heart):
    - Five textareas: top five fixes. Prefill snapshot.top_fixes.
    - Booking link input (snapshot.booking_url).
    - Primary: “Approve” (or “Re-approve & rebuild deck” if already approved) → POST `/snapshots/{id}/approve` { top_fixes: string[], booking_url }.
    - Ghost “Download deck” only if download_ready (status approved). GET `/snapshots/{id}/download` as blob. Filename `HiveBrief-{prospect_domain}.pptx`.
    - Text button “New HiveBrief” → /snapshot.

Recent list: GET `/me/snapshots` → { id, status, prospect_domain, thin_data, api_cost_usd, created_at }. Click opens that id.

If 429 (daily spend cap), show the server `detail` string.

Snapshot GET shape:
{
  id, status, progress, error_message, prospect_url, prospect_domain,
  thin_data, api_cost_usd, usage_log: [{ endpoint, cost, ok }],
  payload: { scores, health, organic, quick_wins, technical, authority, authority_slide, rankings_slide, performance_slide, onpage_slide, geo_slide, citations_slide, site_audit_slide, crawlability_slide, top_fixes, booking_url, date },
  top_fixes, booking_url, created_at, approved_at, download_ready
}

HealthCard: { key?, value, label, subtext, tone }
Do not invent ChatGPT citation counts. Do not show a competitor URL field.

============================================================
SCREEN 3 — BULK (/bulk-audit)
============================================================

Login required. H1: “Bulk”. Sub: Upload CSV or XLSX with a url / website / link / site column. Multiple files run one after another.

Dropzone accept .csv,.xlsx multiple. POST `/analyze/bulk` FormData field `file`. Response { job_id }. Navigate `/bulk-audit/{job_id}`. Poll GET `/bulk/status/{jobId}` every 5s until completed or failed. Show processed_count / total_count and input_filename.

On completed: button Download CSV → GET `/bulk/jobs/{jobId}/download` blob. Fallback `{VITE_API_URL}/reports/{output_filename}`.

History: GET `/me/bulk-jobs`. Rows: filename, status, processed/total, date, download if completed.

============================================================
SCREEN 4 — ADMIN (/admin)
============================================================

Separate from JWT. Super-admin uses HTTP Basic on axios `auth: { username, password }`.

Gate: username + password form. Probe GET `/admin/stats`. On success keep creds in component state (not localStorage JWT).

Dashboard:
- Stats: total_users, total_audits, total_bulk_jobs from GET `/admin/stats`
- Create user: POST `/admin/create-user?email=&password=`
- Table: GET `/admin/users` → { id, email, audit_count }. Delete: DELETE `/admin/users/{id}`
- Sign out admin clears only admin creds.

============================================================
API QUICK LIST
============================================================

Auth JWT: POST /token?email&password
Me audits: GET /me/audits
Analyze: POST /analyze  { url, report_type }
Get audit: GET /audits/{report_id}
Reports: GET /reports/{filename}  (html/pdf, also used as href)

Snapshots: POST /snapshots  { prospect_url }
GET /snapshots/{id}
PATCH /snapshots/{id}  { top_fixes?, booking_url? }  (optional; approve can send the same)
POST /snapshots/{id}/approve  { top_fixes?, booking_url? }
GET /snapshots/{id}/download  (blob, only after approve)
GET /me/snapshots
GET /dataforseo/status  (optional small “credits” check for logged-in users)

Bulk: POST /analyze/bulk  multipart file
GET /bulk/status/{job_id}
GET /me/bulk-jobs
GET /bulk/jobs/{job_id}/download

Admin Basic: GET /admin/stats  GET /admin/users  POST /admin/create-user?email&password  DELETE /admin/users/{id}

CORS already allows localhost:3000 and :3003. Dev server on 3003 is fine.

============================================================
QUALITY BAR
============================================================

Generate the full multi-page app, not a single mock. Every state: idle, loading skeleton, error, empty, success. Forms: label above input, error below, never placeholder-as-label. Primary button contrast 4.5:1. Numbers use tabular nums. Health cards on --wash. Takeaways on --takeaway.

Match the brand board: paper, Hive Blue, HB ligature mark, DM Sans, quiet density.

If an API field is missing, show an em dash “—” (unicode), never fake numbers.

Build it now.

PROMPT END
