# SEO Snapshot — Slide data sources & zero-value fixes

Notionhive · Internal · August 2026

What each deck slide shows, **where the number comes from**, and **what to do when a field is 0 / — / “not found”**.

**Vendors used:** DataForSEO (Labs, Backlinks, OnPage) + Google PageSpeed Insights + our own origin probes (`robots.txt`, `llms.txt`, sitemap).  
**Not used:** Semrush, Ahrefs, Geoptie, ChatGPT citation indexes, Search Console, Analytics.

Full deck (dense Labs): **12 slides**. Thin Labs: **11 slides** (drops Rankings + Quick Wins; inserts Technical Extra).

---

## Pipeline (order of fetch)

```
1. DataForSEO OnPage task_post          (starts crawl early)
2. PageSpeed mobile + desktop (parallel) + origin AI probes (robots / llms / sitemap)
3. DataForSEO Labs domain_rank_overview (global, then primary market if needed)
4. Parallel: backlinks_summary + referring_domains + competitors_domain
            (+ ranked_keywords + ranked_keywords_by_traffic when not thin)
5. DataForSEO bulk_ranks                (prospect + peers)
6. Poll OnPage summary → OnPage pages
7. Build slide payloads → operator review → PPTX
```

Env knobs: `SNAPSHOT_ONPAGE_MAX_PAGES` (default 100), `SNAPSHOT_ONPAGE_POLL_SECONDS` (5), `SNAPSHOT_ONPAGE_POLL_ATTEMPTS` (72), `PAGESPEED_API_KEY`, `DATAFORSEO_API_LOGIN` / `DATAFORSEO_API_PASSWORD`.

---

## Slide map (full / dense deck)

| # | Slide | Builder | Primary sources |
|---|--------|---------|-----------------|
| 1 | Cover | deck-builder | App only — domain, date, Notionhive logo |
| 2 | SEO Health Snapshot | `snapshot_health.build_health_snapshot` | Labs overview + Backlinks + OnPage + PSI CWV + origin robots/llms composite |
| 3 | Authority | `snapshot_health.build_authority_slide` | Backlinks `summary`, `referring_domains`, Labs peers + `bulk_ranks` |
| 4 | Current Rankings | `snapshot_rankings.build_rankings_slide` | Labs `domain_rank_overview` (primary market) + `ranked_keywords_by_traffic` |
| 5 | Performance & CWV | `snapshot_performance.build_performance_slide` | Google PageSpeed Insights (lab + CrUX field) mobile + desktop |
| 6 | On-Page & Content | `snapshot_onpage.build_onpage_slide` | OnPage `summary` checks + PSI Lighthouse SEO scores |
| 7 | GEO Readiness | `snapshot_geo.build_geo_slide` | robots/llms + Backlinks rank + OnPage hygiene + PSI/SEO + peer ranks |
| 8 | AI Visibility & Citations | `snapshot_citations.build_citations_slide` | Same AI Visibility composite as slide 2 + Labs top-10 + sample ranking URLs |
| 9 | Site Audit — Crawl & Links | `snapshot_crawl.build_site_audit_slide` | OnPage crawl counts / issue flags only |
| 10 | Crawlability | `snapshot_crawl.build_crawlability_slide` | Origin probes: robots.txt, llms.txt, sitemap (+ OnPage note for JS off) |
| 11 | Quick Wins | payload `quick_wins` | Labs `ranked_keywords` filtered to positions ~4–15 |
| 12 | 6-Month Projections | `snapshot_projections.build_projections_slide` | **Today:** Snapshot pull (Labs primary market, PSI, OnPage, rank, AI composite). **Target:** deterministic 6‑mo formula (Notionhive-proposed) — operator-editable before approve |
| 13 | Priorities + CTA | `draft_top_fixes` + operator edit | App template + booking URL — not a vendor |

Thin deck replaces **4 Rankings** + **11 Quick Wins** with **Technical Extra** and keeps 9–10 before **12 Projections** and **13 Priorities**.

---

## Field-by-field

### Slide 1 — Cover
| Field | Source | If empty |
|-------|--------|----------|
| Domain / date / logo | Snapshot request + app | Always filled from URL |

### Slide 2 — SEO Health Snapshot
| Field | Source | If 0 / — |
|-------|--------|----------|
| Authority Score | DataForSEO Backlinks rank (`bulk_ranks` / summary) | Domain not in index → stay —; check domain spelling (no `www` mismatch) |
| Organic Traffic | Labs `domain_rank_overview` ETV (Estimated, all markets) | Thin / new site → thin deck; cannot invent Analytics |
| Ranking Keywords | Labs keyword count (primary market when known) | Same as above |
| Referring Domains | Backlinks `summary` / live RD count | 0 can be real for brand-new domains; else re-check host |
| Site Health % | OnPage `onpage_score` | Crawl failed/timeout → —; raise poll ceiling or re-run |
| AI Search Health % | Parsed `robots.txt` vs 6 AI bots | Probe fail used to show “missing”; hardened probe should re-run |
| Core Web Vitals | PSI mobile lab (and field when CrUX exists) | Site too small for CrUX → lab only or n/a |
| AI-Cited Pages | **Our composite** (crawler ×0.45 + llms 25pts + organic band + site health) — **not** ChatGPT citations | Improves when robots/llms/organic/OnPage improve |

### Slide 3 — Authority
| Field | Source | If 0 / — |
|-------|--------|----------|
| Rank / RD / backlinks / spam | Backlinks API | Prepaid credits + correct apex domain |
| Top referring domains | `referring_domains` live | Empty list = no RD data returned |
| Peer ranks (chart) | **Manual:** up to 3 operator URLs + `bulk_ranks`. **Auto:** Labs `competitors_domain` (wide pull) → drop mega platforms (Facebook, YouTube, …) → keep peers in a similar DataForSEO rank band → `bulk_ranks` | Thin peer set after filters = empty chart, not Facebook vs mid-market |

### Slide 4 — Current Rankings (dense only)
| Field | Source | If 0 / — |
|-------|--------|----------|
| Keywords / top-10 / traffic | Labs primary-market metrics | Thin Labs → slide omitted |
| Position buckets | Labs pos_* metrics | All zero = no modeled SERPs |
| Top keywords table | `ranked_keywords_by_traffic` | Empty → no URL samples on later slides |

### Slide 5 — Performance
| Field | Source | If n/a |
|-------|--------|----------|
| LCP / INP / CLS / TBT / scores | PSI API key | Missing `PAGESPEED_API_KEY`, origin blocked, or no CrUX field sample |

### Slide 6 — On-Page
| Field | Source | If 0 |
|-------|--------|------|
| Missing meta / dup titles / multi-H1 / etc. | OnPage `page_metrics.checks` | **0 can be correct** (clean templates) or crawl never finished |
| Lighthouse SEO | PSI `seo_score` mobile/desktop | PSI failure |

### Slide 7 — GEO Readiness
| Pillar | Source | If 0 / low |
|--------|--------|------------|
| Citation Authority | Backlinks rank | Same as slide 3 |
| AI Crawler Access | robots.txt bot parse | Re-run after probe fix; unblock bots in robots if truly blocked |
| Technical Optimization | PSI SEO + OnPage + CWV penalty | Fix CWV / OnPage |
| Competitive Context | Your rank vs lead peer | Needs peers from Labs |
| Answer-First Content | **DataForSEO OnPage only** (meta/title/dup/text-ratio vs pages crawled) — **not PSI, not Labs** | Shows **—** when OnPage crawl is empty (`pages_crawled` = 0). Re-run after OnPage summary succeeds |
| AI Comprehension | H1 hygiene + **llms.txt present** | Ship real `/llms.txt`; re-run Snapshot |

### Slide 8 — AI Visibility & Citations
| Field | Source | If 0 |
|-------|--------|------|
| AI Visibility Score | Same composite as slide 2 | See slide 2 |
| Top-10 / Keywords | Labs | Thin market |
| Brand-term hits | Count of Labs keywords containing brand SLD | **0 is common** if Labs list is non-branded; not a ChatGPT mention count |
| Sample URLs | Ranking URLs from Labs keyword rows | Need keyword pull |

### Slide 9 — Site Audit
| Field | Source | If 0 |
|-------|--------|------|
| Pages crawled / site health / issue hits | OnPage only (JS off, cap 100) | 0 crawled = task failed/timeout; 0 issues can be legit |

### Slide 10 — Crawlability *(no Key Takeaway)*
| Row | Source | If “Not found” but file exists |
|-----|--------|--------------------------------|
| robots.txt | GET `{origin}/robots.txt` (IPv4 probe, browser UA) | Re-run Snapshot; check CDN/bot block of datacenter IPs |
| llms.txt | GET `{origin}/llms.txt` | Must return non-HTML body; soft-404 HTML = not present |
| sitemap | `Sitemap:` lines in robots **first**, then `/sitemap.xml`, `/sitemap_index.xml`, `/wp-sitemap.xml`, … | Notionhive example: file is `sitemap_index.xml`, not `/sitemap.xml` |
| AI bot access | Parse of robots groups | If robots missing, treated as allowed by default |
| Crawl config | Snapshot policy | Informational (JS off + page cap) |

### Slide 11 — Quick Wins (dense only)
| Field | Source | If empty |
|-------|--------|----------|
| Keyword rows | Labs ranked keywords in positions 4–15 | No near-page-one keywords modeled |

### Slide 12 — 6-Month Projections (before CTA)
| Column | Source |
|--------|--------|
| Today | Rankings/Labs primary (top‑10, count, ETV), Backlinks rank, OnPage score, PSI mobile, CWV verdict, AI Visibility composite |
| 6‑Month Target | Formula in `snapshot_projections.py` — always **≥ Today** (never a downgrade). Illustrative only; see slide key note |
| Change | Computed from Today vs Target at build time; recomputed when operator edits targets on approve |

Keyword/traffic rows omitted when `thin_data`. Targets labeled as **Notionhive-proposed**, not Estimated vendor data.

### Slide 13 — Priorities + CTA
| Field | Source | If empty |
|-------|--------|----------|
| Five fixes | `draft_top_fixes` then **operator edit** | Always editable before approve |
| Booking CTA | `BOOKING_URL` / snapshot booking field | Set env or edit on review |

---

## Why notionhive.com showed false “not available” (slides 7 & 10)

On the `b2176aaf-…` pull the payload stored:

- `robots.missing: true` while `https://notionhive.com/robots.txt` is **200** (Yoast)
- `llms_txt: false` while `https://notionhive.com/llms.txt` is **200**
- `sitemap.present: false` while robots declares `Sitemap: https://notionhive.com/sitemap_index.xml` (**200**); `/sitemap.xml` alone is **404**

Root causes:

1. Origin probes from Docker often **hung on IPv6**; exceptions were swallowed → files marked missing.
2. Sitemap check only hit `/sitemap.xml`, ignoring robots `Sitemap:` lines and `sitemap_index.xml`.

**Fix shipped:** dedicated IPv4 httpx client, browser UA, content sniffing (reject HTML soft-404s), parallel robots+llms, sitemap candidates from robots + common paths. **Re-run Snapshot** to refresh slides 2, 7, 8, and 10.

---

## Quick “zeros” playbook

| Symptom | Likely cause | What to do |
|---------|--------------|------------|
| Organic / keywords 0 | Thin Labs coverage | Accept thin deck; do not invent traffic |
| Referring domains 0 | New domain or wrong host | Confirm apex vs www; re-run |
| Brand-term hits 0 | Labs list has no branded queries | Expected often; not a vendor citation API |
| CWV n/a | No CrUX / PSI miss | Confirm `PAGESPEED_API_KEY`; wait for field data |
| OnPage issues all 0 | Clean templates **or** empty crawl | Check `pages_crawled` > 0 |
| robots / llms / sitemap wrong | Probe / path issue | Re-run after probe fix; declare sitemap in robots |
| Entire slide “—” | Old payload before builder existed | Approve rebuild or new Snapshot |

---

## Honesty labels (do not change)

- Labs traffic/keywords → **Estimated**
- AI Visibility / AI-Cited Pages → **our composite**, not Semrush / ChatGPT
- GEO score → **our pillar mix**, not Geoptie
- Site Audit → **OnPage crawl cap**, not Semrush Site Audit
- Crawlability → **live origin probes**, not Search Console validation
