"""6-month projection slide — Today vs. Target (Notionhive-proposed, not vendor forecast)."""

from __future__ import annotations

from typing import Any, Optional

from app.services.snapshot_citations import _top10_count
from app.services.snapshot_health import (
    compute_ai_visibility,
    location_label,
    market_name,
    _fmt_num,
    _int,
)
from app.services.snapshot_performance import _cwv_verdict


def _pct_change(today: Optional[float], target: Optional[float]) -> tuple[str, str]:
    if today is None or target is None or today <= 0:
        return "—", "neutral"
    delta = (target - today) / today * 100
    if delta <= 0:
        return "—", "neutral"
    return f"+{int(round(delta))}%", "pass"


def _pts_change(today: Optional[int], target: Optional[int]) -> tuple[str, str]:
    if today is None or target is None:
        return "—", "neutral"
    delta = target - today
    if delta <= 0:
        return "—", "neutral"
    return f"+{delta} pts", "pass"


def _traffic_display(etv: Optional[float]) -> str:
    if etv is None:
        return "—"
    return f"{_fmt_num(etv)} /mo"


def _cwv_today_label(tech: dict) -> tuple[str, str]:
    mobile = tech.get("mobile") or {}
    desktop = tech.get("desktop") or {}
    verdict, tone, _note = _cwv_verdict(mobile, desktop)
    if verdict == "PASSED":
        return "Pass (3/3)", "pass"
    if verdict == "FAILED":
        for key, label in (("cls", "CLS"), ("lcp", "LCP"), ("inp", "INP")):
            if (mobile or {}).get(f"{key}_status") == "fail" or (desktop or {}).get(
                f"{key}_status"
            ) == "fail":
                return f"Failed ({label})", "fail"
        return "Failed", "fail"
    if verdict == "MIXED":
        return "Needs work", "warn"
    return "n/a", "neutral"


def _keyword_uplift(today: int, thin: bool) -> float:
    if thin or today <= 0:
        return 0.0
    if today >= 200:
        return 0.28
    if today >= 80:
        return 0.35
    if today >= 30:
        return 0.40
    return 0.30


def _traffic_uplift(etv: float, thin: bool) -> float:
    if thin or etv <= 0:
        return 0.0
    if etv >= 10_000:
        return 0.22
    if etv >= 1_000:
        return 0.30
    if etv >= 100:
        return 0.35
    return 0.25


def _rank_uplift(today: int) -> int:
    if today <= 0:
        return 0
    headroom = 100 - today
    return min(8, max(4, int(headroom * 0.14)))


def _points_uplift(
    today: Optional[int],
    lo: int,
    hi: int,
    *,
    ceiling: int = 100,
) -> Optional[int]:
    """Propose a 6-month score target — never below today."""
    if today is None:
        return None
    max_score = min(100, max(ceiling, today))
    if today >= max_score:
        return min(100, today + max(2, lo // 2))
    headroom = max_score - today
    uplift = min(hi, max(lo, int(headroom * 0.35)))
    return min(100, today + uplift)


def _format_target(key: str, raw: Any) -> str:
    if raw is None:
        return "—"
    if key == "site_health":
        return f"{int(raw)}%"
    if key in ("mobile_performance", "ai_visibility"):
        return f"{int(raw)} / 100"
    if key == "authority":
        return str(int(raw))
    if key in ("top10_keywords", "tracked_keywords"):
        return _fmt_num(int(raw))
    if key == "organic_traffic":
        return _traffic_display(float(raw))
    return str(raw)


def _clamp_row_target(row: dict[str, Any]) -> None:
    """Ensure numeric targets never fall below today's value."""
    key = row.get("key")
    today_raw = row.get("today_raw")
    target_raw = row.get("target_raw")
    if key == "cwv" or today_raw is None or target_raw is None:
        return
    try:
        today_n = float(today_raw)
        target_n = float(target_raw)
    except (TypeError, ValueError):
        return
    if target_n >= today_n:
        return
    if key == "organic_traffic":
        row["target_raw"] = today_n
    else:
        row["target_raw"] = int(today_n)
    row["target"] = _format_target(str(key), row["target_raw"])
    _recompute_change(row)


def _row(
    key: str,
    metric: str,
    today: str,
    target: str,
    change: str,
    change_tone: str = "pass",
    *,
    today_raw: Any = None,
    target_raw: Any = None,
    editable: bool = True,
) -> dict[str, Any]:
    return {
        "key": key,
        "metric": metric,
        "today": today,
        "target": target,
        "change": change,
        "change_tone": change_tone,
        "today_raw": today_raw,
        "target_raw": target_raw,
        "editable": editable,
    }


def build_projections_slide(payload: dict) -> dict[str, Any]:
    thin = bool(payload.get("thin_data"))
    organic = payload.get("organic") or {}
    primary = organic.get("primary") or {}
    tech = payload.get("technical") or {}
    authority = payload.get("authority") or {}
    mobile = tech.get("mobile") or {}

    loc = primary.get("location_code") or organic.get("primary_location_code") or payload.get(
        "location_code"
    )
    market = primary.get("market") or market_name(loc)
    loc_tag = location_label(loc) or ""
    market_suffix = f", {loc_tag}" if loc_tag else (f", {market}" if market and market != "this market" else "")

    count = _int(primary.get("count") or organic.get("count_primary") or organic.get("count"))
    top10 = _top10_count(payload)
    etv = primary.get("etv")
    if not isinstance(etv, (int, float)):
        etv = organic.get("etv_primary") or organic.get("etv")
    etv_f = float(etv) if isinstance(etv, (int, float)) else None

    rank = _int(authority.get("rank"))
    site_health_raw = tech.get("onpage_score")
    try:
        site_health = (
            int(round(float(site_health_raw))) if site_health_raw is not None else None
        )
    except (TypeError, ValueError):
        site_health = None

    mobile_perf = mobile.get("perf_score")
    try:
        mobile_perf_n = int(mobile_perf) if mobile_perf is not None else None
    except (TypeError, ValueError):
        mobile_perf_n = None

    ai_score = compute_ai_visibility(payload).get("score")
    ai_n = _int(ai_score)

    cwv_today, cwv_tone = _cwv_today_label(tech)
    cwv_target = "Pass (3/3)"
    cwv_change = "Pass" if cwv_tone == "fail" else "—"
    cwv_change_tone = "pass" if cwv_tone == "fail" else "neutral"

    rows: list[dict[str, Any]] = []

    if not thin and count and top10 is not None:
        kw_pct = _keyword_uplift(top10, thin)
        top10_target = int(round(top10 * (1 + kw_pct))) if top10 else None
        rows.append(
            _row(
                "top10_keywords",
                f"First-page keywords (top 10{market_suffix})",
                _fmt_num(top10),
                _fmt_num(top10_target) if top10_target else "—",
                *_pct_change(top10, top10_target),
                today_raw=top10,
                target_raw=top10_target,
            )
        )
        count_pct = _keyword_uplift(count, thin)
        count_target = int(round(count * (1 + count_pct))) if count else None
        rows.append(
            _row(
                "tracked_keywords",
                f"Total tracked keywords{market_suffix}",
                _fmt_num(count),
                _fmt_num(count_target) if count_target else "—",
                *_pct_change(count, count_target),
                today_raw=count,
                target_raw=count_target,
            )
        )

    if not thin and etv_f is not None and etv_f > 0:
        t_pct = _traffic_uplift(etv_f, thin)
        etv_target = etv_f * (1 + t_pct)
        rows.append(
            _row(
                "organic_traffic",
                f"Organic traffic /mo{market_suffix} (Estimated)",
                _traffic_display(etv_f),
                _traffic_display(etv_target),
                *_pct_change(etv_f, etv_target),
                today_raw=round(etv_f, 1),
                target_raw=round(etv_target, 1),
            )
        )

    if rank is not None:
        rank_target = min(100, rank + _rank_uplift(rank))
        rows.append(
            _row(
                "authority",
                "Authority Score",
                str(rank),
                str(rank_target),
                *_pts_change(rank, rank_target),
                today_raw=rank,
                target_raw=rank_target,
            )
        )

    if site_health is not None:
        sh_target = _points_uplift(site_health, 3, 8, ceiling=98)
        rows.append(
            _row(
                "site_health",
                "Site Health Score",
                f"{site_health}%",
                f"{sh_target}%" if sh_target is not None else "—",
                *_pts_change(site_health, sh_target),
                today_raw=site_health,
                target_raw=sh_target,
            )
        )

    if mobile_perf_n is not None:
        mp_target = _points_uplift(mobile_perf_n, 8, 15, ceiling=92)
        rows.append(
            _row(
                "mobile_performance",
                "Mobile Performance (Lighthouse)",
                f"{mobile_perf_n} / 100",
                f"{mp_target} / 100" if mp_target is not None else "—",
                *_pts_change(mobile_perf_n, mp_target),
                today_raw=mobile_perf_n,
                target_raw=mp_target,
            )
        )

    rows.append(
        _row(
            "cwv",
            "Core Web Vitals",
            cwv_today,
            cwv_target,
            cwv_change,
            cwv_change_tone,
            editable=False,
        )
    )

    if ai_n is not None:
        ai_target = _points_uplift(ai_n, 5, 12, ceiling=100)
        rows.append(
            _row(
                "ai_visibility",
                "AI Visibility Score",
                f"{ai_n} / 100",
                f"{ai_target} / 100",
                *_pts_change(ai_n, ai_target),
                today_raw=ai_n,
                target_raw=ai_target,
            )
        )

    for row in rows:
        _clamp_row_target(row)

    disclaimer = (
        "Targets are Notionhive-proposed, grounded in current Snapshot data and a typical "
        "technical + content SEO program trajectory over ~6 months (not client-supplied KPIs "
        "and not a vendor forecast)."
    )
    if thin:
        disclaimer += " Keyword/traffic rows are omitted where Labs modeled data is thin."

    key_note = (
        "These numbers are illustrative starting points, not exact commitments — "
        "final targets will vary based on discussion, scope, and resources."
    )

    return {
        "title": "6-Month Projections — Today vs. Target",
        "subtitle": disclaimer,
        "takeaway": key_note,
        "horizon": "6 months",
        "rows": rows,
    }


def _recompute_change(row: dict[str, Any]) -> None:
    key = row.get("key")
    today_raw = row.get("today_raw")
    target_raw = row.get("target_raw")
    if key == "cwv":
        return
    if key in ("organic_traffic", "top10_keywords", "tracked_keywords"):
        try:
            t = float(today_raw) if today_raw is not None else None
            g = float(target_raw) if target_raw is not None else None
        except (TypeError, ValueError):
            t = g = None
        change, tone = _pct_change(t, g)
    elif key == "mobile_performance":
        change, tone = _pts_change(
            _int(today_raw), _int(target_raw) if target_raw is not None else None
        )
    elif key == "ai_visibility":
        change, tone = _pts_change(_int(today_raw), _int(target_raw))
    else:
        change, tone = _pts_change(
            _int(today_raw) if today_raw is not None else None,
            _int(target_raw) if target_raw is not None else None,
        )
    row["change"] = change
    row["change_tone"] = tone


def apply_projection_edits(
    slide: dict[str, Any], edits: Optional[list[dict[str, Any]]]
) -> dict[str, Any]:
    """Merge operator target edits keyed by row key; recompute change column."""
    if not slide or not edits:
        return slide or {}
    by_key = {
        str(e.get("key")): str(e.get("target") or "").strip()
        for e in edits
        if e.get("key") and e.get("target") is not None
    }
    rows = []
    for row in slide.get("rows") or []:
        row = dict(row)
        key = row.get("key")
        if key in by_key and row.get("editable", True):
            row["target"] = by_key[key]
            raw = by_key[key]
            if key in ("site_health",):
                row["target_raw"] = _int(str(raw).replace("%", "").split()[0])
            elif key == "mobile_performance":
                row["target_raw"] = _int(str(raw).split("/")[0].strip())
            elif key == "ai_visibility":
                row["target_raw"] = _int(str(raw).split("/")[0].strip())
            elif key == "authority":
                row["target_raw"] = _int(raw)
            elif key in ("top10_keywords", "tracked_keywords"):
                cleaned = raw.replace(",", "").replace("K", "000").replace("M", "000000")
                try:
                    row["target_raw"] = int(float(cleaned))
                except ValueError:
                    pass
            elif key == "organic_traffic":
                cleaned = raw.replace("/mo", "").replace(",", "").strip()
                mult = 1.0
                if cleaned.upper().endswith("K"):
                    mult = 1000.0
                    cleaned = cleaned[:-1]
                elif cleaned.upper().endswith("M"):
                    mult = 1_000_000.0
                    cleaned = cleaned[:-1]
                try:
                    row["target_raw"] = float(cleaned) * mult
                except ValueError:
                    pass
            _recompute_change(row)
        _clamp_row_target(row)
        rows.append(row)
    out = dict(slide)
    out["rows"] = rows
    return out
