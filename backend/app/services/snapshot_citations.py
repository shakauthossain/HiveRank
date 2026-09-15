"""Slide after GEO: AI Visibility & Citations from this Snapshot pull only.

Not Semrush. Not ChatGPT/Gemini citation counts. Cards, mix, and sample URLs
are Labs rankings + robots.txt + the same AI Visibility composite as slide 2.
"""

from __future__ import annotations

from typing import Any, Optional
from urllib.parse import urlparse

from app.services.snapshot_health import (
    brand_label,
    compute_ai_visibility,
    _fmt_num,
    _int,
    _tone_from_score,
)

MIX_COLORS = {
    "Top 3": "1158E5",
    "4–10": "D97706",
    "4-10": "D97706",
    "11–20": "059669",
    "11-20": "059669",
    "21–50": "EAB308",
    "21-50": "EAB308",
    "51–100": "64748B",
    "51-100": "64748B",
    "Crawlers allowed": "1158E5",
    "Crawlers blocked": "DC2626",
}
FALLBACK_COLORS = ("1158E5", "D97706", "059669", "EAB308", "64748B")


def _short_url(raw: Optional[str], domain: str) -> Optional[str]:
    if not raw:
        return None
    text = str(raw).strip()
    if not text:
        return None
    parsed = urlparse(text if "://" in text else f"https://{text}")
    host = (parsed.netloc or domain or "").replace("www.", "")
    path = parsed.path or "/"
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")
    display = f"{host}{path}"
    return display[:72] if display else None


def _top10_count(payload: dict) -> Optional[int]:
    rankings = payload.get("rankings_slide") or {}
    buckets = rankings.get("buckets") or []
    if not buckets:
        primary = (payload.get("organic") or {}).get("primary") or {}
        buckets = primary.get("buckets") or []
    if buckets:
        labels = {str(b.get("label") or ""): _int(b.get("count")) or 0 for b in buckets}
        return (labels.get("Top 3") or 0) + (labels.get("4–10") or labels.get("4-10") or 0)
    organic = payload.get("organic") or {}
    p1 = _int(organic.get("pos_1")) or 0
    p23 = _int(organic.get("pos_2_3")) or 0
    p410 = _int(organic.get("pos_4_10")) or 0
    total = p1 + p23 + p410
    return total if total else None


def _mix(payload: dict) -> list[dict[str, Any]]:
    rankings = payload.get("rankings_slide") or {}
    buckets = rankings.get("buckets") or ((payload.get("organic") or {}).get("primary") or {}).get("buckets") or []
    if buckets:
        rows = []
        for b in buckets:
            n = _int(b.get("count")) or 0
            if n:
                label = b.get("label") or "—"
                rows.append({"label": label, "value": n})
        return _with_colors(rows)
    vis = compute_ai_visibility(payload)
    allowed = vis.get("allowed") or 0
    blocked = vis.get("blocked") or 0
    mix = []
    if allowed:
        mix.append({"label": "Crawlers allowed", "value": allowed})
    if blocked:
        mix.append({"label": "Crawlers blocked", "value": blocked})
    return _with_colors(mix)


def _with_colors(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    for i, row in enumerate(rows):
        label = str(row.get("label") or "")
        row["color"] = MIX_COLORS.get(label) or FALLBACK_COLORS[i % len(FALLBACK_COLORS)]
    return rows


def build_citations_slide(payload: dict) -> dict[str, Any]:
    vis = compute_ai_visibility(payload)
    score = vis["score"]
    domain = payload.get("prospect_domain") or ""
    organic = payload.get("organic") or {}
    primary = organic.get("primary") or {}
    count = _int(primary.get("count") or organic.get("count_primary") or organic.get("count"))
    top10 = _top10_count(payload)
    keywords = list(payload.get("top_keywords") or []) + list(payload.get("quick_wins") or [])
    urls: list[str] = []
    seen = set()
    for row in keywords:
        short = _short_url((row or {}).get("url"), domain)
        if short and short not in seen:
            seen.add(short)
            urls.append(short)
        if len(urls) >= 4:
            break
    brand = brand_label(domain).lower().split()[0] if domain else ""
    branded = 0
    if brand:
        branded = sum(1 for row in keywords if brand in str((row or {}).get("keyword") or "").lower())

    cards = [
        {
            "value": f"{score} / 100",
            "label": "AI Visibility Score",
            "subtext": "this Snapshot pull",
            "tone": _tone_from_score(score),
        },
        {
            "value": "—" if top10 is None else _fmt_num(top10),
            "label": "Top-10 Rankings",
            "subtext": "Estimated · AIO-eligible band",
            "tone": "pass" if (top10 or 0) >= 50 else ("warn" if top10 else "neutral"),
        },
        {
            "value": "—" if count is None else _fmt_num(count),
            "label": "Keywords Tracked",
            "subtext": "Estimated · this market (Labs)",
            "tone": "pass" if (count or 0) >= 100 else "neutral",
        },
        {
            "value": str(branded) if keywords else ("Yes" if vis["llms"] else "No"),
            "label": "Brand-term hits" if keywords else "llms.txt",
            "subtext": (
                "in this-market Labs list"
                if keywords
                else ("present at origin" if vis["llms"] else "missing at origin")
            ),
            "tone": (
                "pass" if (keywords and branded) or (not keywords and vis["llms"]) else "warn"
            ),
        },
    ]

    mix = _mix(payload)
    mix_title = (
        "Ranking mix (Estimated, this market)"
        if any(r["label"] in ("Top 3", "4–10", "11–20", "21–50", "51–100") for r in mix)
        else "AI crawler access"
    )
    total_mix = sum(r["value"] for r in mix) or 1
    for row in mix:
        row["pct"] = round(100 * row["value"] / total_mix)

    takeaway = (
        f"The headline visibility score is {score}/100 from this Snapshot pull — crawler access "
        f"({vis['crawler']}%), llms.txt ({'25 points' if vis['llms'] else '0'}), estimated ranking "
        f"coverage, and OnPage site health. It is not Semrush and not a ChatGPT citation count. "
        f"The number to act on underneath is top-10 coverage"
        f"{'' if top10 is None else f' ({_fmt_num(top10)} keywords)'} "
        f"— that is the band Google AI Overviews usually select from."
    )

    return {
        "title": "AI Visibility & Citations",
        "cards": cards,
        "mix_title": mix_title,
        "mix": mix,
        "sample_title": "Sample ranking URLs (Estimated, Labs):",
        "sample_urls": urls,
        "reading_title": f"How to read the {score}/100",
        "takeaway": takeaway,
        "score": score,
    }
