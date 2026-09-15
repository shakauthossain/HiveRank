**SEO Snapshot Tool**

Implementation Brief for the Technology Team  |  Notionhive  |  August 12, 2026

**Objective**

Build an internal tool that turns any prospect domain into a branded 8-10 slide initial SEO audit deck. Sales uses it as a lead gen value add. Input: prospect domain plus one competitor domain. Output: NH branded PPTX/pdf. A human reviews and approves every deck before it goes out. 

**Pipeline**

1\.  Operator enters the prospect domain and one competitor in an internal web form.

2\.  Backend pulls data from the DataForSEO API and the Google PageSpeed Insights API.

3\.  A Node script builds the deck with pptxgenjs using the NH brand template (NH Blue 1158E5, DM Sans, Calibri fallback).

4\.  Review screen shows the pulled data and draft narrative. Operator edits, approves, and downloads the deck.

5\.  Sales sends the deck to the prospect.

**Slide to data mapping**

| Slide | Content | Data source and endpoint |
| :---- | :---- | :---- |
| 1\. Cover | Prospect domain, date, NH brand | None |
| 2\. Scorecard | Four scores: visibility, technical, content, authority | Computed from the data below |
| 3\. Organic snapshot | Estimated traffic and ranking keyword count, labeled Estimated | Labs: dataforseo\_labs/google/domain\_rank\_overview/live |
| 4\. Quick wins | Keywords ranking in positions 4 to 15 | Labs: dataforseo\_labs/google/ranked\_keywords/live (filter by position) |
| 5\. Technical health | Core Web Vitals plus top crawl issues (titles, metas, broken links, duplicates) | PageSpeed Insights API (free) plus OnPage: on\_page/task\_post, then on\_page/summary and on\_page/pages. Cap crawl at 100 pages, JS rendering off |
| 6\. Authority | Referring domain count vs one competitor | Backlinks: backlinks/summary/live and backlinks/referring\_domains/live |
| 7\. Competitor gap | Keyword overlap and gaps vs one or two competitors | Labs: dataforseo\_labs/google/competitors\_domain/live and domain\_intersection/live |
| 8\. Priorities \+ CTA | Top five fixes and a booking link | Generated narrative, edited by the operator |

**Build rules**

* Label every traffic and keyword figure as Estimated on the slide. These are modeled numbers, not verified analytics.

* Show referring domain counts only. Never show total backlink counts, since other tools report different totals.

* Thin data fallback: if Labs returns little or no data (small or new sites), drop slides 3, 4, and 7 and expand the technical findings instead.

* Set a daily spend limit in the DataForSEO dashboard before the first production run. Test on the free trial credit and log API usage per audit.

* Auth is basic auth with the API login and password from the dashboard. Keep credentials in environment variables, never in the repo.

* Prototype the queries with the official DataForSEO MCP server in Claude Code, then move to direct REST calls for production.

**Links**

* **DataForSEO API docs:**  [https://docs.dataforseo.com/v3/](https://docs.dataforseo.com/v3/)

* **Official MCP server:**  [https://github.com/dataforseo/mcp-server-typescript](https://github.com/dataforseo/mcp-server-typescript)

* **MCP setup guide:**  [https://dataforseo.com/help-center/setting-up-the-official-dataforseo-mcp-server-simple-guide](https://dataforseo.com/help-center/setting-up-the-official-dataforseo-mcp-server-simple-guide)

* **DataForSEO dashboard and API credentials:**  [https://app.dataforseo.com/](https://app.dataforseo.com/)

* **PageSpeed Insights API:**  [https://developers.google.com/speed/docs/insights/v5/get-started](https://developers.google.com/speed/docs/insights/v5/get-started)

* **pptxgenjs:**  [https://github.com/gitbrent/PptxGenJS](https://github.com/gitbrent/PptxGenJS)