"""Scorecard and draft-priority helpers. Narrative is template-based, not AI."""

from __future__ import annotations

import math
from typing import Any, Optional


def clamp_score(value: float) -> int:
    return max(0, min(100, int(round(value))))


def _log_scale(value: float, cap: float, points: float) -> float:
    if value <= 0:
        return 0.0
    return min(points, (math.log10(value + 1) / math.log10(cap + 1)) * points)


def visibility_score(organic: Optional[dict]) -> int:
    if not organic:
        return 0
    count = float(organic.get("count") or 0)
    etv = float(organic.get("etv") or 0)
    pos_1 = float(organic.get("pos_1") or 0)
    return clamp_score(
        _log_scale(count, 5000, 40)
        + _log_scale(etv, 50000, 40)
        + min(20.0, pos_1 / 5.0)
    )


def technical_score(cwv: dict, onpage: dict) -> int:
    score = 100.0
    for key in ("lcp_status", "inp_status", "cls_status"):
        status = (cwv or {}).get(key)
        if status == "fail":
            score -= 16
        elif status == "warning":
            score -= 8
        elif status in (None, "na"):
            score -= 2

    perf = (cwv or {}).get("perf_score")
    if isinstance(perf, (int, float)):
        score = 0.6 * score + 0.4 * float(perf)

    metrics = (onpage or {}).get("page_metrics") or {}
    broken = int(metrics.get("broken_links") or 0)
    if broken:
        score -= min(18, 4 + broken)

    onpage_score = metrics.get("onpage_score")
    if isinstance(onpage_score, (int, float)):
        score = 0.55 * score + 0.45 * float(onpage_score)

    return clamp_score(score)


def content_score(onpage: dict) -> int:
    metrics = (onpage or {}).get("page_metrics") or {}
    checks = metrics.get("checks") or {}
    crawled = int(
        ((onpage or {}).get("crawl_status") or {}).get("pages_crawled")
        or metrics.get("pages_with_content")
        or 1
    )
    crawled = max(crawled, 1)
    penalties = 0.0
    weights = {
        "no_title": 22,
        "title_too_long": 6,
        "title_too_short": 6,
        "duplicate_title_tag": 16,
        "no_description": 12,
        "duplicate_description": 10,
        "no_h1_tag": 10,
        "duplicate_h1_tag": 8,
        "low_content_rate": 16,
        "low_character_count": 10,
        "no_image_alt": 6,
        "canonical_to_redirect": 8,
    }
    for key, weight in weights.items():
        n = int(checks.get(key) or 0)
        if n:
            penalties += min(weight, weight * n / crawled)

    duplicate_title = int(metrics.get("duplicate_title") or 0)
    duplicate_desc = int(metrics.get("duplicate_description") or 0)
    if duplicate_title:
        penalties += min(16, 4 + duplicate_title)
    if duplicate_desc:
        penalties += min(10, 3 + duplicate_desc)

    return clamp_score(100 - penalties)


def authority_score(prospect_rd: Optional[int], competitor_rd: Optional[int] = None) -> int:
    prospect = int(prospect_rd or 0)
    return clamp_score(_log_scale(prospect, 5000, 100))


def is_thin_labs(organic: Optional[dict]) -> bool:
    if not organic:
        return True
    count = int(organic.get("count") or 0)
    etv = float(organic.get("etv") or 0)
    return count < 15 or (count < 40 and etv < 20)


def draft_top_fixes(payload: dict) -> list[str]:
    """Deterministic operator starting points. Not model-generated copy."""
    fixes: list[str] = []
    cwv = payload.get("technical") or {}
    onpage = payload.get("onpage") or {}
    metrics = onpage.get("page_metrics") or {}
    checks = metrics.get("checks") or {}
    organic = payload.get("organic") or {}
    quick_wins = payload.get("quick_wins") or []
    authority = payload.get("authority") or {}
    domain = payload.get("prospect_domain") or "the site"

    def add(text: str) -> None:
        if text not in fixes and len(fixes) < 5:
            fixes.append(text)

    if cwv.get("lcp_status") == "fail":
        add(
            f"Bring Largest Contentful Paint down from {cwv.get('lcp') or 'the current value'} "
            "(compress hero media, preload the LCP asset, reduce server wait)."
        )
    elif cwv.get("lcp_status") == "warning":
        add(f"Improve LCP ({cwv.get('lcp')}) so it stays under 2.5s on mobile.")

    if cwv.get("inp_status") == "fail":
        add(
            f"Reduce Interaction to Next Paint ({cwv.get('inp') or 'poor'}) by cutting main-thread JS."
        )
    elif cwv.get("cls_status") == "fail":
        add(
            f"Stop layout shift (CLS {cwv.get('cls')}) by reserving image/ad space and avoiding late font swaps."
        )

    broken = int(metrics.get("broken_links") or 0)
    if broken:
        add(f"Fix {broken} broken link{'s' if broken != 1 else ''} found in the crawl.")

    no_title = int(checks.get("no_title") or 0)
    dup_title = int(metrics.get("duplicate_title") or checks.get("duplicate_title_tag") or 0)
    if no_title:
        add(f"Write unique title tags for {no_title} page{'s' if no_title != 1 else ''} missing them.")
    elif dup_title:
        add(f"Deduplicate {dup_title} repeated title tag{'s' if dup_title != 1 else ''}.")

    no_desc = int(checks.get("no_description") or 0)
    if no_desc:
        add(f"Add meta descriptions on {no_desc} page{'s' if no_desc != 1 else ''}.")

    if quick_wins:
        kws = ", ".join(f"“{w['keyword']}” (#{w['position']})" for w in quick_wins[:3] if w.get("keyword"))
        if kws:
            add(f"Push near-page-one terms with on-page refreshes: {kws}.")

    p_rd = authority.get("prospect_referring_domains")
    if isinstance(p_rd, int) and p_rd < 50:
        add(
            f"Build referring domains: {domain} currently has {p_rd:,} "
            "linking root domains."
        )

    low_content = int(checks.get("low_content_rate") or 0)
    if low_content:
        add(f"Expand thin copy on {low_content} page{'s' if low_content != 1 else ''}.")

    if payload.get("thin_data"):
        add(
            f"{domain} has little modeled keyword data. Prioritize indexable service/location pages "
            "and a clean XML sitemap before chasing rankings."
        )
        if cwv.get("perf_score") is not None and isinstance(cwv.get("perf_score"), (int, float)) and cwv["perf_score"] < 70:
            add("Raise the mobile PageSpeed score with image, cache, and JS-budget work.")

    if not organic.get("count") and not payload.get("thin_data"):
        add("Confirm the domain is indexed and that robots.txt / noindex are not blocking Google.")

    fallbacks = [
        "Standardize title and H1 patterns on template pages (one primary topic per URL).",
        "Point internal links from strong pages to money pages using descriptive anchors.",
        "Set up Search Console and a monthly crawl so title, status-code, and index issues stay visible.",
        "Compress and lazy-load below-the-fold images; keep the hero image explicit size attributes.",
        f"Book a working session to turn this snapshot into a 90-day SEO plan for {domain}.",
    ]
    for line in fallbacks:
        add(line)

    return fixes[:5]
