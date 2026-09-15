"""Slide 4: Current Rankings for the primary Labs market."""

from __future__ import annotations

from typing import Any, Optional

from app.services.snapshot_health import brand_label, market_name, _fmt_num, _int


def _fmt_money(value: Optional[float]) -> str:
    if value is None:
        return "—"
    try:
        n = float(value)
    except (TypeError, ValueError):
        return "—"
    if n <= 0:
        return "—"
    if n >= 1000:
        return f"${_fmt_num(n)}"
    return f"${int(round(n))}"


def _n(metrics: dict, *keys: str) -> int:
    total = 0
    for key in keys:
        try:
            total += int(round(float(metrics.get(key) or 0)))
        except (TypeError, ValueError):
            continue
    return total


def buckets_from_metrics(metrics: dict) -> list[dict[str, Any]]:
    return [
        {"label": "Top 3", "count": _n(metrics, "pos_1", "pos_2_3")},
        {"label": "4–10", "count": _n(metrics, "pos_4_10")},
        {"label": "11–20", "count": _n(metrics, "pos_11_20")},
        {"label": "21–50", "count": _n(metrics, "pos_21_30", "pos_31_40", "pos_41_50")},
        {"label": "51–100", "count": _n(metrics, "pos_51_60", "pos_61_70", "pos_71_80", "pos_81_90", "pos_91_100")},
    ]


def build_rankings_slide(payload: dict) -> dict[str, Any]:
    organic = payload.get("organic") or {}
    primary = organic.get("primary") or {}
    loc = primary.get("location_code") or organic.get("primary_location_code") or payload.get("location_code")
    market = primary.get("market") or market_name(loc)
    domain = payload.get("prospect_domain") or "this domain"
    metrics = primary.get("metrics") or {}

    count = _int(primary.get("count") or organic.get("count_primary"))
    etv = primary.get("etv")
    if not isinstance(etv, (int, float)):
        etv = organic.get("etv_primary")
    etv_display = primary.get("etv_display") or (
        f"{_fmt_num(etv)} /mo" if isinstance(etv, (int, float)) else "—"
    )
    if etv_display != "—" and "/mo" not in str(etv_display):
        etv_display = f"{etv_display} /mo"
    traffic_cost = primary.get("estimated_paid_traffic_cost")
    buckets = primary.get("buckets") or buckets_from_metrics(metrics)
    top3 = buckets[0]["count"] if buckets else 0
    top10 = top3 + (buckets[1]["count"] if len(buckets) > 1 else 0)
    keywords = payload.get("top_keywords") or []

    cards = [
        {
            "value": "—" if count is None else _fmt_num(count),
            "label": "Keywords Tracked",
            "subtext": f"DataForSEO Labs, {market} database",
            "tone": "neutral",
        },
        {
            "value": _fmt_num(top10) if count else "—",
            "label": "Top-10 Rankings",
            "subtext": f"{_fmt_num(top3)} in top 3",
            "tone": "pass" if top10 and count and top10 / max(count, 1) >= 0.4 else "neutral",
        },
        {
            "value": etv_display,
            "label": "Organic Traffic",
            "subtext": (
                f"{_fmt_money(traffic_cost)} traffic value · Estimated"
                if isinstance(traffic_cost, (int, float)) and traffic_cost > 0
                else "Estimated · this market"
            ),
            "tone": "pass" if isinstance(etv, (int, float)) and etv >= 1000 else "neutral",
        },
    ]

    brand = brand_label(domain).lower().split()[0] if domain else ""
    branded = [
        row
        for row in keywords
        if brand and brand in str(row.get("keyword") or "").lower()
    ]
    share = (top10 / count) if count else 0
    if branded and share >= 0.35:
        lead = branded[0]
        takeaway = (
            f"Ranking strength is concentrated in branded terms — "
            f"“{lead.get('keyword')}” at #{lead.get('position')}. "
            f"Category-level terms remain weaker in {market}."
        )
    elif share >= 0.5:
        takeaway = (
            f"{_fmt_num(top10)} of {_fmt_num(count)} tracked keywords already sit in the "
            f"top 10 in {market}. Next gains are in the 11–20 band."
        )
    elif top3 < 5:
        takeaway = (
            f"Few keywords are in the top 3 in {market}. Visibility is spread through "
            f"page two and beyond (Estimated, DataForSEO Labs)."
        )
    else:
        takeaway = (
            f"{_fmt_num(top10)} top-10 rankings from {_fmt_num(count)} tracked keywords "
            f"in {market} (Estimated, DataForSEO Labs)."
        )

    return {
        "title": f"Current Rankings — {market}",
        "market": market,
        "cards": cards,
        "buckets": buckets,
        "bucket_caption": f"Position distribution ({_fmt_num(count) if count is not None else '—'} keywords)",
        "takeaway": takeaway,
        "top_keywords": keywords[:8],
    }
