# SEO Snapshot — Feature to tool map

Notionhive  |  Internal  |  August 2026

One prepaid vendor (DataForSEO REST API) plus one free Google API (PageSpeed Insights). No Ahrefs, Semrush, Analytics, or Search Console — those need a monthly seat or the prospect’s login.

**How we talk to DataForSEO:** official REST API at `https://api.dataforseo.com/v3` with HTTP Basic Auth. Copy **API Access** login + generated API password from [app.dataforseo.com/api-access](https://app.dataforseo.com/api-access). That is not the website account password, and DataForSEO does not issue a separate Bearer API key.

---

## Serial map


| #   | Feature                                                                   | Tool                                                               | Why this tool                                                                     |
| --- | ------------------------------------------------------------------------- | ------------------------------------------------------------------ | --------------------------------------------------------------------------------- |
| 1   | Cover                                                                     | None (app)                                                         | Domain, date, and NH brand only.                                                  |
| 2   | Scorecard (visibility, technical, content, authority)                     | Computed in our app                                                | DataForSEO does not sell this four-score card. We derive it from the pulls below. |
| 3   | Organic snapshot                                                          | **DataForSEO Labs** — `domain_rank_overview`                       | Estimated traffic and ranking keyword count for a site we do not control.         |
| 4   | Quick wins                                                                | **DataForSEO Labs** — `ranked_keywords` (positions 4–15)           | Keywords the prospect already ranks for, just off page one.                       |
| 5a  | Technical health — Core Web Vitals (LCP, INP, CLS)                        | **Google PageSpeed Insights**                                      | Google’s own lab data, free. Do not pay DataForSEO Lighthouse for the same thing. |
| 5b  | Technical health — crawl issues (titles, metas, broken links, duplicates) | **DataForSEO OnPage** — `task_post` → `summary` / `pages`          | Site crawl without prospect login. Cap 100 pages, JS rendering off.               |
| 6   | Authority                                                                 | **DataForSEO Backlinks** — `summary` + `referring_domains`         | Referring domain **counts** vs one competitor. Never show total backlink counts.  |
| 7   | Competitor gap                                                            | **DataForSEO Labs** — `competitors_domain` + `domain_intersection` | Keyword overlap and gaps vs the competitor, same index as organic/quick wins.     |
| 8   | Priorities + CTA                                                          | App template, **edited by the operator**                           | Not AI. Not a data vendor. Booking link from env.                                 |


---



## What we will not use for this product


| Tool                               | Reason                                                    |
| ---------------------------------- | --------------------------------------------------------- |
| Ahrefs / Semrush                   | Monthly subscription. CEO brief is prepaid credits only.  |
| DataForSEO Lighthouse / OnPage CWV | Duplicate of PageSpeed; extra cost.                       |
| Google Analytics                   | Needs prospect access. This is a cold sales leave-behind. |
| Google Search Console              | Same — no prospect login.                                 |
| Screaming Frog                     | Desktop crawler, not an API for this internal tool.       |


---



## Thin-data rule

If Labs returns little or no keyword data (new or tiny sites), drop features **3, 4, and 7**. Keep PageSpeed + OnPage (5) and referring domains (6). The deck still goes out.

---



## Cost reminder

- DataForSEO: prepaid credits, target ~$0.15 per deck (cap ~$0.50).
- PageSpeed Insights: $0.
- Daily spend cap: set in the DataForSEO dashboard **and** `SNAPSHOT_DAILY_SPEND_CAP` in the app.

