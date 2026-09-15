"""Slide 6: On-Page & Content Health from DataForSEO OnPage + Lighthouse SEO."""

from __future__ import annotations

from typing import Any, Optional


def _int(value: Any) -> int:
    if isinstance(value, bool) or value is None or value == "":
        return 0
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _count(metrics: dict, checks: dict, *keys: str) -> int:
    for src in (metrics, checks):
        for key in keys:
            if key not in src or src[key] is None or isinstance(src[key], bool):
                continue
            return _int(src[key])
    return 0


def _count_tone(n: int, severity: str) -> str:
    if n <= 0:
        return "pass"
    return "fail" if severity == "fail" else "warn"


def _score_tone(score: Optional[int]) -> str:
    if score is None:
        return "neutral"
    if score >= 90:
        return "pass"
    if score >= 50:
        return "warn"
    return "fail"


def _seo_scores(payload: dict) -> tuple[Optional[int], Optional[int], Optional[int]]:
    tech = payload.get("technical") or {}
    mobile = tech.get("mobile") or {}
    desktop = tech.get("desktop") or {}
    m = mobile.get("seo_score")
    d = desktop.get("seo_score")
    if m is None:
        m = tech.get("seo_score")
    scores = [s for s in (m, d) if isinstance(s, (int, float))]
    shown = int(min(scores)) if scores else None
    return (
        int(m) if isinstance(m, (int, float)) else None,
        int(d) if isinstance(d, (int, float)) else None,
        shown,
    )


def build_onpage_slide(payload: dict) -> dict[str, Any]:
    onpage = payload.get("onpage") or {}
    tech = payload.get("technical") or {}
    metrics = onpage.get("page_metrics") or {}
    checks = metrics.get("checks") or {}
    crawled = _int(tech.get("pages_crawled") or (onpage.get("crawl_status") or {}).get("pages_crawled"))
    cap = _int(payload.get("onpage_max_pages") or 100) or 100

    missing_meta = _count(metrics, checks, "no_description")
    dup_titles = _count(metrics, checks, "duplicate_title", "duplicate_title_tag")
    dup_content = _count(metrics, checks, "duplicate_content")
    low_ratio = _count(metrics, checks, "low_content_rate")
    multi_h1 = _count(metrics, checks, "duplicate_h1_tag")
    mobile_seo, desktop_seo, seo_shown = _seo_scores(payload)
    has_crawl = crawled > 0
    crawl_err = onpage.get("error")

    if mobile_seo is not None and desktop_seo is not None:
        if mobile_seo == desktop_seo:
            seo_sub = "mobile & desktop"
        else:
            seo_sub = f"mobile {mobile_seo} · desktop {desktop_seo}"
        seo_value = f"{seo_shown} / 100"
    elif seo_shown is not None:
        which = "mobile" if mobile_seo is not None else "desktop"
        seo_sub = f"Lighthouse, PSI · {which}"
        seo_value = f"{seo_shown} / 100"
    else:
        seo_sub = "PSI SEO category · re-run Snapshot"
        seo_value = "—"

    def issue_card(n: int, label: str, subtext: str, severity: str) -> dict[str, str]:
        if not has_crawl:
            return {
                "value": "—",
                "label": label,
                "subtext": "OnPage crawl empty — re-run Snapshot",
                "tone": "neutral",
            }
        return {
            "value": str(n),
            "label": label,
            "subtext": subtext,
            "tone": _count_tone(n, severity),
        }

    cards = [
        issue_card(missing_meta, "Pages Missing Meta Descriptions", "suppresses SERP CTR", "fail"),
        issue_card(dup_titles, "Duplicate Title Tags", "dilutes topical relevance", "fail"),
        issue_card(dup_content, "Pages with Duplicate Content", "cannibalization risk", "fail"),
        issue_card(low_ratio, "Pages with Low Text-HTML Ratio", "thin-content signal", "warn"),
        issue_card(multi_h1, "Pages with Multiple H1 Tags", "confuses search & AI parsing", "warn"),
        {
            "value": seo_value,
            "label": "Lighthouse SEO Score",
            "subtext": seo_sub,
            "tone": _score_tone(seo_shown),
        },
    ]

    crawl_bit = (
        f"Counts are from the {crawled}-page crawl (cap {cap}, JavaScript off), not the full index."
        if has_crawl
        else (
            f"OnPage crawl did not return page metrics this pull"
            + (f" ({crawl_err})" if crawl_err else "")
            + f". Re-run Snapshot — summary is GET on_page/summary/{{id}} (cap {cap}, JS off)."
        )
    )

    hygiene = [
        (missing_meta, "without meta descriptions"),
        (dup_titles, "with duplicated titles"),
        (dup_content, "with duplicate content"),
    ]
    hygiene = [(n, label) for n, label in hygiene if n > 0]
    if not has_crawl:
        takeaway = crawl_bit
    elif hygiene:
        if len(hygiene) == 1:
            lead = f"{hygiene[0][0]} pages in this crawl are shipping {hygiene[0][1]}"
        else:
            parts = [f"{n} {label}" for n, label in hygiene]
            lead = f"{parts[0]}"
            if len(parts) == 2:
                lead = f"{parts[0]} and {parts[1]}"
            else:
                lead = f"{parts[0]}, {parts[1]}, and {parts[2]}"
            lead = f"{lead} in this crawl"
        takeaway = (
            f"{lead} — a templated fix (dynamic meta generation from product or page "
            f"attributes) resolves the majority of these in one pass rather than page-by-page. "
            f"{crawl_bit}"
        )
    elif low_ratio or multi_h1:
        bits = []
        if low_ratio:
            bits.append(f"{low_ratio} pages flagged for low text-to-HTML ratio")
        if multi_h1:
            bits.append(f"{multi_h1} pages with more than one H1")
        takeaway = (
            f"{' and '.join(bits)}. Tighten templates so each indexable URL has one H1 and "
            f"enough unique copy. {crawl_bit}"
        )
    elif seo_shown is not None and seo_shown < 90:
        takeaway = (
            f"Lighthouse SEO is {seo_shown}/100. Crawl hygiene counts are low in this pull — "
            f"fix the PageSpeed SEO audits (canonicals, crawlability, valid meta) before "
            f"chasing content volume. {crawl_bit}"
        )
    else:
        takeaway = (
            "On-page hygiene looks clean in this crawl. Keep title, meta, and H1 templates "
            f"from regressing when new pages ship. {crawl_bit}"
        )

    return {
        "title": "On-Page & Content Health",
        "cards": cards,
        "takeaway": takeaway,
    }
