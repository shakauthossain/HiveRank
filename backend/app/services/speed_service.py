from datetime import datetime
from typing import Optional

import requests


def fetch_pagespeed_data_sync(
    url: str,
    api_key: str,
    strategy: str = "mobile",
    *,
    timeout: float = 120,
    categories: Optional[list] = None,
):
    endpoint = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
    # Repeated category params — need performance + seo for Snapshot decks.
    cats = categories or ["performance", "seo"]
    params = [
        ("url", url),
        ("key", api_key),
        ("strategy", strategy),
    ]
    for cat in cats:
        params.append(("category", cat))
    try:
        resp = requests.get(endpoint, params=params, timeout=timeout)
    except requests.Timeout:
        print(f"--- ERROR: PageSpeed timeout ({timeout}s) for {url} ({strategy}) ---")
        return None
    except requests.RequestException as exc:
        print(f"--- ERROR: PageSpeed request failed for {url} ({strategy}): {exc} ---")
        return None
    if resp.status_code != 200:
        print(f"--- ERROR: PageSpeed API {resp.status_code} for {url} ({strategy}) ---")
        print(f"--- DETAIL: {resp.text[:200]} ---")
        return None
    return resp.json()


def parse_pagespeed_data(raw: dict, url: str, strategy: str):
    lhr = raw.get("lighthouseResult", {})
    cats = lhr.get("categories", {})
    audits = lhr.get("audits", {})
    final_url = lhr.get("finalUrl") or lhr.get("requestedUrl") or url

    def score(cat_key):
        s = cats.get(cat_key, {}).get("score")
        return round(s * 100) if s is not None else "N/A"

    def ms_val(key):
        return audits.get(key, {}).get("numericValue")

    def ms_str(key):
        val = ms_val(key)
        if val is None:
            return "N/A"
        return f"{val / 1000:.1f}s" if val >= 1000 else f"{round(val)}ms"

    lcp_raw = ms_val("largest-contentful-paint")
    tbt_raw = ms_val("total-blocking-time")
    cls_raw = ms_val("cumulative-layout-shift")
    fcp_raw = ms_val("first-contentful-paint")
    si_raw = ms_val("speed-index")
    tti_raw = ms_val("interactive")

    # Status helpers
    def lcp_status(v):
        return "pass" if v is None or v < 2500 else "warning" if v < 4000 else "fail"

    def tbt_status(v):
        return "pass" if v is None or v < 200 else "warning" if v < 600 else "fail"

    def cls_status(v):
        return "pass" if v is None or v < 0.1 else "warning" if v < 0.25 else "fail"

    def fcp_status(v):
        return "pass" if v is None or v < 1800 else "warning" if v < 3000 else "fail"

    def si_status(v):
        return "pass" if v is None or v < 3400 else "warning" if v < 5800 else "fail"

    def tti_status(v):
        return "pass" if v is None or v < 3800 else "warning" if v < 7300 else "fail"

    def get_perf_items(group_ids):
        items = []
        for audit_id in group_ids:
            audit = audits.get(audit_id, {})
            title = audit.get("title", "")
            description = audit.get("description", "")
            s = audit.get("score")
            display_val = audit.get("displayValue", "")
            if not title:
                continue

            if s is None:
                status = "info"
            elif s >= 0.9:
                status = "pass"
            elif s >= 0.5:
                status = "warning"
            else:
                status = "fail"

            detail = (
                display_val
                if display_val
                else (
                    description[:150] + "…" if len(description) > 150 else description
                )
            )
            items.append({"title": title, "content": detail, "status": status})
        return items

    speed_groups = [
        {
            "icon": "🖼️",
            "name": "Images & Media",
            "tagline": "Unoptimized images are a main cause of slowness.",
            "ids": [
                "uses-optimized-images",
                "uses-webp-images",
                "uses-responsive-images",
                "uses-lazy-loading",
                "offscreen-images",
            ],
        },
        {
            "icon": "📦",
            "name": "Code & Scripts",
            "tagline": "Heavy JS ruins interactivity.",
            "ids": [
                "unused-javascript",
                "unused-css-rules",
                "unminified-javascript",
                "unminified-css",
                "render-blocking-resources",
                "bootup-time",
            ],
        },
        {
            "icon": "🌐",
            "name": "Server & Network",
            "tagline": "Fast hosting is critical.",
            "ids": [
                "uses-text-compression",
                "server-response-time",
                "redirects",
                "efficient-cache-policy",
            ],
        },
    ]

    categories = []
    for grp in speed_groups:
        items = get_perf_items(grp["ids"])
        if items:
            categories.append(
                {
                    "icon": grp["icon"],
                    "name": grp["name"],
                    "tagline": grp["tagline"],
                    "items": items,
                }
            )

    cls_display = f"{cls_raw:.3f}" if cls_raw is not None else "N/A"

    return {
        "url": url,
        "final_url": final_url,
        "strategy": strategy,
        "timestamp": datetime.now().strftime("%B %d, %Y at %H:%M"),
        "perf_score": score("performance"),
        "lcp": ms_str("largest-contentful-paint"),
        "tbt": ms_str("total-blocking-time"),
        "cls": cls_display,
        "fcp": ms_str("first-contentful-paint"),
        "si": ms_str("speed-index"),
        "tti": ms_str("interactive"),
        "lcp_status": lcp_status(lcp_raw),
        "tbt_status": tbt_status(tbt_raw),
        "cls_status": cls_status(cls_raw),
        "fcp_status": fcp_status(fcp_raw),
        "si_status": si_status(si_raw),
        "tti_status": tti_status(tti_raw),
        "categories": categories,
    }


def generate_html(data: dict) -> str:
    """Generates a premium dual-strategy slide-deck HTML report for Speed data."""
    try:
        # Extract mobile/desktop data
        m = data.get("mobile", {})
        d = data.get("desktop", {})

        # ── Inline helpers ────────────────────────────────────────────────────
        def score_color(s):
            try:
                v = int(s)
                if v >= 90: return "#22c55e" # Green
                if v > 50: return "#f59e0b"  # Yellowish/Amber (51-89)
                return "#ef4444"             # Red (0-50)
            except: return "#6b7280"

        def grade(s):
            try:
                v = int(s)
                if v >= 90: return "A"
                if v >= 70: return "B"
                if v >= 50: return "C"
                if v >= 30: return "D"
                return "F"
            except: return "?"

        def status_meta(st):
            if st == "pass": return ("✅", "Good", "#15803d", "bd-g")
            if st == "warning": return ("⚠️", "Warn", "#d97706", "bd-y")
            if st == "fail": return ("❌", "Fix", "#dc2626", "bd-r")
            return ("ℹ️", "Info", "#1d4ed8", "bd-b")

        def get_gauge_html(score, label, color):
            try:
                val = int(score) if score != "N/A" else 0
            except:
                val = 0
            offset = 251.2 * (1 - val / 100)
            return f"""
            <div class="gauge-item">
              <div class="gauge-label">{label}</div>
              <div class="gauge-visual">
                <svg class="gauge-svg" viewBox="0 0 100 100">
                  <circle class="gauge-bg" cx="50" cy="50" r="40" />
                  <circle class="gauge-fill" cx="50" cy="50" r="40" stroke="{color}" 
                    stroke-dasharray="251.2" stroke-dashoffset="{offset}" />
                </svg>
                <div class="gauge-center">
                  <span class="gauge-val" style="color:{color}">{score}</span>
                </div>
              </div>
            </div>"""

        # ── Derived values ────────────────────────────────────────────────────
        url = m.get("url") or d.get("url") or "unknown"
        domain = url.replace("https://", "").replace("http://", "").rstrip("/")
        timestamp = m.get("timestamp") or d.get("timestamp") or datetime.now().strftime("%B %d, %Y")
        
        m_score = m.get("perf_score", "N/A")
        d_score = d.get("perf_score", "N/A")
        
        m_color = score_color(m_score)
        d_color = score_color(d_score)
        
        m_grade = grade(m_score)
        d_grade = grade(d_score)

        num_cats = len(m.get("categories", []))
        total_slides = 2 + num_cats + 1
        total_slides_str = str(total_slides).zfill(2)

        # ── Dashboard Metrics Table ──────────────────────────────────────────
        def get_metric_row(label, key_m, key_d, desc):
            val_m = m.get(key_m, "N/A")
            val_d = d.get(key_d, "N/A")
            st_m = m.get(key_m + "_status", "info")
            st_d = d.get(key_d + "_status", "info")
            
            clr_m = "#16a34a" if st_m == "pass" else "#d97706" if st_m == "warning" else "#dc2626"
            clr_d = "#16a34a" if st_d == "pass" else "#d97706" if st_d == "warning" else "#dc2626"
            
            return f"""
            <tr>
              <td><strong>{label}</strong><br><small>{desc}</small></td>
              <td style="color:{clr_m}; font-weight:800;">{val_m}</td>
              <td style="color:{clr_d}; font-weight:800;">{val_d}</td>
            </tr>"""

        metrics_html = (
            get_metric_row("LCP", "lcp", "lcp", "Largest Contentful Paint (Visual Load)") +
            get_metric_row("TBT", "tbt", "tbt", "Total Blocking Time (Interactivity)") +
            get_metric_row("CLS", "cls", "cls", "Cumulative Layout Shift (Stability)") +
            get_metric_row("FCP", "fcp", "fcp", "First Contentful Paint") +
            get_metric_row("SI", "si", "si", "Speed Index") +
            get_metric_row("TTI", "tti", "tti", "Time to Interactive")
        )

        # ── Category slides ───────────────────────────────────────────────────
        category_slides = ""
        m_cats = m.get("categories", [])
        d_cats = d.get("categories", [])
        
        for idx in range(num_cats):
            m_cat = m_cats[idx]
            d_cat = d_cats[idx] if idx < len(d_cats) else {}
            
            slide_num = str(idx + 3).zfill(2)
            
            # Combine opportunities - if it fails in either, show it
            items_html = ""
            # We'll use mobile items as primary list
            for i_idx, m_item in enumerate(m_cat.get("items", [])):
                d_item = d_cat.get("items", [{}])[i_idx] if i_idx < len(d_cat.get("items", [])) else {}
                
                # Pick worst status
                status = m_item["status"]
                if d_item.get("status") == "fail": status = "fail"
                elif d_item.get("status") == "warning" and status == "pass": status = "warning"
                
                emoji, label, clr, bdg_cls = status_meta(status)
                safe_content = m_item.get("content", "")[:260].replace("<", "&lt;").replace(">", "&gt;")
                
                # Annotate if platform specific
                platform_note = ""
                if m_item["status"] != d_item.get("status"):
                    if m_item["status"] == "fail": platform_note = '<span style="color:#dc2626; font-size:9px; font-weight:800;">⚠️ MOBILE ISSUE</span>'
                    if d_item.get("status") == "fail": platform_note = '<span style="color:#dc2626; font-size:9px; font-weight:800;">🖥️ DESKTOP ISSUE</span>'

                items_html += f"""
            <div class="ci">
              <span class="cico">{emoji}</span>
              <div class="ctx">
                <h4>{m_item["title"]}</h4>
                <p>{safe_content}</p>
                {platform_note}
              </div>
              <span class="cbdg {bdg_cls}">{label}</span>
            </div>"""

            category_slides += f"""
        <div class="slide">
          <div class="slide-sidebar spd-sb">
            <div class="sb-logo">SPEED AUDIT</div>
            <div class="sb-score-row">
              <div class="sb-sc-box">
                <div class="sb-sc-val">{m_score}</div>
                <div class="sb-sc-lbl">MOBILE</div>
              </div>
              <div class="sb-sc-box">
                <div class="sb-sc-val" style="color:#fcd34d">{d_score}</div>
                <div class="sb-sc-lbl">DESKTOP</div>
              </div>
            </div>
            <div class="sb-stat"><span class="sl">Grade (M)</span><span class="sv">{m_grade}</span></div>
            <div class="sb-stat"><span class="sl">Grade (D)</span><span class="sv" style="color:#fcd34d">{d_grade}</span></div>
            <div class="sb-slide-num">SLIDE {slide_num} / {total_slides_str}</div>
            <div class="sb-domain">{m_cat["name"]}</div>
          </div>
          <div class="slide-content" style="justify-content: flex-start; padding-top: 40px">
            <div class="c-title">{m_cat["name"]}</div>
            <div class="c-sub">{m_cat["tagline"]}</div>
            <div class="check-list">{items_html}</div>
          </div>
        </div>"""

        dots_html = "".join(
            f'<div class="dot {"active" if i == 0 else ""}" data-goto="{i+1}"></div>'
            for i in range(total_slides)
        )

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Speed Report — {domain}</title>
<link href="https://fonts.googleapis.com/css2?family=Sora:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
html, body {{ height: 100%; background: #e8edf5; font-family: "Sora", sans-serif; overflow: hidden; color: #0a0f1e; }}
.deck {{ width: 100vw; height: 100vh; position: relative; }}
.slide {{ position: absolute; inset: 0; opacity: 0; pointer-events: none; transform: scale(0.97); transition: opacity 0.38s ease, transform 0.38s ease; display: flex; overflow: hidden; }}
.slide.active {{ opacity: 1; pointer-events: all; transform: scale(1); }}
.slide.exit {{ opacity: 0; transform: scale(1.02); }}
.slide-sidebar {{ width: 280px; flex-shrink: 0; padding: 48px 32px; display: flex; flex-direction: column; }}
.slide-content {{ flex: 1; background: #fff; padding: 52px 48px; overflow-y: auto; display: flex; flex-direction: column; justify-content: center; }}
.sb-logo {{ font-size: 13px; font-weight: 700; letter-spacing: 0.12em; text-transform: uppercase; opacity: 0.5; margin-bottom: 48px; }}

.sb-score-row {{ display: flex; gap: 16px; margin-bottom: 32px; }}
.sb-sc-box {{ flex: 1; }}
.sb-sc-val {{ font-size: 48px; font-weight: 800; line-height: 1; letter-spacing: -0.04em; }}
.sb-sc-lbl {{ font-size: 10px; font-weight: 700; opacity: 0.5; margin-top: 4px; }}

.sb-stat {{ display: flex; justify-content: space-between; align-items: center; padding: 10px 0; border-bottom: 1px solid rgba(255, 255, 255, 0.12); }}
.sb-stat .sl {{ font-size: 11px; font-weight: 600; opacity: 0.6; }}
.sb-stat .sv {{ font-size: 16px; font-weight: 800; }}
.sb-slide-num {{ margin-top: auto; font-size: 11px; font-weight: 700; opacity: 0.35; letter-spacing: 0.1em; }}
.sb-domain {{ font-size: 12px; font-weight: 600; opacity: 0.35; margin-top: 6px; }}

.cover-sb {{ background: #0a0f1e; color: #fff; }}
.cover-sb .sb-sc-val {{ color: #6366f1; }}
.sum-sb {{ background: #6366f1; color: #fff; }}
.spd-sb {{ background: #b45309; color: #fff; }}
.end-sb {{ background: #1e1b4b; color: #fff; }}

.cover-title {{ font-size: 40px; font-weight: 800; line-height: 1.15; letter-spacing: -0.03em; margin-bottom: 16px; color: #0a0f1e; }}
.cover-sub {{ font-size: 15px; color: #64748b; margin-bottom: 36px; line-height: 1.6; }}

.gauge-grid {{ display: flex; gap: 120px; margin-bottom: 60px; justify-content: center; padding: 20px 0; }}
.gauge-item {{ text-align: center; display: flex; flex-direction: column; align-items: center; }}
.gauge-label {{ font-size: 14px; font-weight: 800; color: #64748b; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 24px; }}
.gauge-visual {{ position: relative; width: 220px; height: 220px; display: flex; align-items: center; justify-content: center; }}
.gauge-svg {{ width: 220px; height: 220px; transform: rotate(-90deg); }}
.gauge-bg {{ fill: none; stroke: #f1f5f9; stroke-width: 4; }}
.gauge-fill {{ fill: none; stroke-width: 4; stroke-linecap: round; transition: stroke-dashoffset 1s ease-out; }}
.gauge-center {{ position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; }}
.gauge-val {{ font-size: 64px; font-weight: 800; }}

.c-title {{ font-size: 32px; font-weight: 800; letter-spacing: -0.02em; margin-bottom: 8px; color: #0a0f1e; }}
.c-sub {{ font-size: 14px; color: #64748b; margin-bottom: 32px; }}
.m-table {{ width: 100%; border-collapse: collapse; margin-top: 16px; }}
.m-table th {{ text-align: left; padding: 12px; font-size: 11px; font-weight: 800; color: #64748b; text-transform: uppercase; border-bottom: 2px solid #f1f5f9; }}
.m-table td {{ padding: 16px 12px; border-bottom: 1px solid #f1f5f9; font-size: 14px; }}
.m-table small {{ display: block; font-size: 11px; font-weight: 500; color: #94a3b8; margin-top: 2px; }}
.check-list {{ display: flex; flex-direction: column; gap: 10px; }}
.ci {{ display: flex; gap: 14px; padding: 14px 18px; border-radius: 12px; background: #f8fafc; border: 1px solid #e2e8f0; align-items: flex-start; transition: all 0.2s; max-width: 100%; }}
.ci:hover {{ background: #fff; border-color: #cbd5e1; box-shadow: 0 4px 12px -2px rgba(0,0,0,0.05); }}
.cico {{ font-size: 20px; flex-shrink: 0; margin-top: 1px; }}
.ctx {{ flex: 1; min-width: 0; }}
.ctx h4 {{ font-size: 13px; font-weight: 700; color: #0f172a; margin-bottom: 4px; }}
.ctx p {{ font-size: 12px; color: #64748b; line-height: 1.6; word-break: break-word; overflow-wrap: break-word; }}
.cbdg {{ flex-shrink: 0; margin-left: auto; font-size: 10px; font-weight: 700; padding: 4px 10px; border-radius: 6px; white-space: nowrap; text-transform: uppercase; letter-spacing: 0.02em; }}
.bd-r {{ background: #fee2e2; color: #dc2626; }}
.bd-y {{ background: #fef9c3; color: #d97706; }}
.bd-b {{ background: #dbeafe; color: #1d4ed8; }}
.bd-g {{ background: #dcfce7; color: #15803d; }}

.premium-cta {{ background: linear-gradient(135deg, #f8faff 0%, #f1f5fe 100%); border-radius: 24px; padding: 40px; margin-top: 24px; display: grid; grid-template-columns: 1.2fr 0.8fr; gap: 32px; align-items: center; border: 1px solid #e2e8f1; text-align: left; }}
.hero-text h3 {{ font-size: 22px; font-weight: 800; color: #0a0f1e; margin-bottom: 12px; }}
.hero-text p {{ font-size: 13px; color: #64748b; line-height: 1.6; margin-bottom: 24px; }}
.p-btn {{ display: block; background: linear-gradient(135deg, #6366f1, #4f46e5); color: #fff; padding: 16px; border-radius: 12px; text-decoration: none; font-weight: 800; font-size: 13px; text-align: center; }}

.floating-nav {{ position: fixed; bottom: 32px; left: 50%; transform: translateX(-50%); background: rgba(255, 255, 255, 0.7); backdrop-filter: blur(15px); border: 1px solid rgba(255, 255, 255, 0.4); box-shadow: 0 15px 35px -5px rgba(0, 0, 0, 0.1); padding: 10px 14px; border-radius: 100px; display: flex; align-items: center; gap: 16px; z-index: 1000; }}
.nav-btn {{ background: transparent; border: none; color: #0a0f1e; font-size: 18px; cursor: pointer; padding: 8px; border-radius: 50%; }}
.nav-btn:hover {{ background: rgba(99, 102, 241, 0.1); color: #6366f1; }}
.nav-btn:disabled {{ opacity: 0.2; cursor: default; }}
.step-dots {{ display: flex; gap: 8px; align-items: center; }}
.dot {{ width: 8px; height: 8px; border-radius: 50%; background: #e2e8f0; cursor: pointer; transition: all 0.3s; }}
.dot.active {{ background: #6366f1; width: 24px; border-radius: 10px; }}
.nav-ctr {{ font-size: 11px; font-weight: 800; color: #94a3b8; min-width: 35px; }}
@media print {{
  @page {{ size: A4 landscape; margin: 0; }}
  html, body {{ height: auto !important; overflow: visible !important; background: white !important; }}
  .deck {{ height: auto !important; width: 100% !important; display: block !important; overflow: visible !important; }}
  .slide {{ position: relative !important; opacity: 1 !important; transform: none !important; display: flex !important; page-break-after: always !important; break-after: page !important; height: auto !important; min-height: 21cm; }}
  .slide-sidebar {{ width: 220px !important; }}
  .floating-nav {{ display: none !important; }}
}}
</style>
</head>
<body>
<div class="deck" id="deck">

  <!-- SLIDE 01: Cover -->
  <div class="slide active">
    <div class="slide-sidebar cover-sb">
      <div class="sb-logo">SPEED AUDIT</div>
      <div class="sb-score-row">
        <div class="sb-sc-box">
          <div class="sb-sc-val">{m_score}</div>
          <div class="sb-sc-lbl">MOBILE</div>
        </div>
        <div class="sb-sc-box">
          <div class="sb-sc-val" style="color:#6366f1">{d_score}</div>
          <div class="sb-sc-lbl">DESKTOP</div>
        </div>
      </div>
      <div class="sb-stat"><span class="sl">Grade (M)</span><span class="sv">{m_grade}</span></div>
      <div class="sb-stat"><span class="sl">Grade (D)</span><span class="sv" style="color:#6366f1">{d_grade}</span></div>
      <div class="sb-slide-num">SLIDE 01 / {total_slides_str}</div>
      <div class="sb-domain">{domain}</div>
    </div>
    <div class="slide-content">
      <div class="cover-title">Multi-Platform Speed Analysis</div>
      <div class="cover-sub">Comparing performance signals for <strong>{domain}</strong> across Mobile and Desktop. Generated on {timestamp}.</div>
      
      <div class="gauge-grid">
        {get_gauge_html(m_score, "📱 Mobile Performance", m_color)}
        {get_gauge_html(d_score, "🖥️ Desktop Performance", d_color)}
      </div>

      <div style="background:#f1f5f9; padding:20px; border-radius:16px; font-size:13px; color:#475569; line-height:1.5;">
        <strong>Why analyze both?</strong> Google uses "Mobile-First" indexing, meaning your mobile speed determines your rank. However, desktop speed remains critical for conversion and user engagement.
      </div>
    </div>
  </div>

  <!-- SLIDE 02: CWV Comparison -->
  <div class="slide">
    <div class="slide-sidebar sum-sb">
      <div class="sb-logo">SPEED AUDIT</div>
      <div class="sb-score-row">
        <div class="sb-sc-box">
          <div class="sb-sc_val" style="font-size:24px; color:#fff">M vs D</div>
        </div>
      </div>
      <div class="sb-stat"><span class="sl">Status</span><span class="sv">Analyzed</span></div>
      <div class="sb-slide-num">SLIDE 02 / {total_slides_str}</div>
      <div class="sb-domain">Core Web Vitals</div>
    </div>
    <div class="slide-content">
      <div class="c-title">Core Metrics Comparison</div>
      <div class="c-sub">Comparison of Core Web Vitals across both strategies.</div>
      
      <table class="m-table">
        <thead>
          <tr>
            <th>Metric</th>
            <th>📱 Mobile</th>
            <th>🖥️ Desktop</th>
          </tr>
        </thead>
        <tbody>
          {metrics_html}
        </tbody>
      </table>
    </div>
  </div>

  <!-- CATEGORY SLIDES -->
  {category_slides}

  <!-- SLIDE: End -->
  <div class="slide">
    <div class="slide-sidebar end-sb">
      <div class="sb-logo">SPEED AUDIT</div>
      <div class="sb-score-row">
        <div class="sb-sc-box">
          <div class="sb-sc-val">{m_score}</div>
          <div class="sb-sc-lbl">FINAL (M)</div>
        </div>
        <div class="sb-sc-box">
          <div class="sb-sc-val" style="color:#a5b4fc">{d_score}</div>
          <div class="sb-sc-lbl">FINAL (D)</div>
        </div>
      </div>
      <div class="sb-stat"><span class="sl">Status</span><span class="sv">Complete</span></div>
      <div class="sb-slide-num">SLIDE {total_slides} / {total_slides}</div>
      <div class="sb-domain">Complete</div>
    </div>
    <div class="slide-content" style="justify-content: center; padding: 48px">
      <div style="display:inline-block; background:#f0f9ff; color:#0369a1; font-size:11px; font-weight:700; letter-spacing:0.12em; text-transform:uppercase; padding:6px 16px; border-radius:50px; margin-bottom:24px;">🎉 Audit Complete</div>
      <div class="cover-title" style="font-size: 48px; line-height: 1">Let's build your<br><span style="color: #6366f1">digital dominance.</span></div>

      <div class="premium-cta">
        <div class="hero-text">
          <h3>Optimized for every screen.</h3>
          <p>Fast load times are no longer optional. We've identified the key opportunities to make your site fly on both mobile and desktop.</p>
          <div style="display: flex; align-items: center; gap: 12px">
            <div style="width: 40px; height: 40px; border-radius: 50%; background:#6366f1; display:flex; align-items:center; justify-content:center; color:white; font-weight:bold;">NH</div>
            <div>
              <div style="font-size: 12px; font-weight: 800; color: #0a0f1e">Notionhive Digital Agency</div>
              <div style="font-size: 11px; color: #64748b">15+ Years · 1,500+ Projects</div>
            </div>
          </div>
        </div>
        <div class="action-box">
          <a href="https://notionhive.com" class="p-btn">Claim Your Free Audit</a>
          <div style="margin-top: 16px; font-size: 10px; font-weight: 700; color: #94a3b8; letter-spacing: 0.05em; text-align:center;">HELLO@NOTIONHIVE.COM</div>
        </div>
      </div>
    </div>
  </div>

</div>

<div class="floating-nav">
  <button class="nav-btn" id="prev" onclick="go(-1)">←</button>
  <div class="step-dots" id="dots">{dots_html}</div>
  <span class="nav-ctr" id="ctr">1 / {total_slides}</span>
  <button class="nav-btn" id="next" onclick="go(1)">→</button>
</div>

<script>
const slides = document.querySelectorAll(".slide");
const ctr = document.getElementById("ctr");
const prev = document.getElementById("prev");
const next = document.getElementById("next");
let cur = 0;

function goTo(n) {{
  if (n < 0 || n >= slides.length) return;
  slides[cur].classList.remove("active");
  slides[cur].classList.add("exit");
  const o = cur;
  setTimeout(() => {{ if(slides[o]) slides[o].classList.remove("exit"); }}, 400);
  cur = n;
  slides[cur].classList.add("active");
  document.querySelectorAll(".dot").forEach((d, i) => d.classList.toggle("active", i === cur));
  ctr.textContent = (cur + 1) + " / " + slides.length;
  prev.disabled = cur === 0;
  next.disabled = cur === slides.length - 1;
  slides[cur].scrollTop = 0;
}}

function go(d) {{
  goTo(cur + d);
}}

document.querySelectorAll(".dot").forEach((d, i) => {{
  d.onclick = () => goTo(i);
}});

document.addEventListener("keydown", (e) => {{
  if (e.key === "ArrowRight" || e.key === "ArrowDown") go(1);
  if (e.key === "ArrowLeft" || e.key === "ArrowUp") go(-1);
}});

goTo(0);
</script>
</body>
</html>"""
        return html
    except Exception as e:
        return f"<h1>Error generating dual speed report: {e}</h1>"
