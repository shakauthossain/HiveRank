import asyncio
import os
import time
from datetime import datetime


async def scrape_rankmath_async(url: str):
    from playwright.async_api import async_playwright

    data = {
        "url": url,
        "seo_score": "N/A",
        "passed": "0",
        "warnings": "0",
        "failed": "0",
        "categories": [],
        "timestamp": datetime.now().strftime("%B %d, %Y at %H:%M"),
    }

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
        )
        page = await context.new_page()

        try:
            await page.goto("https://rankmath.com/tools/seo-analyzer/", timeout=60000)
            await page.wait_for_load_state("domcontentloaded")
            await asyncio.sleep(2)

            # Find input
            input_box = None
            for sel in [
                "input#url",
                "input[name='url']",
                "input[type='url']",
                "input[placeholder*='http']",
                "input[placeholder*='URL']",
                "input[placeholder*='url']",
                "input[placeholder*='Enter']",
                "input[placeholder*='website']",
                "form input[type='text']",
                "input[type='text']",
            ]:
                try:
                    el = page.locator(sel).first
                    await el.wait_for(timeout=3000, state="visible")
                    input_box = el
                    break
                except Exception:
                    continue

            if input_box is None:
                try:
                    input_box = page.locator("input").first
                    await input_box.wait_for(timeout=5000, state="visible")
                except Exception:
                    await browser.close()
                    return data

            await input_box.click()
            await input_box.fill("")
            await input_box.type(url, delay=50)

            # Find button
            btn = None
            for sel in [
                "button#analyze",
                "button[type='submit']",
                "input[type='submit']",
                "button:has-text('Analyze')",
                "button:has-text('Check')",
                ".analyzer button",
                "form button",
            ]:
                try:
                    el = page.locator(sel).first
                    await el.wait_for(timeout=3000, state="visible")
                    btn = el
                    break
                except Exception:
                    continue

            if btn:
                await btn.click()
            else:
                await input_box.press("Enter")

            # Wait for results
            result_found = False
            for sel in [
                "div.container.analysis-result.clear",
                "div.analysis-result",
                ".rank-math-result-graphs",
                "#analysis",
                "[class*='result']",
            ]:
                try:
                    await page.wait_for_selector(sel, timeout=60000)
                    result_found = True
                    break
                except Exception:
                    continue

            if not result_found:
                await browser.close()
                return data

            await asyncio.sleep(3)

            # Scrape score
            graphs = page.locator("div.rank-math-result-graphs")
            text = await graphs.inner_text()
            lines = [l.strip() for l in text.splitlines() if l.strip()]

            for i, line in enumerate(lines):
                if "Passed Tests" in line and i > 0:
                    data["passed"] = lines[i - 1].strip()
                if "Warnings" in line and i > 0:
                    data["warnings"] = lines[i - 1].strip()
                if "Failed Tests" in line and i > 0:
                    data["failed"] = lines[i - 1].strip()

            for line in lines:
                if "/" in line and "Tests" not in line and "Warnings" not in line:
                    data["seo_score"] = line.split("/")[0].strip()
                    break

            # Scrape categories
            tables = await page.locator("div.rank-math-result-table").all()
            for table in tables:
                cat_name_el = table.locator("div.category-title")
                cat_name = (
                    await cat_name_el.inner_text()
                    if await cat_name_el.count() > 0
                    else "Analysis"
                )

                rows = await table.locator("div.table-row").all()
                items = []
                for row in rows:
                    title_el = row.locator("div.row-title")
                    content_el = row.locator("div.row-content")

                    if await title_el.count() == 0:
                        continue

                    title = await title_el.inner_text()
                    content = (
                        await content_el.inner_text()
                        if await content_el.count() > 0
                        else ""
                    )

                    status = "info"
                    try:
                        ic = (
                            await row.locator("div.status-icon").get_attribute("class")
                            or ""
                        )
                        if any(x in ic for x in ["check", "good", "success"]):
                            status = "pass"
                        elif any(x in ic for x in ["warning", "warn"]):
                            status = "warning"
                        elif any(x in ic for x in ["times", "error", "fail"]):
                            status = "fail"
                    except:
                        pass
                    items.append(
                        {
                            "title": title.strip(),
                            "content": content.strip(),
                            "status": status,
                        }
                    )
                if items:
                    data["categories"].append(
                        {"name": cat_name.strip(), "items": items}
                    )

        except Exception as e:
            print(f"Error scraping SEO: {e}")
        finally:
            await browser.close()
            return data


def generate_html(data: dict) -> str:
    """Generates the premium Slide-Deck HTML report for SEO (no Jinja2 â pure inline f-string)."""
    try:
        # ââ Inline helper functions âââââââââââââââââââââââââââââââââââââââââââ

        def to_int(v):
            if not v:
                return 0
            if isinstance(v, int):
                return v
            s = "".join(filter(str.isdigit, str(v)))
            return int(s) if s else 0

        def score_color(s):
            try:
                n = int(s)
                if n >= 80:
                    return "#16a34a"
                if n >= 60:
                    return "#d97706"
                return "#dc2626"
            except:
                return "#6b7280"

        def score_label(s):
            try:
                n = int(s)
                if n >= 80:
                    return (
                        "Excellent",
                        "Your website is well-optimized! A few tweaks and you could be perfect.",
                    )
                if n >= 60:
                    return (
                        "Needs Work",
                        "Your site has a decent foundation but several things need attention.",
                    )
                return (
                    "Critical Issues",
                    "Your website has serious SEO problems that are likely hurting your visibility.",
                )
            except:
                return ("Unknown", "We couldn't determine your score.")

        def grade(s):
            try:
                n = int(s)
                if n >= 90:
                    return "A"
                if n >= 80:
                    return "B"
                if n >= 70:
                    return "C"
                if n >= 60:
                    return "D"
                return "F"
            except:
                return "?"

        def status_meta(status):
            if status == "pass":
                return ("✅", "Good", "#15803d", "bd-g")
            if status == "warning":
                return ("⚠️", "Warn", "#d97706", "bd-y")
            if status == "fail":
                return ("❌", "Fix", "#dc2626", "bd-r")
            return ("ℹ️", "Info", "#1d4ed8", "bd-b")

        def friendly_name(raw):
            mapping = {
                "Basic SEO": (
                    "🔍",
                    "Basic SEO Checks",
                    "The fundamental building blocks of your site's visibility on Google.",
                ),
                "Advanced SEO": (
                    "⚙️",
                    "Advanced SEO",
                    "Deeper technical signals that help Google better understand your site.",
                ),
                "Title": (
                    "📄",
                    "Title Optimization",
                    "How well your page titles are crafted for search engines and users.",
                ),
                "Content": (
                    "📝",
                    "Content Analysis",
                    "The quality and structure of your on-page content.",
                ),
                "Links": (
                    "🔗",
                    "Links & Navigation",
                    "Internal and external links that help Google crawl your site.",
                ),
                "Performance": (
                    "⚡",
                    "Page Speed & Performance",
                    "How fast your website loads â€” slow sites lose visitors and rankings.",
                ),
                "Social": (
                    "📱",
                    "Social Media Sharing",
                    "How your site looks when shared on Facebook, Twitter, etc.",
                ),
                "Schema": (
                    "📁",
                    "Schema & Structured Data",
                    "Rich data markup that helps Google understand your content better.",
                ),
            }
            for key, val in mapping.items():
                if key.lower() in raw.lower():
                    return val
            return ("📋", raw, "Analysis results for this category.")

        # â”€â”€ Parse raw data â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

        score = to_int(data.get("seo_score", 0))
        p = to_int(data.get("passed", 0))
        w = to_int(data.get("warnings", 0))
        f = to_int(data.get("failed", 0))
        total = max(p + w + f, 1)

        color = score_color(score)
        s_label, s_desc = score_label(score)
        g = grade(score)
        dash_val = round(3.14159 * 2 * 54 * score / 100, 1)

        domain = (
            data.get("url", "")
            .replace("https://", "")
            .replace("http://", "")
            .rstrip("/")
            .split("/")[0]
        )
        timestamp = data.get("timestamp", datetime.now().strftime("%B %d, %Y at %H:%M"))

        p_pct = round(p / total * 100)
        w_pct = round(w / total * 100)
        f_pct = round(f / total * 100)

        categories = data.get("categories", [])
        num_cats = len(categories)
        total_slides = 2 + num_cats + 1
        total_slides_str = str(total_slides).zfill(2)

        def get_cat_theme(name):
            n = name.lower()
            if "basic" in n: return "basic-sb", "🔍 Basic SEO"
            if "advanced" in n: return "adv-sb", "🚀 Advanced SEO"
            if "speed" in n or "performance" in n: return "spd-sb", "⚡ Speed"
            if "security" in n: return "sec-sb", "🔒 Security"
            return "cover-sb", name

        # â”€â”€ Build category slides â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

        category_slides = ""
        for idx, cat in enumerate(categories):
            sb_theme, friendly_title = get_cat_theme(cat["name"])
            slide_num = str(idx + 3).zfill(2)

            pass_c = sum(1 for i in cat["items"] if i["status"] == "pass")
            warn_c = sum(1 for i in cat["items"] if i["status"] == "warning")
            fail_c = sum(1 for i in cat["items"] if i["status"] == "fail")
            cat_total = len(cat["items"])

            items_html = ""
            for item in cat["items"]:
                emoji, lbl, clr, bdg_cls = status_meta(item["status"])
                # Sanitize content to prevent broken HTML tags from wrecking layout
                raw_content = item.get("content", "")
                display = raw_content[:400].replace("<", "&lt;").replace(">", "&gt;")
                if len(raw_content) > 400:
                    display += "..."

                items_html += f"""
            <div class="ci">
              <span class="cico">{emoji}</span>
              <div class="ctx">
                <h4>{item["title"]}</h4>
                <p>{display}</p>
              </div>
              <span class="cbdg {bdg_cls}">{lbl}</span>
            </div>"""

            category_slides += f"""
      <div class="slide">
        <div class="slide-sidebar {sb_theme}">
          <div class="sb-logo">SEO AUDIT</div>
          <div class="sb-big-num">{cat_total}</div>
          <div class="sb-big-label">CHECKS</div>
          <div class="sb-stat"><span class="sl">Problems</span><span class="sv">{fail_c}</span></div>
          <div class="sb-stat"><span class="sl">Warnings</span><span class="sv">{warn_c}</span></div>
          <div class="sb-stat"><span class="sl">Passing</span><span class="sv">{pass_c}</span></div>
          <div class="sb-slide-num">SLIDE {slide_num} / {total_slides_str}</div>
          <div class="sb-domain">{cat["name"]}</div>
        </div>
        <div class="slide-content" style="justify-content: flex-start; padding-top: 40px">
          <div class="c-title">{friendly_title}</div>
          <div class="c-sub">Category analysis for {domain}</div>
          <div class="pills-row">
            <span class="pill pill-r">{fail_c} Problems</span>
            <span class="pill pill-y">{warn_c} Warnings</span>
            <span class="pill pill-b">{pass_c} Passing</span>
          </div>
          <div class="check-list">{items_html}</div>
        </div>
      </div>"""

        # â”€â”€ Build nav dots â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        slide_nav_dots = "".join(
            f'<div class="dot {"active" if i == 0 else ""}" data-goto="{i+1}"></div>'
            for i in range(total_slides)
        )

        html = f"""<!DOCTYPE html>
<html>
<head>
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
.sb-big-num {{ font-size: 96px; font-weight: 800; line-height: 1; letter-spacing: -0.04em; margin-bottom: 4px; }}
.sb-big-label {{ font-size: 12px; font-weight: 600; opacity: 0.5; letter-spacing: 0.06em; margin-bottom: 32px; }}
.sb-stat {{ display: flex; justify-content: space-between; align-items: center; padding: 10px 0; border-bottom: 1px solid rgba(255, 255, 255, 0.12); }}
.sb-stat .sl {{ font-size: 12px; font-weight: 600; opacity: 0.6; }}
.sb-stat .sv {{ font-size: 18px; font-weight: 800; }}
.sb-slide-num {{ margin-top: auto; font-size: 11px; font-weight: 700; opacity: 0.35; letter-spacing: 0.1em; }}
.sb-domain {{ font-size: 12px; font-weight: 600; opacity: 0.35; margin-top: 6px; }}
.cover-sb {{ background: #0a0f1e; color: #fff; }}
.cover-sb .sb-big-num {{ color: #6366f1; }}
.sum-sb {{ background: #6366f1; color: #fff; }}
.basic-sb {{ background: #0f766e; color: #fff; }}
.basic-sb .sb-big-num {{ color: #5eead4; }}
.adv-sb {{ background: #7c3aed; color: #fff; }}
.adv-sb .sb-big-num {{ color: #c4b5fd; }}
.spd-sb {{ background: #b45309; color: #fff; }}
.spd-sb .sb-big-num {{ color: #fcd34d; }}
.sec-sb {{ background: #166534; color: #fff; }}
.sec-sb .sb-big-num {{ color: #86efac; }}
.end-sb {{ background: #1e1b4b; color: #fff; }}
.end-sb .sb-big-num {{ color: #a5b4fc; }}
.cover-title {{ font-size: 40px; font-weight: 800; line-height: 1.15; letter-spacing: -0.03em; margin-bottom: 16px; color: #0a0f1e; }}
.cover-sub {{ font-size: 15px; color: #64748b; margin-bottom: 36px; line-height: 1.6; }}
.chips {{ display: flex; flex-direction: column; gap: 10px; }}
.chip {{ display: flex; align-items: center; justify-content: space-between; padding: 14px 18px; border-radius: 12px; font-size: 14px; font-weight: 700; }}
.chip-g {{ background: #f0fdf4; color: #15803d; }}
.chip-y {{ background: #fffbeb; color: #b45309; }}
.chip-r {{ background: #fef2f2; color: #dc2626; }}
.chip .cn {{ font-size: 22px; font-weight: 800; }}
.c-title {{ font-size: 32px; font-weight: 800; letter-spacing: -0.02em; margin-bottom: 8px; color: #0a0f1e; }}
.c-sub {{ font-size: 14px; color: #64748b; margin-bottom: 32px; }}
.donut-row {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-top: 24px; }}
.dcol {{ border-radius: 14px; padding: 20px; text-align: center; }}
.dcol.g {{ background: #f0fdf4; }}
.dcol.y {{ background: #fffbeb; }}
.dcol.r {{ background: #fef2f2; }}
.dcol .dn {{ font-size: 36px; font-weight: 800; line-height: 1; margin-bottom: 4px; }}
.dcol .dl {{ font-size: 12px; font-weight: 600; color: #64748b; }}
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
.pills-row {{ display: flex; gap: 8px; margin-bottom: 18px; flex-wrap: wrap; }}
.pill {{ padding: 5px 14px; border-radius: 20px; font-size: 11px; font-weight: 700; }}
.pill-r {{ background: #fee2e2; color: #dc2626; }}
.pill-y {{ background: #fef9c3; color: #d97706; }}
.pill-b {{ background: #dbeafe; color: #1d4ed8; }}
.floating-nav {{ position: fixed; bottom: 32px; left: 50%; transform: translateX(-50%); background: rgba(255, 255, 255, 0.7); backdrop-filter: blur(15px); border: 1px solid rgba(255, 255, 255, 0.4); box-shadow: 0 15px 35px -5px rgba(0, 0, 0, 0.1); padding: 10px 14px; border-radius: 100px; display: flex; align-items: center; gap: 16px; z-index: 1000; }}
.nav-btn {{ background: transparent; border: none; color: #0a0f1e; font-size: 18px; cursor: pointer; padding: 8px; border-radius: 50%; }}
.nav-btn:hover {{ background: rgba(99, 102, 241, 0.1); color: #6366f1; }}
.nav-btn:disabled {{ opacity: 0.2; cursor: default; }}
.step-dots {{ display: flex; gap: 8px; align-items: center; }}
.dot {{ width: 8px; height: 8px; border-radius: 50%; background: #e2e8f0; cursor: pointer; transition: all 0.3s; }}
.dot.active {{ background: #6366f1; width: 24px; border-radius: 10px; }}
.nav-ctr {{ font-size: 11px; font-weight: 800; color: #94a3b8; min-width: 35px; }}
.gauge-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 24px; margin-bottom: 32px; }}
.gauge-item {{ text-align: center; display: flex; flex-direction: column; align-items: center; }}
.gauge-label {{ font-size: 12px; font-weight: 800; color: #0a0f1e; text-transform: uppercase; margin-bottom: 12px; }}
.gauge-visual {{ position: relative; width: 120px; height: 120px; display: flex; align-items: center; justify-content: center; }}
.gauge-svg {{ width: 120px; height: 120px; transform: rotate(-90deg); }}
.gauge-bg {{ fill: none; stroke: #f1f5f9; stroke-width: 8; }}
.gauge-fill {{ fill: none; stroke-width: 10; stroke-linecap: round; transition: stroke-dashoffset 1s; }}
.gauge-center {{ position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; }}
.gauge-val {{ font-size: 24px; font-weight: 800; color: #0a0f1e; }}
.gauge-unit {{ font-size: 12px; color: #94a3b8; }}
.hint {{ position: fixed; top: 14px; right: 14px; font-size: 10px; color: #94a3b8; font-weight: 600; }}
.premium-cta {{ background: linear-gradient(135deg, #f8faff 0%, #f1f5fe 100%); border-radius: 24px; padding: 40px; margin-top: 24px; display: grid; grid-template-columns: 1.2fr 0.8fr; gap: 32px; align-items: center; border: 1px solid #e2e8f1; }}
.hero-text h3 {{ font-size: 22px; font-weight: 800; color: #0a0f1e; margin-bottom: 12px; }}
.hero-text p {{ font-size: 13px; color: #64748b; line-height: 1.6; margin-bottom: 24px; }}
.p-btn {{ display: block; background: linear-gradient(135deg, #6366f1, #4f46e5); color: #fff; padding: 16px; border-radius: 12px; text-decoration: none; font-weight: 800; font-size: 13px; text-align: center; }}
@media print {{
  @page {{ size: A4 landscape; margin: 0; }}
  html, body {{ height: auto !important; overflow: visible !important; background: white !important; }}
  .deck {{ height: auto !important; width: 100% !important; display: block !important; overflow: visible !important; }}
  .slide {{ position: relative !important; opacity: 1 !important; transform: none !important; display: flex !important; page-break-after: always !important; break-after: page !important; height: auto !important; min-height: 21cm; }}
  .slide-sidebar {{ width: 200px !important; }}
  .floating-nav, .hint {{ display: none !important; }}
}}
</style>
</head>
<body>
<div class="deck" id="deck">

  <!-- SLIDE 01: Cover -->
  <div class="slide active">
    <div class="slide-sidebar cover-sb">
      <div class="sb-logo">SEO AUDIT</div>
      <div class="sb-big-num">{score}</div>
      <div class="sb-big-label">OVERALL SCORE</div>
      <div class="sb-stat"><span class="sl">Grade</span><span class="sv">{g}</span></div>
      <div class="sb-stat"><span class="sl">Verdict</span><span class="sv" style="font-size:12px;">{s_label}</span></div>
      <div class="sb-slide-num">SLIDE 01 / {total_slides_str}</div>
      <div class="sb-domain">{domain}</div>
    </div>
    <div class="slide-content">
      <div class="cover-title">Full SEO Performance Analysis</div>
      <div class="cover-sub">
        We've analyzed <strong>{domain}</strong> across {num_cats} technical categories. 
        Generated on {timestamp}.
      </div>
      <div class="chips">
        <div class="chip chip-g"><span>✅ Passed Checks</span><span class="cn">{p}</span></div>
        <div class="chip chip-y"><span>⚠️ Improvements Needed</span><span class="cn">{w}</span></div>
        <div class="chip chip-r"><span>❌ Critical Problems</span><span class="cn">{f}</span></div>
      </div>
    </div>
  </div>

  <!-- SLIDE 02: Summary -->
  <div class="slide">
    <div class="slide-sidebar sum-sb">
      <div class="sb-logo">SEO AUDIT</div>
      <div class="sb-big-num">{total}</div>
      <div class="sb-big-label">TOTAL CHECKS</div>
      <div class="sb-stat"><span class="sl">Status</span><span class="sv">Analysis</span></div>
      <div class="sb-slide-num">SLIDE 02 / {total_slides_str}</div>
      <div class="sb-domain">Executive Summary</div>
    </div>
    <div class="slide-content">
      <div class="c-title">Executive Summary</div>
      <div class="c-sub">High-level breakdown of your website's search engine health.</div>
      
      <div class="gauge-grid">
        <div class="gauge-item">
          <div class="gauge-label">Working Well</div>
          <div class="gauge-visual">
            <svg class="gauge-svg" viewBox="0 0 100 100">
              <circle class="gauge-bg" cx="50" cy="50" r="40" />
              <circle class="gauge-fill" cx="50" cy="50" r="40" stroke="#10b981" 
                stroke-dasharray="251.2" stroke-dashoffset="{251.2 * (1 - p/total)}" />
            </svg>
            <div class="gauge-center"><span class="gauge-val" style="color:#10b981">{p_pct}</span><span class="gauge-unit">%</span></div>
          </div>
        </div>
        <div class="gauge-item">
          <div class="gauge-label">Warnings</div>
          <div class="gauge-visual">
            <svg class="gauge-svg" viewBox="0 0 100 100">
              <circle class="gauge-bg" cx="50" cy="50" r="40" />
              <circle class="gauge-fill" cx="50" cy="50" r="40" stroke="#f59e0b" 
                stroke-dasharray="251.2" stroke-dashoffset="{251.2 * (1 - w/total)}" />
            </svg>
            <div class="gauge-center"><span class="gauge-val" style="color:#f59e0b">{w_pct}</span><span class="gauge-unit">%</span></div>
          </div>
        </div>
        <div class="gauge-item">
          <div class="gauge-label">Problems</div>
          <div class="gauge-visual">
            <svg class="gauge-svg" viewBox="0 0 100 100">
              <circle class="gauge-bg" cx="50" cy="50" r="40" />
              <circle class="gauge-fill" cx="50" cy="50" r="40" stroke="#ef4444" 
                stroke-dasharray="251.2" stroke-dashoffset="{251.2 * (1 - f/total)}" />
            </svg>
            <div class="gauge-center"><span class="gauge-val" style="color:#ef4444">{f_pct}</span><span class="gauge-unit">%</span></div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- CATEGORY SLIDES -->
  {category_slides}

  <!-- SLIDE: End -->
  <div class="slide">
    <div class="slide-sidebar end-sb">
      <div class="sb-logo">SEO AUDIT</div>
      <div class="sb-big-num">{score}</div>
      <div class="sb-big-label">FINAL SCORE</div>
      <div class="sb-stat"><span class="sl">Grade</span><span class="sv">{g}</span></div>
      <div class="sb-stat"><span class="sl">Priority Fixes</span><span class="sv">{f}</span></div>
      <div class="sb-slide-num">SLIDE {total_slides} / {total_slides}</div>
      <div class="sb-domain">Complete</div>
    </div>
    <div class="slide-content" style="justify-content: center; padding: 48px">
      <div style="display:inline-block; background:#f0f9ff; color:#0369a1; font-size:11px; font-weight:700; letter-spacing:0.12em; text-transform:uppercase; padding:6px 16px; border-radius:50px; margin-bottom:24px;">🎉 Audit Complete</div>
      <div class="cover-title" style="font-size: 48px; line-height: 1">Let's build your<br><span style="color: #6366f1">digital dominance.</span></div>

      <div class="premium-cta">
        <div class="hero-text">
          <h3>Turning data into growth.</h3>
          <p>Fixing these {f} priority items is just the start. We build high-performance digital ecosystems that rank and convert.</p>
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

</div><!-- /deck -->

<div class="floating-nav">
  <button class="nav-btn" id="prev" onclick="go(-1)">←</button>
  <div class="step-dots" id="dots">{slide_nav_dots}</div>
  <span class="nav-ctr" id="ctr">1 / {total_slides}</span>
  <button class="nav-btn" id="next" onclick="go(1)">→</button>
</div>

<div class="hint">Use Arrow Keys to Navigate</div>

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
  setTimeout(() => slides[o].classList.remove("exit"), 400);
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
        return f"<h1>Error generating report: {e}</h1>"
