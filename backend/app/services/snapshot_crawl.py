"""Site Audit (Crawl & Links) + Crawlability slides from this Snapshot pull.

Not Semrush. Crawl counts are DataForSEO OnPage (JS off, page cap).
Crawlability uses robots.txt / llms.txt / sitemap.xml probes plus the same crawl.
"""

from __future__ import annotations

from typing import Any

from app.services.snapshot_health import AI_BOTS, _fmt_num, _int, _tone_from_score


def _count(metrics: dict, checks: dict, *keys: str) -> int:
    for src in (metrics, checks):
        for key in keys:
            if key not in src or src[key] is None or isinstance(src[key], bool):
                continue
            try:
                return int(src[key])
            except (TypeError, ValueError):
                continue
    return 0


def _issue_rows(metrics: dict, checks: dict) -> list[dict[str, Any]]:
    catalog = [
        ("broken_links", "broken internal links", "fail", True),
        ("is_4xx_code", "4xx pages", "fail", False),
        ("is_5xx_code", "5xx pages", "fail", False),
        ("duplicate_title", "duplicate title tags", "fail", True),
        ("duplicate_title_tag", "duplicate title tags", "fail", False),
        ("duplicate_content", "pages with duplicate content", "fail", False),
        ("no_description", "pages missing meta descriptions", "warn", False),
        ("duplicate_description", "duplicate meta descriptions", "warn", True),
        ("duplicate_h1_tag", "pages with multiple H1 tags", "warn", False),
        ("no_h1_tag", "pages missing H1", "warn", False),
        ("low_content_rate", "pages with low text-HTML ratio", "warn", False),
        ("canonical_to_redirect", "canonicals pointing to redirects", "warn", False),
        ("no_title", "pages missing title tags", "fail", False),
    ]
    seen_labels: set[str] = set()
    rows: list[dict[str, Any]] = []
    for key, label, tone, prefer_metrics in catalog:
        if prefer_metrics:
            n = _count(metrics, {}, key) or _count({}, checks, key)
        else:
            n = _count(metrics, checks, key)
        if n <= 0 or label in seen_labels:
            continue
        seen_labels.add(label)
        rows.append({"count": n, "label": label, "tone": tone})
    rows.sort(key=lambda r: (-r["count"], r["label"]))
    return rows[:7]


def build_site_audit_slide(payload: dict) -> dict[str, Any]:
    tech = payload.get("technical") or {}
    onpage = payload.get("onpage") or {}
    metrics = onpage.get("page_metrics") or {}
    checks = metrics.get("checks") or {}
    crawled = _int(tech.get("pages_crawled") or (onpage.get("crawl_status") or {}).get("pages_crawled")) or 0
    cap = _int(payload.get("onpage_max_pages")) or 100

    onpage_score = tech.get("onpage_score")
    try:
        site_health = int(round(float(onpage_score))) if onpage_score is not None else None
    except (TypeError, ValueError):
        site_health = None

    issues = _issue_rows(metrics, checks)
    error_total = sum(r["count"] for r in issues)
    issue_types = len(issues)

    broken = _count(metrics, checks, "is_4xx_code") + _count(metrics, checks, "is_5xx_code")
    redirect = _count(
        metrics,
        checks,
        "is_redirect",
        "is_http_to_https_redirect",
        "canonical_to_redirect",
    )
    flagged = max(
        (
            _count(metrics, checks, "duplicate_title", "duplicate_title_tag"),
            _count(metrics, checks, "no_description"),
            _count(metrics, checks, "duplicate_content"),
            _count(metrics, checks, "low_content_rate"),
            _count(metrics, checks, "duplicate_h1_tag"),
            _count(metrics, checks, "broken_links"),
        ),
        default=0,
    )
    # Pages that still look clean after status + top hygiene flags (no double-count guarantee).
    accounted = min(crawled, broken + redirect + flagged) if crawled else broken + redirect + flagged
    healthy = max(0, crawled - accounted) if crawled else 0
    have_issues = max(0, crawled - healthy - broken - redirect) if crawled else flagged

    status = [
        {"label": "Healthy", "count": healthy},
        {"label": "Broken", "count": broken},
        {"label": "Redirect", "count": redirect},
        {"label": "Have issues", "count": have_issues},
    ]
    max_bar = max((s["count"] for s in status), default=0) or 1

    cards = [
        {
            "value": f"{_fmt_num(crawled)} / {_fmt_num(cap)}" if crawled else f"— / {_fmt_num(cap)}",
            "label": "Pages Crawled",
            "subtext": f"crawl cap {cap:,}",
            "tone": "neutral",
        },
        {
            "value": f"{site_health}%" if site_health is not None else "—",
            "label": "Site Health",
            "subtext": "OnPage score · this crawl",
            "tone": _tone_from_score(site_health),
        },
        {
            "value": _fmt_num(error_total) if issues else "0",
            "label": "Issue hits",
            "subtext": (
                f"across {issue_types} issue type{'s' if issue_types != 1 else ''}"
                if issue_types
                else "no OnPage issue flags in this crawl"
            ),
            "tone": "fail" if error_total else "pass",
        },
    ]

    takeaway = (
        f"DataForSEO OnPage crawled {crawled or '—'} pages (cap {cap}, JavaScript off) — "
        f"not a Semrush Site Audit and not a full-site index. "
    )
    if issues:
        top = issues[0]
        takeaway += (
            f"Highest-count flag: {top['count']:,} {top['label']}. "
            f"Fix the template once where counts cluster."
        )
    else:
        takeaway += "No high-volume OnPage flags in this pull — keep templates from regressing."

    return {
        "title": "Site Audit — Crawl & Links",
        "cards": cards,
        "status_title": "Crawled-page status",
        "status": status,
        "status_max": max_bar,
        "status_note": (
            f"Reconciled from this Snapshot OnPage pull only — {error_total:,} issue hits "
            f"across {issue_types} types."
            if issues
            else "Reconciled from this Snapshot OnPage pull only."
        ),
        "issues_title": "Top issues (by count)",
        "issues": issues,
        "takeaway": takeaway,
    }


def build_crawlability_slide(payload: dict) -> dict[str, Any]:
    ai = payload.get("ai") or {}
    robots = ai.get("robots") or {}
    tech = payload.get("technical") or {}
    onpage = payload.get("onpage") or {}
    metrics = onpage.get("page_metrics") or {}
    checks = metrics.get("checks") or {}
    crawled = _int(tech.get("pages_crawled") or (onpage.get("crawl_status") or {}).get("pages_crawled"))
    cap = _int(payload.get("onpage_max_pages")) or 100

    robots_missing = bool(robots.get("missing"))
    robots_present = not robots_missing and bool(robots)
    blocked = _int(robots.get("blocked")) or 0
    bot_total = _int(robots.get("total")) or len(AI_BOTS)
    bots = robots.get("bots") or {}
    allowed_names = [
        name for name in AI_BOTS if not (bots.get(name) or {}).get("blocked")
    ]
    blocked_names = [
        name for name in AI_BOTS if (bots.get(name) or {}).get("blocked")
    ]
    llms = bool(ai.get("llms_txt"))
    sitemap = ai.get("sitemap") or {}
    sitemap_ok = bool(sitemap.get("present"))
    sitemap_status = sitemap.get("status_code")

    if robots_missing:
        robots_state = "Not found at origin"
        robots_rec = "Publish a valid robots.txt and confirm AI crawlers you want are allowed"
        robots_tone = "fail"
    else:
        robots_state = "Present at origin (syntax not Search Console–validated)"
        robots_rec = "Keep allowing the AI crawlers you want; re-check after CMS or CDN changes"
        robots_tone = "pass"

    if llms:
        llms_state = "Present at origin"
        llms_rec = "Keep llms.txt updated as key URLs change"
        llms_tone = "pass"
    else:
        llms_state = "Not found"
        llms_rec = "Publish an llms.txt to guide AI crawlers to key content"
        llms_tone = "fail"

    sitemap_url = sitemap.get("url") or "/sitemap.xml"
    if sitemap_ok:
        sitemap_state = (
            f"Present at {sitemap_url}"
            + (f" (HTTP {sitemap_status})" if sitemap_status else "")
        )
        sitemap_rec = "Regenerate when URL inventory changes; spot-check for stale or soft-404 URLs"
        sitemap_tone = "pass"
    else:
        sitemap_state = f"Not found (tried robots Sitemap: + {sitemap_url})"
        sitemap_rec = (
            "Publish a clean XML sitemap (or sitemap_index.xml), declare it in robots.txt, "
            "and submit it in Search Console"
        )
        sitemap_tone = "fail"

    if blocked == 0 and robots_present:
        bot_state = (
            f"0 of {bot_total} AI crawlers blocked — "
            + ", ".join(allowed_names[:8])
            + ("…" if len(allowed_names) > 8 else "")
            + " all pass"
        )
        bot_rec = "No action needed — this is a genuine strength; maintain on any future changes"
        bot_tone = "pass"
    elif blocked:
        bot_state = (
            f"{blocked} of {bot_total} AI crawlers blocked"
            + (f" ({', '.join(blocked_names)})" if blocked_names else "")
        )
        bot_rec = "Unblock the AI crawlers you want citing you, then re-fetch robots.txt"
        bot_tone = "fail"
    else:
        bot_state = "robots.txt missing — crawlers treated as allowed by default"
        bot_rec = "Publish robots.txt so access rules are explicit"
        bot_tone = "warn"

    crawl_state = "JS rendering was disabled for this audit crawl"
    crawl_rec = (
        f"Re-run with JS rendering enabled only if the site is a heavy SPA — "
        f"this pull used a {cap}-page cap with JavaScript off"
        + (f" ({crawled} pages crawled)" if crawled else "")
    )

    rows = [
        {"item": "robots.txt", "state": robots_state, "recommendation": robots_rec, "tone": robots_tone},
        {"item": "llms.txt", "state": llms_state, "recommendation": llms_rec, "tone": llms_tone},
        {"item": "sitemap.xml", "state": sitemap_state, "recommendation": sitemap_rec, "tone": sitemap_tone},
        {"item": "AI bot access", "state": bot_state, "recommendation": bot_rec, "tone": bot_tone},
        {"item": "Crawl config", "state": crawl_state, "recommendation": crawl_rec, "tone": "neutral"},
    ]

    return {
        "title": "Crawlability — robots.txt, sitemap.xml & llms.txt",
        "rows": rows,
    }
