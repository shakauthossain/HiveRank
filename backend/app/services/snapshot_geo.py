"""GEO Readiness slide from signals already on the Snapshot pull.

Each bar is a
0–100 scale derived from robots.txt, llms.txt, DataForSEO, OnPage, or PageSpeed.
"""

from __future__ import annotations

from typing import Any, Optional

from app.services.snapshot_onpage import _count, _seo_scores
from app.services.snapshot_scoring import authority_score, clamp_score


def _tone(score: Optional[int]) -> str:
    if score is None:
        return "neutral"
    if score >= 70:
        return "pass"
    if score >= 45:
        return "warn"
    return "fail"


def _mean(values: list[Optional[int]]) -> Optional[int]:
    nums = [v for v in values if isinstance(v, (int, float))]
    if not nums:
        return None
    return clamp_score(sum(nums) / len(nums))


def _inverted(flagged: int, crawled: int) -> Optional[int]:
    if crawled <= 0:
        return None
    return clamp_score(100 - 100 * min(1.0, flagged / crawled))


def _cwv_penalty(tech: dict) -> int:
    penalty = 0
    for key in ("lcp_status", "inp_status", "cls_status"):
        status = tech.get(key)
        if status == "fail":
            penalty += 12
        elif status == "warning":
            penalty += 6
    return min(30, penalty)


def build_geo_slide(payload: dict) -> dict[str, Any]:
    ai = payload.get("ai") or {}
    authority = payload.get("authority") or {}
    tech = payload.get("technical") or {}
    onpage = payload.get("onpage") or {}
    metrics = onpage.get("page_metrics") or {}
    checks = metrics.get("checks") or {}

    robots = ai.get("robots") or {}
    crawler = robots.get("score")
    if not isinstance(crawler, (int, float)):
        crawler = None
    else:
        crawler = int(round(crawler))
    blocked = int(robots.get("blocked") or 0)
    bot_total = int(robots.get("total") or 0)
    llms = bool(ai.get("llms_txt"))
    llms_score = 100 if llms else 0

    rank = authority.get("rank")
    try:
        rank_n = int(rank) if rank is not None else None
    except (TypeError, ValueError):
        rank_n = None
    rd = authority.get("prospect_referring_domains")
    citation = rank_n if rank_n is not None else authority_score(rd)

    crawled = int(tech.get("pages_crawled") or (onpage.get("crawl_status") or {}).get("pages_crawled") or 0)
    missing_meta = _count(metrics, checks, "no_description")
    dup_titles = _count(metrics, checks, "duplicate_title", "duplicate_title_tag")
    dup_content = _count(metrics, checks, "duplicate_content")
    low_ratio = _count(metrics, checks, "low_content_rate")
    multi_h1 = _count(metrics, checks, "duplicate_h1_tag")
    no_h1 = _count(metrics, checks, "no_h1_tag")

    _m, _d, seo_shown = _seo_scores(payload)
    onpage_score = metrics.get("onpage_score")
    try:
        onpage_n = int(round(float(onpage_score))) if onpage_score is not None else None
    except (TypeError, ValueError):
        onpage_n = None
    perf = tech.get("perf_score")
    try:
        perf_n = int(perf) if perf is not None else None
    except (TypeError, ValueError):
        perf_n = None
    technical = _mean([seo_shown, onpage_n, perf_n])
    if technical is not None:
        technical = clamp_score(technical - _cwv_penalty(tech))

    peers = [
        int(p["rank"])
        for p in (authority.get("peers") or [])
        if isinstance(p, dict) and not p.get("is_you") and p.get("rank") is not None
    ]
    lead_peer = max(peers) if peers else None
    if rank_n is not None and lead_peer:
        competitive = clamp_score(100 * rank_n / lead_peer)
    elif rank_n is not None:
        competitive = rank_n
    else:
        competitive = None

    answer = _mean(
        [
            _inverted(missing_meta, crawled),
            _inverted(dup_titles, crawled),
            _inverted(dup_content, crawled),
            _inverted(low_ratio, crawled),
        ]
    )
    heading = _inverted(multi_h1 + no_h1, crawled)
    if heading is None:
        comprehension = llms_score if llms else None
        if comprehension is None:
            comprehension = 40
    else:
        comprehension = clamp_score(0.65 * heading + 0.35 * (100 if llms else 30))

    bars = [
        {
            "label": "Citation Authority",
            "score": citation,
            "tone": _tone(citation),
            "note": "DataForSEO rank 0–100",
        },
        {
            "label": "AI Crawler Access",
            "score": crawler,
            "tone": _tone(crawler),
            "note": "robots.txt vs GPTBot, ClaudeBot, PerplexityBot, and related crawlers",
        },
        {
            "label": "Technical Optimization",
            "score": technical,
            "tone": _tone(technical),
            "note": "Lighthouse SEO + OnPage score + CWV penalty",
        },
        {
            "label": "Competitive Context",
            "score": competitive,
            "tone": _tone(competitive),
            "note": "Your DataForSEO rank vs lead category peer",
        },
        {
            "label": "Answer-First Content",
            "score": answer,
            "tone": _tone(answer),
            "note": "OnPage meta/title/dup/text-ratio vs pages crawled — not PSI, not Labs",
        },
        {
            "label": "AI Comprehension",
            "score": comprehension,
            "tone": _tone(comprehension),
            "note": "H1 hygiene in the crawl + llms.txt",
        },
    ]
    overall = _mean([b["score"] for b in bars])

    worst = min(
        (b for b in bars if isinstance(b.get("score"), int)),
        key=lambda b: b["score"],
        default=None,
    )
    if multi_h1 > 0 and worst and worst["label"] in ("AI Comprehension", "Answer-First Content"):
        takeaway = (
            f"{multi_h1} pages in this crawl ship multiple H1 tags. That heading-hierarchy "
            f"problem pulls down AI comprehension on this GEO score — fixing the template "
            f"once helps classic rankings and AI parsing together."
        )
    elif crawler is not None and crawler < 80 and blocked:
        takeaway = (
            f"{blocked} of {bot_total or blocked} AI crawlers are blocked in robots.txt. "
            f"Allowing GPTBot, ClaudeBot, and PerplexityBot is the fastest GEO lift on this pull."
        )
    elif not llms:
        takeaway = (
            "No llms.txt at the origin. A short llms.txt that points crawlers at your key "
            "service/product URLs is the cheapest GEO win available from this Snapshot."
        )
    elif worst:
        takeaway = (
            f"GEO score {overall if overall is not None else '—'}/100 from this Snapshot pull. "
            f"The weakest pillar is {worst['label']} ({worst['score']}/100). "
            f"{worst.get('note') or ''}"
        )
    else:
        takeaway = "GEO signals were incomplete on this pull. Re-run after robots.txt and OnPage return."

    return {
        "title": "GEO Readiness Score",
        "overall": overall,
        "crawler": crawler,
        "llms": llms,
        "llms_score": llms_score,
        "lead_peer": lead_peer,
        "bars": bars,
        "takeaway": takeaway,
        "source": "This Snapshot pull — robots.txt, llms.txt, DataForSEO, PageSpeed.",
    }
