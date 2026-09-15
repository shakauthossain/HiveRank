"""Analyze HTML report in Snapshot slide structure.

Keeps RankMath / PageSpeed titles and descriptions. Does not call DataForSEO.
"""

from __future__ import annotations

import os
import re
from datetime import datetime
from html import escape
from typing import Any, Optional
from urllib.parse import urlparse

NH = "1158E5"
NH_DARK = "0B3FA8"
INK = "0B1220"
MUTED = "64748B"
LINE = "E2E8F0"
WASH = "F1F6FE"
PASS = "059669"
WARN = "D97706"
FAIL = "DC2626"
ITEMS_PER_SLIDE = 6
CONTENT_LIMIT = 400

CAT_COPY = (
    (
        "basic",
        "ON-PAGE",
        "Basic SEO Checks",
        "The fundamental building blocks of your site's visibility on Google.",
    ),
    (
        "advanced",
        "TECHNICAL",
        "Advanced SEO",
        "Deeper technical signals that help Google better understand your site.",
    ),
    (
        "title",
        "CONTENT",
        "Title Optimization",
        "How well your page titles are crafted for search engines and users.",
    ),
    (
        "content",
        "CONTENT",
        "Content Analysis",
        "The quality and structure of your on-page content.",
    ),
    (
        "link",
        "AUTHORITY SIGNALS",
        "Links & Navigation",
        "Internal and external links that help Google crawl your site.",
    ),
    (
        "performance",
        "TECHNICAL HEALTH",
        "Page Speed & Performance",
        "How fast your website loads — slow sites lose visitors and rankings.",
    ),
    (
        "social",
        "AUTHORITY SIGNALS",
        "Social Media Sharing",
        "How your site looks when shared on Facebook, Twitter, and similar networks.",
    ),
    (
        "schema",
        "CONTENT",
        "Schema & Structured Data",
        "Rich data markup that helps Google understand your content better.",
    ),
)


def _to_int(value: Any) -> Optional[int]:
    if value is None or value == "N/A":
        return None
    if isinstance(value, (int, float)):
        return int(value)
    match = re.search(r"\d+", str(value))
    return int(match.group()) if match else None


def _score_color(n: Optional[int]) -> str:
    if n is None:
        return MUTED
    if n >= 70:
        return PASS
    if n >= 50:
        return WARN
    return FAIL


def _status_label(status: str) -> tuple[str, str]:
    if status == "pass":
        return "Good", PASS
    if status == "warning":
        return "Warn", WARN
    if status == "fail":
        return "Fix", FAIL
    return "Info", "1d4ed8"


def _esc(value: Any) -> str:
    return escape(str(value or ""), quote=True)


def _clip(text: Any, limit: int = CONTENT_LIMIT) -> str:
    raw = str(text or "").strip()
    if len(raw) <= limit:
        return raw
    return raw[:limit].rstrip() + "…"


def _items(categories: list, name_bits: tuple[str, ...]) -> list[dict]:
    found = []
    for cat in categories:
        name = (cat.get("name") or "").lower()
        if any(bit in name for bit in name_bits):
            found.extend(cat.get("items") or [])
    return found


def _check_score(items: list[dict]) -> Optional[int]:
    """Pass-rate score: pass=100, warning=50, fail=0. Info checks are skipped."""
    scored = [i for i in items if i.get("status") in ("pass", "warning", "fail")]
    if not scored:
        return None
    weights = {"pass": 100, "warning": 50, "fail": 0}
    return round(sum(weights[i["status"]] for i in scored) / len(scored))


def _seo_blurb(score: Optional[int]) -> str:
    if score is None:
        return "We could not determine an on-page SEO score for this URL."
    if score >= 80:
        return "Your website is well-optimized. A few tweaks and you could be perfect."
    if score >= 60:
        return "Your site has a decent foundation but several things need attention."
    return "Your website has serious SEO problems that are likely hurting your visibility."


def _cat_meta(raw_name: str) -> tuple[str, str, str]:
    name = (raw_name or "").lower()
    for key, kicker, title, note in CAT_COPY:
        if key in name:
            return kicker, title, note
    return "ON-PAGE", raw_name or "Checks", "Analysis results for this category."


def _chunks(items: list[dict], size: int = ITEMS_PER_SLIDE) -> list[list[dict]]:
    if not items:
        return [[]]
    return [items[i : i + size] for i in range(0, len(items), size)]


def _finding_rows(items: list[dict]) -> str:
    rows = []
    for item in items:
        label, color = _status_label(item.get("status") or "info")
        title = _esc(item.get("title") or "Check")
        body = _esc(_clip(item.get("content") or ""))
        rows.append(
            f"""<div class="finding">
  <span class="badge" style="color:{color};border-color:{color}33;background:{color}14">{label}</span>
  <div>
    <h4>{title}</h4>
    <p>{body or "No extra detail was returned for this check."}</p>
  </div>
</div>"""
        )
    return "".join(rows) or "<p class='empty'>No items in this section.</p>"


def _domain_from(url: str) -> str:
    raw = (url or "").strip()
    if not raw:
        return ""
    if "://" not in raw:
        raw = "https://" + raw
    host = urlparse(raw).netloc or raw
    return host.removeprefix("www.")


def generate_analyze_deck(seo_data: Optional[dict], speed_data: Optional[dict]) -> str:
    seo = seo_data or {}
    speed = speed_data or {}
    mobile = speed.get("mobile") if isinstance(speed.get("mobile"), dict) else speed
    desktop = speed.get("desktop") if isinstance(speed.get("desktop"), dict) else {}
    booking = os.getenv("SNAPSHOT_BOOKING_URL", "https://notionhive.com/").rstrip("/") or "https://notionhive.com"

    url = seo.get("url") or mobile.get("url") or desktop.get("url") or ""
    domain = _domain_from(url)
    date = (
        seo.get("timestamp")
        or mobile.get("timestamp")
        or datetime.utcnow().strftime("%d %B %Y")
    )

    seo_score = _to_int(seo.get("seo_score"))
    mobile_score = _to_int(mobile.get("perf_score") or speed.get("perf_score"))
    desktop_score = _to_int(desktop.get("perf_score") or speed.get("perf_score_desktop"))
    categories = seo.get("categories") or []
    content_items = _items(categories, ("content", "title"))
    link_items = _items(categories, ("link",))
    content_score = _check_score(content_items)
    link_score = _check_score(link_items)

    all_seo = [i for c in categories for i in (c.get("items") or [])]
    speed_items = []
    for block in (mobile, desktop):
        for cat in block.get("categories") or []:
            speed_items.extend(cat.get("items") or [])
    seen: dict[str, dict] = {}
    rank = {"fail": 0, "warning": 1, "info": 2, "pass": 3}
    for item in speed_items:
        title = item.get("title") or ""
        prev = seen.get(title)
        if prev is None or rank.get(item.get("status"), 9) < rank.get(prev.get("status"), 9):
            seen[title] = item
    speed_items = list(seen.values())

    fails = [i for i in all_seo if i.get("status") == "fail"]
    warns = [i for i in all_seo if i.get("status") == "warning"]
    speed_fails = [i for i in speed_items if i.get("status") in ("fail", "warning")]
    quick = (fails + speed_fails + warns)[: ITEMS_PER_SLIDE + 1]
    priorities = (fails + speed_fails)[:5]
    if len(priorities) < 5:
        priorities = (priorities + warns)[:5]

    passed = _to_int(seo.get("passed")) or sum(1 for i in all_seo if i.get("status") == "pass")
    warning_n = _to_int(seo.get("warnings")) or len(warns)
    failed_n = _to_int(seo.get("failed")) or len(fails)

    slides: list[str] = []

    def body_slide(kicker: str, title: str, note: str, inner: str) -> str:
        return f"""<section class="slide">
  <div class="rail"></div>
  <div class="pad">
    <div class="kicker"><i></i>{_esc(kicker)}</div>
    <h2>{_esc(title)}</h2>
    <p class="note">{_esc(note)}</p>
    {inner}
  </div>
  __FOOT__
</section>"""

    def add_item_slides(
        kicker: str, title: str, note: str, items: list[dict], extra: str = ""
    ) -> None:
        chunks = _chunks(items)
        for idx, chunk in enumerate(chunks):
            suffix = f" ({idx + 1}/{len(chunks)})" if len(chunks) > 1 else ""
            prefix = extra if idx == 0 else ""
            slides.append(
                body_slide(
                    kicker,
                    f"{title}{suffix}",
                    note,
                    prefix + f'<div class="list">{_finding_rows(chunk)}</div>',
                )
            )

    slides.append(
        f"""<section class="slide cover">
  <div class="blob"></div>
  <div class="pad">
    <div class="brand">NOTIONHIVE</div>
    <h2>SEO Audit</h2>
    <div class="domain">{_esc(domain)}</div>
    <p class="sub">On-page SEO and page experience for this URL. RankMath and PageSpeed only — no estimated traffic or keywords.<br/>{_esc(date)}</p>
  </div>
  __FOOT__
</section>"""
    )

    def card(label: str, value: Optional[int], hint: str) -> str:
        shown = "—" if value is None else str(value)
        return f"""<div class="score">
  <b>{label}</b>
  <div class="n" style="color:#{_score_color(value)}">{shown}</div>
  <small>{_esc(hint)}</small>
</div>"""

    slides.append(
        body_slide(
            "SCORES",
            "Score overview",
            f"{_seo_blurb(seo_score)} These are not Snapshot visibility/authority scores and not traffic.",
            f"""<div class="scores">
      {card("SEO", seo_score, "RankMath overall score")}
      {card("Speed", mobile_score, "Google PageSpeed · mobile")}
      {card("Content", content_score, "Pass-rate of title and content checks")}
      {card("Links", link_score, "Pass-rate of link checks")}
    </div>
    <p class="note" style="margin-top:16px">Content and Links: pass = 100, warning = 50, fail = 0, then averaged. Speed is Google’s lab performance score. Traffic and ranking keywords are not in Analyze — use Snapshot.</p>""",
        )
    )

    slides.append(
        body_slide(
            "ON-PAGE",
            "RankMath check counts",
            "Counts of on-page tests RankMath ran on this URL. These are not monthly visits or ranking keywords.",
            f"""<div class="pair">
      <div class="wash"><b>PASSED</b><div class="n" style="color:#{PASS}">{passed}</div><span>Checks that look healthy</span></div>
      <div class="wash"><b>WARNINGS</b><div class="n" style="color:#{WARN}">{warning_n}</div><span>Checks that need cleanup</span></div>
      <div class="wash"><b>FAILED</b><div class="n" style="color:#{FAIL}">{failed_n}</div><span>Checks that failed</span></div>
    </div>""",
        )
    )

    add_item_slides(
        "PRIORITY",
        "Failed and warning checks",
        "RankMath and PageSpeed findings with the original title and explanation. Not keyword opportunities.",
        quick,
    )

    lcp = mobile.get("lcp") or "N/A"
    tbt = mobile.get("tbt") or "N/A"
    cls = mobile.get("cls") or "N/A"

    def cwv_color(status: Any) -> str:
        if status == "pass":
            return PASS
        if status == "warning":
            return WARN
        return FAIL

    slides.append(
        body_slide(
            "TECHNICAL HEALTH",
            "Core Web Vitals",
            f"Mobile PageSpeed {mobile_score if mobile_score is not None else '—'} · Desktop {desktop_score if desktop_score is not None else '—'}. Lab data from PageSpeed Insights.",
            f"""<div class="cwv">
      <article><b>LCP</b><div class="n" style="color:#{cwv_color(mobile.get("lcp_status"))}">{_esc(lcp)}</div><span>Largest Contentful Paint</span></article>
      <article><b>TBT</b><div class="n" style="color:#{cwv_color(mobile.get("tbt_status"))}">{_esc(tbt)}</div><span>Total Blocking Time (lab stand-in for INP)</span></article>
      <article><b>CLS</b><div class="n" style="color:#{cwv_color(mobile.get("cls_status"))}">{_esc(cls)}</div><span>Cumulative Layout Shift</span></article>
    </div>
    {('<div class="list">' + _finding_rows((speed_fails or speed_items)[:4]) + "</div>") if (speed_fails or speed_items) else ""}""",
        )
    )

    for cat in categories:
        items = cat.get("items") or []
        if not items:
            continue
        kicker, title, note = _cat_meta(cat.get("name") or "")
        add_item_slides(kicker, title, note, items)

    speed_cats = mobile.get("categories") or []
    if not speed_cats:
        speed_cats = desktop.get("categories") or []
    for cat in speed_cats:
        items = cat.get("items") or []
        if not items:
            continue
        add_item_slides(
            "TECHNICAL HEALTH",
            cat.get("name") or "Speed checks",
            cat.get("tagline") or "PageSpeed Insights findings for this URL.",
            items,
        )

    prio_html = ""
    for i, item in enumerate(priorities or quick[:5], 1):
        prio_html += (
            f"""<div class="fix"><div class="num">{i}</div><div><strong>{_esc(item.get("title"))}</strong>"""
            f"""<p>{_esc(_clip(item.get("content") or "", 220))}</p></div></div>"""
        )
    if not prio_html:
        prio_html = "<p class='empty'>No critical fixes were flagged. Keep monitoring titles, speed, and internal links.</p>"

    slides.append(
        body_slide(
            "NEXT STEP",
            "Top fixes",
            "Pulled from failed and warning checks on this URL. Estimated traffic and keywords are in Snapshot.",
            f"""<div class="fixes">
      <div>{prio_html}</div>
      <aside class="cta">
        <b>BOOK A WORKING SESSION</b>
        <p>Notionhive can turn these findings into a scoped plan.</p>
        <a href="{_esc(booking)}">{_esc(booking.replace("https://", ""))}</a>
      </aside>
    </div>""",
        )
    )

    total = len(slides)
    numbered = []
    for idx, html in enumerate(slides, 1):
        foot = (
            f'<div class="foot"><span>NOTIONHIVE · SEO AUDIT</span>'
            f"<span>{_esc(date)} · {idx} / {total}</span></div>"
        )
        numbered.append(html.replace("__FOOT__", foot))

    slides_html = "\n".join(numbered)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>SEO Audit — {_esc(domain)}</title>
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap" rel="stylesheet" />
<style>
:root {{ --nh:#{NH}; --nh-dark:#{NH_DARK}; --ink:#{INK}; --muted:#{MUTED}; --line:#{LINE}; --wash:#{WASH}; }}
* {{ box-sizing:border-box; margin:0; padding:0; }}
html,body {{ background:#e8edf5; font-family:"DM Sans",Calibri,sans-serif; color:var(--ink); }}
.chrome {{ position:sticky; top:0; z-index:20; display:flex; align-items:center; justify-content:space-between; gap:16px; padding:12px 24px; background:#fff; border-bottom:1px solid var(--line); }}
.chrome h1 {{ font-size:14px; font-weight:600; }}
.chrome p {{ font-size:12px; color:var(--muted); }}
.deck {{ padding:28px 24px 80px; display:flex; flex-direction:column; align-items:center; gap:28px; }}
.slide {{ width:min(1120px,100%); aspect-ratio:16/9; background:#fff; position:relative; overflow:hidden; box-shadow:0 18px 40px rgba(11,18,32,.12); border-radius:4px; }}
.cover {{ background:var(--nh); color:#fff; }}
.blob {{ position:absolute; right:-80px; top:-90px; width:420px; height:420px; background:var(--nh-dark); transform:rotate(18deg); }}
.pad {{ padding:28px 40px 48px; height:100%; position:relative; z-index:1; }}
.cover .pad {{ padding-top:88px; }}
.rail {{ position:absolute; left:0; top:0; bottom:0; width:10px; background:var(--nh); }}
.foot {{ position:absolute; left:0; right:0; bottom:0; height:28px; background:var(--nh); color:#fff; display:flex; align-items:center; justify-content:space-between; padding:0 28px 0 36px; font-size:10px; letter-spacing:.08em; }}
.brand {{ letter-spacing:.28em; font-size:13px; font-weight:700; }}
.cover h2 {{ font-size:52px; margin:12px 0 8px; }}
.domain {{ font-size:26px; color:#d6e4ff; }}
.sub {{ margin-top:18px; max-width:720px; font-size:16px; line-height:1.45; color:#eef3ff; }}
.kicker {{ display:flex; align-items:center; gap:10px; color:var(--nh); font-size:11px; font-weight:700; letter-spacing:.16em; }}
.kicker i {{ width:8px; height:16px; background:var(--nh); display:block; }}
h2 {{ font-size:28px; margin:8px 0 6px; letter-spacing:-.03em; }}
.note {{ font-size:13px; color:var(--muted); font-style:italic; margin-bottom:12px; }}
.scores {{ display:grid; grid-template-columns:repeat(4,1fr); gap:16px; margin-top:18px; }}
.score {{ border:1px solid var(--line); border-radius:12px; padding:18px 10px; text-align:center; box-shadow:0 6px 18px rgba(11,18,32,.06); }}
.score b {{ display:block; font-size:11px; color:var(--muted); letter-spacing:.12em; }}
.score .n {{ font-size:48px; font-weight:700; line-height:1.1; margin:8px 0 4px; }}
.score small {{ color:var(--muted); font-size:12px; }}
.pair {{ display:grid; grid-template-columns:repeat(3,1fr); gap:14px; margin-top:18px; }}
.wash {{ background:var(--wash); border-radius:12px; padding:16px 18px; }}
.wash b {{ color:var(--nh); font-size:11px; letter-spacing:.12em; }}
.wash .n {{ font-size:32px; font-weight:700; margin:6px 0; }}
.wash span {{ color:var(--muted); font-size:12px; }}
.cwv {{ display:grid; grid-template-columns:repeat(3,1fr); gap:14px; margin:8px 0 10px; }}
.cwv article {{ border:1px solid var(--line); border-radius:12px; padding:12px 16px; }}
.cwv b {{ font-size:11px; color:var(--muted); letter-spacing:.1em; }}
.cwv .n {{ font-size:24px; font-weight:700; margin:4px 0; }}
.list {{ display:flex; flex-direction:column; gap:8px; max-height:46%; overflow:auto; }}
.finding {{ display:flex; gap:12px; padding:10px 12px; border:1px solid var(--line); border-radius:10px; background:#f8fafc; }}
.finding h4 {{ font-size:13px; margin-bottom:4px; }}
.finding p {{ font-size:12px; color:var(--muted); line-height:1.45; }}
.badge {{ flex:none; font-size:10px; font-weight:700; letter-spacing:.04em; text-transform:uppercase; padding:4px 8px; border-radius:6px; border:1px solid; height:fit-content; }}
.fixes {{ display:grid; grid-template-columns:1fr 240px; gap:18px; }}
.fix {{ display:flex; gap:12px; margin-bottom:10px; }}
.fix p {{ font-size:12px; color:var(--muted); margin-top:4px; }}
.num {{ width:26px; height:26px; border-radius:50%; background:var(--nh); color:#fff; display:grid; place-items:center; font-size:13px; font-weight:700; flex:none; }}
.cta {{ background:var(--nh); color:#fff; border-radius:12px; padding:20px 18px; min-height:240px; }}
.cta a {{ color:#fff; font-weight:700; font-size:13px; }}
.empty {{ color:var(--muted); }}
@media print {{
  @page {{ size: 13.333in 7.5in; margin: 0; }}
  html,body {{ background:#fff; }}
  .chrome {{ display:none; }}
  .deck {{ padding:0; gap:0; }}
  .slide {{ width:13.333in; height:7.5in; box-shadow:none; border-radius:0; page-break-after:always; break-after:page; }}
}}
</style>
</head>
<body>
<div class="chrome">
  <div>
    <h1>SEO Audit · {_esc(domain) or "Report"}</h1>
    <p>Snapshot slide structure · RankMath and PageSpeed findings · scroll the 16:9 deck</p>
  </div>
</div>
<div class="deck">{slides_html}</div>
</body>
</html>"""
