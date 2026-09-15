"""Slide 2 health states: real pulled numbers, not the old four computed scores."""

from __future__ import annotations

import asyncio
from typing import Any, Optional
from urllib.parse import urljoin, urlparse

AI_BOTS = (
    "GPTBot",
    "ChatGPT-User",
    "Google-Extended",
    "ClaudeBot",
    "PerplexityBot",
    "Bytespider",
)

LOCATION_LABELS = {
    2036: "BD",
    2124: "CA",
    2250: "FR",
    2276: "DE",
    2356: "IN",
    2360: "ID",
    2372: "IE",
    2392: "JP",
    2458: "MY",
    2528: "NL",
    2554: "NZ",
    2586: "PK",
    2608: "PH",
    2682: "SA",
    2702: "SG",
    2724: "ES",
    2784: "AE",
    2826: "UK",
    2840: "US",
    2792: "TR",
    2076: "BR",
    2158: "CN",
    2710: "ZA",
    2040: "AU",
}

MARKET_NAMES = {
    2036: "Bangladesh",
    2040: "Australia",
    2076: "Brazil",
    2124: "Canada",
    2158: "China",
    2250: "France",
    2276: "Germany",
    2356: "India",
    2360: "Indonesia",
    2372: "Ireland",
    2392: "Japan",
    2458: "Malaysia",
    2528: "Netherlands",
    2554: "New Zealand",
    2586: "Pakistan",
    2608: "Philippines",
    2682: "Saudi Arabia",
    2702: "Singapore",
    2710: "South Africa",
    2724: "Spain",
    2784: "United Arab Emirates",
    2792: "Turkey",
    2826: "United Kingdom",
    2840: "United States",
}


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
        return str(int(round(n)))
    if n == int(n):
        return str(int(n))
    return f"{n:.1f}"


def _int(value: Any) -> Optional[int]:
    try:
        if value is None:
            return None
        return int(round(float(value)))
    except (TypeError, ValueError):
        return None


def _rating(score: Optional[int]) -> str:
    if score is None:
        return "n/a"
    if score >= 70:
        return "Strong"
    if score >= 50:
        return "Good"
    if score >= 30:
        return "Fair"
    return "Weak"


def location_label(code: Any) -> Optional[str]:
    try:
        return LOCATION_LABELS.get(int(code))
    except (TypeError, ValueError):
        return None


def market_name(code: Any) -> str:
    try:
        n = int(code)
    except (TypeError, ValueError):
        return "this market"
    return MARKET_NAMES.get(n) or location_label(n) or "this market"


def parse_robots(text: str) -> dict[str, dict[str, Any]]:
    """Return allowed/blocked for the AI crawlers we care about."""
    groups: list[tuple[list[str], list[tuple[str, str]]]] = []
    agents: list[str] = []
    rules: list[tuple[str, str]] = []

    def flush() -> None:
        nonlocal agents, rules
        if agents:
            groups.append((agents, rules))
        agents, rules = [], []

    for raw in (text or "").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip().lower()
        value = value.strip()
        if key == "user-agent":
            if rules and agents:
                flush()
            agents.append(value.lower())
        elif key in ("disallow", "allow") and agents:
            rules.append((key, value))
    flush()

    def blocked_for(bot: str) -> bool:
        bot_l = bot.lower()
        specific = [g for g in groups if bot_l in g[0]]
        wildcard = [g for g in groups if "*" in g[0]]
        chosen = specific or wildcard
        if not chosen:
            return False
        disallow_root = False
        allow_root = False
        for _agents, rec_rules in chosen:
            for kind, path in rec_rules:
                path_n = path.strip()
                if not path_n:
                    # Empty Disallow means "allow all" in robots.txt.
                    if kind == "allow":
                        allow_root = True
                    continue
                if path_n not in ("/", "/*"):
                    continue
                if kind == "disallow":
                    disallow_root = True
                elif kind == "allow":
                    allow_root = True
        return disallow_root and not allow_root

    bots = {}
    blocked = 0
    for bot in AI_BOTS:
        is_blocked = blocked_for(bot)
        bots[bot] = {"blocked": is_blocked}
        if is_blocked:
            blocked += 1
    total = len(AI_BOTS)
    allowed = total - blocked
    return {
        "bots": bots,
        "blocked": blocked,
        "allowed": allowed,
        "total": total,
        "score": round(100 * allowed / total) if total else 0,
    }


def _looks_like_html(body: str) -> bool:
    head = (body or "")[:800].lower()
    return "<!doctype html" in head or "<html" in head


def _looks_like_robots(body: str) -> bool:
    if not body or _looks_like_html(body):
        return False
    low = body.lower()
    return any(
        token in low
        for token in ("user-agent:", "disallow:", "allow:", "sitemap:", "crawl-delay:")
    )


def _looks_like_llms(body: str) -> bool:
    text = (body or "").strip()
    if len(text) < 8 or _looks_like_html(text):
        return False
    return True


def _looks_like_sitemap(body: str) -> bool:
    low = (body or "").strip().lower()
    if not low or _looks_like_html(low):
        return False
    return "<urlset" in low or "<sitemapindex" in low or (
        "<?xml" in low and ("urlset" in low or "sitemap" in low)
    )


def _sitemap_candidates(origin: str, robots_text: str) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()
    for line in (robots_text or "").splitlines():
        stripped = line.strip()
        if not stripped.lower().startswith("sitemap:"):
            continue
        url = stripped.split(":", 1)[1].strip()
        if url and url not in seen:
            seen.add(url)
            found.append(url)
    for path in (
        "sitemap.xml",
        "sitemap_index.xml",
        "sitemap-index.xml",
        "wp-sitemap.xml",
        "sitemap/sitemap.xml",
    ):
        url = urljoin(origin + "/", path)
        if url not in seen:
            seen.add(url)
            found.append(url)
    return found


async def _probe_get(client, url: str, timeout: float = 10.0):
    """Return (ok, status, text, error). Uses short connect timeout; never raises."""
    try:
        response = await client.get(url, timeout=timeout, follow_redirects=True)
        return True, response.status_code, response.text or "", None
    except Exception as exc:
        return False, None, "", f"{type(exc).__name__}: {exc}"


async def fetch_ai_signals(client, prospect_url: str) -> dict[str, Any]:
    """Probe origin robots.txt / llms.txt / sitemap from the Snapshot runner.

    Uses a dedicated IPv4-bound client — shared httpx clients often hang on IPv6
    from Docker and silently mark files missing even when they exist at the origin.
    """
    import httpx

    parsed = urlparse(prospect_url)
    scheme = parsed.scheme or "https"
    origin = f"{scheme}://{parsed.netloc}"
    robots_url = urljoin(origin + "/", "robots.txt")
    llms_url = urljoin(origin + "/", "llms.txt")
    default_sitemap = urljoin(origin + "/", "sitemap.xml")

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (compatible; NotionhiveSEOSnapshot/1.1; "
            "+https://notionhive.com)"
        ),
        "Accept": "text/plain,text/*,application/xml,application/xhtml+xml,*/*",
    }
    timeout = httpx.Timeout(10.0, connect=5.0)
    transport = httpx.AsyncHTTPTransport(local_address="0.0.0.0")

    robots_text = ""
    robots_status = None
    robots_error = None
    llms_ok = False
    llms_status = None
    llms_error = None
    sitemap: dict[str, Any] = {
        "present": False,
        "status_code": None,
        "url": default_sitemap,
        "error": None,
    }

    async with httpx.AsyncClient(
        transport=transport,
        headers=headers,
        follow_redirects=True,
        timeout=timeout,
    ) as probe:
        # Parallel robots + llms; sitemap needs robots Sitemap: lines first.
        (r_ok, robots_status, robots_body, robots_error), (
            l_ok,
            llms_status,
            llms_body,
            llms_error,
        ) = await asyncio.gather(
            _probe_get(probe, robots_url),
            _probe_get(probe, llms_url),
        )
        if r_ok and robots_status is not None and robots_status < 400 and _looks_like_robots(
            robots_body
        ):
            robots_text = robots_body
        if l_ok and llms_status is not None and llms_status < 400 and _looks_like_llms(
            llms_body
        ):
            llms_ok = True

        for sm_url in _sitemap_candidates(origin, robots_text):
            sm_ok, sm_status, sm_body, sm_err = await _probe_get(probe, sm_url)
            sitemap["status_code"] = sm_status
            sitemap["url"] = sm_url
            if sm_ok and sm_status is not None and sm_status < 400 and _looks_like_sitemap(
                sm_body
            ):
                sitemap["present"] = True
                sitemap["error"] = None
                break
            sitemap["error"] = sm_err or f"HTTP {sm_status}"
            if sm_ok and sm_status == 404:
                continue

    parsed_robots = (
        parse_robots(robots_text)
        if robots_text
        else {
            "bots": {bot: {"blocked": False} for bot in AI_BOTS},
            "blocked": 0,
            "allowed": len(AI_BOTS),
            "total": len(AI_BOTS),
            "score": 100,
            "missing": True,
        }
    )
    parsed_robots["missing"] = not bool(robots_text)
    if robots_status is not None:
        parsed_robots["status_code"] = robots_status
    if robots_error:
        parsed_robots["probe_error"] = robots_error

    return {
        "robots": parsed_robots,
        "llms_txt": llms_ok,
        "llms_status": llms_status,
        "llms_error": llms_error,
        "sitemap": sitemap,
        "origin": origin,
        "robots_url": robots_url,
        "llms_url": llms_url,
    }


def _card(
    key: str,
    value: str,
    label: str,
    subtext: str,
    tone: str,
) -> dict[str, str]:
    return {
        "key": key,
        "value": value,
        "label": label,
        "subtext": subtext,
        "tone": tone,
    }


def _tone_from_score(score: Optional[int], invert_low: bool = False) -> str:
    if score is None:
        return "neutral"
    if invert_low:
        if score >= 70:
            return "pass"
        if score >= 45:
            return "warn"
        return "fail"
    if score >= 70:
        return "pass"
    if score >= 45:
        return "warn"
    return "fail"


def _cwv_card(technical: dict) -> dict[str, str]:
    order = (
        ("cls", "CLS", "0.25"),
        ("lcp", "LCP", "2.5s"),
        ("inp", "INP", "200ms"),
    )
    failed = [item for item in order if technical.get(f"{item[0]}_status") == "fail"]
    warned = [item for item in order if technical.get(f"{item[0]}_status") == "warning"]
    if failed:
        key, name, threshold = failed[0]
        raw = technical.get(key) or "fail"
        extra = ""
        if key == "cls" and technical.get("cls"):
            extra = f"Layout shift {technical.get('cls')} vs {threshold} threshold"
        elif key == "lcp":
            extra = f"{technical.get('lcp')} vs {threshold} threshold"
        else:
            extra = f"{technical.get('inp')} vs {threshold} threshold"
        return _card(
            "cwv",
            name,
            "Core Web Vitals: Failed",
            extra or raw,
            "fail",
        )
    if warned:
        key, name, threshold = warned[0]
        return _card(
            "cwv",
            name,
            "Core Web Vitals: Needs work",
            f"{technical.get(key)} vs {threshold} good threshold",
            "warn",
        )
    if all(technical.get(f"{k}_status") == "pass" for k, _n, _t in order):
        return _card("cwv", "Pass", "Core Web Vitals: Passed", "LCP, INP, and CLS are in range on mobile lab data", "pass")
    return _card("cwv", "—", "Core Web Vitals", "PageSpeed did not return a full set of vitals", "neutral")


def compute_ai_visibility(payload: dict) -> dict[str, Any]:
    """Composite 0–100 from this pull."""
    organic = payload.get("organic") or {}
    technical = payload.get("technical") or {}
    ai = payload.get("ai") or {}
    scores = payload.get("scores") or {}
    robots = ai.get("robots") or {}
    crawler = _int(robots.get("score")) or 0
    blocked = _int(robots.get("blocked")) or 0
    bot_total = _int(robots.get("total")) or len(AI_BOTS)
    llms = bool(ai.get("llms_txt"))
    count_global = _int(organic.get("count"))
    vis_organic = min(20.0, (count_global / 500.0) * 20.0) if count_global else 0.0
    onpage_score = technical.get("onpage_score")
    try:
        site_health = int(round(float(onpage_score))) if onpage_score is not None else _int(scores.get("technical"))
    except (TypeError, ValueError):
        site_health = _int(scores.get("technical"))
    site_points = (site_health or 0) * 0.15
    score = int(round(crawler * 0.45 + (25 if llms else 0) + vis_organic + site_points))
    score = max(0, min(100, score))
    return {
        "score": score,
        "crawler": crawler,
        "llms": llms,
        "organic_points": round(vis_organic, 1),
        "site_points": round(site_points, 1),
        "blocked": blocked,
        "bot_total": bot_total,
        "allowed": max(0, bot_total - blocked),
        "site_health": site_health,
        "count_global": count_global,
    }


def build_health_snapshot(payload: dict) -> dict[str, Any]:
    organic = payload.get("organic") or {}
    technical = payload.get("technical") or {}
    authority = payload.get("authority") or {}
    ai = payload.get("ai") or {}
    scores = payload.get("scores") or {}
    thin = bool(payload.get("thin_data"))

    rank = _int(authority.get("rank"))
    if rank is None:
        rank = _int(scores.get("authority"))
    rd = _int(authority.get("prospect_referring_domains"))
    backlinks = _int(authority.get("backlinks"))

    etv = organic.get("etv")
    etv_display = organic.get("etv_display") or _fmt_num(etv if etv is not None else None)
    count_global = _int(organic.get("count"))
    count_primary = _int(organic.get("count_primary"))
    loc_label = location_label(organic.get("primary_location_code") or payload.get("location_code"))

    onpage_score = technical.get("onpage_score")
    try:
        site_health = int(round(float(onpage_score))) if onpage_score is not None else _int(scores.get("technical"))
    except (TypeError, ValueError):
        site_health = _int(scores.get("technical"))
    crawled = _int(technical.get("pages_crawled"))
    max_pages = _int(payload.get("onpage_max_pages")) or 100

    robots = ai.get("robots") or {}
    ai_search = _int(robots.get("score"))
    blocked = _int(robots.get("blocked")) or 0
    bot_total = _int(robots.get("total")) or len(AI_BOTS)
    llms = bool(ai.get("llms_txt"))
    vis = compute_ai_visibility(payload)
    ai_visibility = vis["score"]

    kw_hero = count_primary if count_primary is not None else count_global
    kw_label = f"Ranking Keywords ({loc_label})" if loc_label else "Ranking Keywords"
    if thin or not count_global:
        kw_sub = "Little modeled keyword data for this domain"
        kw_tone = "warn"
        kw_value = "—" if not kw_hero else _fmt_num(kw_hero)
    else:
        worldwide = _fmt_num(count_global)
        if loc_label and count_primary is not None and count_global != count_primary:
            kw_sub = f"{worldwide} keywords worldwide (Estimated)"
        else:
            kw_sub = "Estimated ranking SERPs · global markets"
        kw_tone = "pass" if (count_global or 0) >= 100 else "neutral"
        kw_value = _fmt_num(kw_hero)

    if backlinks:
        rd_sub = f"Estimated {_fmt_num(backlinks)} backlinks (DataForSEO)"
    else:
        rd_sub = "Live referring domains"

    cards = [
        _card(
            "authority",
            "—" if rank is None else str(rank),
            "Authority Score",
            f'DataForSEO rank — rated "{_rating(rank)}"',
            _tone_from_score(rank),
        ),
        _card(
            "traffic",
            "—" if etv is None and not etv_display else f"{etv_display} /mo",
            "Organic Traffic",
            "Estimated · global markets" if not thin else "Thin modeled traffic",
            "pass" if isinstance(etv, (int, float)) and etv >= 1000 else ("warn" if thin else "neutral"),
        ),
        _card("keywords", kw_value, kw_label, kw_sub, kw_tone),
        _card(
            "referring",
            "—" if rd is None else _fmt_num(rd),
            "Referring Domains",
            rd_sub,
            "pass" if (rd or 0) >= 200 else "neutral",
        ),
    ]
    if payload.get("deck_mode") != "quick":
        cards.append(
            _card(
                "site_health",
                "—" if site_health is None else f"{site_health}%",
                "Site Health Score",
                f"{crawled if crawled is not None else '—'} of {max_pages} pages crawled",
                _tone_from_score(site_health),
            )
        )
    cards.extend(
        [
            _card(
                "ai_search",
                "—" if ai_search is None else f"{ai_search}%",
                "AI Search Health",
                f"{blocked} of {bot_total} AI crawlers blocked in robots.txt"
                if not robots.get("missing")
                else "robots.txt not found — crawlers treated as allowed",
                "fail" if blocked else "pass",
            ),
            _cwv_card(technical),
            _card(
                "ai_cited",
                str(ai_visibility),
                "AI-Cited Pages",
                f"AI Visibility score {ai_visibility} / 100 · crawler access + llms.txt",
                _tone_from_score(ai_visibility),
            ),
        ]
    )

    blockers: list[str] = []
    cwv = next((c for c in cards if c["key"] == "cwv"), None)
    if cwv and cwv["tone"] == "fail":
        blockers.append("Core Web Vitals")
    if payload.get("deck_mode") != "quick" and site_health is not None and site_health < 75:
        blockers.append("content hygiene")
    if thin or (count_global is not None and count_global < 40):
        blockers.append("organic visibility")
    if rank is not None and rank < 30:
        blockers.append("authority")
    blockers = blockers[:2]

    if len(blockers) == 2:
        subtitle = (
            f"Solid foundations, but {blockers[0]} and {blockers[1]} are the "
            "two biggest blockers to the next growth stage."
        )
    elif len(blockers) == 1:
        subtitle = f"{blockers[0][0].upper() + blockers[0][1:]} is the main blocker to the next growth stage."
    else:
        subtitle = "Foundations look solid. Use the later slides for the working list."

    strengths = []
    if (rd or 0) >= 100:
        strengths.append("referring-domain profile")
    if blocked == 0:
        strengths.append("AI-crawler access")
    if payload.get("deck_mode") != "quick" and site_health is not None and site_health >= 80:
        strengths.append("on-page health")
    strength_bit = (
        f"{' and '.join(strengths)} {'are' if len(strengths) > 1 else 'is'} "
        "a healthy strength to build on. "
        if strengths
        else ""
    )
    if cwv and cwv["tone"] == "fail":
        takeaway = (
            f"{strength_bit}The single highest-leverage fix is {cwv['value']} — "
            f"{cwv['subtext']}. Confirmed on mobile PageSpeed lab data."
        ).strip()
    elif blockers:
        takeaway = f"{strength_bit}Start with {blockers[0]} before chasing new keywords.".strip()
    else:
        takeaway = f"{strength_bit}Keep the working list tight and book the session from the last slide.".strip()

    return {
        "title": "SEO Health Snapshot",
        "subtitle": subtitle,
        "takeaway": takeaway,
        "cards": cards,
    }


def brand_label(domain: str) -> str:
    host = (domain or "").lower().replace("www.", "").split("/")[0]
    sld = host.split(".")[0] if host else ""
    return sld.replace("-", " ").title() if sld else (domain or "this domain")


def build_authority_slide(payload: dict) -> dict[str, Any]:
    organic = payload.get("organic") or {}
    authority = payload.get("authority") or {}
    domain = payload.get("prospect_domain") or "this domain"
    rank = _int(authority.get("rank"))
    rd = _int(authority.get("prospect_referring_domains"))
    backlinks = _int(authority.get("backlinks"))
    spam = _int(authority.get("spam_score"))
    etv = organic.get("etv")
    etv_display = organic.get("etv_display") or _fmt_num(etv if isinstance(etv, (int, float)) else None)
    ratio = None
    if rd and backlinks:
        ratio = round(backlinks / rd, 1)

    you_label = f"{brand_label(domain)} (You)"
    peers = []
    for row in authority.get("peers") or []:
        if not isinstance(row, dict):
            continue
        peers.append(
            {
                "domain": row.get("domain"),
                "label": row.get("label") or brand_label(row.get("domain") or ""),
                "rank": _int(row.get("rank")),
                "is_you": False,
            }
        )
    chart = [p for p in peers if p.get("rank") is not None]
    chart.sort(key=lambda p: p["rank"] or 0, reverse=True)
    chart.append(
        {
            "domain": domain,
            "label": you_label,
            "rank": rank,
            "is_you": True,
        }
    )

    cards = [
        {
            "value": "—" if rank is None else str(rank),
            "label": "Authority Score",
            "subtext": f'DataForSEO — {_rating(rank)}',
            "tone": "neutral",
        },
        {
            "value": "—" if rd is None else _fmt_num(rd),
            "label": "Referring Domains",
            "subtext": "current snapshot",
            "tone": "neutral",
        },
        {
            "value": "—" if backlinks is None else f"~{_fmt_num(backlinks)}",
            "label": "Total Backlinks",
            "subtext": (
                f"{ratio} links / ref. domain"
                if ratio is not None
                else "Estimated (DataForSEO)"
            ),
            "tone": "neutral",
        },
        {
            "value": "—" if etv is None and etv_display in (None, "—") else f"{etv_display} /mo",
            "label": "Organic Traffic",
            "subtext": "Estimated · global markets",
            "tone": "pass" if isinstance(etv, (int, float)) and etv >= 1000 else "neutral",
        },
    ]

    reading: list[dict[str, str]] = []
    if spam is not None and spam >= 40:
        reading.append(
            {
                "title": "Spam signal is elevated.",
                "body": (
                    f"DataForSEO spam score is {spam}/100. Review the referring-domain "
                    "list before treating this as a healthy link profile."
                ),
            }
        )
    else:
        ratio_bit = (
            f"Backlinks-to-referring-domains ratio ({ratio}x) is within a normal range — "
            if ratio is not None and ratio <= 15
            else (
                f"Backlinks-to-referring-domains ratio is {ratio}x, which is high — "
                if ratio is not None
                else ""
            )
        )
        reading.append(
            {
                "title": "No spam signal detected." if (spam is None or spam < 40) else "Spam score is moderate.",
                "body": (
                    f"{ratio_bit}no evidence of a sudden link spike in this snapshot."
                ).strip(),
            }
        )

    ranked_peers = [p for p in peers if p.get("rank") is not None]
    if rank is not None and ranked_peers:
        leader = max(ranked_peers, key=lambda p: p["rank"] or 0)
        names = ", ".join((p.get("label") or p.get("domain") or "") for p in ranked_peers[:4])
        reading.append(
            {
                "title": "Authority gap is real." if (leader.get("rank") or 0) > rank else "Authority is in range of peers.",
                "body": (
                    f"At rank {rank}, {brand_label(domain)} sits "
                    f"{'roughly half the score of' if (leader.get('rank') or 0) >= rank * 1.6 else 'below'} "
                    f"the peer leader ({leader.get('label')}, {leader.get('rank')})"
                    f"{' and below ' + names if names else ''}."
                    if (leader.get("rank") or 0) > rank
                    else f"At rank {rank}, {brand_label(domain)} is at or above this peer set."
                ),
            }
        )
    else:
        reading.append(
            {
                "title": "Peer set is thin.",
                "body": (
                    "No similar-authority peers made it onto the chart after filtering "
                    "mega platforms and rank-band outliers — or none were entered in manual mode. "
                    "The four cards still use this domain’s live backlink and traffic pull."
                ),
            }
        )

    if isinstance(etv, (int, float)) and etv > 0:
        reading.append(
            {
                "title": "Traffic is modeled, not Analytics.",
                "body": (
                    f"Estimated organic traffic is {etv_display} per month across all Google markets. "
                    "A referring-domain push would compound whatever is already ranking."
                ),
            }
        )
    else:
        reading.append(
            {
                "title": "Organic traffic is thin in the model.",
                "body": "Labs has little estimated traffic for this domain. Authority work still matters, but indexable pages come first.",
            }
        )

    peer_mode = (authority.get("competitor_mode") or "").lower()
    peer_source = (authority.get("peer_source") or "").lower()
    chart_title = (
        "Authority Score vs. selected competitors"
        if peer_mode == "manual" or peer_source == "manual"
        else "Authority Score vs. similar peers (Labs)"
    )

    return {
        "title": "Authority & Backlink Profile",
        "chart_title": chart_title,
        "peer_source": authority.get("peer_source") or "labs_filtered",
        "cards": cards,
        "peers": chart,
        "reading": reading[:3],
    }
