"""Balanced Quick Audit: Labs×1 + Backlinks×1 + Lighthouse×2 + free probes.

Uses DataForSEO Lighthouse (not Google PSI) — Google often exceeds 35s on real
prospect sites from our host. DFS Lighthouse averages ~10–20s and costs ~$0.005
per strategy.

4-slide deck: Cover → SEO Health → Performance & CWV → Ending (priorities).
"""

from __future__ import annotations

import asyncio
import os
import time
import uuid
from datetime import datetime
from typing import Any, Optional

import httpx

from app.services.dataforseo_client import DataForSeoClient, DataForSeoError
from app.services.snapshot_health import build_health_snapshot, fetch_ai_signals
from app.services.snapshot_performance import build_performance_slide
from app.services.snapshot_pptx import build_pptx
from app.services.snapshot_scoring import draft_top_fixes, technical_score, visibility_score
from app.services.snapshot_service import (
    DEFAULT_BOOKING_URL,
    _backlinks_profile,
    _organic_from_overview,
    extract_cwv,
    extract_psi,
)
from app.url_utils import extract_domain, normalize_url

DFS_TIMEOUT_S = 15.0
LIGHTHOUSE_TIMEOUT_S = 55.0


async def _safe(coro):
    try:
        return await coro, None
    except Exception as exc:
        return None, str(exc)


def _psi_ok(raw: Optional[dict]) -> bool:
    return bool(raw and (raw.get("lighthouseResult") or {}).get("categories"))


def _strip_site_health(health: dict) -> dict:
    cards = [
        c
        for c in (health.get("cards") or [])
        if c.get("key") != "site_health"
    ]
    return {**health, "cards": cards}


async def run_quick_audit(url: str, *, reports_dir: str) -> dict[str, Any]:
    started = time.monotonic()
    prospect_url = normalize_url(url)
    prospect_domain = extract_domain(prospect_url)
    if not prospect_domain:
        raise ValueError("A valid domain is required.")

    report_id = str(uuid.uuid4())
    # Lighthouse live can take up to ~60s; keep client open that long.
    async with httpx.AsyncClient(timeout=LIGHTHOUSE_TIMEOUT_S + 5.0) as client:
        try:
            dfs = DataForSeoClient.from_env(client)
        except DataForSeoError as exc:
            raise ValueError(str(exc)) from exc

        # Parallel: Labs + Backlinks + AI + mobile LH + desktop LH.
        # Wall clock ≈ slowest Lighthouse call (~15–40s), not the sum.
        mobile_res, desktop_res, ai_res, labs_pair, bl_pair = await asyncio.gather(
            _safe(
                dfs.lighthouse_live(
                    prospect_url,
                    for_mobile=True,
                    timeout=LIGHTHOUSE_TIMEOUT_S,
                )
            ),
            _safe(
                dfs.lighthouse_live(
                    prospect_url,
                    for_mobile=False,
                    timeout=LIGHTHOUSE_TIMEOUT_S,
                )
            ),
            fetch_ai_signals(client, prospect_url),
            _safe(dfs.domain_rank_overview(prospect_domain)),
            _safe(dfs.backlinks_summary(prospect_domain)),
            return_exceptions=True,
        )

        raw_mobile = None
        raw_desktop = None
        if not isinstance(mobile_res, Exception) and mobile_res:
            raw_mobile, mobile_err = mobile_res
            if mobile_err:
                print(f"--- WARNING: Quick Audit mobile Lighthouse: {mobile_err} ---")
        elif isinstance(mobile_res, Exception):
            print(f"--- WARNING: Quick Audit mobile Lighthouse: {mobile_res} ---")

        if not isinstance(desktop_res, Exception) and desktop_res:
            raw_desktop, desktop_err = desktop_res
            if desktop_err:
                print(f"--- WARNING: Quick Audit desktop Lighthouse: {desktop_err} ---")
        elif isinstance(desktop_res, Exception):
            print(f"--- WARNING: Quick Audit desktop Lighthouse: {desktop_res} ---")

        ai_signals = {} if isinstance(ai_res, Exception) else (ai_res or {})
        overview, labs_err = (None, None)
        if not isinstance(labs_pair, Exception) and labs_pair:
            overview, labs_err = labs_pair
        if labs_err:
            print(f"--- WARNING: Quick Audit Labs: {labs_err} ---")
        p_sum, bl_err = (None, None)
        if not isinstance(bl_pair, Exception) and bl_pair:
            p_sum, bl_err = bl_pair
        if bl_err:
            print(f"--- WARNING: Quick Audit Backlinks: {bl_err} ---")

        # Retry a single missing strategy if we still have time.
        for label, for_mobile, current in (
            ("mobile", True, raw_mobile),
            ("desktop", False, raw_desktop),
        ):
            if _psi_ok(current):
                continue
            left = 70.0 - (time.monotonic() - started)
            if left < 20.0:
                print(f"--- WARNING: Quick Audit {label} Lighthouse retry skipped ---")
                continue
            print(f"--- INFO: Retrying {label} Lighthouse ({left:.0f}s budget) ---")
            retried, err = await _safe(
                dfs.lighthouse_live(
                    prospect_url,
                    for_mobile=for_mobile,
                    timeout=min(LIGHTHOUSE_TIMEOUT_S, left),
                )
            )
            if err:
                print(f"--- WARNING: Quick Audit {label} retry: {err} ---")
            if label == "mobile":
                raw_mobile = retried if _psi_ok(retried) else raw_mobile
            else:
                raw_desktop = retried if _psi_ok(retried) else raw_desktop

        psi_mobile = extract_psi(raw_mobile if _psi_ok(raw_mobile) else None, prospect_url)
        psi_desktop = extract_psi(
            raw_desktop if _psi_ok(raw_desktop) else None, prospect_url
        )
        cwv = extract_cwv(raw_mobile if _psi_ok(raw_mobile) else None, prospect_url)
        organic = _organic_from_overview(overview) if overview else None
        bl_profile = _backlinks_profile(p_sum)

        tech = {
            **(cwv or {}),
            "pages_crawled": None,
            "onpage_score": None,
            "mobile": psi_mobile,
            "desktop": psi_desktop,
            "psi_mobile": psi_mobile,
            "psi_desktop": psi_desktop,
        }
        payload: dict[str, Any] = {
            "deck_mode": "quick",
            "prospect_url": prospect_url,
            "prospect_domain": prospect_domain,
            "date": datetime.utcnow().strftime("%d %B %Y"),
            "booking_url": DEFAULT_BOOKING_URL,
            "thin_data": False,
            "onpage_max_pages": 0,
            "organic": organic or {},
            "authority": {
                "rank": bl_profile.get("rank"),
                "backlinks": bl_profile.get("backlinks"),
                "prospect_referring_domains": bl_profile.get("referring_domains"),
                "spam_score": bl_profile.get("spam_score"),
            },
            "technical": tech,
            "ai": ai_signals,
            "onpage": {},
            "scores": {
                "visibility": visibility_score(organic),
                "technical": technical_score(cwv or {}, {}),
                "authority": bl_profile.get("rank"),
            },
        }
        health = build_health_snapshot(payload)
        payload["health"] = _strip_site_health(health)
        payload["performance_slide"] = build_performance_slide(payload)
        payload["top_fixes"] = draft_top_fixes(payload)

        pptx_name = f"{report_id}_quick.pptx"
        pptx_path = os.path.join(reports_dir, pptx_name)
        build_pptx(payload, pptx_path)

        elapsed_s = round(time.monotonic() - started, 1)
        print(
            f"--- SUCCESS: Quick Audit {prospect_domain} in {elapsed_s}s "
            f"(mobile={psi_mobile.get('perf_score')}, desktop={psi_desktop.get('perf_score')}, "
            f"cost=${dfs.total_cost:.4f}) ---"
        )

        return {
            "id": report_id,
            "url": prospect_url,
            "domain": prospect_domain,
            "type": "quick",
            "payload": payload,
            "health": payload["health"],
            "performance_slide": payload["performance_slide"],
            "top_fixes": payload["top_fixes"],
            "api_cost_usd": round(dfs.total_cost, 6),
            "usage_log": dfs.usage,
            "elapsed_s": elapsed_s,
            "pptx_filename": pptx_name,
            "quick_report_url": f"/reports/{pptx_name}",
            "reused": False,
        }
