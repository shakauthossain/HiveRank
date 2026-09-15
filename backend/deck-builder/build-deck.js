#!/usr/bin/env node
/**
 * Notionhive SEO Snapshot deck builder (pptxgenjs).
 * Usage: node build-deck.js <input.json> <output.pptx>
 */

const fs = require("fs");
const path = require("path");
const PptxGenJS = require("pptxgenjs");

const NH_BLUE = "1158E5";
const NH_BLUE_DARK = "0B3FA8";
const INK = "0B1220";
const MUTED = "64748B";
const LINE = "E2E8F0";
const WASH = "F1F6FE";
const WHITE = "FFFFFF";
const PASS = "059669";
const WARN = "D97706";
const FAIL = "DC2626";
const FONT = "Calibri";

const TAKEAWAY = "FBF3D5";
const TAKEAWAY_INK = "7A5B00";
const ASSETS = path.join(__dirname, "assets");
const LOGO_WHITE = path.join(ASSETS, "notionhive-logo-white.png");

function logoWhitePath() {
  return fs.existsSync(LOGO_WHITE) ? LOGO_WHITE : null;
}

function toneColor(tone) {
  if (tone === "pass") return PASS;
  if (tone === "warn" || tone === "warning") return WARN;
  if (tone === "fail") return FAIL;
  return NH_BLUE;
}

function cellColor(tone) {
  if (tone === "pass") return PASS;
  if (tone === "warn" || tone === "warning") return WARN;
  if (tone === "fail") return FAIL;
  return MUTED;
}

function fallbackHealth(data) {
  const organic = data.organic || {};
  const tech = data.technical || {};
  const auth = data.authority || {};
  const scores = data.scores || {};
  const crawled = tech.pages_crawled != null ? tech.pages_crawled : "—";
  const site = tech.onpage_score != null ? Math.round(tech.onpage_score) : scores.technical;
  const rank = auth.rank != null ? auth.rank : scores.authority;
  const cwvFail = ["cls", "lcp", "inp"].find((k) => tech[`${k}_status`] === "fail");
  return {
    title: "SEO Health Snapshot",
    subtitle: "Scores and counts from this pull. Re-run the snapshot for AI crawler and DataForSEO rank detail.",
    takeaway: "Review the later slides, edit the top five fixes, then approve.",
    cards: [
      { value: rank != null ? String(rank) : "—", label: "Authority Score", subtext: "DataForSEO rank or referring-domain scale", tone: "neutral" },
      { value: organic.etv_display ? `${organic.etv_display} /mo` : "—", label: "Organic Traffic", subtext: "Estimated · global markets", tone: "neutral" },
      { value: organic.count_display || dash(organic.count), label: "Ranking Keywords", subtext: "Estimated ranking SERPs", tone: "neutral" },
      { value: auth.prospect_display || dash(auth.prospect_referring_domains), label: "Referring Domains", subtext: "Live referring domains", tone: "neutral" },
      { value: site != null ? `${site}%` : "—", label: "Site Health Score", subtext: `${crawled} pages crawled`, tone: "neutral" },
      { value: "—", label: "AI Search Health", subtext: "Re-run to read robots.txt", tone: "neutral" },
      {
        value: cwvFail ? cwvFail.toUpperCase() : "—",
        label: cwvFail ? "Core Web Vitals: Failed" : "Core Web Vitals",
        subtext: cwvFail ? `${tech[cwvFail] || ""} on mobile lab data` : "PageSpeed mobile",
        tone: cwvFail ? "fail" : "neutral",
      },
      { value: dash(scores.visibility), label: "AI-Cited Pages", subtext: "Re-run for AI Visibility score from crawler access + llms.txt", tone: "neutral" },
    ],
  };
}

function fallbackPerformance(data) {
  const tech = data.technical || {};
  const mobile = tech.mobile || tech;
  const desktop = tech.desktop || {};
  const fail = ["cls", "lcp", "inp"].find((k) => tech[`${k}_status`] === "fail");
  return {
    title: "Performance & Core Web Vitals",
    cards: [
      { value: mobile.perf_score != null ? `${mobile.perf_score} / 100` : "—", label: "Mobile Performance", subtext: "Lighthouse, PSI", tone: "fail" },
      { value: desktop.perf_score != null ? `${desktop.perf_score} / 100` : "—", label: "Desktop Performance", subtext: "Lighthouse, PSI", tone: "neutral" },
      { value: mobile.tbt || "—", label: "Lab TBT", subtext: "PageSpeed lab", tone: "neutral" },
      { value: fail ? "FAILED" : "—", label: "Core Web Vitals", subtext: "lab assessment", tone: fail ? "fail" : "neutral" },
    ],
    rows: [
      { metric: "LCP — Largest Contentful Paint", mobile: { text: dash(tech.lcp), tone: tech.lcp_status }, desktop: { text: "n/a", tone: "neutral" }, lab: { text: dash(tech.lcp), tone: tech.lcp_status } },
      { metric: "INP / TBT — Responsiveness", mobile: { text: dash(tech.inp), tone: tech.inp_status }, desktop: { text: "n/a", tone: "neutral" }, lab: { text: dash(tech.tbt || tech.inp), tone: tech.inp_status } },
      { metric: "CLS — Cumulative Layout Shift", mobile: { text: dash(tech.cls), tone: tech.cls_status }, desktop: { text: "n/a", tone: "neutral" }, lab: { text: dash(tech.cls), tone: tech.cls_status } },
    ],
    takeaway: "Re-run the snapshot to fill Chrome field (CrUX) and desktop lab columns.",
    lab_header: "Lab (PageSpeed · mobile)",
  };
}

function fallbackOnpage(data) {
  const tech = data.technical || {};
  const onpage = data.onpage || {};
  const metrics = onpage.page_metrics || {};
  const checks = metrics.checks || {};
  const n = (obj, key, alt) => {
    const v = obj[key] != null ? obj[key] : alt;
    if (v === 0) return 0;
    if (v == null || v === "") return 0;
    const num = Number(v);
    return Number.isFinite(num) ? num : 0;
  };
  const missing = n(checks, "no_description", tech.missing_meta);
  const dups = n(metrics, "duplicate_title", n(checks, "duplicate_title_tag", tech.duplicate_titles));
  return {
    title: "On-Page & Content Health",
    cards: [
      { value: String(missing), label: "Pages Missing Meta Descriptions", subtext: "suppresses SERP CTR", tone: missing ? "fail" : "pass" },
      { value: String(dups), label: "Duplicate Title Tags", subtext: "dilutes topical relevance", tone: dups ? "fail" : "pass" },
      { value: "—", label: "Pages with Duplicate Content", subtext: "Re-run for OnPage checks", tone: "neutral" },
      { value: "—", label: "Pages with Low Text-HTML Ratio", subtext: "Re-run for OnPage checks", tone: "neutral" },
      { value: "—", label: "Pages with Multiple H1 Tags", subtext: "Re-run for OnPage checks", tone: "neutral" },
      { value: "—", label: "Lighthouse SEO Score", subtext: "Re-run for PageSpeed SEO category", tone: "neutral" },
    ],
    takeaway: "Re-run the snapshot to fill OnPage check counts and Lighthouse SEO. Approve still rebuilds this slide from whatever is stored.",
  };
}

function fallbackAuthority(data) {
  const organic = data.organic || {};
  const auth = data.authority || {};
  const rank = auth.rank != null ? auth.rank : null;
  const rd = auth.prospect_display || dash(auth.prospect_referring_domains);
  const backlinks = auth.backlinks != null ? `~${auth.backlinks}` : "—";
  return {
    title: "Authority & Backlink Profile",
    cards: [
      { value: rank != null ? String(rank) : "—", label: "Authority Score", subtext: "DataForSEO rank", tone: "neutral" },
      { value: rd, label: "Referring Domains", subtext: "current snapshot", tone: "neutral" },
      { value: String(backlinks), label: "Total Backlinks", subtext: "Estimated (DataForSEO)", tone: "neutral" },
      { value: organic.etv_display ? `${organic.etv_display} /mo` : "—", label: "Organic Traffic", subtext: "Estimated · global markets", tone: "pass" },
    ],
    peers: Array.isArray(auth.peers) ? auth.peers : [],
    reading: [
      { title: "Re-run for the full profile.", body: "Category-peer bars and spam ratio fill in on a new Snapshot pull." },
    ],
  };
}

function fallbackRankings(data) {
  const organic = data.organic || {};
  const primary = organic.primary || {};
  const count = primary.count != null ? primary.count : organic.count_primary;
  const top3 = (organic.pos_1 || 0) + (organic.pos_2_3 || 0);
  const top10 = top3 + (organic.pos_4_10 || 0);
  return {
    title: "Current Rankings — primary market",
    cards: [
      { value: dash(count || organic.count_display), label: "Keywords Tracked", subtext: "Re-run for this-market Labs counts", tone: "neutral" },
      { value: dash(top10 || null), label: "Top-10 Rankings", subtext: `${dash(top3)} in top 3 · all-market mix`, tone: "neutral" },
      { value: organic.etv_display ? `${organic.etv_display} /mo` : "—", label: "Organic Traffic", subtext: "Estimated · may be global markets on older pulls", tone: "neutral" },
    ],
    buckets: [
      { label: "Top 3", count: organic.pos_1 || 0 },
      { label: "4–10", count: organic.pos_4_10 || 0 },
      { label: "11–20", count: organic.pos_11_20 || 0 },
      { label: "21–50", count: 0 },
      { label: "51–100", count: 0 },
    ],
    bucket_caption: "Position distribution (re-run for this-market buckets)",
    takeaway: "Re-run the snapshot to fill this-market position buckets and top keywords by traffic. Older pulls stored global mix only.",
    top_keywords: Array.isArray(data.top_keywords) ? data.top_keywords : [],
  };
}

function fallbackGeo(data) {
  const ai = data.ai || {};
  const robots = ai.robots || {};
  const crawler = robots.score;
  return {
    title: "GEO Readiness Score",
    overall: null,
    crawler: crawler,
    llms: Boolean(ai.llms_txt),
    llms_score: ai.llms_txt ? 100 : 0,
    bars: [
      { label: "Citation Authority", score: (data.authority || {}).rank, tone: "neutral", note: "DataForSEO rank" },
      { label: "AI Crawler Access", score: crawler, tone: "neutral", note: "robots.txt" },
      { label: "Technical Optimization", score: (data.technical || {}).seo_score, tone: "neutral" },
      { label: "Competitive Context", score: null, tone: "neutral" },
      { label: "Answer-First Content", score: null, tone: "neutral" },
      { label: "AI Comprehension", score: ai.llms_txt ? 100 : 0, tone: "neutral" },
    ],
    takeaway: "Re-run the snapshot to compose the GEO score from robots.txt, llms.txt, DataForSEO, OnPage, and PageSpeed.",
    source: "This Snapshot pull — robots.txt, llms.txt, DataForSEO, PageSpeed.",
  };
}

function fallbackSiteAudit(data) {
  const tech = data.technical || {};
  const crawled = tech.pages_crawled;
  const cap = data.onpage_max_pages || 100;
  const site = tech.onpage_score != null ? Math.round(tech.onpage_score) : null;
  return {
    title: "Site Audit — Crawl & Links",
    cards: [
      { value: crawled != null ? `${crawled} / ${cap}` : `— / ${cap}`, label: "Pages Crawled", subtext: `crawl cap ${cap}`, tone: "neutral" },
      { value: site != null ? `${site}%` : "—", label: "Site Health", subtext: "OnPage score · this crawl", tone: "neutral" },
      { value: "—", label: "Issue hits", subtext: "Re-run for OnPage issue flags", tone: "neutral" },
    ],
    status_title: "Crawled-page status",
    status: [
      { label: "Healthy", count: 0 },
      { label: "Broken", count: 0 },
      { label: "Redirect", count: 0 },
      { label: "Have issues", count: 0 },
    ],
    status_max: 1,
    status_note: "Re-run the snapshot to fill OnPage crawl status.",
    issues_title: "Top issues (by count)",
    issues: [],
    takeaway: "Re-run the snapshot to fill Site Audit from the DataForSEO OnPage crawl (JS off, page cap).",
  };
}

function fallbackCrawlability(data) {
  const ai = data.ai || {};
  const robots = ai.robots || {};
  const blocked = robots.blocked || 0;
  const llms = Boolean(ai.llms_txt);
  const sitemap = ai.sitemap || {};
  return {
    title: "Crawlability — robots.txt, sitemap.xml & llms.txt",
    rows: [
      {
        item: "robots.txt",
        state: robots.missing ? "Not found at origin" : "Present at origin (syntax not Search Console–validated)",
        recommendation: robots.missing ? "Publish a valid robots.txt" : "Keep AI crawler rules intentional",
        tone: robots.missing ? "fail" : "pass",
      },
      {
        item: "llms.txt",
        state: llms ? "Present at origin" : "Not found",
        recommendation: llms ? "Keep llms.txt updated" : "Publish an llms.txt to guide AI crawlers to key content",
        tone: llms ? "pass" : "fail",
      },
      {
        item: "sitemap.xml",
        state: sitemap.present ? "Present at origin" : "Not found at /sitemap.xml",
        recommendation: sitemap.present ? "Regenerate when URL inventory changes" : "Publish a clean XML sitemap",
        tone: sitemap.present ? "pass" : "fail",
      },
      {
        item: "AI bot access",
        state: `${blocked} AI crawlers blocked in robots.txt`,
        recommendation: blocked ? "Unblock the AI crawlers you want citing you" : "No action needed if access stays open",
        tone: blocked ? "fail" : "pass",
      },
      {
        item: "Crawl config",
        state: "JS rendering was disabled for this audit crawl",
        recommendation: "This pull uses a page cap with JavaScript off",
        tone: "neutral",
      },
    ],
  };
}

function fallbackCitations(data) {
  const health = data.health || {};
  const aiCited = (health.cards || []).find((c) => c.key === "ai_cited" || /AI Visibility|AI-Cited/i.test(c.label || ""));
  const organic = data.organic || {};
  const ai = data.ai || {};
  const robots = ai.robots || {};
  const scoreMatch = String((aiCited && aiCited.value) || "").match(/(\d+)/);
  const score = scoreMatch ? Number(scoreMatch[1]) : null;
  const allowed = Math.max(0, (robots.total || 6) - (robots.blocked || 0));
  const blocked = robots.blocked || 0;
  const mix = [];
  if (allowed) mix.push({ label: "Crawlers allowed", value: allowed, color: "1158E5", pct: 0 });
  if (blocked) mix.push({ label: "Crawlers blocked", value: blocked, color: "DC2626", pct: 0 });
  const total = mix.reduce((sum, row) => sum + row.value, 0) || 1;
  mix.forEach((row) => {
    row.pct = Math.round((100 * row.value) / total);
  });
  return {
    title: "AI Visibility & Citations",
    cards: [
      { value: score != null ? `${score} / 100` : "—", label: "AI Visibility Score", subtext: "this Snapshot pull", tone: "neutral" },
      { value: dash(organic.count_display || organic.count), label: "Keywords Tracked", subtext: "Estimated · Labs", tone: "neutral" },
      { value: "—", label: "Top-10 Rankings", subtext: "Re-run for this-market Labs mix", tone: "neutral" },
      { value: ai.llms_txt ? "Yes" : "No", label: "llms.txt", subtext: "present at origin", tone: ai.llms_txt ? "pass" : "warn" },
    ],
    mix_title: mix.length ? "AI crawler access" : "Ranking mix",
    mix,
    sample_title: "Sample ranking URLs (Estimated, Labs):",
    sample_urls: [],
    reading_title: score != null ? `How to read the ${score}/100` : "How to read this score",
    takeaway: "Re-run the snapshot to fill AI Visibility from crawler access, llms.txt, estimated rankings, and OnPage. This is not Semrush and not a ChatGPT citation count.",
    score,
  };
}

function statusColor(status) {
  if (status === "pass") return PASS;
  if (status === "warning") return WARN;
  if (status === "fail") return FAIL;
  return MUTED;
}

function dash(value) {
  if (value === 0) return "0";
  if (value === undefined || value === null || value === "") return "—";
  return String(value);
}

function addFooter(slide, page, total, date) {
  slide.addShape("rect", {
    x: 0,
    y: 7.22,
    w: 13.333,
    h: 0.28,
    fill: { color: NH_BLUE },
  });
  slide.addText("NOTIONHIVE  ·  SEO SNAPSHOT ", {
    x: 0.45,
    y: 7.24,
    w: 10.2,
    h: 0.24,
    fontFace: FONT,
    fontSize: 10,
    color: WHITE,
    margin: 0,
  });
  slide.addText(`${date || ""}   ${page} / ${total}`, {
    x: 10.6,
    y: 7.24,
    w: 2.3,
    h: 0.24,
    fontFace: FONT,
    fontSize: 10,
    color: WHITE,
    align: "right",
    margin: 0,
  });
}

function kicker(slide, text) {
  slide.addShape("rect", {
    x: 0.5,
    y: 0.32,
    w: 0.18,
    h: 0.42,
    fill: { color: NH_BLUE },
  });
  slide.addText(text, {
    x: 0.82,
    y: 0.32,
    w: 11.6,
    h: 0.42,
    fontFace: FONT,
    fontSize: 12,
    bold: true,
    color: NH_BLUE,
    margin: 0,
    charSpacing: 1.5,
  });
}

function title(slide, text) {
  slide.addText(text, {
    x: 0.5,
    y: 0.78,
    w: 12.3,
    h: 0.5,
    fontFace: FONT,
    fontSize: 26,
    bold: true,
    color: INK,
    margin: 0,
  });
}

function estimatedNote(slide, y = 1.28) {
  slide.addText("Figures labeled Estimated are modeled DataForSEO numbers, not verified analytics.", {
    x: 0.5,
    y,
    w: 12.3,
    h: 0.28,
    fontFace: FONT,
    fontSize: 11,
    italic: true,
    color: MUTED,
    margin: 0,
  });
}

function fallbackProjections(data) {
  return {
    title: "6-Month Projections — Today vs. Target",
    subtitle:
      "Re-run the snapshot to draft 6-month targets from current Snapshot data (Notionhive-proposed, not a vendor forecast).",
    rows: [],
  };
}

function build(data, outputPath) {
  const pres = new PptxGenJS();
  pres.defineLayout({ name: "LAYOUT_WIDE", width: 13.333, height: 7.5 });
  pres.layout = "LAYOUT_WIDE";
  pres.author = "Notionhive";
  const thin = Boolean(data.thin_data);
  const quick = data.deck_mode === "quick";
  pres.title = quick
    ? `Quick Audit — ${data.prospect_domain || "Prospect"}`
    : `SEO Snapshot — ${data.prospect_domain || "Prospect"}`;
  pres.subject = quick
    ? "Balanced Quick Audit for sales"
    : "Initial SEO audit for sales";

  const slides = quick
    ? ["cover", "scorecard", "performance", "priorities"]
    : thin
    ? ["cover", "scorecard", "authority", "technical_extra", "performance", "onpage", "geo", "citations", "site_audit", "crawlability", "projections", "priorities"]
    : ["cover", "scorecard", "authority", "rankings", "performance", "onpage", "geo", "citations", "site_audit", "crawlability", "quick_wins", "projections", "priorities"];
  const total = slides.length;
  const date = data.date || "";
  const technical = data.technical || {};
  const fixes = Array.isArray(data.top_fixes) ? data.top_fixes : [];
  let page = 0;

  function nextSlide() {
    page += 1;
    const slide = pres.addSlide();
    slide.addShape("rect", {
      x: 0,
      y: 0,
      w: 0.12,
      h: 7.5,
      fill: { color: NH_BLUE },
    });
    return slide;
  }

  // 1. Cover
  {
    const slide = nextSlide();
    slide.addShape("rect", {
      x: 0,
      y: 0,
      w: 13.333,
      h: 7.5,
      fill: { color: NH_BLUE },
    });
    slide.addShape("rect", {
      x: 8.6,
      y: -1.2,
      w: 6,
      h: 6,
      fill: { color: NH_BLUE_DARK },
      rotate: 18,
    });
    const logo = logoWhitePath();
    if (logo) {
      slide.addImage({
        path: logo,
        x: 0.7,
        y: 1.28,
        w: 2.75,
        h: 0.4,
      });
    } else {
      slide.addText("NOTIONHIVE", {
        x: 0.7,
        y: 1.35,
        w: 8,
        h: 0.35,
        fontFace: FONT,
        fontSize: 14,
        bold: true,
        color: WHITE,
        charSpacing: 3,
        margin: 0,
      });
    }
    slide.addText(quick ? "Quick Audit" : "SEO Snapshot", {
      x: 0.7,
      y: 1.85,
      w: 11.5,
      h: 0.9,
      fontFace: FONT,
      fontSize: 44,
      bold: true,
      color: WHITE,
      margin: 0,
    });
    slide.addText(data.prospect_domain || "", {
      x: 0.7,
      y: 2.8,
      w: 11.5,
      h: 0.55,
      fontFace: FONT,
      fontSize: 24,
      color: "D6E4FF",
      margin: 0,
    });
    slide.addText(
      quick
        ? `${date}\nBalanced Quick Audit — visibility, backlinks, and Core Web Vitals. No full site crawl. A specialist reviews every number before this leaves Notionhive.`
        : `${date}\nStandalone SEO snapshot for this domain. A specialist reviews every number before this leaves Notionhive.`,
      {
        x: 0.7,
        y: 3.55,
        w: 10.5,
        h: 1.1,
        fontFace: FONT,
        fontSize: 14,
        color: WHITE,
        margin: 0,
      }
    );
    slide.addText(`${page} / ${total}`, {
      x: 0.7,
      y: 6.85,
      w: 3,
      h: 0.28,
      fontFace: FONT,
      fontSize: 12,
      color: WHITE,
      margin: 0,
    });
  }

  // 2. SEO Health Snapshot
  {
    const slide = nextSlide();
    const health = data.health && Array.isArray(data.health.cards) && data.health.cards.length
      ? data.health
      : fallbackHealth(data);
    const domain = data.prospect_domain || "";

    slide.addText(`${domain}  /  Overview`, {
      x: 0.5,
      y: 0.22,
      w: 12.3,
      h: 0.28,
      fontFace: FONT,
      fontSize: 11,
      color: MUTED,
      margin: 0,
    });
    slide.addText(health.title || "SEO Health Snapshot", {
      x: 0.5,
      y: 0.48,
      w: 12.3,
      h: 0.42,
      fontFace: FONT,
      fontSize: 24,
      bold: true,
      color: INK,
      margin: 0,
    });
    slide.addText(health.subtitle || "", {
      x: 0.5,
      y: 0.92,
      w: 12.3,
      h: 0.58,
      fontFace: FONT,
      fontSize: 13,
      italic: true,
      color: MUTED,
      margin: 0,
    });

    const cards = (health.cards || []).slice(0, 8);
    cards.forEach((card, i) => {
      const col = i % 4;
      const row = Math.floor(i / 4);
      const x = 0.42 + col * 3.2;
      const y = 1.58 + row * 1.88;
      slide.addShape("roundRect", {
        x,
        y,
        w: 3.05,
        h: 1.76,
        fill: { color: WASH },
        rectRadius: 0.1,
        line: { color: LINE, width: 0 },
      });
      slide.addText(dash(card.value), {
        x: x + 0.14,
        y: y + 0.1,
        w: 2.77,
        h: 0.62,
        fontFace: FONT,
        fontSize: 26,
        bold: true,
        color: toneColor(card.tone),
        margin: 0,
      });
      slide.addText(card.label || "", {
        x: x + 0.14,
        y: y + 0.72,
        w: 2.77,
        h: 0.36,
        fontFace: FONT,
        fontSize: 12,
        bold: true,
        color: INK,
        margin: 0,
      });
      slide.addText(card.subtext || "", {
        x: x + 0.14,
        y: y + 1.08,
        w: 2.77,
        h: 0.56,
        fontFace: FONT,
        fontSize: 11,
        color: MUTED,
        margin: 0,
      });
    });

    slide.addShape("roundRect", {
      x: 0.42,
      y: 5.4,
      w: 12.48,
      h: 1.58,
      fill: { color: TAKEAWAY },
      rectRadius: 0.08,
    });
    slide.addText("KEY TAKEAWAY", {
      x: 0.66,
      y: 5.52,
      w: 12.0,
      h: 0.28,
      fontFace: FONT,
      fontSize: 11,
      bold: true,
      color: TAKEAWAY_INK,
      margin: 0,
    });
    slide.addText(health.takeaway || "", {
      x: 0.66,
      y: 5.82,
      w: 12.0,
      h: 1.0,
      fontFace: FONT,
      fontSize: 13,
      color: INK,
      margin: 0,
    });
    addFooter(slide, page, total, date);
  }

  // 3. Authority & Backlink Profile (traffic + rank + links)
  if (!quick) {
    const slide = nextSlide();
    const block = data.authority_slide && Array.isArray(data.authority_slide.cards)
      ? data.authority_slide
      : fallbackAuthority(data);
    const domain = data.prospect_domain || "";

    slide.addText(`${domain}  /  Authority`, {
      x: 0.42,
      y: 0.2,
      w: 12.4,
      h: 0.26,
      fontFace: FONT,
      fontSize: 11,
      color: MUTED,
      margin: 0,
    });
    slide.addText(block.title || "Authority & Backlink Profile", {
      x: 0.42,
      y: 0.46,
      w: 12.4,
      h: 0.42,
      fontFace: FONT,
      fontSize: 24,
      bold: true,
      color: INK,
      margin: 0,
    });

    const metrics = (block.cards || []).slice(0, 4);
    metrics.forEach((card, i) => {
      const col = i % 2;
      const row = Math.floor(i / 2);
      const x = 0.42 + col * 4.35;
      const y = 1.05 + row * 1.48;
      slide.addShape("roundRect", {
        x,
        y,
        w: 4.2,
        h: 1.36,
        fill: { color: WASH },
        rectRadius: 0.1,
      });
      slide.addText(dash(card.value), {
        x: x + 0.16,
        y: y + 0.08,
        w: 3.88,
        h: 0.52,
        fontFace: FONT,
        fontSize: 24,
        bold: true,
        color: toneColor(card.tone),
        margin: 0,
      });
      slide.addText(card.label || "", {
        x: x + 0.16,
        y: y + 0.6,
        w: 3.88,
        h: 0.28,
        fontFace: FONT,
        fontSize: 12,
        bold: true,
        color: INK,
        margin: 0,
      });
      slide.addText(card.subtext || "", {
        x: x + 0.16,
        y: y + 0.9,
        w: 3.88,
        h: 0.32,
        fontFace: FONT,
        fontSize: 11,
        color: MUTED,
        margin: 0,
      });
    });

    slide.addText(block.chart_title || "Authority Score vs. similar peers (Labs)", {
      x: 0.42,
      y: 4.05,
      w: 8.5,
      h: 0.28,
      fontFace: FONT,
      fontSize: 12,
      bold: true,
      color: INK,
      margin: 0,
    });

    const peers = (block.peers || []).slice(0, 6);
    const numeric = peers.map((p) => p.rank).filter((n) => typeof n === "number");
    const maxRank = Math.max(60, ...(numeric.length ? numeric : [0]));
    const labelW = 2.2;
    const barX = 0.42 + labelW;
    const barMax = 5.7;
    if (!peers.length) {
      slide.addText("No overlapping ranking domains returned for a peer chart in this market.", {
        x: 0.42,
        y: 4.4,
        w: 8.5,
        h: 0.5,
        fontFace: FONT,
        fontSize: 12,
        color: MUTED,
        margin: 0,
      });
    } else {
      peers.forEach((peer, i) => {
        const y = 4.38 + i * 0.4;
        const rank = typeof peer.rank === "number" ? peer.rank : 0;
        const w = Math.max(0.14, (rank / maxRank) * barMax);
        slide.addText(peer.label || peer.domain || "—", {
          x: 0.42,
          y,
          w: labelW - 0.08,
          h: 0.32,
          fontFace: FONT,
          fontSize: 11,
          bold: !!peer.is_you,
          color: INK,
          margin: 0,
        });
        slide.addShape("roundRect", {
          x: barX,
          y: y + 0.04,
          w,
          h: 0.24,
          fill: { color: peer.is_you ? NH_BLUE_DARK : NH_BLUE },
          rectRadius: 0.04,
        });
        slide.addText(dash(peer.rank), {
          x: barX + w + 0.08,
          y,
          w: 0.7,
          h: 0.32,
          fontFace: FONT,
          fontSize: 11,
          bold: true,
          color: INK,
          margin: 0,
        });
      });
    }

    slide.addShape("roundRect", {
      x: 9.15,
      y: 1.05,
      w: 3.75,
      h: 5.85,
      fill: { color: "F4F6FA" },
      rectRadius: 0.1,
    });
    slide.addText("Reading the profile", {
      x: 9.35,
      y: 1.18,
      w: 3.35,
      h: 0.36,
      fontFace: FONT,
      fontSize: 14,
      bold: true,
      color: INK,
      margin: 0,
    });
    const notes = (block.reading || []).slice(0, 3);
    notes.forEach((note, i) => {
      const y = 1.62 + i * 1.7;
      slide.addText(note.title || "", {
        x: 9.35,
        y,
        w: 3.35,
        h: 0.4,
        fontFace: FONT,
        fontSize: 12,
        bold: true,
        color: INK,
        margin: 0,
      });
      slide.addText(note.body || "", {
        x: 9.35,
        y: y + 0.4,
        w: 3.35,
        h: 1.2,
        fontFace: FONT,
        fontSize: 11,
        color: MUTED,
        margin: 0,
      });
    });
    addFooter(slide, page, total, date);
  }

  // 4. Current Rankings (primary market)
  if (!thin && !quick) {
    const slide = nextSlide();
    const block = data.rankings_slide && Array.isArray(data.rankings_slide.cards)
      ? data.rankings_slide
      : fallbackRankings(data);
    const domain = data.prospect_domain || "";

    slide.addText(`${domain}  /  Keyword Visibility`, {
      x: 0.42,
      y: 0.2,
      w: 12.4,
      h: 0.26,
      fontFace: FONT,
      fontSize: 11,
      color: MUTED,
      margin: 0,
    });
    slide.addText(block.title || "Current Rankings", {
      x: 0.42,
      y: 0.46,
      w: 12.4,
      h: 0.42,
      fontFace: FONT,
      fontSize: 24,
      bold: true,
      color: INK,
      margin: 0,
    });

    const metrics = (block.cards || []).slice(0, 3);
    metrics.forEach((card, i) => {
      const x = 0.42 + i * 4.22;
      slide.addShape("roundRect", {
        x,
        y: 1.0,
        w: 4.05,
        h: 1.22,
        fill: { color: WASH },
        rectRadius: 0.1,
      });
      slide.addText(dash(card.value), {
        x: x + 0.16,
        y: 1.06,
        w: 3.73,
        h: 0.46,
        fontFace: FONT,
        fontSize: 22,
        bold: true,
        color: toneColor(card.tone),
        margin: 0,
      });
      slide.addText(card.label || "", {
        x: x + 0.16,
        y: 1.5,
        w: 3.73,
        h: 0.28,
        fontFace: FONT,
        fontSize: 13,
        bold: true,
        color: INK,
        margin: 0,
      });
      slide.addText(card.subtext || "", {
        x: x + 0.16,
        y: 1.78,
        w: 3.73,
        h: 0.34,
        fontFace: FONT,
        fontSize: 11,
        color: MUTED,
        margin: 0,
      });
    });

    slide.addText(block.bucket_caption || "Position distribution", {
      x: 0.42,
      y: 2.38,
      w: 6.2,
      h: 0.32,
      fontFace: FONT,
      fontSize: 14,
      bold: true,
      color: INK,
      margin: 0,
    });

    const buckets = Array.isArray(block.buckets) ? block.buckets.slice(0, 5) : [];
    const maxCount = Math.max(1, ...buckets.map((b) => Number(b.count) || 0));
    const chartBottom = 5.55;
    const chartMaxH = 2.35;
    buckets.forEach((b, i) => {
      const count = Number(b.count) || 0;
      const h = Math.max(0.08, chartMaxH * (count / maxCount));
      const x = 0.55 + i * 1.22;
      const y = chartBottom - h;
      slide.addShape("rect", {
        x,
        y,
        w: 0.85,
        h,
        fill: { color: NH_BLUE },
      });
      slide.addText(String(count), {
        x: x - 0.08,
        y: y - 0.28,
        w: 1.0,
        h: 0.26,
        fontFace: FONT,
        fontSize: 12,
        bold: true,
        color: INK,
        align: "center",
        margin: 0,
      });
      slide.addText(b.label || "", {
        x: x - 0.12,
        y: chartBottom + 0.08,
        w: 1.1,
        h: 0.28,
        fontFace: FONT,
        fontSize: 11,
        color: MUTED,
        align: "center",
        margin: 0,
      });
    });

    slide.addText(block.takeaway || "", {
      x: 0.42,
      y: 6.0,
      w: 6.2,
      h: 0.95,
      fontFace: FONT,
      fontSize: 12,
      italic: true,
      color: MUTED,
      margin: 0,
    });

    slide.addText("Top keywords by traffic", {
      x: 6.9,
      y: 2.38,
      w: 5.95,
      h: 0.32,
      fontFace: FONT,
      fontSize: 14,
      bold: true,
      color: INK,
      margin: 0,
    });

    const kws = Array.isArray(block.top_keywords) ? block.top_keywords.slice(0, 8) : [];
    if (!kws.length) {
      slide.addText("No ranked keywords returned for this market. Re-run if Labs has coverage.", {
        x: 6.9,
        y: 2.85,
        w: 5.95,
        h: 0.8,
        fontFace: FONT,
        fontSize: 13,
        color: MUTED,
        margin: 0,
      });
    } else {
      const rows = [
        [
          { text: "Keyword", options: { bold: true, color: WHITE, fill: { color: NH_BLUE } } },
          { text: "Pos", options: { bold: true, color: WHITE, fill: { color: NH_BLUE }, align: "center" } },
          { text: "Traffic", options: { bold: true, color: WHITE, fill: { color: NH_BLUE }, align: "right" } },
        ],
      ];
      kws.forEach((row) => {
        rows.push([
          row.keyword || "—",
          { text: dash(row.position), options: { align: "center" } },
          { text: row.etv_display || dash(row.etv), options: { align: "right" } },
        ]);
      });
      slide.addTable(rows, {
        x: 6.9,
        y: 2.78,
        w: 5.95,
        colW: [3.55, 0.9, 1.5],
        border: [{ pt: 0 }, { pt: 0 }, { pt: 0.5, color: LINE }, { pt: 0 }],
        fontFace: FONT,
        fontSize: 12,
        color: INK,
        valign: "middle",
        rowH: 0.38,
      });
    }
    addFooter(slide, page, total, date);
  }

  // 4. Expanded crawl (thin-data decks only — becomes slide 4)
  if (thin && !quick) {
    const slide = nextSlide();
    kicker(slide, "TECHNICAL HEALTH");
    title(slide, "Expanded crawl findings");
    slide.addText(
      "Keyword tools often return little data for new or small sites. The crawl (100-page cap, JavaScript off) is the primary evidence in this deck.",
      {
        x: 0.5,
        y: 1.32,
        w: 12.3,
        h: 0.45,
        fontFace: FONT,
        fontSize: 13,
        color: MUTED,
        margin: 0,
      }
    );
    const pages = Array.isArray(technical.worst_pages) ? technical.worst_pages.slice(0, 8) : [];
    if (pages.length) {
      const rows = [
        [
          { text: "URL", options: { bold: true, color: WHITE, fill: { color: NH_BLUE } } },
          { text: "Status", options: { bold: true, color: WHITE, fill: { color: NH_BLUE }, align: "center" } },
          { text: "On-page score", options: { bold: true, color: WHITE, fill: { color: NH_BLUE }, align: "center" } },
          { text: "Title", options: { bold: true, color: WHITE, fill: { color: NH_BLUE } } },
        ],
      ];
      pages.forEach((p) => {
        rows.push([
          p.url || "—",
          { text: dash(p.status_code), options: { align: "center" } },
          { text: dash(p.onpage_score), options: { align: "center" } },
          p.title || "—",
        ]);
      });
      slide.addTable(rows, {
        x: 0.5,
        y: 1.9,
        w: 12.3,
        colW: [5.1, 1.4, 1.8, 4.0],
        border: [{ pt: 0 }, { pt: 0 }, { pt: 0.5, color: LINE }, { pt: 0 }],
        fontFace: FONT,
        fontSize: 11,
        color: INK,
        valign: "middle",
        rowH: 0.42,
      });
    } else {
      slide.addText("The crawl did not return page-level rows. Re-run if the site blocked the bot.", {
        x: 0.5,
        y: 2.1,
        w: 12.3,
        h: 0.5,
        fontFace: FONT,
        fontSize: 16,
        color: MUTED,
        margin: 0,
      });
    }
    addFooter(slide, page, total, date);
  }

  // 5. Performance & Core Web Vitals
  {
    const slide = nextSlide();
    const block = data.performance_slide && Array.isArray(data.performance_slide.cards)
      ? data.performance_slide
      : fallbackPerformance(data);
    const domain = data.prospect_domain || "";

    slide.addText(`${domain}  /  Performance`, {
      x: 0.42,
      y: 0.2,
      w: 12.4,
      h: 0.26,
      fontFace: FONT,
      fontSize: 11,
      color: MUTED,
      margin: 0,
    });
    slide.addText(block.title || "Performance & Core Web Vitals", {
      x: 0.42,
      y: 0.46,
      w: 12.4,
      h: 0.42,
      fontFace: FONT,
      fontSize: 24,
      bold: true,
      color: INK,
      margin: 0,
    });

    const metrics = (block.cards || []).slice(0, 4);
    metrics.forEach((card, i) => {
      const x = 0.42 + i * 3.2;
      slide.addShape("roundRect", {
        x,
        y: 1.0,
        w: 3.05,
        h: 1.22,
        fill: { color: WASH },
        rectRadius: 0.1,
      });
      slide.addText(dash(card.value), {
        x: x + 0.14,
        y: 1.06,
        w: 2.77,
        h: 0.46,
        fontFace: FONT,
        fontSize: 22,
        bold: true,
        color: toneColor(card.tone),
        margin: 0,
      });
      slide.addText(card.label || "", {
        x: x + 0.14,
        y: 1.5,
        w: 2.77,
        h: 0.28,
        fontFace: FONT,
        fontSize: 12,
        bold: true,
        color: INK,
        margin: 0,
      });
      slide.addText(card.subtext || "", {
        x: x + 0.14,
        y: 1.78,
        w: 2.77,
        h: 0.34,
        fontFace: FONT,
        fontSize: 11,
        color: MUTED,
        margin: 0,
      });
    });

    const labHeader = block.lab_header || "Lab (PageSpeed · mobile)";
    const tableRows = [
      [
        { text: "Metric", options: { bold: true, color: WHITE, fill: { color: NH_BLUE } } },
        { text: "Mobile (Field / CrUX)", options: { bold: true, color: WHITE, fill: { color: NH_BLUE } } },
        { text: "Desktop (Field / CrUX)", options: { bold: true, color: WHITE, fill: { color: NH_BLUE } } },
        { text: labHeader, options: { bold: true, color: WHITE, fill: { color: NH_BLUE } } },
      ],
    ];
    (block.rows || []).forEach((row) => {
      const mobile = row.mobile || {};
      const desktop = row.desktop || {};
      const lab = row.lab || {};
      tableRows.push([
        { text: row.metric || "—", options: { color: INK, bold: true } },
        { text: dash(mobile.text), options: { color: cellColor(mobile.tone), bold: true } },
        { text: dash(desktop.text), options: { color: cellColor(desktop.tone), bold: true } },
        { text: dash(lab.text), options: { color: cellColor(lab.tone), bold: true } },
      ]);
    });
    slide.addTable(tableRows, {
      x: 0.42,
      y: 2.38,
      w: 12.48,
      colW: [3.4, 3.02, 3.02, 3.04],
      border: [{ pt: 0 }, { pt: 0 }, { pt: 0.5, color: LINE }, { pt: 0 }],
      fontFace: FONT,
      fontSize: 12,
      color: INK,
      valign: "middle",
      rowH: 0.46,
    });

    slide.addShape("roundRect", {
      x: 0.42,
      y: 5.45,
      w: 12.48,
      h: 1.15,
      fill: { color: TAKEAWAY },
      rectRadius: 0.08,
    });
    slide.addText("KEY TAKEAWAY", {
      x: 0.66,
      y: 5.54,
      w: 12.0,
      h: 0.24,
      fontFace: FONT,
      fontSize: 11,
      bold: true,
      color: TAKEAWAY_INK,
      margin: 0,
    });
    slide.addText(block.takeaway || "", {
      x: 0.66,
      y: 5.8,
      w: 12.0,
      h: 0.7,
      fontFace: FONT,
      fontSize: 13,
      color: INK,
      margin: 0,
    });
    addFooter(slide, page, total, date);
  }

  // 6–10. Full snapshot slides (skipped for Quick Audit)
  if (!quick) {
  // 6. On-Page & Content Health
  {
    const slide = nextSlide();
    const block = data.onpage_slide && Array.isArray(data.onpage_slide.cards)
      ? data.onpage_slide
      : fallbackOnpage(data);
    const domain = data.prospect_domain || "";

    slide.addText(`${domain}  /  On-Page SEO`, {
      x: 0.42,
      y: 0.2,
      w: 12.4,
      h: 0.26,
      fontFace: FONT,
      fontSize: 11,
      color: MUTED,
      margin: 0,
    });
    slide.addText(block.title || "On-Page & Content Health", {
      x: 0.42,
      y: 0.46,
      w: 12.4,
      h: 0.42,
      fontFace: FONT,
      fontSize: 24,
      bold: true,
      color: INK,
      margin: 0,
    });

    const cards = (block.cards || []).slice(0, 6);
    cards.forEach((card, i) => {
      const col = i % 3;
      const row = Math.floor(i / 3);
      const x = 0.42 + col * 4.22;
      const y = 1.08 + row * 1.92;
      slide.addShape("roundRect", {
        x,
        y,
        w: 4.05,
        h: 1.78,
        fill: { color: WASH },
        rectRadius: 0.1,
      });
      slide.addText(dash(card.value), {
        x: x + 0.18,
        y: y + 0.12,
        w: 3.7,
        h: 0.62,
        fontFace: FONT,
        fontSize: 28,
        bold: true,
        color: toneColor(card.tone),
        margin: 0,
      });
      slide.addText(card.label || "", {
        x: x + 0.18,
        y: y + 0.78,
        w: 3.7,
        h: 0.48,
        fontFace: FONT,
        fontSize: 13,
        bold: true,
        color: INK,
        margin: 0,
      });
      slide.addText(card.subtext || "", {
        x: x + 0.18,
        y: y + 1.28,
        w: 3.7,
        h: 0.36,
        fontFace: FONT,
        fontSize: 12,
        color: MUTED,
        margin: 0,
      });
    });

    slide.addShape("roundRect", {
      x: 0.42,
      y: 5.5,
      w: 12.48,
      h: 1.15,
      fill: { color: TAKEAWAY },
      rectRadius: 0.08,
    });
    slide.addText("KEY TAKEAWAY", {
      x: 0.66,
      y: 5.59,
      w: 12.0,
      h: 0.24,
      fontFace: FONT,
      fontSize: 11,
      bold: true,
      color: TAKEAWAY_INK,
      margin: 0,
    });
    slide.addText(block.takeaway || "", {
      x: 0.66,
      y: 5.85,
      w: 12.0,
      h: 0.7,
      fontFace: FONT,
      fontSize: 13,
      color: INK,
      margin: 0,
    });
    addFooter(slide, page, total, date);
  }

  // 7. GEO Readiness
  {
    const slide = nextSlide();
    const block = data.geo_slide && Array.isArray(data.geo_slide.bars)
      ? data.geo_slide
      : fallbackGeo(data);
    const domain = data.prospect_domain || "";
    const TRACK = "E8EEF6";

    slide.addText(`${domain}  /  AI Search  /  GEO`, {
      x: 0.42,
      y: 0.2,
      w: 12.4,
      h: 0.26,
      fontFace: FONT,
      fontSize: 11,
      color: MUTED,
      margin: 0,
    });
    slide.addText(block.title || "GEO Readiness Score", {
      x: 0.42,
      y: 0.46,
      w: 12.4,
      h: 0.42,
      fontFace: FONT,
      fontSize: 24,
      bold: true,
      color: INK,
      margin: 0,
    });

    slide.addShape("roundRect", {
      x: 0.42,
      y: 1.02,
      w: 3.25,
      h: 3.95,
      fill: { color: NH_BLUE },
      rectRadius: 0.1,
    });
    slide.addText(block.overall != null ? String(block.overall) : "—", {
      x: 0.56,
      y: 1.18,
      w: 2.97,
      h: 0.95,
      fontFace: FONT,
      fontSize: 52,
      bold: true,
      color: WHITE,
      align: "center",
      margin: 0,
    });
    slide.addText("/ 100 GEO SCORE", {
      x: 0.56,
      y: 2.1,
      w: 2.97,
      h: 0.32,
      fontFace: FONT,
      fontSize: 11,
      bold: true,
      color: WHITE,
      align: "center",
      charSpacing: 1.2,
      margin: 0,
    });
    slide.addShape("rect", {
      x: 0.82,
      y: 2.52,
      w: 2.45,
      h: 0.015,
      fill: { color: "93B4F5" },
    });
    slide.addText(block.crawler != null ? String(block.crawler) : "—", {
      x: 0.56,
      y: 2.68,
      w: 2.97,
      h: 0.42,
      fontFace: FONT,
      fontSize: 22,
      bold: true,
      color: block.crawler == null ? WHITE : toneColor(block.crawler >= 70 ? "pass" : block.crawler >= 45 ? "warn" : "fail"),
      align: "center",
      margin: 0,
    });
    slide.addText("AI crawler access", {
      x: 0.56,
      y: 3.08,
      w: 2.97,
      h: 0.26,
      fontFace: FONT,
      fontSize: 12,
      color: WHITE,
      align: "center",
      margin: 0,
    });
    slide.addText(block.llms ? "Yes" : "No", {
      x: 0.56,
      y: 3.42,
      w: 2.97,
      h: 0.42,
      fontFace: FONT,
      fontSize: 22,
      bold: true,
      color: block.llms ? PASS : FAIL,
      align: "center",
      margin: 0,
    });
    slide.addText("llms.txt present", {
      x: 0.56,
      y: 3.82,
      w: 2.97,
      h: 0.26,
      fontFace: FONT,
      fontSize: 12,
      color: WHITE,
      align: "center",
      margin: 0,
    });
    slide.addText(block.source || "This Snapshot pull — robots.txt, llms.txt, DataForSEO, PageSpeed.", {
      x: 0.62,
      y: 4.28,
      w: 2.85,
      h: 0.55,
      fontFace: FONT,
      fontSize: 10,
      italic: true,
      color: "C5D4F5",
      align: "center",
      margin: 0,
    });

    const bars = (block.bars || []).slice(0, 6);
    bars.forEach((bar, i) => {
      const y = 1.02 + i * 0.48;
      const score = bar.score;
      const pct = typeof score === "number" ? Math.max(0, Math.min(100, score)) / 100 : 0;
      slide.addText(bar.label || "", {
        x: 3.85,
        y,
        w: 2.35,
        h: 0.4,
        fontFace: FONT,
        fontSize: 13,
        color: INK,
        valign: "middle",
        margin: 0,
      });
      slide.addShape("roundRect", {
        x: 6.25,
        y: y + 0.08,
        w: 4.55,
        h: 0.24,
        fill: { color: TRACK },
        rectRadius: 0.04,
      });
      if (pct > 0) {
        slide.addShape("roundRect", {
          x: 6.25,
          y: y + 0.08,
          w: Math.max(0.12, 4.55 * pct),
          h: 0.24,
          fill: { color: toneColor(bar.tone) },
          rectRadius: 0.04,
        });
      }
      slide.addText(score == null ? "—" : String(score), {
        x: 10.9,
        y,
        w: 0.85,
        h: 0.4,
        fontFace: FONT,
        fontSize: 14,
        bold: true,
        color: toneColor(bar.tone),
        valign: "middle",
        align: "right",
        margin: 0,
      });
    });

    slide.addShape("roundRect", {
      x: 0.42,
      y: 5.55,
      w: 12.48,
      h: 1.1,
      fill: { color: TAKEAWAY },
      rectRadius: 0.08,
    });
    slide.addText("KEY TAKEAWAY", {
      x: 0.66,
      y: 5.64,
      w: 12.0,
      h: 0.24,
      fontFace: FONT,
      fontSize: 11,
      bold: true,
      color: TAKEAWAY_INK,
      margin: 0,
    });
    slide.addText(block.takeaway || "", {
      x: 0.66,
      y: 5.9,
      w: 12.0,
      h: 0.65,
      fontFace: FONT,
      fontSize: 13,
      color: INK,
      margin: 0,
    });
    addFooter(slide, page, total, date);
  }

  // 8. AI Visibility & Citations
  {
    const slide = nextSlide();
    const block = data.citations_slide && Array.isArray(data.citations_slide.cards)
      ? data.citations_slide
      : fallbackCitations(data);
    const domain = data.prospect_domain || "";
    const PALETTE = ["1158E5", "D97706", "059669", "EAB308", "64748B"];

    slide.addText(`${domain}  /  AI Search  /  GEO`, {
      x: 0.42,
      y: 0.2,
      w: 12.4,
      h: 0.26,
      fontFace: FONT,
      fontSize: 11,
      color: MUTED,
      margin: 0,
    });
    slide.addText(block.title || "AI Visibility & Citations", {
      x: 0.42,
      y: 0.46,
      w: 12.4,
      h: 0.42,
      fontFace: FONT,
      fontSize: 24,
      bold: true,
      color: INK,
      margin: 0,
    });
    slide.addShape("rect", {
      x: 0.42,
      y: 0.92,
      w: 12.48,
      h: 0.012,
      fill: { color: LINE },
    });

    const metrics = (block.cards || []).slice(0, 4);
    metrics.forEach((card, i) => {
      const col = i % 2;
      const row = Math.floor(i / 2);
      const x = 0.42 + col * 4.32;
      const y = 1.06 + row * 1.32;
      slide.addShape("roundRect", {
        x,
        y,
        w: 4.18,
        h: 1.22,
        fill: { color: WASH },
        rectRadius: 0.1,
      });
      slide.addText(dash(card.value), {
        x: x + 0.16,
        y: y + 0.06,
        w: 3.86,
        h: 0.46,
        fontFace: FONT,
        fontSize: 22,
        bold: true,
        color: toneColor(card.tone),
        margin: 0,
      });
      slide.addText(card.label || "", {
        x: x + 0.16,
        y: y + 0.52,
        w: 3.86,
        h: 0.28,
        fontFace: FONT,
        fontSize: 12,
        bold: true,
        color: INK,
        margin: 0,
      });
      slide.addText(card.subtext || "", {
        x: x + 0.16,
        y: y + 0.8,
        w: 3.86,
        h: 0.32,
        fontFace: FONT,
        fontSize: 11,
        color: MUTED,
        margin: 0,
      });
    });

    slide.addText(block.mix_title || "Ranking mix", {
      x: 0.42,
      y: 3.76,
      w: 4.3,
      h: 0.28,
      fontFace: FONT,
      fontSize: 13,
      bold: true,
      color: INK,
      margin: 0,
    });

    const mix = (block.mix || []).filter((row) => Number(row.value) > 0);
    const colors = mix.map((row, i) => row.color || PALETTE[i % PALETTE.length]);
    if (mix.length) {
      slide.addChart("doughnut", [
        {
          name: "Mix",
          labels: mix.map((row) => row.label),
          values: mix.map((row) => Number(row.value) || 0),
        },
      ], {
        x: 0.28,
        y: 3.98,
        w: 2.55,
        h: 2.85,
        showLegend: false,
        showTitle: false,
        showValue: false,
        showPercent: false,
        holeSize: 58,
        chartColors: colors,
      });
      mix.forEach((row, i) => {
        const y = 4.18 + i * 0.42;
        slide.addShape("ellipse", {
          x: 2.85,
          y: y + 0.06,
          w: 0.16,
          h: 0.16,
          fill: { color: colors[i] },
        });
        slide.addText(`${row.label}  ${row.pct != null ? `${row.pct}%` : ""}`, {
          x: 3.1,
          y,
          w: 1.85,
          h: 0.36,
          fontFace: FONT,
          fontSize: 12,
          color: INK,
          valign: "middle",
          margin: 0,
        });
      });
    } else {
      slide.addText("No ranking mix or crawler split in this pull.", {
        x: 0.42,
        y: 4.2,
        w: 4.3,
        h: 0.7,
        fontFace: FONT,
        fontSize: 12,
        color: MUTED,
        margin: 0,
      });
    }

    slide.addText(block.sample_title || "Sample ranking URLs (Estimated, Labs):", {
      x: 5.15,
      y: 3.76,
      w: 3.8,
      h: 0.28,
      fontFace: FONT,
      fontSize: 13,
      bold: true,
      color: INK,
      margin: 0,
    });
    const urls = (block.sample_urls || []).slice(0, 4);
    if (urls.length) {
      urls.forEach((url, i) => {
        slide.addText(url, {
          x: 5.15,
          y: 4.14 + i * 0.42,
          w: 3.8,
          h: 0.38,
          fontFace: FONT,
          fontSize: 12,
          color: INK,
          valign: "middle",
          margin: 0,
        });
      });
    } else {
      slide.addText("No ranking URLs stored on this pull. Re-run for Labs keyword URLs.", {
        x: 5.15,
        y: 4.14,
        w: 3.8,
        h: 1.1,
        fontFace: FONT,
        fontSize: 12,
        color: MUTED,
        margin: 0,
      });
    }

    slide.addShape("roundRect", {
      x: 9.15,
      y: 1.06,
      w: 3.75,
      h: 5.84,
      fill: { color: "F4F6FA" },
      rectRadius: 0.1,
    });
    slide.addText(block.reading_title || "How to read this score", {
      x: 9.35,
      y: 1.22,
      w: 3.35,
      h: 0.7,
      fontFace: FONT,
      fontSize: 16,
      bold: true,
      color: INK,
      margin: 0,
    });
    slide.addText(block.takeaway || "", {
      x: 9.35,
      y: 2.02,
      w: 3.35,
      h: 4.6,
      fontFace: FONT,
      fontSize: 13,
      color: INK,
      margin: 0,
    });
    addFooter(slide, page, total, date);
  }

  // 9. Site Audit — Crawl & Links
  {
    const slide = nextSlide();
    const block = data.site_audit_slide && Array.isArray(data.site_audit_slide.cards)
      ? data.site_audit_slide
      : fallbackSiteAudit(data);
    const domain = data.prospect_domain || "";

    slide.addText(`${domain}  /  Technical SEO`, {
      x: 0.42,
      y: 0.2,
      w: 12.4,
      h: 0.26,
      fontFace: FONT,
      fontSize: 11,
      color: MUTED,
      margin: 0,
    });
    slide.addText(block.title || "Site Audit — Crawl & Links", {
      x: 0.42,
      y: 0.46,
      w: 12.4,
      h: 0.42,
      fontFace: FONT,
      fontSize: 24,
      bold: true,
      color: INK,
      margin: 0,
    });

    const cards = (block.cards || []).slice(0, 3);
    cards.forEach((card, i) => {
      const x = 0.42 + i * 4.2;
      slide.addShape("roundRect", {
        x,
        y: 1.0,
        w: 4.05,
        h: 1.2,
        fill: { color: WASH },
        rectRadius: 0.1,
      });
      slide.addText(dash(card.value), {
        x: x + 0.16,
        y: 1.06,
        w: 3.73,
        h: 0.44,
        fontFace: FONT,
        fontSize: 22,
        bold: true,
        color: toneColor(card.tone),
        margin: 0,
      });
      slide.addText(card.label || "", {
        x: x + 0.16,
        y: 1.5,
        w: 3.73,
        h: 0.28,
        fontFace: FONT,
        fontSize: 12,
        bold: true,
        color: INK,
        margin: 0,
      });
      slide.addText(card.subtext || "", {
        x: x + 0.16,
        y: 1.78,
        w: 3.73,
        h: 0.3,
        fontFace: FONT,
        fontSize: 11,
        color: MUTED,
        margin: 0,
      });
    });

    slide.addText(block.status_title || "Crawled-page status", {
      x: 0.42,
      y: 2.4,
      w: 7.2,
      h: 0.3,
      fontFace: FONT,
      fontSize: 14,
      bold: true,
      color: INK,
      margin: 0,
    });

    const status = (block.status || []).slice(0, 4);
    const maxBar = Math.max(1, Number(block.status_max) || 1);
    const barMaxW = 5.6;
    status.forEach((row, i) => {
      const y = 2.82 + i * 0.55;
      const count = Number(row.count) || 0;
      const w = Math.max(count ? 0.12 : 0, (count / maxBar) * barMaxW);
      slide.addText(row.label || "", {
        x: 0.42,
        y,
        w: 1.35,
        h: 0.4,
        fontFace: FONT,
        fontSize: 13,
        color: INK,
        valign: "middle",
        margin: 0,
      });
      if (w > 0) {
        slide.addShape("roundRect", {
          x: 1.85,
          y: y + 0.08,
          w,
          h: 0.24,
          fill: { color: FAIL },
          rectRadius: 0.04,
        });
      }
      slide.addText(String(count), {
        x: 1.85 + w + 0.1,
        y,
        w: 0.8,
        h: 0.4,
        fontFace: FONT,
        fontSize: 13,
        bold: true,
        color: INK,
        valign: "middle",
        margin: 0,
      });
    });

    slide.addText(block.status_note || "", {
      x: 0.42,
      y: 5.1,
      w: 7.2,
      h: 1.5,
      fontFace: FONT,
      fontSize: 11,
      italic: true,
      color: MUTED,
      margin: 0,
    });

    slide.addShape("roundRect", {
      x: 7.9,
      y: 2.4,
      w: 5.0,
      h: 4.2,
      fill: { color: WASH },
      rectRadius: 0.1,
    });
    slide.addText(block.issues_title || "Top issues (by count)", {
      x: 8.1,
      y: 2.55,
      w: 4.6,
      h: 0.32,
      fontFace: FONT,
      fontSize: 14,
      bold: true,
      color: INK,
      margin: 0,
    });
    const issues = (block.issues || []).slice(0, 7);
    if (issues.length) {
      issues.forEach((issue, i) => {
        const y = 3.0 + i * 0.48;
        slide.addText(dash(issue.count), {
          x: 8.1,
          y,
          w: 0.85,
          h: 0.4,
          fontFace: FONT,
          fontSize: 16,
          bold: true,
          color: toneColor(issue.tone),
          margin: 0,
        });
        slide.addText(issue.label || "", {
          x: 9.0,
          y,
          w: 3.7,
          h: 0.4,
          fontFace: FONT,
          fontSize: 13,
          color: INK,
          valign: "middle",
          margin: 0,
        });
      });
    } else {
      slide.addText("No OnPage issue flags in this crawl.", {
        x: 8.1,
        y: 3.1,
        w: 4.6,
        h: 0.8,
        fontFace: FONT,
        fontSize: 13,
        color: MUTED,
        margin: 0,
      });
    }
    addFooter(slide, page, total, date);
  }

  // 10. Crawlability
  {
    const slide = nextSlide();
    const block = data.crawlability_slide && Array.isArray(data.crawlability_slide.rows)
      ? data.crawlability_slide
      : fallbackCrawlability(data);
    const domain = data.prospect_domain || "";

    slide.addText(`${domain}  /  Technical SEO`, {
      x: 0.42,
      y: 0.2,
      w: 12.4,
      h: 0.26,
      fontFace: FONT,
      fontSize: 11,
      color: MUTED,
      margin: 0,
    });
    slide.addText(block.title || "Crawlability — robots.txt, sitemap.xml & llms.txt", {
      x: 0.42,
      y: 0.46,
      w: 12.4,
      h: 0.42,
      fontFace: FONT,
      fontSize: 22,
      bold: true,
      color: INK,
      margin: 0,
    });

    const tableRows = [
      [
        { text: "Item", options: { bold: true, color: WHITE, fill: { color: NH_BLUE } } },
        { text: "Current State", options: { bold: true, color: WHITE, fill: { color: NH_BLUE } } },
        { text: "Recommendation", options: { bold: true, color: WHITE, fill: { color: NH_BLUE } } },
      ],
    ];
    (block.rows || []).forEach((row) => {
      tableRows.push([
        { text: row.item || "—", options: { bold: true, color: INK } },
        { text: row.state || "—", options: { color: cellColor(row.tone) } },
        { text: row.recommendation || "—", options: { color: INK } },
      ]);
    });
    slide.addTable(tableRows, {
      x: 0.42,
      y: 1.05,
      w: 12.48,
      colW: [2.1, 5.2, 5.18],
      border: [{ pt: 0 }, { pt: 0 }, { pt: 0.5, color: LINE }, { pt: 0 }],
      fontFace: FONT,
      fontSize: 12,
      color: INK,
      valign: "middle",
      rowH: 0.78,
    });
    addFooter(slide, page, total, date);
  }

  } // end !quick (slides 6–10)

  // 11. Quick wins (moved after AI Visibility + crawl slides)
  if (!thin && !quick) {
    const slide = nextSlide();
    kicker(slide, "OPPORTUNITY");
    title(slide, "Quick wins — keywords in positions 4 to 15");
    estimatedNote(slide);
    const wins = Array.isArray(data.quick_wins) ? data.quick_wins.slice(0, 8) : [];
    if (!wins.length) {
      slide.addText("No modeled keywords in positions 4–15 for this market. Skip this slide in follow-up if it stays empty.", {
        x: 0.5,
        y: 2.0,
        w: 12.3,
        h: 1,
        fontFace: FONT,
        fontSize: 16,
        color: MUTED,
        margin: 0,
      });
    } else {
      const rows = [
        [
          { text: "Keyword (Estimated)", options: { bold: true, color: WHITE, fill: { color: NH_BLUE } } },
          { text: "Pos.", options: { bold: true, color: WHITE, fill: { color: NH_BLUE }, align: "center" } },
          { text: "Est. volume", options: { bold: true, color: WHITE, fill: { color: NH_BLUE }, align: "center" } },
          { text: "Ranking URL", options: { bold: true, color: WHITE, fill: { color: NH_BLUE } } },
        ],
      ];
      wins.forEach((w) => {
        rows.push([
          w.keyword || "—",
          { text: dash(w.position), options: { align: "center" } },
          { text: w.volume_display || dash(w.volume), options: { align: "center" } },
          w.url || "—",
        ]);
      });
      slide.addTable(rows, {
        x: 0.5,
        y: 1.75,
        w: 12.3,
        colW: [4.2, 1.2, 1.8, 5.1],
        border: [{ pt: 0 }, { pt: 0 }, { pt: 0.5, color: LINE }, { pt: 0 }],
        fontFace: FONT,
        fontSize: 12,
        color: INK,
        valign: "middle",
        rowH: 0.42,
        align: "left",
      });
    }
    addFooter(slide, page, total, date);
  }

  // Projections (6-month) — before Priorities + CTA
  if (!quick) {
    const slide = nextSlide();
    const block =
      data.projections_slide && Array.isArray(data.projections_slide.rows)
        ? data.projections_slide
        : fallbackProjections(data);
    const domain = data.prospect_domain || "";

    slide.addText(`${domain}  /  Projections`, {
      x: 0.42,
      y: 0.2,
      w: 12.4,
      h: 0.26,
      fontFace: FONT,
      fontSize: 11,
      color: MUTED,
      margin: 0,
    });
    slide.addText(block.title || "6-Month Projections — Today vs. Target", {
      x: 0.42,
      y: 0.46,
      w: 12.4,
      h: 0.42,
      fontFace: FONT,
      fontSize: 22,
      bold: true,
      color: INK,
      margin: 0,
    });
    slide.addText(block.subtitle || "", {
      x: 0.42,
      y: 0.92,
      w: 12.4,
      h: 0.55,
      fontFace: FONT,
      fontSize: 11,
      italic: true,
      color: MUTED,
      margin: 0,
    });

    const tableRows = [
      [
        { text: "Metric", options: { bold: true, color: WHITE, fill: { color: NH_BLUE } } },
        { text: "Today", options: { bold: true, color: WHITE, fill: { color: NH_BLUE } } },
        {
          text: "6-Month Target",
          options: { bold: true, color: WHITE, fill: { color: NH_BLUE } },
        },
        { text: "Change", options: { bold: true, color: WHITE, fill: { color: NH_BLUE } } },
      ],
    ];
    (block.rows || []).forEach((row) => {
      tableRows.push([
        { text: row.metric || "—", options: { bold: true, color: INK } },
        { text: row.today || "—", options: { color: INK } },
        { text: row.target || "—", options: { color: INK, bold: true } },
        {
          text: row.change || "—",
          options: { color: cellColor(row.change_tone), bold: true },
        },
      ]);
    });
    if ((block.rows || []).length === 0) {
      tableRows.push([
        { text: "Re-run Snapshot to populate projection rows", options: { color: MUTED, colspan: 4 } },
        { text: "", options: {} },
        { text: "", options: {} },
        { text: "", options: {} },
      ]);
    }
    slide.addTable(tableRows, {
      x: 0.42,
      y: 1.52,
      w: 12.48,
      colW: [5.0, 2.4, 2.6, 2.48],
      border: [{ pt: 0 }, { pt: 0 }, { pt: 0.5, color: LINE }, { pt: 0 }],
      fontFace: FONT,
      fontSize: 11.5,
      color: INK,
      valign: "middle",
      rowH: 0.41,
    });

    slide.addShape("roundRect", {
      x: 0.42,
      y: 5.28,
      w: 12.48,
      h: 0.95,
      fill: { color: TAKEAWAY },
      rectRadius: 0.08,
    });
    slide.addText("KEY NOTE", {
      x: 0.66,
      y: 5.36,
      w: 12.0,
      h: 0.22,
      fontFace: FONT,
      fontSize: 11,
      bold: true,
      color: TAKEAWAY_INK,
      margin: 0,
    });
    slide.addText(
      block.takeaway ||
        "These numbers are illustrative starting points, not exact commitments — final targets will vary based on discussion, scope, and resources.",
      {
        x: 0.66,
        y: 5.58,
        w: 12.0,
        h: 0.58,
        fontFace: FONT,
        fontSize: 12,
        color: INK,
        margin: 0,
      },
    );
    addFooter(slide, page, total, date);
  }

  // Priorities + CTA (Variant A — ink panel, Notionhive logo)
  {
    const slide = nextSlide();
    const domain = data.prospect_domain || "";
    const booking = data.booking_url || "https://notionhive.com/";
    let bookingHost = "notionhive.com";
    try {
      bookingHost = new URL(booking).host.replace(/^www\./, "") || bookingHost;
    } catch (_) {
      /* keep default */
    }

    slide.addText(`${domain}  /  Next step`, {
      x: 0.42,
      y: 0.22,
      w: 7.4,
      h: 0.26,
      fontFace: FONT,
      fontSize: 11,
      color: MUTED,
      margin: 0,
    });
    slide.addText("Five fixes to start with", {
      x: 0.42,
      y: 0.5,
      w: 7.4,
      h: 0.42,
      fontFace: FONT,
      fontSize: 24,
      bold: true,
      color: INK,
      margin: 0,
    });
    slide.addText("Edited and approved by a Notionhive operator. Not auto-sent.", {
      x: 0.42,
      y: 0.95,
      w: 7.4,
      h: 0.28,
      fontFace: FONT,
      fontSize: 12,
      italic: true,
      color: MUTED,
      margin: 0,
    });

    const list = fixes.length
      ? fixes.slice(0, 5)
      : ["Review technical findings and confirm priorities with the prospect."];
    list.forEach((fix, i) => {
      const y = 1.4 + i * 0.92;
      slide.addShape("roundRect", {
        x: 0.42,
        y: y,
        w: 0.42,
        h: 0.42,
        fill: { color: WASH },
        rectRadius: 0.08,
      });
      slide.addText(String(i + 1), {
        x: 0.42,
        y: y + 0.02,
        w: 0.42,
        h: 0.4,
        fontFace: FONT,
        fontSize: 14,
        bold: true,
        color: NH_BLUE,
        align: "center",
        margin: 0,
      });
      slide.addText(fix, {
        x: 1.0,
        y: y - 0.02,
        w: 6.9,
        h: 0.8,
        fontFace: FONT,
        fontSize: 14,
        color: INK,
        valign: "middle",
        margin: 0,
      });
    });

    slide.addShape("roundRect", {
      x: 8.2,
      y: 0.42,
      w: 4.7,
      h: 6.35,
      fill: { color: INK },
      rectRadius: 0.12,
    });
    slide.addShape("rect", {
      x: 11.35,
      y: 0.2,
      w: 2.1,
      h: 2.1,
      fill: { color: NH_BLUE },
      rotate: 18,
    });

    const logo = logoWhitePath();
    if (logo) {
      slide.addImage({
        path: logo,
        x: 8.5,
        y: 0.72,
        w: 2.4,
        h: 0.35,
      });
    } else {
      slide.addText("NOTIONHIVE", {
        x: 8.5,
        y: 0.72,
        w: 4.1,
        h: 0.35,
        fontFace: FONT,
        fontSize: 14,
        bold: true,
        color: WHITE,
        charSpacing: 2,
        margin: 0,
      });
    }

    slide.addText("Book a working session", {
      x: 8.5,
      y: 1.4,
      w: 4.1,
      h: 1.0,
      fontFace: FONT,
      fontSize: 26,
      bold: true,
      color: WHITE,
      margin: 0,
    });
    slide.addText(
      "This brief is a starting point. We turn the five fixes into a scoped 90-day plan.",
      {
        x: 8.5,
        y: 2.55,
        w: 4.1,
        h: 1.15,
        fontFace: FONT,
        fontSize: 14,
        color: "C5D4F5",
        margin: 0,
      }
    );

    slide.addShape("roundRect", {
      x: 8.5,
      y: 4.35,
      w: 4.1,
      h: 0.58,
      fill: { color: NH_BLUE },
      rectRadius: 0.08,
    });
    slide.addText("Schedule with Notionhive  →", {
      x: 8.5,
      y: 4.42,
      w: 4.1,
      h: 0.45,
      fontFace: FONT,
      fontSize: 14,
      bold: true,
      color: WHITE,
      align: "center",
      margin: 0,
      hyperlink: { url: booking },
    });
    slide.addText(bookingHost, {
      x: 8.5,
      y: 5.05,
      w: 4.1,
      h: 0.3,
      fontFace: FONT,
      fontSize: 12,
      color: "93B4F5",
      align: "center",
      margin: 0,
    });

    slide.addShape("rect", {
      x: 8.5,
      y: 5.55,
      w: 4.1,
      h: 0.012,
      fill: { color: "2A3548" },
    });
    slide.addText(
      "Reviewed before it leaves the hive. A specialist signed off every number on this deck.",
      {
        x: 8.5,
        y: 5.7,
        w: 4.1,
        h: 0.75,
        fontFace: FONT,
        fontSize: 11,
        color: "93B4F5",
        margin: 0,
      }
    );
    addFooter(slide, page, total, date);
  }

  return pres.writeFile({ fileName: outputPath });
}

async function main() {
  const inputPath = process.argv[2];
  const outputPath = process.argv[3];
  if (!inputPath || !outputPath) {
    console.error("Usage: node build-deck.js <input.json> <output.pptx>");
    process.exit(1);
  }
  const data = JSON.parse(fs.readFileSync(path.resolve(inputPath), "utf8"));
  await build(data, path.resolve(outputPath));
}

main().catch((err) => {
  console.error(err && err.stack ? err.stack : err);
  process.exit(1);
});
