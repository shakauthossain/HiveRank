"""SEO Snapshot pipeline: pull data, score, draft top 5, persist for human review."""

from __future__ import annotations

import asyncio
import os
from datetime import datetime
from typing import Any, Optional

import httpx

from app.database import SessionLocal, close_db
from app.models import Snapshot
from app.services.credits import add_user_credit, as_cost
from app.services.dataforseo_client import (
    DataForSeoClient,
    DataForSeoError,
    all_results,
    first_result,
)
from app.services.snapshot_health import (
    brand_label,
    build_authority_slide,
    build_health_snapshot,
    fetch_ai_signals,
    market_name,
)
from app.services.snapshot_citations import build_citations_slide
from app.services.snapshot_crawl import build_crawlability_slide, build_site_audit_slide
from app.services.snapshot_geo import build_geo_slide
from app.services.snapshot_onpage import build_onpage_slide
from app.services.snapshot_projections import apply_projection_edits, build_projections_slide
from app.services.snapshot_performance import build_performance_slide
from app.services.snapshot_rankings import buckets_from_metrics, build_rankings_slide
from app.services.snapshot_scoring import (
    authority_score,
    content_score,
    draft_top_fixes,
    is_thin_labs,
    technical_score,
    visibility_score,
)
from app.services.speed_service import fetch_pagespeed_data_sync

PAGESPEED_API_KEY = os.getenv("PAGESPEED_API_KEY")
ONPAGE_MAX_PAGES = int(os.getenv("SNAPSHOT_ONPAGE_MAX_PAGES", "100"))
ONPAGE_POLL_SECONDS = int(os.getenv("SNAPSHOT_ONPAGE_POLL_SECONDS", "5"))
ONPAGE_POLL_ATTEMPTS = int(os.getenv("SNAPSHOT_ONPAGE_POLL_ATTEMPTS", "72"))  # ~6 min at 5s
DEFAULT_BOOKING_URL = os.getenv("SNAPSHOT_BOOKING_URL", "https://notionhive.com/")


def _fmt_num(value: Optional[float]) -> str:
    if value is None:
        return "—"
    try:
        n = float(value)
    except (TypeError, ValueError):
        return "—"
    abs_n = abs(n)
    if abs_n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M".replace(".0M", "M")
    if abs_n >= 1_000:
        return f"{n / 1_000:.1f}K".replace(".0K", "K")
    if abs_n >= 100:
        return f"{int(round(n))}"
    if n == int(n):
        return str(int(n))
    return f"{n:.1f}"


def _ms_display(ms: Optional[float]) -> str:
    if ms is None:
        return "N/A"
    if ms >= 1000:
        return f"{ms / 1000:.1f}s"
    return f"{int(round(ms))}ms"


def _lcp_status(ms: Optional[float]) -> str:
    if ms is None:
        return "na"
    if ms < 2500:
        return "pass"
    if ms < 4000:
        return "warning"
    return "fail"


def _inp_status(ms: Optional[float]) -> str:
    if ms is None:
        return "na"
    if ms < 200:
        return "pass"
    if ms < 500:
        return "warning"
    return "fail"


def _tbt_status(ms: Optional[float]) -> str:
    if ms is None:
        return "na"
    if ms < 200:
        return "pass"
    if ms < 600:
        return "warning"
    return "fail"


def _cls_status(value: Optional[float]) -> str:
    if value is None:
        return "na"
    if value < 0.1:
        return "pass"
    if value < 0.25:
        return "warning"
    return "fail"


def extract_cwv(raw: Optional[dict], url: str) -> dict:
    bundle = extract_psi(raw, url)
    return {
        "url": bundle.get("url") or url,
        "final_url": bundle.get("final_url"),
        "perf_score": bundle.get("perf_score"),
        "lcp": bundle.get("lcp") or "N/A",
        "lcp_ms": bundle.get("lcp_ms"),
        "lcp_status": bundle.get("lcp_status") or "na",
        "inp": bundle.get("inp") or "N/A",
        "inp_ms": bundle.get("inp_ms"),
        "inp_status": bundle.get("inp_status") or "na",
        "cls": bundle.get("cls") or "N/A",
        "cls_raw": bundle.get("cls_raw"),
        "cls_status": bundle.get("cls_status") or "na",
        "tbt": bundle.get("tbt"),
        "tbt_ms": bundle.get("tbt_ms"),
        "tbt_status": bundle.get("tbt_status"),
        "field": bundle.get("field"),
        "causes": bundle.get("causes") or [],
        "field_overall": bundle.get("field_overall"),
        "seo_score": bundle.get("seo_score"),
    }


def _crux_category(raw: Optional[str]) -> str:
    cat = (raw or "").upper()
    if cat == "FAST":
        return "pass"
    if cat == "AVERAGE":
        return "warning"
    if cat in ("SLOW", "NONE"):
        return "fail" if cat == "SLOW" else "na"
    return "na"


def _crux_label(status: str) -> str:
    return {
        "pass": "Good",
        "warning": "Needs Improvement",
        "fail": "Poor",
        "na": "n/a",
    }.get(status, "n/a")


def _parse_crux(block: Optional[dict]) -> Optional[dict]:
    if not isinstance(block, dict):
        return None
    metrics = block.get("metrics") or {}
    if not metrics:
        return None

    def metric(keys: tuple[str, ...], kind: str) -> dict:
        data = {}
        for key in keys:
            if key in metrics:
                data = metrics.get(key) or {}
                break
        percentile = data.get("percentile")
        status = _crux_category(data.get("category"))
        display = "n/a"
        raw_val = None
        if isinstance(percentile, (int, float)):
            if kind == "cls":
                raw_val = percentile / 100.0 if percentile > 5 else float(percentile)
                display = f"{raw_val:.2f}"
            else:
                raw_val = float(percentile)
                display = _ms_display(raw_val)
        return {
            "display": display,
            "raw": raw_val,
            "status": status,
            "label": _crux_label(status),
        }

    overall = _crux_category(block.get("overall_category"))
    parsed = {
        "lcp": metric(("LARGEST_CONTENTFUL_PAINT_MS",), "ms"),
        "inp": metric(
            ("INTERACTION_TO_NEXT_PAINT", "EXPERIMENTAL_INTERACTION_TO_NEXT_PAINT"),
            "ms",
        ),
        "cls": metric(("CUMULATIVE_LAYOUT_SHIFT_SCORE",), "cls"),
        "overall": overall,
        "overall_label": _crux_label(overall) if overall != "na" else "n/a",
    }
    if all(parsed[k]["status"] == "na" for k in ("lcp", "inp", "cls")):
        return None
    return parsed


CAUSE_AUDITS = (
    ("lcp-lazy-loaded", "a lazy-loaded LCP image"),
    ("unsized-images", "images without explicit width/height"),
    ("non-composited-animations", "non-composited animations"),
    ("layout-shift-elements", "elements that shift layout"),
    ("uses-rel-preconnect", "slow third-party origin connections"),
    ("prioritize-lcp-image", "the LCP image is not prioritized"),
    ("render-blocking-resources", "render-blocking CSS/JS"),
)


def extract_psi(raw: Optional[dict], url: str) -> dict:
    empty_field = None
    if not raw:
        return {
            "url": url,
            "perf_score": None,
            "lcp": "N/A",
            "lcp_status": "na",
            "inp": "N/A",
            "inp_status": "na",
            "cls": "N/A",
            "cls_status": "na",
            "tbt": "N/A",
            "tbt_status": "na",
            "field": empty_field,
            "causes": [],
            "seo_score": None,
        }
    lhr = raw.get("lighthouseResult") or {}
    audits = lhr.get("audits") or {}
    cats = lhr.get("categories") or {}
    perf = (cats.get("performance") or {}).get("score")
    perf_score = round(perf * 100) if isinstance(perf, (int, float)) else None
    seo = (cats.get("seo") or {}).get("score")
    seo_score = round(seo * 100) if isinstance(seo, (int, float)) else None

    def numeric(audit_id: str) -> Optional[float]:
        val = (audits.get(audit_id) or {}).get("numericValue")
        return float(val) if isinstance(val, (int, float)) else None

    lcp = numeric("largest-contentful-paint")
    inp = numeric("interaction-to-next-paint")
    cls = numeric("cumulative-layout-shift")
    tbt = numeric("total-blocking-time")
    cls_display = f"{cls:.2f}" if cls is not None else "N/A"
    field = _parse_crux(raw.get("loadingExperience")) or _parse_crux(
        raw.get("originLoadingExperience")
    )
    field_source = "url" if _parse_crux(raw.get("loadingExperience")) else (
        "origin" if field else None
    )
    if field:
        field = {**field, "source": field_source}

    causes = []
    for audit_id, phrase in CAUSE_AUDITS:
        audit = audits.get(audit_id) or {}
        score = audit.get("score")
        if score is None:
            continue
        try:
            if float(score) < 0.9:
                causes.append(phrase)
        except (TypeError, ValueError):
            continue

    return {
        "url": url,
        "final_url": lhr.get("finalUrl") or lhr.get("requestedUrl") or url,
        "perf_score": perf_score,
        "lcp": _ms_display(lcp) if lcp is not None else "N/A",
        "lcp_ms": lcp,
        "lcp_status": _lcp_status(lcp),
        "inp": _ms_display(inp) if inp is not None else "N/A",
        "inp_ms": inp,
        "inp_status": _inp_status(inp),
        "cls": cls_display,
        "cls_raw": cls,
        "cls_status": _cls_status(cls),
        "tbt": _ms_display(tbt) if tbt is not None else "N/A",
        "tbt_ms": tbt,
        "tbt_status": _tbt_status(tbt),
        "field": field,
        "causes": causes[:4],
        "field_overall": (field or {}).get("overall"),
        "seo_score": seo_score,
    }


def _organic_rows(payload: dict) -> list[dict]:
    result = first_result(payload)
    if not result:
        return []
    items = result.get("items") or []
    rows = []
    for item in items:
        organic = ((item or {}).get("metrics") or {}).get("organic") or {}
        if not organic:
            continue
        rows.append(
            {
                "location_code": item.get("location_code"),
                "language_code": item.get("language_code"),
                "organic": organic,
            }
        )
    if rows:
        return rows
    organic = ((result.get("metrics") or {}).get("organic") or {})
    if not organic:
        return []
    return [
        {
            "location_code": result.get("location_code"),
            "language_code": result.get("language_code"),
            "organic": organic,
        }
    ]


def _organic_from_overview(payload: dict) -> Optional[dict]:
    rows = _organic_rows(payload)
    if not rows:
        return None

    def total(key: str) -> float:
        return sum(float(row["organic"].get(key) or 0) for row in rows)

    primary = max(
        rows,
        key=lambda row: (
            float(row["organic"].get("etv") or 0),
            float(row["organic"].get("count") or 0),
        ),
    )
    po = primary["organic"]
    etv = total("etv")
    count = total("count")
    cost = po.get("estimated_paid_traffic_cost")
    try:
        cost_n = float(cost) if cost is not None else None
    except (TypeError, ValueError):
        cost_n = None

    return {
        "scope": "global",
        "markets": len(rows),
        "etv": etv,
        "count": int(round(count)),
        "pos_1": int(round(total("pos_1"))),
        "pos_2_3": int(round(total("pos_2_3"))),
        "pos_4_10": int(round(total("pos_4_10"))),
        "pos_11_20": int(round(total("pos_11_20"))),
        "etv_display": _fmt_num(etv),
        "count_display": _fmt_num(count),
        "primary_location_code": primary.get("location_code"),
        "primary_language_code": primary.get("language_code"),
        "count_primary": int(round(float(po.get("count") or 0))),
        "etv_primary": float(po.get("etv") or 0),
        "primary": {
            "location_code": primary.get("location_code"),
            "language_code": primary.get("language_code"),
            "market": market_name(primary.get("location_code")),
            "count": int(round(float(po.get("count") or 0))),
            "etv": float(po.get("etv") or 0),
            "etv_display": _fmt_num(po.get("etv")),
            "estimated_paid_traffic_cost": cost_n,
            "metrics": po,
            "buckets": buckets_from_metrics(po),
        },
    }


def _quick_wins_from_ranked(payload: dict) -> list[dict]:
    result = first_result(payload)
    if not result:
        return []
    wins = []
    for item in result.get("items") or []:
        kd = item.get("keyword_data") or {}
        info = kd.get("keyword_info") or {}
        serp = (item.get("ranked_serp_element") or {}).get("serp_item") or {}
        keyword = kd.get("keyword")
        position = serp.get("rank_group") or serp.get("rank_absolute")
        if not keyword or position is None:
            continue
        wins.append(
            {
                "keyword": keyword,
                "position": int(position),
                "volume": info.get("search_volume"),
                "volume_display": _fmt_num(info.get("search_volume")),
                "etv": serp.get("etv"),
                "etv_display": _fmt_num(serp.get("etv")),
                "url": serp.get("url"),
            }
        )
    return wins[:12]


def _backlinks_profile(payload: Optional[dict]) -> dict:
    empty = {"rank": None, "backlinks": None, "referring_domains": None}
    if not payload:
        return empty
    result = first_result(payload)
    if not result:
        return empty

    def as_int(key: str) -> Optional[int]:
        val = result.get(key)
        if val is None:
            val = (result.get("metrics") or {}).get(key)
        try:
            return int(val) if val is not None else None
        except (TypeError, ValueError):
            return None

    return {
        "rank": as_int("rank"),
        "backlinks": as_int("backlinks"),
        "referring_domains": as_int("referring_domains"),
        "spam_score": as_int("backlinks_spam_score"),
    }


def _norm_host(domain: Optional[str]) -> str:
    return (domain or "").lower().replace("www.", "").strip().strip(".")


# Platforms / mega properties that Labs often returns as "competitors" via
# keyword overlap — useless for a mid-market sales leave-behind chart.
MEGA_PEER_DOMAINS = frozenset(
    {
        "facebook.com",
        "fb.com",
        "meta.com",
        "youtube.com",
        "youtu.be",
        "google.com",
        "google.co.uk",
        "google.com.bd",
        "wikipedia.org",
        "twitter.com",
        "x.com",
        "instagram.com",
        "linkedin.com",
        "amazon.com",
        "amazon.co.uk",
        "apple.com",
        "microsoft.com",
        "reddit.com",
        "tiktok.com",
        "pinterest.com",
        "yahoo.com",
        "bing.com",
        "baidu.com",
        "yandex.ru",
        "yandex.com",
        "wordpress.com",
        "blogspot.com",
        "blogger.com",
        "medium.com",
        "github.com",
        "play.google.com",
        "apps.apple.com",
        "netflix.com",
        "spotify.com",
        "whatsapp.com",
        "telegram.org",
        "discord.com",
        "quora.com",
        "imgur.com",
        "tumblr.com",
        "craigslist.org",
        "ebay.com",
        "walmart.com",
        "cnn.com",
        "bbc.com",
        "bbc.co.uk",
        "nytimes.com",
        "forbes.com",
        "businessinsider.com",
    }
)


def _is_mega_peer(domain: str) -> bool:
    host = _norm_host(domain)
    if not host:
        return True
    if host in MEGA_PEER_DOMAINS:
        return True
    # Subdomains of mega properties (m.facebook.com, en.wikipedia.org)
    return any(host.endswith("." + mega) for mega in MEGA_PEER_DOMAINS)


def _competitor_domains(payload: Optional[dict], prospect: str, limit: int = 5) -> list[str]:
    """Raw Labs competitors_domain domains (unfiltered except self)."""
    if not payload:
        return []
    prospect_n = _norm_host(prospect)
    result = first_result(payload) or {}
    rows = result.get("items") or []
    if not rows:
        rows = all_results(payload)
    out: list[str] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        nested = row.get("items")
        candidates = nested if isinstance(nested, list) else [row]
        for item in candidates:
            if not isinstance(item, dict):
                continue
            d = _norm_host(item.get("domain"))
            if not d or d == prospect_n or d.endswith("." + prospect_n):
                continue
            if d not in out:
                out.append(d)
            if len(out) >= limit:
                return out
    return out


def _filter_peers_similar_rank(
    candidates: list[str],
    rank_map: dict[str, int],
    prospect_rank: Optional[int],
    limit: int = 5,
) -> list[str]:
    """Drop mega sites and Fortune-500-scale peers; keep similar authority band."""
    scored: list[tuple[int, str, int]] = []
    for host in candidates:
        if _is_mega_peer(host):
            continue
        rank = rank_map.get(host)
        if rank is None:
            continue
        # Mid-market prospect vs near-max authority giants
        if prospect_rank is not None and prospect_rank < 75 and rank >= 95:
            continue
        if prospect_rank is not None and prospect_rank < 55 and rank >= 90:
            continue
        gap = abs(rank - prospect_rank) if prospect_rank is not None else 0
        scored.append((gap, host, rank))

    scored.sort(key=lambda row: (row[0], -row[2]))

    def take(max_gap: Optional[int]) -> list[str]:
        picked: list[str] = []
        for gap, host, _rank in scored:
            if max_gap is not None and gap > max_gap:
                continue
            if host not in picked:
                picked.append(host)
            if len(picked) >= limit:
                break
        return picked

    tight = take(30)
    if len(tight) >= 3:
        return tight
    mid = take(45)
    if len(mid) >= 2:
        return mid
    # Closest remaining non-mega peers (still excludes rank≥95 when prospect < 75)
    return take(None)[:limit]

def _ranks_from_bulk(payload: Optional[dict]) -> dict[str, int]:
    mapping: dict[str, int] = {}
    if not payload:
        return mapping
    rows = all_results(payload)
    result = first_result(payload)
    if result and isinstance(result.get("items"), list):
        rows = result["items"]
    for row in rows:
        if not isinstance(row, dict):
            continue
        host = _norm_host(row.get("target") or row.get("domain"))
        try:
            rank = int(row["rank"]) if row.get("rank") is not None else None
        except (TypeError, ValueError):
            rank = None
        if host and rank is not None:
            mapping[host] = rank
    return mapping


def _top_referring_domains(payload: dict) -> list[dict]:
    result = first_result(payload)
    if not result:
        return []
    rows = []
    for item in result.get("items") or []:
        domain = item.get("domain")
        if not domain:
            continue
        rows.append(
            {
                "domain": domain,
                "rank": item.get("rank"),
                "backlinks": None,
                "referring_domains": item.get("referring_domains"),
            }
        )
    return rows[:8]


def _onpage_issues(onpage: dict, worst_pages: list[dict], thin_data: bool) -> list[dict]:
    metrics = onpage.get("page_metrics") or {}
    checks = metrics.get("checks") or {}
    issues = []

    def add(severity: str, title: str, detail: str) -> None:
        issues.append({"severity": severity, "title": title, "detail": detail})

    broken = int(metrics.get("broken_links") or 0)
    if broken:
        add("high", "Broken links", f"{broken} broken link(s) in the crawl.")
    dup_t = int(metrics.get("duplicate_title") or checks.get("duplicate_title_tag") or 0)
    if dup_t:
        add("high", "Duplicate titles", f"{dup_t} page(s) share a title tag.")
    dup_d = int(metrics.get("duplicate_description") or checks.get("duplicate_description") or 0)
    if dup_d:
        add("medium", "Duplicate meta descriptions", f"{dup_d} page(s) share a description.")
    no_title = int(checks.get("no_title") or 0)
    if no_title:
        add("high", "Missing titles", f"{no_title} page(s) have no title tag.")
    no_desc = int(checks.get("no_description") or 0)
    if no_desc:
        add("medium", "Missing meta descriptions", f"{no_desc} page(s) have no description.")
    no_h1 = int(checks.get("no_h1_tag") or 0)
    if no_h1:
        add("medium", "Missing H1", f"{no_h1} page(s) have no H1.")
    low = int(checks.get("low_content_rate") or 0)
    if low:
        add("medium", "Thin content", f"{low} page(s) flagged for low content.")
    is_4xx = int(checks.get("is_4xx_code") or 0)
    if is_4xx:
        add("high", "4xx pages", f"{is_4xx} HTML page(s) returned a 4xx status.")
    is_5xx = int(checks.get("is_5xx_code") or 0)
    if is_5xx:
        add("high", "5xx pages", f"{is_5xx} HTML page(s) returned a 5xx status.")

    if thin_data:
        for page in worst_pages[:8]:
            url = page.get("url")
            score = page.get("onpage_score")
            if url:
                add(
                    "medium",
                    "Low on-page score",
                    f"{url} (score {score if score is not None else 'n/a'}).",
                )

    return issues[:16] if thin_data else issues[:8]


def _worst_pages(payload: dict) -> list[dict]:
    result = first_result(payload)
    if not result:
        return []
    pages = []
    for item in result.get("items") or []:
        meta = item.get("meta") or {}
        pages.append(
            {
                "url": item.get("url"),
                "status_code": item.get("status_code"),
                "title": (meta.get("title") or item.get("title")),
                "onpage_score": item.get("onpage_score"),
            }
        )
    return pages[:10]


def _persist(snapshot_pk: int, **fields) -> Optional[Snapshot]:
    db = SessionLocal()
    try:
        snapshot = db.query(Snapshot).filter(Snapshot.id == snapshot_pk).first()
        if not snapshot:
            return None
        prev_cost = as_cost(getattr(snapshot, "api_cost_usd", 0))
        for key, value in fields.items():
            setattr(snapshot, key, value)
        # Attribute DFS spend once when a pull finishes with a cost.
        new_cost = as_cost(getattr(snapshot, "api_cost_usd", 0))
        if (
            fields.get("status") == "review"
            and new_cost > 0
            and prev_cost <= 0
            and snapshot.user_id
        ):
            add_user_credit(db, snapshot.user_id, new_cost)
        db.commit()
        db.refresh(snapshot)
        db.expunge(snapshot)
        return snapshot
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass
        raise
    finally:
        close_db(db)


def _set_progress(snapshot_pk: int, text: str) -> None:
    _persist(snapshot_pk, progress=text)


async def _safe(coro, fallback=None):
    try:
        return await coro, None
    except Exception as exc:
        return fallback, str(exc)


async def process_snapshot(snapshot_pk: int) -> None:
    client: Optional[httpx.AsyncClient] = None
    try:
        snapshot = _persist(
            snapshot_pk,
            status="running",
            progress="Starting data pull",
            error_message=None,
        )
        if not snapshot:
            return

        prospect_url = snapshot.prospect_url
        prospect_domain = snapshot.prospect_domain
        loc = snapshot.location_code or 2840
        lang = snapshot.language_code or "en"
        booking_url = snapshot.booking_url or DEFAULT_BOOKING_URL
        competitor_mode = (getattr(snapshot, "competitor_mode", None) or "auto").lower()
        if competitor_mode not in ("auto", "manual"):
            competitor_mode = "auto"
        manual_competitors = [
            _norm_host(d)
            for d in (getattr(snapshot, "competitor_urls", None) or [])
            if _norm_host(d)
        ][:3]
        if competitor_mode == "manual" and not manual_competitors:
            legacy = _norm_host(getattr(snapshot, "competitor_domain", None) or "")
            if legacy and legacy != _norm_host(prospect_domain):
                manual_competitors = [legacy]

        client = httpx.AsyncClient()
        dfs = DataForSeoClient.from_env(client)

        # Start OnPage crawl first so it overlaps PSI + Labs + backlinks.
        _set_progress(snapshot_pk, "Starting on-page crawl (up to 100 pages)")
        posted, post_err = await _safe(
            dfs.onpage_task_post(prospect_url, ONPAGE_MAX_PAGES)
        )
        task_id = None
        if posted:
            tasks = posted.get("tasks") or []
            if tasks:
                task_id = tasks[0].get("id")

        _set_progress(snapshot_pk, "Fetching Core Web Vitals")
        mobile_task = asyncio.to_thread(
            fetch_pagespeed_data_sync, prospect_url, PAGESPEED_API_KEY, "mobile"
        )
        desktop_task = asyncio.to_thread(
            fetch_pagespeed_data_sync, prospect_url, PAGESPEED_API_KEY, "desktop"
        )
        ai_task = fetch_ai_signals(client, prospect_url)
        mobile_res, desktop_res, ai_res = await asyncio.gather(
            mobile_task, desktop_task, ai_task, return_exceptions=True
        )
        raw_mobile = None if isinstance(mobile_res, Exception) else mobile_res
        raw_desktop = None if isinstance(desktop_res, Exception) else desktop_res
        ai_signals = {} if isinstance(ai_res, Exception) else (ai_res or {})
        # Desktop PSI is required on the deck — retry once if the parallel call failed
        # (Google often rate-limits concurrent mobile+desktop).
        if not raw_desktop or not (raw_desktop.get("lighthouseResult") or {}).get(
            "categories"
        ):
            _set_progress(snapshot_pk, "Retrying desktop PageSpeed")
            try:
                raw_desktop = await asyncio.to_thread(
                    fetch_pagespeed_data_sync,
                    prospect_url,
                    PAGESPEED_API_KEY,
                    "desktop",
                )
            except Exception:
                raw_desktop = None
        if not raw_mobile or not (raw_mobile.get("lighthouseResult") or {}).get(
            "categories"
        ):
            try:
                raw_mobile = await asyncio.to_thread(
                    fetch_pagespeed_data_sync,
                    prospect_url,
                    PAGESPEED_API_KEY,
                    "mobile",
                )
            except Exception:
                raw_mobile = None
        psi_mobile = extract_psi(raw_mobile, prospect_url)
        psi_desktop = extract_psi(raw_desktop, prospect_url)
        cwv = extract_cwv(raw_mobile, prospect_url)

        organic = None
        _set_progress(snapshot_pk, "Fetching estimated organic visibility (global markets)")
        overview, overview_err = await _safe(dfs.domain_rank_overview(prospect_domain))
        if not overview:
            overview, overview_err = await _safe(
                dfs.domain_rank_overview(prospect_domain, loc, lang)
            )
        if overview:
            organic = _organic_from_overview(overview)
            primary_loc = (organic or {}).get("primary_location_code")
            primary_lang = (organic or {}).get("primary_language_code")
            if primary_loc:
                loc = int(primary_loc)
            if primary_lang:
                lang = str(primary_lang)[:8]
            if primary_loc or primary_lang:
                _persist(snapshot_pk, location_code=loc, language_code=lang)
        thin = is_thin_labs(organic)

        quick_wins: list[dict] = []
        top_keywords: list[dict] = []

        # Parallel: keywords (when dense) + backlinks + referring domains
        # (+ Labs competitors only in auto mode).
        _set_progress(snapshot_pk, "Fetching rankings, backlinks, and peers")
        parallel = [
            _safe(dfs.backlinks_summary(prospect_domain)),
            _safe(dfs.referring_domains(prospect_domain)),
        ]
        fetch_labs_peers = competitor_mode == "auto"
        if fetch_labs_peers:
            # Pull a wide set — we filter mega sites + similar rank band after bulk_ranks.
            parallel.append(
                _safe(dfs.competitors_domain(prospect_domain, loc, lang, 25))
            )
        if not thin:
            parallel.extend(
                [
                    _safe(dfs.ranked_keywords(prospect_domain, loc, lang)),
                    _safe(dfs.ranked_keywords_by_traffic(prospect_domain, loc, lang, 10)),
                ]
            )
        else:
            if overview_err:
                _set_progress(
                    snapshot_pk,
                    "Little keyword data — expanding technical findings",
                )

        gathered = await asyncio.gather(*parallel)
        p_sum, _ = gathered[0]
        rd_live, _ = gathered[1]
        idx = 2
        comp_payload = None
        if fetch_labs_peers:
            comp_payload, _ = gathered[idx]
            idx += 1
        if not thin:
            ranked, _ = gathered[idx]
            top_raw, _ = gathered[idx + 1]
            if ranked:
                quick_wins = _quick_wins_from_ranked(ranked)
            if top_raw:
                top_keywords = _quick_wins_from_ranked(top_raw)[:8]

        bl_profile = _backlinks_profile(p_sum)
        prospect_rd = bl_profile.get("referring_domains")
        top_rd: list[dict] = []
        if rd_live:
            top_rd = _top_referring_domains(rd_live)

        peer_source = "manual" if competitor_mode == "manual" else "labs_filtered"
        peer_domains: list[str] = []
        rank_map: dict[str, int] = {}

        if competitor_mode == "manual":
            peer_domains = [
                d
                for d in manual_competitors
                if d and d != _norm_host(prospect_domain)
            ][:3]
            bulk_targets = [prospect_domain] + peer_domains
            bulk_payload, _ = await _safe(dfs.bulk_ranks(bulk_targets))
            if bulk_payload:
                rank_map = _ranks_from_bulk(bulk_payload)
        else:
            candidates = _competitor_domains(comp_payload, prospect_domain, 25)
            candidates = [d for d in candidates if not _is_mega_peer(d)]
            # Rank prospect first from summary, then score candidates.
            bulk_targets = [prospect_domain] + candidates[:20]
            bulk_payload, _ = await _safe(dfs.bulk_ranks(bulk_targets))
            if bulk_payload:
                rank_map = _ranks_from_bulk(bulk_payload)
            if bl_profile.get("rank") is None and _norm_host(prospect_domain) in rank_map:
                bl_profile["rank"] = rank_map[_norm_host(prospect_domain)]
            prospect_rank = bl_profile.get("rank")
            if prospect_rank is None:
                prospect_rank = rank_map.get(_norm_host(prospect_domain))
            peer_domains = _filter_peers_similar_rank(
                candidates, rank_map, prospect_rank, limit=5
            )

        if bl_profile.get("rank") is None and _norm_host(prospect_domain) in rank_map:
            bl_profile["rank"] = rank_map[_norm_host(prospect_domain)]
        peers = []
        for host in peer_domains:
            peers.append(
                {
                    "domain": host,
                    "label": brand_label(host),
                    "rank": rank_map.get(host),
                    "is_you": False,
                }
            )

        # OnPage has been crawling during the pulls above — poll until finished.
        # Summary is GET /on_page/summary/{id}; empty result means the poll never
        # successfully read the task (do not treat zeros as a clean site).
        onpage: dict = {}
        worst_pages: list[dict] = []
        onpage_poll_error: Optional[str] = None
        if task_id:
            _set_progress(snapshot_pk, "Waiting for on-page crawl to finish")
            summary_payload = None
            for _ in range(ONPAGE_POLL_ATTEMPTS):
                summary_payload, poll_err = await _safe(dfs.onpage_summary(task_id))
                if poll_err:
                    onpage_poll_error = poll_err
                result = first_result(summary_payload) if summary_payload else None
                progress = (result or {}).get("crawl_progress")
                if progress == "finished":
                    onpage_poll_error = None
                    break
                crawled = ((result or {}).get("crawl_status") or {}).get(
                    "pages_crawled"
                )
                if crawled:
                    _set_progress(
                        snapshot_pk,
                        f"Crawling on-page issues ({crawled} pages so far)",
                    )
                await asyncio.sleep(ONPAGE_POLL_SECONDS)
            if summary_payload:
                onpage = first_result(summary_payload) or {}
            if not onpage.get("crawl_status") and onpage_poll_error:
                onpage = {"error": onpage_poll_error}
            pages_payload, _ = await _safe(dfs.onpage_pages(task_id))
            if pages_payload:
                worst_pages = _worst_pages(pages_payload)
        elif post_err:
            onpage = {"error": post_err}

        issues = _onpage_issues(onpage, worst_pages, thin)
        vis = visibility_score(organic)
        tech = technical_score(cwv, onpage)
        cont = content_score(onpage)
        auth = authority_score(prospect_rd)

        crawl_status = onpage.get("crawl_status") or {}
        page_metrics = onpage.get("page_metrics") or {}

        technical_block = {
            **cwv,
            "pages_crawled": crawl_status.get("pages_crawled"),
            "onpage_score": page_metrics.get("onpage_score"),
            "broken_links": page_metrics.get("broken_links") or 0,
            "duplicate_titles": page_metrics.get("duplicate_title") or 0,
            "duplicate_descriptions": page_metrics.get("duplicate_description") or 0,
            "issues": issues,
            "worst_pages": worst_pages if thin else worst_pages[:5],
            "mobile": psi_mobile,
            "desktop": psi_desktop,
        }

        payload = {
            "prospect_url": prospect_url,
            "prospect_domain": prospect_domain,
            "date": datetime.utcnow().strftime("%d %B %Y"),
            "location_code": loc,
            "language_code": lang,
            "organic_scope": "global",
            "booking_url": booking_url,
            "thin_data": thin,
            "scores": {
                "visibility": vis,
                "technical": tech,
                "content": cont,
                "authority": auth,
            },
            "organic": organic,
            "quick_wins": quick_wins,
            "top_keywords": top_keywords,
            "technical": technical_block,
            "onpage": {
                "crawl_status": crawl_status,
                "page_metrics": page_metrics,
            },
            "authority": {
                "prospect_referring_domains": prospect_rd,
                "prospect_display": _fmt_num(prospect_rd),
                "rank": bl_profile.get("rank"),
                "backlinks": bl_profile.get("backlinks"),
                "spam_score": bl_profile.get("spam_score"),
                "top_referring_domains": top_rd,
                "peers": peers,
                "peer_source": peer_source,
                "competitor_mode": competitor_mode,
            },
            "ai": ai_signals or {},
            "onpage_max_pages": ONPAGE_MAX_PAGES,
            "included_slides": (
                [
                    "cover",
                    "scorecard",
                    "authority",
                    "technical_extra",
                    "performance",
                    "onpage",
                    "geo",
                    "citations",
                    "site_audit",
                    "crawlability",
                    "projections",
                    "priorities",
                ]
                if thin
                else [
                    "cover",
                    "scorecard",
                    "authority",
                    "rankings",
                    "performance",
                    "onpage",
                    "geo",
                    "citations",
                    "site_audit",
                    "crawlability",
                    "quick_wins",
                    "projections",
                    "priorities",
                ]
            ),
        }
        payload["health"] = build_health_snapshot(payload)
        payload["authority_slide"] = build_authority_slide(payload)
        payload["rankings_slide"] = build_rankings_slide(payload)
        payload["performance_slide"] = build_performance_slide(payload)
        payload["onpage_slide"] = build_onpage_slide(payload)
        payload["geo_slide"] = build_geo_slide(payload)
        payload["citations_slide"] = build_citations_slide(payload)
        payload["site_audit_slide"] = build_site_audit_slide(payload)
        payload["crawlability_slide"] = build_crawlability_slide(payload)
        payload["projections_slide"] = build_projections_slide(payload)
        payload["top_fixes"] = draft_top_fixes(payload)

        _persist(
            snapshot_pk,
            payload=payload,
            top_fixes=payload["top_fixes"],
            thin_data=thin,
            api_cost_usd=round(dfs.total_cost, 6),
            usage_log=dfs.usage,
            status="review",
            progress="Ready for review",
            error_message=None,
        )
    except DataForSeoError as exc:
        _fail(snapshot_pk, str(exc))
    except Exception as exc:
        _fail(snapshot_pk, str(exc))
    finally:
        if client:
            await client.aclose()


def _fail(snapshot_pk: int, message: str) -> None:
    try:
        _persist(
            snapshot_pk,
            status="failed",
            error_message=message[:2000],
            progress="Failed",
        )
    except Exception:
        pass

