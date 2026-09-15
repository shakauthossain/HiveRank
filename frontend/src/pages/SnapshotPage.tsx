import React, { useCallback, useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  AlertCircle,
  CheckCircle2,
  Download,
  Loader2,
  Lock,
} from "lucide-react";
import { useLocation, useNavigate } from "react-router-dom";
import api from "../api";

export interface SnapshotRow {
  id: string;
  status: string;
  prospect_domain: string;
  thin_data: boolean;
  api_cost_usd: number;
  created_at: string | null;
}

interface HealthCard {
  key?: string;
  value?: string;
  label?: string;
  subtext?: string;
  tone?: string;
}

interface SnapshotPayload {
  scores?: {
    visibility?: number;
    technical?: number;
    content?: number;
    authority?: number;
  };
  health?: {
    title?: string;
    subtitle?: string;
    takeaway?: string;
    cards?: HealthCard[];
  };
    organic?: {
    etv?: number;
    etv_display?: string;
    count?: number;
    count_display?: string;
    pos_1?: number;
    pos_2_3?: number;
    pos_4_10?: number;
    pos_11_20?: number;
    scope?: string;
    markets?: number;
  };
  quick_wins?: Array<{
    keyword: string;
    position: number;
    volume?: number;
    volume_display?: string;
    url?: string;
  }>;
  technical?: {
    lcp?: string;
    lcp_status?: string;
    inp?: string;
    inp_status?: string;
    cls?: string;
    cls_status?: string;
    tbt?: string;
    tbt_status?: string;
    perf_score?: number;
    pages_crawled?: number;
    onpage_score?: number;
    issues?: Array<{ severity: string; title: string; detail: string }>;
    worst_pages?: Array<{
      url?: string;
      status_code?: number;
      onpage_score?: number;
      title?: string;
    }>;
    mobile?: { perf_score?: number; tbt?: string };
    desktop?: { perf_score?: number };
  };
  authority?: {
    prospect_referring_domains?: number;
    prospect_display?: string;
    rank?: number;
    backlinks?: number;
    spam_score?: number;
    top_referring_domains?: Array<{ domain: string }>;
    peers?: Array<{
      domain?: string;
      label?: string;
      rank?: number;
      is_you?: boolean;
    }>;
  };
  authority_slide?: {
    title?: string;
    chart_title?: string;
    peer_source?: string;
    cards?: HealthCard[];
    peers?: Array<{
      domain?: string;
      label?: string;
      rank?: number;
      is_you?: boolean;
    }>;
    reading?: Array<{ title?: string; body?: string }>;
  };
  rankings_slide?: {
    title?: string;
    market?: string;
    cards?: HealthCard[];
    buckets?: Array<{ label?: string; count?: number }>;
    bucket_caption?: string;
    takeaway?: string;
    top_keywords?: Array<{
      keyword?: string;
      position?: number;
      etv?: number;
      etv_display?: string;
    }>;
  };
  performance_slide?: {
    title?: string;
    cards?: HealthCard[];
    rows?: Array<{
      metric?: string;
      mobile?: { text?: string; tone?: string };
      desktop?: { text?: string; tone?: string };
      lab?: { text?: string; tone?: string };
    }>;
    takeaway?: string;
    lab_header?: string;
  };
  onpage_slide?: {
    title?: string;
    cards?: HealthCard[];
    takeaway?: string;
  };
  geo_slide?: {
    title?: string;
    overall?: number | null;
    crawler?: number | null;
    llms?: boolean;
    llms_score?: number;
    bars?: Array<{
      label?: string;
      score?: number | null;
      tone?: string;
      note?: string;
    }>;
    takeaway?: string;
    source?: string;
  };
  citations_slide?: {
    title?: string;
    cards?: HealthCard[];
    mix_title?: string;
    mix?: Array<{
      label?: string;
      value?: number;
      pct?: number;
      color?: string;
    }>;
    sample_title?: string;
    sample_urls?: string[];
    reading_title?: string;
    takeaway?: string;
    score?: number;
  };
  site_audit_slide?: {
    title?: string;
    cards?: HealthCard[];
    status_title?: string;
    status?: Array<{ label?: string; count?: number }>;
    status_max?: number;
    status_note?: string;
    issues_title?: string;
    issues?: Array<{ count?: number; label?: string; tone?: string }>;
    takeaway?: string;
  };
  crawlability_slide?: {
    title?: string;
    rows?: Array<{
      item?: string;
      state?: string;
      recommendation?: string;
      tone?: string;
    }>;
    takeaway?: string;
  };
  projections_slide?: {
    title?: string;
    subtitle?: string;
    takeaway?: string;
    horizon?: string;
    rows?: Array<{
      key?: string;
      metric?: string;
      today?: string;
      target?: string;
      change?: string;
      change_tone?: string;
      editable?: boolean;
    }>;
  };
}

interface SnapshotDetail extends SnapshotRow {
  progress: string | null;
  error_message: string | null;
  prospect_url: string;
  payload: SnapshotPayload | null;
  top_fixes: string[] | null;
  booking_url: string | null;
  download_ready: boolean;
  reused?: boolean;
  usage_log?: Array<{ endpoint: string; cost: number; ok: boolean }>;
}

interface SnapshotPageProps {
  isLoggedIn: boolean;
  onAuthRequired: () => void;
}

function parseId(pathname: string): string | null {
  const m = pathname.match(/^\/snapshot\/([^/]+)$/);
  return m ? m[1] : null;
}

function healthView(payload: SnapshotPayload) {
  if (payload.health?.cards?.length) return payload.health;
  const organic = payload.organic || {};
  const tech = payload.technical || {};
  const auth = payload.authority || {};
  const scores = payload.scores || {};
  const site =
    tech.onpage_score != null ? Math.round(tech.onpage_score) : scores.technical;
  const rank = scores.authority;
  const cwvFail = (["cls", "lcp", "inp"] as const).find(
    (k) => tech[`${k}_status`] === "fail",
  );
  return {
    title: "SEO Health Snapshot",
    subtitle:
      "Re-run this snapshot to fill AI crawler and DataForSEO rank on slide 2.",
    takeaway:
      "Review the later slides, edit the top five fixes, then approve. Re-run for the full eight-state grid.",
    cards: [
      {
        key: "authority",
        value: rank != null ? String(rank) : "—",
        label: "Authority Score",
        subtext: "Re-run for DataForSEO rank (0–100)",
        tone: "neutral",
      },
      {
        key: "traffic",
        value: organic.etv_display ? `${organic.etv_display} /mo` : "—",
        label: "Organic Traffic",
        subtext: "Estimated · global markets",
        tone: "neutral",
      },
      {
        key: "keywords",
        value: organic.count_display ?? (organic.count != null ? String(organic.count) : "—"),
        label: "Ranking Keywords",
        subtext: "Estimated ranking SERPs",
        tone: "neutral",
      },
      {
        key: "referring",
        value: auth.prospect_display ?? "—",
        label: "Referring Domains",
        subtext: "Live referring domains",
        tone: "neutral",
      },
      {
        key: "site_health",
        value: site != null ? `${site}%` : "—",
        label: "Site Health Score",
        subtext: `${tech.pages_crawled ?? "—"} pages crawled`,
        tone: "neutral",
      },
      {
        key: "ai_search",
        value: "—",
        label: "AI Search Health",
        subtext: "Re-run to read robots.txt",
        tone: "neutral",
      },
      {
        key: "cwv",
        value: cwvFail ? cwvFail.toUpperCase() : "—",
        label: cwvFail ? "Core Web Vitals: Failed" : "Core Web Vitals",
        subtext: cwvFail
          ? `${tech[cwvFail] || ""} on mobile lab data`
          : "PageSpeed mobile",
        tone: cwvFail ? "fail" : "neutral",
      },
      {
        key: "ai_cited",
        value: "—",
        label: "AI-Cited Pages",
        subtext: "Re-run for AI Visibility score",
        tone: "neutral",
      },
    ] as HealthCard[],
  };
}

function toneClass(tone?: string) {
  if (tone === "pass") return "text-pass";
  if (tone === "warn" || tone === "warning") return "text-warn";
  if (tone === "fail") return "text-fail";
  return "text-text-main";
}

function cwvClass(status?: string) {
  if (status === "pass") return "text-pass";
  if (status === "warning") return "text-warn";
  if (status === "fail") return "text-fail";
  return "text-text-muted";
}

function apiError(err: unknown, fallback: string) {
  const detail = (err as { response?: { data?: { detail?: string } } })?.response
    ?.data?.detail;
  return typeof detail === "string" ? detail : fallback;
}

export default function SnapshotPage({
  isLoggedIn,
  onAuthRequired,
}: SnapshotPageProps) {
  const navigate = useNavigate();
  const location = useLocation();
  const [prospect, setProspect] = useState("");
  const [competitorMode, setCompetitorMode] = useState<"auto" | "manual">("auto");
  const [competitors, setCompetitors] = useState(["", "", ""]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [snapshot, setSnapshot] = useState<SnapshotDetail | null>(null);
  const [history, setHistory] = useState<SnapshotRow[]>([]);
  const [fixes, setFixes] = useState<string[]>(["", "", "", "", ""]);
  const [projectionRows, setProjectionRows] = useState<
    NonNullable<SnapshotPayload["projections_slide"]>["rows"]
  >([]);
  const [bookingUrl, setBookingUrl] = useState("");
  const [saving, setSaving] = useState(false);
  const [reusedNotice, setReusedNotice] = useState(false);

  const fetchHistory = useCallback(async () => {
    if (!isLoggedIn) {
      setHistory([]);
      return;
    }
    try {
      const { data } = await api.get<SnapshotRow[]>("/me/snapshots");
      setHistory(data);
    } catch {
      setHistory([]);
    }
  }, [isLoggedIn]);

  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  useEffect(() => {
    const id = parseId(location.pathname);
    if (!id) {
      setSnapshot(null);
      setError(null);
      setReusedNotice(false);
      return undefined;
    }
    if (!isLoggedIn) return undefined;
    let cancelled = false;
    let timer: number | null = null;

    const apply = (data: SnapshotDetail) => {
      setSnapshot(data);
      setError(null);
      if (data.top_fixes?.length) {
        setFixes([...data.top_fixes, "", "", "", "", ""].slice(0, 5));
      }
      if (data.payload?.projections_slide?.rows?.length) {
        setProjectionRows(
          data.payload.projections_slide.rows.map((row) => ({ ...row })),
        );
      } else {
        setProjectionRows([]);
      }
      setBookingUrl(data.booking_url || "");
      if (data.status === "failed") setError(data.error_message);
    };

    const loadOnce = async (): Promise<SnapshotDetail | null> => {
      try {
        const { data } = await api.get<SnapshotDetail>(`/snapshots/${id}`);
        if (cancelled) return null;
        apply(data);
        return data;
      } catch (err) {
        if (!cancelled) setError(apiError(err, "Could not load snapshot"));
        return null;
      }
    };

    const startPolling = () => {
      if (timer != null) return;
      timer = window.setInterval(async () => {
        const data = await loadOnce();
        if (!data || cancelled) return;
        if (!["pending", "running"].includes(data.status)) {
          if (timer != null) window.clearInterval(timer);
          timer = null;
          fetchHistory();
        }
      }, 3000);
    };

    (async () => {
      const data = await loadOnce();
      if (cancelled) return;
      // Keep polling while in-flight — even if the first GET failed (auth race /
      // aborted request). Create response may already show "Queued" in UI.
      if (!data || ["pending", "running"].includes(data.status)) {
        startPolling();
      }
    })();

    return () => {
      cancelled = true;
      if (timer != null) window.clearInterval(timer);
    };
  }, [location.pathname, isLoggedIn, fetchHistory]);

  const handleCreate = async (
    e: React.FormEvent,
    opts?: { force?: boolean; prospectUrl?: string },
  ) => {
    e.preventDefault();
    if (!isLoggedIn) {
      onAuthRequired();
      return;
    }
    const prospectUrl = (opts?.prospectUrl || prospect || "").trim();
    if (!prospectUrl) {
      setError("Enter a prospect website.");
      return;
    }
    setIsSubmitting(true);
    setError(null);
    setReusedNotice(false);
    try {
      const force = Boolean(opts?.force);
      const body: {
        prospect_url: string;
        competitor_mode: "auto" | "manual";
        competitor_urls?: string[];
        force?: boolean;
      } = {
        prospect_url: prospectUrl,
        competitor_mode: competitorMode,
        force,
      };
      if (competitorMode === "manual") {
        const urls = competitors.map((c) => c.trim()).filter(Boolean).slice(0, 3);
        if (!urls.length) {
          setError("Add at least one competitor URL (up to 3).");
          setIsSubmitting(false);
          return;
        }
        body.competitor_urls = urls;
      }
      const { data } = await api.post<SnapshotDetail>("/snapshots", body);
      setProspect(prospectUrl);
      setSnapshot(data);
      setReusedNotice(Boolean(data.reused));
      navigate(`/snapshot/${data.id}`);
      fetchHistory();
    } catch (err) {
      setError(apiError(err, "Could not start snapshot"));
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleForceRerun = async () => {
    const fakeEvent = { preventDefault() {} } as React.FormEvent;
    await handleCreate(fakeEvent, {
      force: true,
      prospectUrl:
        prospect || snapshot?.prospect_url || snapshot?.prospect_domain || "",
    });
  };

  const handleApprove = async () => {
    if (!snapshot) return;
    setSaving(true);
    setError(null);
    try {
      const { data } = await api.post<SnapshotDetail>(
        `/snapshots/${snapshot.id}/approve`,
        {
          top_fixes: fixes.map((f) => f.trim()).filter(Boolean),
          booking_url: bookingUrl,
          projection_rows: (projectionRows || [])
            .filter((row) => row.key && row.editable !== false)
            .map((row) => ({ key: row.key!, target: row.target || "" })),
        },
      );
      setSnapshot(data);
      fetchHistory();
    } catch (err) {
      setError(apiError(err, "Could not approve / build the deck"));
    } finally {
      setSaving(false);
    }
  };

  const handleDownload = async () => {
    if (!snapshot) return;
    setSaving(true);
    try {
      const res = await api.get(`/snapshots/${snapshot.id}/download`, {
        responseType: "blob",
      });
      const url = URL.createObjectURL(res.data);
      const a = document.createElement("a");
      a.href = url;
      a.download = `NH-SEO-Snapshot-${snapshot.prospect_domain}.pptx`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(apiError(err, "Download failed"));
    } finally {
      setSaving(false);
    }
  };

  const running =
    snapshot && ["pending", "running"].includes(snapshot.status);
  const ready =
    snapshot && ["review", "approved"].includes(snapshot.status);
  const payload = snapshot?.payload;
  const health = payload ? healthView(payload) : null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-8"
    >
      {!running && !ready && (
        <div className="run-dock run-dock--snapshot">
          <p className="run-dock__label">Pull a snapshot</p>
          <p className="run-dock__sub">
            DataForSEO + PSI leave-behind. Someone reviews every number before it
            goes out. Peers are operator-selected or Labs overlaps in a similar
            rank band.
          </p>
          {!isLoggedIn ? (
            <button
              type="button"
              className="btn btn--ghost"
              onClick={onAuthRequired}
            >
              <Lock className="w-4 h-4" />
              Sign in to run a snapshot
            </button>
          ) : (
            <form onSubmit={handleCreate}>
              <div className="field" style={{ marginBottom: "0.9rem" }}>
                <label htmlFor="snap-prospect">Prospect website</label>
                <input
                  id="snap-prospect"
                  value={prospect}
                  onChange={(e) => setProspect(e.target.value)}
                  placeholder="prospect.com"
                  required
                />
              </div>

              <fieldset style={{ border: "none", padding: 0, margin: "0 0 1rem" }}>
                <legend
                  style={{
                    fontSize: "0.6875rem",
                    fontWeight: 600,
                    letterSpacing: "0.06em",
                    textTransform: "uppercase",
                    color: "var(--color-muted)",
                    marginBottom: "0.5rem",
                  }}
                >
                  Authority chart peers
                </legend>
                <div className="mode-tabs">
                  <button
                    type="button"
                    className={`mode-tab${competitorMode === "auto" ? " is-active" : ""}`}
                    onClick={() => setCompetitorMode("auto")}
                  >
                    Auto (Labs, filtered)
                  </button>
                  <button
                    type="button"
                    className={`mode-tab${competitorMode === "manual" ? " is-active" : ""}`}
                    onClick={() => setCompetitorMode("manual")}
                  >
                    Enter competitors manually
                  </button>
                </div>
                {competitorMode === "auto" ? (
                  <p className="analyze-hint" style={{ marginTop: "0.5rem" }}>
                    DataForSEO finds keyword-overlap domains, then we drop mega
                    platforms and keep peers in a similar authority rank band.
                  </p>
                ) : (
                  <div className="stack" style={{ marginTop: "0.65rem", display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                    {competitors.map((value, index) => (
                      <div className="field" key={index}>
                        <label htmlFor={`comp-${index}`}>
                          Competitor {index + 1}
                          {index === 0 ? "" : " (optional)"}
                        </label>
                        <input
                          id={`comp-${index}`}
                          value={value}
                          onChange={(e) => {
                            const next = [...competitors];
                            next[index] = e.target.value;
                            setCompetitors(next);
                          }}
                          placeholder={
                            index === 0
                              ? "competitor.com"
                              : `competitor ${index + 1}`
                          }
                          required={index === 0}
                        />
                      </div>
                    ))}
                  </div>
                )}
              </fieldset>

              <button
                type="submit"
                className="btn btn--primary"
                disabled={isSubmitting}
              >
                {isSubmitting ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : null}
                Pull data →
              </button>
            </form>
          )}
        </div>
      )}

      {error && (
        <div className="flex items-start gap-2 rounded-xl border border-fail/30 bg-fail/5 px-4 py-3 text-sm text-fail">
          <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
          <div className="flex-1 space-y-2">
            <p>{error}</p>
            {snapshot?.status === "failed" && (
              <button
                type="button"
                onClick={() => {
                  setSnapshot(null);
                  setError(null);
                  navigate("/snapshot");
                }}
                className="text-sm font-medium underline underline-offset-2"
              >
                Start a new snapshot
              </button>
            )}
          </div>
        </div>
      )}

      {running && snapshot && (
        <div className="rounded-2xl border border-border-subtle bg-bg-card p-8 max-w-xl">
          {reusedNotice && (
            <p className="text-sm text-text-muted mb-4">
              A pull for this domain was already in progress — joined that run
              instead of starting another.
            </p>
          )}
          <div className="flex items-center gap-3 mb-3">
            <Loader2 className="w-5 h-5 animate-spin text-text-muted" />
            <h3 className="text-xl font-semibold">Pulling snapshot data</h3>
          </div>
          <p className="text-text-muted">
            {snapshot.progress || "This usually takes a few minutes (100-page crawl, JS off)."}
          </p>
          <p className="text-sm text-text-muted mt-3">
            {snapshot.prospect_domain}
          </p>
        </div>
      )}

      {ready && snapshot && payload && health && (
        <div className="space-y-5">
          {reusedNotice && (
            <div className="banner">
              <div>
                <strong>Already snapshotted.</strong> Opened the latest shared
                result for this domain so the team does not re-pull the same
                site.{" "}
                <button
                  type="button"
                  className="btn btn--ghost btn--sm"
                  style={{ marginLeft: "0.5rem" }}
                  onClick={() => handleForceRerun()}
                  disabled={isSubmitting}
                >
                  {isSubmitting ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  ) : null}
                  Pull again
                </button>
              </div>
            </div>
          )}

          <section className="snap-section">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="snap-section__head">
                <p>
                  {snapshot.prospect_domain} / Overview
                </p>
                <h3>
                  {health.title || "SEO Health Snapshot"}
                </h3>
                {health.subtitle && (
                  <p className="snap-section__sub">
                    {health.subtitle}
                  </p>
                )}
                {snapshot.thin_data && (
                  <p className="text-sm text-warn mt-2">
                    Thin keyword data — rankings and quick-win slides will be
                    dropped; technical findings are expanded.
                  </p>
                )}
              </div>
              <p className="text-xs text-text-muted">
                API cost this run: ${Number(snapshot.api_cost_usd || 0).toFixed(4)}
              </p>
            </div>

            <div className="snap-metrics snap-metrics--4">
              {(health.cards || []).map((card) => (
                <div
                  key={card.key || card.label}
                  className="snap-metric snap-metric--tall"
                >
                  <p className={`snap-metric__value snap-metric__value--lg ${toneClass(card.tone)}`}>
                    {card.value ?? "—"}
                  </p>
                  <p className="snap-metric__label">{card.label}</p>
                  <p className="snap-metric__sub">{card.subtext}</p>
                </div>
              ))}
            </div>
            {health.takeaway && (
              <div className="snap-takeaway">
                <p className="snap-takeaway__label">Key takeaway</p>
                <p className="snap-takeaway__body">{health.takeaway}</p>
              </div>
            )}
            <p className="snap-footnote">
              Slide 2 is an eight-state health grid from this pull — not the old
              four computed scores. Authority is DataForSEO domain rank (0–100),
              Traffic and keywords are Estimated across global markets
              markets. Site health is OnPage score. Core Web Vitals are Google
              PageSpeed (mobile lab). AI Search Health reads robots.txt for
              GPTBot, ClaudeBot, PerplexityBot, and related crawlers. AI-Cited
              Pages is an AI Visibility score from crawler access + llms.txt +
              organic — we do not buy a ChatGPT citation index on this prepaid
              pull.
            </p>
          </section>

          <section className="snap-section">
            <div className="snap-section__head">
              <p>
                {snapshot.prospect_domain} / Authority
              </p>
              <h3>
                {payload.authority_slide?.title || "Authority & Backlink Profile"}
              </h3>
            </div>
            <div className="snap-metrics">
              {(payload.authority_slide?.cards || []).map((card) => (
                <div key={card.label} className="snap-metric">
                  <p className={`snap-metric__value ${toneClass(card.tone)}`}>
                    {card.value}
                  </p>
                  <p className="snap-metric__label">{card.label}</p>
                  <p className="snap-metric__sub">{card.subtext}</p>
                </div>
              ))}
            </div>
            {!!payload.authority_slide?.peers?.length && (
              <div>
                <p className="text-sm font-semibold mb-2">
                  {payload.authority_slide?.chart_title ||
                    "Authority Score vs. similar peers (Labs)"}
                </p>
                <ul className="space-y-1 text-sm">
                  {payload.authority_slide.peers.slice(0, 6).map((peer) => (
                    <li
                      key={peer.domain || peer.label}
                      className={peer.is_you ? "font-semibold" : "text-text-muted"}
                    >
                      {peer.label || peer.domain}: {peer.rank ?? "—"}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {!!payload.authority_slide?.reading?.length && (
              <div className="snap-note space-y-3">
                <p className="text-sm font-semibold">Reading the profile</p>
                {payload.authority_slide.reading.map((note) => (
                  <div key={note.title}>
                    <p className="text-sm font-semibold">{note.title}</p>
                    <p className="text-xs text-text-muted mt-1 leading-relaxed">
                      {note.body}
                    </p>
                  </div>
                ))}
              </div>
            )}
            <p className="snap-footnote">
              Slide 3 uses DataForSEO rank (0–100), referring domains, estimated
              backlinks, and estimated organic traffic. Category peers come from
              Labs overlapping ranking domains — not a competitor you typed in.
              Traffic is Estimated, not Analytics. No month-over-month trend in
              this pull.
            </p>
          </section>

          {!snapshot.thin_data && payload.rankings_slide?.cards?.length ? (
            <section className="snap-section">
              <div>
                <p className="text-sm text-text-muted">
                  {snapshot.prospect_domain} / Keyword Visibility
                </p>
                <h3 className="font-semibold mt-1">
                  {payload.rankings_slide.title || "Current Rankings"}
                </h3>
              </div>
              <div className="snap-metrics snap-metrics--3">
                {payload.rankings_slide.cards.map((card) => (
                  <div key={card.label} className="snap-metric">
                    <p className={`snap-metric__value ${toneClass(card.tone)}`}>
                      {card.value}
                    </p>
                    <p className="snap-metric__label">{card.label}</p>
                    <p className="snap-metric__sub">{card.subtext}</p>
                  </div>
                ))}
              </div>
              {!!payload.rankings_slide.buckets?.length && (
                <div>
                  <p className="text-sm font-semibold mb-2">
                    {payload.rankings_slide.bucket_caption || "Position distribution"}
                  </p>
                  <ul className="text-sm space-y-1">
                    {payload.rankings_slide.buckets.map((b) => (
                      <li key={b.label} className="flex justify-between gap-4">
                        <span>{b.label}</span>
                        <span className="font-medium">{b.count ?? "—"}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {!!payload.rankings_slide.top_keywords?.length && (
                <div className="overflow-x-auto">
                  <p className="text-sm font-semibold mb-2">Top keywords by traffic</p>
                  <table className="w-full text-sm">
                    <thead className="text-left text-text-muted">
                      <tr>
                        <th className="pb-2 font-medium">Keyword</th>
                        <th className="pb-2 font-medium">Pos</th>
                        <th className="pb-2 font-medium">Traffic</th>
                      </tr>
                    </thead>
                    <tbody>
                      {payload.rankings_slide.top_keywords.slice(0, 8).map((row) => (
                        <tr
                          key={row.keyword}
                          className="border-t border-border-subtle"
                        >
                          <td className="py-2">{row.keyword}</td>
                          <td className="py-2">{row.position ?? "—"}</td>
                          <td className="py-2">
                            {row.etv_display ?? row.etv ?? "—"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
              {payload.rankings_slide.takeaway && (
                <p className="text-sm italic text-text-muted leading-relaxed">
                  {payload.rankings_slide.takeaway}
                </p>
              )}
              <p className="text-xs text-text-muted">
                Slide 4 is the primary Labs market (highest estimated traffic).
                Keywords, traffic, position mix, and top keywords are Estimated
                DataForSEO Labs figures — not Semrush, not Analytics. Traffic
                value is Labs estimated paid traffic cost. The all-markets
                footprint slide was dropped; this slide carries the ranking story.
              </p>
            </section>
          ) : null}

          {snapshot.thin_data && !!payload.technical?.worst_pages?.length && (
            <section className="snap-section overflow-x-auto">
              <h3 className="font-semibold mb-3">Expanded crawl findings</h3>
              <table className="w-full text-sm">
                <thead className="text-left text-text-muted">
                  <tr>
                    <th className="pb-2 font-medium">URL</th>
                    <th className="pb-2 font-medium">Status</th>
                    <th className="pb-2 font-medium">On-page</th>
                  </tr>
                </thead>
                <tbody>
                  {payload.technical.worst_pages.slice(0, 8).map((page) => (
                    <tr
                      key={page.url || page.title}
                      className="border-t border-border-subtle"
                    >
                      <td className="py-2">{page.url ?? "—"}</td>
                      <td className="py-2">{page.status_code ?? "—"}</td>
                      <td className="py-2">{page.onpage_score ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>
          )}

          <section className="snap-section">
            <div>
              <p className="text-sm text-text-muted">
                {snapshot.prospect_domain} / Performance
              </p>
              <h3 className="font-semibold mt-1">
                {payload.performance_slide?.title ||
                  "Performance & Core Web Vitals"}
              </h3>
            </div>
            <div className="snap-metrics snap-metrics--4">
              {(payload.performance_slide?.cards || []).map((card) => (
                <div key={card.label} className="snap-metric">
                  <p className={`snap-metric__value ${toneClass(card.tone)}`}>
                    {card.value}
                  </p>
                  <p className="snap-metric__label">{card.label}</p>
                  <p className="snap-metric__sub">{card.subtext}</p>
                </div>
              ))}
            </div>
            {!!payload.performance_slide?.rows?.length && (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="text-left text-text-muted">
                    <tr>
                      <th className="pb-2 font-medium">Metric</th>
                      <th className="pb-2 font-medium">Mobile (Field / CrUX)</th>
                      <th className="pb-2 font-medium">Desktop (Field / CrUX)</th>
                      <th className="pb-2 font-medium">
                        {payload.performance_slide.lab_header ||
                          "Lab (PageSpeed · mobile)"}
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {payload.performance_slide.rows.map((row) => (
                      <tr
                        key={row.metric}
                        className="border-t border-border-subtle"
                      >
                        <td className="py-2 font-medium">{row.metric}</td>
                        <td className={`py-2 ${toneClass(row.mobile?.tone)}`}>
                          {row.mobile?.text ?? "n/a"}
                        </td>
                        <td className={`py-2 ${toneClass(row.desktop?.tone)}`}>
                          {row.desktop?.text ?? "n/a"}
                        </td>
                        <td className={`py-2 ${toneClass(row.lab?.tone)}`}>
                          {row.lab?.text ?? "n/a"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            {payload.performance_slide?.takeaway && (
              <div className="snap-takeaway">
                <p className="snap-takeaway__label">Key takeaway</p>
                <p className="snap-takeaway__body">
                  {payload.performance_slide.takeaway}
                </p>
              </div>
            )}
            {!payload.performance_slide?.cards?.length && (
              <div className="flex flex-wrap gap-6 text-sm">
                <span>
                  LCP{" "}
                  <strong className={cwvClass(payload.technical?.lcp_status)}>
                    {payload.technical?.lcp ?? "—"}
                  </strong>
                </span>
                <span>
                  INP{" "}
                  <strong className={cwvClass(payload.technical?.inp_status)}>
                    {payload.technical?.inp ?? "—"}
                  </strong>
                </span>
                <span>
                  CLS{" "}
                  <strong className={cwvClass(payload.technical?.cls_status)}>
                    {payload.technical?.cls ?? "—"}
                  </strong>
                </span>
              </div>
            )}
            <p className="text-xs text-text-muted">
              Slide 5 is PageSpeed Insights only — mobile and desktop Lighthouse
              plus Chrome field (CrUX) when Google has it. Lab TBT is the
              PageSpeed proxy for INP. We do not pull GTmetrix on this prepaid
              snapshot. Re-run older reviews to fill desktop and field columns.
            </p>
          </section>

          <section className="snap-section">
            <div>
              <p className="text-sm text-text-muted">
                {snapshot.prospect_domain} / On-Page SEO
              </p>
              <h3 className="font-semibold mt-1">
                {payload.onpage_slide?.title || "On-Page & Content Health"}
              </h3>
            </div>
            <div className="snap-metrics snap-metrics--3">
              {(payload.onpage_slide?.cards || []).map((card) => (
                <div key={card.label} className="snap-metric">
                  <p className={`snap-metric__value ${toneClass(card.tone)}`}>
                    {card.value}
                  </p>
                  <p className="snap-metric__label">{card.label}</p>
                  <p className="snap-metric__sub">{card.subtext}</p>
                </div>
              ))}
            </div>
            {payload.onpage_slide?.takeaway && (
              <div className="snap-takeaway">
                <p className="snap-takeaway__label">Key takeaway</p>
                <p className="snap-takeaway__body">
                  {payload.onpage_slide.takeaway}
                </p>
              </div>
            )}
            <p className="text-xs text-text-muted">
              Slide 6 counts come from the DataForSEO OnPage crawl (JavaScript
              off, 100-page cap) — not a full-site index. Lighthouse SEO is
              PageSpeed, not RankMath. Duplicate content, low text-HTML ratio,
              and multiple H1s are OnPage checks, not a separate crawler.
            </p>
          </section>

          <section className="snap-section">
            <div>
              <p className="text-sm text-text-muted">
                {snapshot.prospect_domain} / AI Search / GEO
              </p>
              <h3 className="font-semibold mt-1">
                {payload.geo_slide?.title || "GEO Readiness Score"}
              </h3>
            </div>
            <div className="snap-metrics snap-metrics--3">
              <div className="snap-metric">
                <p className="snap-metric__value snap-metric__value--lg">
                  {payload.geo_slide?.overall ?? "—"}
                  <span className="text-sm font-medium text-text-muted"> / 100</span>
                </p>
                <p className="snap-metric__label">GEO score</p>
                <p className="snap-metric__sub">From this pull</p>
              </div>
              <div className="snap-metric">
                <p
                  className={`snap-metric__value ${toneClass(
                    (payload.geo_slide?.crawler ?? 0) >= 70
                      ? "pass"
                      : (payload.geo_slide?.crawler ?? 0) >= 45
                        ? "warn"
                        : "fail",
                  )}`}
                >
                  {payload.geo_slide?.crawler ?? "—"}
                </p>
                <p className="snap-metric__label">AI crawler access</p>
                <p className="snap-metric__sub">robots.txt probe</p>
              </div>
              <div className="snap-metric">
                <p
                  className={`snap-metric__value ${
                    payload.geo_slide?.llms ? "text-pass" : "text-fail"
                  }`}
                >
                  {payload.geo_slide?.llms ? "Yes" : "No"}
                </p>
                <p className="snap-metric__label">llms.txt present</p>
                <p className="snap-metric__sub">File at site root</p>
              </div>
            </div>
            <ul className="space-y-2">
              {(payload.geo_slide?.bars || []).map((bar) => (
                <li key={bar.label} className="text-sm">
                  <div className="flex justify-between gap-3 mb-1">
                    <span>{bar.label}</span>
                    <span className={`font-semibold ${toneClass(bar.tone)}`}>
                      {bar.score ?? "—"}
                    </span>
                  </div>
                  <div className="h-2 rounded-full bg-[#E8EEF6] overflow-hidden">
                    <div
                      className={`h-full rounded-full ${
                        bar.tone === "pass"
                          ? "bg-pass"
                          : bar.tone === "warn"
                            ? "bg-warn"
                            : bar.tone === "fail"
                              ? "bg-fail"
                              : "bg-[#1158E5]"
                      }`}
                      style={{
                        width: `${Math.max(0, Math.min(100, bar.score ?? 0))}%`,
                      }}
                    />
                  </div>
                  {bar.note && (
                    <p className="text-xs text-text-muted mt-1">{bar.note}</p>
                  )}
                </li>
              ))}
            </ul>
            {payload.geo_slide?.takeaway && (
              <div className="snap-takeaway">
                <p className="snap-takeaway__label">Key takeaway</p>
                <p className="snap-takeaway__body">
                  {payload.geo_slide.takeaway}
                </p>
              </div>
            )}
            <p className="text-xs text-text-muted">
              Slide 7 is composed only from this Snapshot pull: robots.txt AI
              crawler rules, llms.txt, DataForSEO rank and peers, OnPage
              heading/meta/content checks, and PageSpeed Lighthouse SEO / CWV.
              It is not a Geoptie score, not Semrush, and not a ChatGPT
              citation count. We do not invent an industry-average GEO number.
            </p>
          </section>

          <section className="snap-section">
            <div>
              <p className="text-sm text-text-muted">
                {snapshot.prospect_domain} / AI Search / GEO
              </p>
              <h3 className="font-semibold mt-1">
                {payload.citations_slide?.title || "AI Visibility & Citations"}
              </h3>
            </div>
            <div className="snap-metrics">
              {(payload.citations_slide?.cards || []).length ? (
                (payload.citations_slide?.cards || []).map((card) => (
                <div
                  key={card.label}
                  className="snap-metric"
                >
                  <p className={`snap-metric__value ${toneClass(card.tone)}`}>
                    {card.value ?? "—"}
                  </p>
                  <p className="snap-metric__label">{card.label}</p>
                  <p className="snap-metric__sub">{card.subtext}</p>
                </div>
                ))
              ) : (
                <p className="text-sm text-text-muted col-span-2">
                  Re-run the snapshot to fill AI Visibility & Citations from
                  this pull.
                </p>
              )}
            </div>
            <div className="grid md:grid-cols-2 gap-6">
              <div>
                <h4 className="text-sm font-semibold mb-2">
                  {payload.citations_slide?.mix_title || "Ranking mix"}
                </h4>
                <ul className="space-y-2">
                  {(payload.citations_slide?.mix || []).map((row) => (
                    <li key={row.label} className="flex items-center gap-2 text-sm">
                      <span
                        className="inline-block w-2.5 h-2.5 rounded-full shrink-0"
                        style={{ background: `#${row.color || "1158E5"}` }}
                      />
                      <span className="flex-1">{row.label}</span>
                      <span className="font-semibold">
                        {row.pct != null ? `${row.pct}%` : row.value}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
              <div>
                <h4 className="text-sm font-semibold mb-2">
                  {payload.citations_slide?.sample_title ||
                    "Sample ranking URLs (Estimated, Labs):"}
                </h4>
                {(payload.citations_slide?.sample_urls || []).length ? (
                  <ul className="text-sm space-y-1 text-text-muted">
                    {payload.citations_slide?.sample_urls?.map((url) => (
                      <li key={url}>{url}</li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-sm text-text-muted">
                    No ranking URLs stored on this pull.
                  </p>
                )}
              </div>
            </div>
            {payload.citations_slide?.takeaway && (
              <div className="snap-note">
                <p className="text-sm font-semibold">
                  {payload.citations_slide.reading_title || "How to read this score"}
                </p>
                <p className="text-sm mt-2 leading-relaxed">
                  {payload.citations_slide.takeaway}
                </p>
              </div>
            )}
            <p className="text-xs text-text-muted">
              Slide 8 is not Semrush and not a ChatGPT / Gemini / AI Overviews
              citation index. AI Visibility is the same composite as slide 2
              (crawler access, llms.txt, estimated organic coverage, OnPage).
              Top-10 and keyword counts are DataForSEO Labs. Sample URLs are
              ranking URLs from this pull, labeled Estimated.
            </p>
          </section>

          <section className="snap-section">
            <div>
              <p className="text-sm text-text-muted">
                {snapshot.prospect_domain} / Technical SEO
              </p>
              <h3 className="font-semibold mt-1">
                {payload.site_audit_slide?.title || "Site Audit — Crawl & Links"}
              </h3>
            </div>
            <div className="snap-metrics snap-metrics--3">
              {(payload.site_audit_slide?.cards || []).map((card) => (
                <div key={card.label} className="snap-metric">
                  <p className={`snap-metric__value ${toneClass(card.tone)}`}>
                    {card.value ?? "—"}
                  </p>
                  <p className="snap-metric__label">{card.label}</p>
                  <p className="snap-metric__sub">{card.subtext}</p>
                </div>
              ))}
            </div>
            <div className="grid md:grid-cols-2 gap-6">
              <div>
                <h4 className="text-sm font-semibold mb-3">
                  {payload.site_audit_slide?.status_title || "Crawled-page status"}
                </h4>
                <ul className="space-y-2">
                  {(payload.site_audit_slide?.status || []).map((row) => {
                    const max = Math.max(1, payload.site_audit_slide?.status_max || 1);
                    const pct = Math.min(100, ((row.count || 0) / max) * 100);
                    return (
                      <li key={row.label} className="text-sm">
                        <div className="flex justify-between gap-3 mb-1">
                          <span>{row.label}</span>
                          <span className="font-semibold">{row.count ?? 0}</span>
                        </div>
                        <div className="h-2 rounded-full bg-[#E8EEF6] overflow-hidden">
                          <div
                            className="h-full rounded-full bg-fail"
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                      </li>
                    );
                  })}
                </ul>
                {payload.site_audit_slide?.status_note && (
                  <p className="text-xs italic text-text-muted mt-3">
                    {payload.site_audit_slide.status_note}
                  </p>
                )}
              </div>
              <div className="snap-note">
                <h4 className="text-sm font-semibold mb-3">
                  {payload.site_audit_slide?.issues_title || "Top issues (by count)"}
                </h4>
                {(payload.site_audit_slide?.issues || []).length ? (
                  <ul className="space-y-2 text-sm">
                    {payload.site_audit_slide?.issues?.map((issue) => (
                      <li key={issue.label} className="flex gap-3">
                        <span className={`font-semibold w-14 ${toneClass(issue.tone)}`}>
                          {issue.count}
                        </span>
                        <span>{issue.label}</span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-sm text-text-muted">
                    Re-run for OnPage issue flags, or none in this crawl.
                  </p>
                )}
              </div>
            </div>
            <p className="text-xs text-text-muted">
              Slide 9 is DataForSEO OnPage only (JS off, crawl cap) — not Semrush
              Site Audit, not a category average.
            </p>
          </section>

          <section className="snap-section">
            <div>
              <p className="text-sm text-text-muted">
                {snapshot.prospect_domain} / Technical SEO
              </p>
              <h3 className="font-semibold mt-1">
                {payload.crawlability_slide?.title ||
                  "Crawlability — robots.txt, sitemap.xml & llms.txt"}
              </h3>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="text-left text-text-muted">
                  <tr>
                    <th className="pb-2 font-medium">Item</th>
                    <th className="pb-2 font-medium">Current State</th>
                    <th className="pb-2 font-medium">Recommendation</th>
                  </tr>
                </thead>
                <tbody>
                  {(payload.crawlability_slide?.rows || []).map((row) => (
                    <tr key={row.item} className="border-t border-border-subtle align-top">
                      <td className="py-2 font-medium">{row.item}</td>
                      <td className={`py-2 ${toneClass(row.tone)}`}>{row.state}</td>
                      <td className="py-2 text-text-muted">{row.recommendation}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="text-xs text-text-muted">
              Slide 10 probes robots.txt, llms.txt, and sitemap URLs declared in
              robots.txt (plus common paths like sitemap_index.xml). It does not
              invent Semrush orphan counts or Search Console validation errors.
            </p>
          </section>

          {!snapshot.thin_data && !!payload.quick_wins?.length && (
            <section className="snap-section overflow-x-auto">
              <h3 className="font-semibold mb-3">Quick wins (positions 4–15)</h3>
              <table className="w-full text-sm">
                <thead className="text-left text-text-muted">
                  <tr>
                    <th className="pb-2 font-medium">Keyword</th>
                    <th className="pb-2 font-medium">Pos</th>
                    <th className="pb-2 font-medium">Est. volume</th>
                  </tr>
                </thead>
                <tbody>
                  {payload.quick_wins.slice(0, 8).map((w) => (
                    <tr key={w.keyword} className="border-t border-border-subtle">
                      <td className="py-2">{w.keyword}</td>
                      <td className="py-2">{w.position}</td>
                      <td className="py-2">{w.volume_display ?? w.volume ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <p className="text-xs text-text-muted mt-3">
                Slide 11 — moved after AI Visibility and the crawl slides.
              </p>
            </section>
          )}

          <section className="snap-section">
            <h3 className="font-semibold">Crawl findings (operator notes)</h3>
            <p className="text-sm text-text-muted">
              Crawl {payload.technical?.pages_crawled ?? "—"} pages · On-page
              score {payload.technical?.onpage_score ?? "—"}
            </p>
            {!!payload.technical?.issues?.length && (
              <ul className="text-sm space-y-1 text-text-muted">
                {payload.technical.issues.slice(0, 8).map((issue) => (
                  <li key={`${issue.title}-${issue.detail}`}>
                    <span className="text-text-main font-medium">
                      {issue.title}:
                    </span>{" "}
                    {issue.detail}
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="snap-section">
            <div>
              <p className="text-sm text-text-muted">
                {snapshot.prospect_domain} / Projections
              </p>
              <h3 className="font-semibold mt-1">
                {payload.projections_slide?.title ||
                  "6-Month Projections — Today vs. Target"}
              </h3>
              {payload.projections_slide?.subtitle && (
                <p className="text-sm text-text-muted italic mt-2 max-w-3xl">
                  {payload.projections_slide.subtitle}
                </p>
              )}
            </div>
            {!!projectionRows?.length ? (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="text-left text-text-muted">
                    <tr>
                      <th className="pb-2 font-medium">Metric</th>
                      <th className="pb-2 font-medium">Today</th>
                      <th className="pb-2 font-medium">6-Month Target</th>
                      <th className="pb-2 font-medium">Change</th>
                    </tr>
                  </thead>
                  <tbody>
                    {projectionRows.map((row) => (
                      <tr
                        key={row.key || row.metric}
                        className="border-t border-border-subtle align-top"
                      >
                        <td className="py-2 font-medium pr-3">{row.metric}</td>
                        <td className="py-2 text-text-muted">{row.today}</td>
                        <td className="py-2">
                          {row.editable === false ? (
                            row.target
                          ) : (
                            <input
                              value={row.target || ""}
                              onChange={(e) => {
                                const next = projectionRows.map((r) =>
                                  r.key === row.key
                                    ? { ...r, target: e.target.value }
                                    : r,
                                );
                                setProjectionRows(next);
                              }}
                              className="w-full min-w-[7rem] rounded-lg border border-border-subtle bg-bg-card px-2 py-1.5 text-sm outline-none focus:border-border-focus"
                            />
                          )}
                        </td>
                        <td
                          className={`py-2 font-medium ${toneClass(row.change_tone)}`}
                        >
                          {row.change}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="text-sm text-text-muted">
                Re-run Snapshot to generate 6-month projection rows from current
                data.
              </p>
            )}
            {payload.projections_slide?.takeaway && (
              <div className="snap-takeaway">
                <p className="snap-takeaway__label">Key note</p>
                <p className="snap-takeaway__body">
                  {payload.projections_slide.takeaway}
                </p>
              </div>
            )}
            <p className="text-xs text-text-muted">
              Today is from this Snapshot pull. Targets are Notionhive-proposed
              (formula draft) — edit before approve. Not Analytics or a vendor
              forecast.
            </p>
          </section>

          <section className="snap-section">
            <h3 className="font-semibold">Top five fixes (edit before approve)</h3>
            {fixes.map((fix, i) => (
              <textarea
                key={i}
                value={fix}
                onChange={(e) => {
                  const next = [...fixes];
                  next[i] = e.target.value;
                  setFixes(next);
                }}
                rows={2}
                className="w-full rounded-lg border border-border-subtle bg-bg-card p-3 text-sm outline-none focus:border-border-focus"
                placeholder={`Fix ${i + 1}`}
              />
            ))}
            <label className="block">
              <span className="text-xs font-medium text-text-muted uppercase tracking-wider">
                Booking link
              </span>
              <input
                value={bookingUrl}
                onChange={(e) => setBookingUrl(e.target.value)}
                className="mt-2 w-full rounded-lg border border-border-subtle bg-bg-card p-3 text-sm outline-none focus:border-border-focus"
              />
            </label>
            <div className="flex flex-wrap gap-3 pt-2">
              <button
                type="button"
                onClick={handleApprove}
                disabled={saving}
                className="bg-accent text-accent-fg px-5 py-2.5 rounded-lg font-medium inline-flex items-center gap-2 disabled:opacity-60"
              >
                {saving ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <CheckCircle2 className="w-4 h-4" />
                )}
                {snapshot.status === "approved"
                  ? "Re-approve & rebuild deck"
                  : "Approve & build deck"}
              </button>
              {snapshot.download_ready && (
                <button
                  type="button"
                  onClick={handleDownload}
                  disabled={saving}
                  className="border border-border-subtle px-5 py-2.5 rounded-lg font-medium inline-flex items-center gap-2"
                >
                  <Download className="w-4 h-4" /> Download PPTX
                </button>
              )}
              <button
                type="button"
                onClick={() => handleForceRerun()}
                disabled={isSubmitting || saving}
                className="btn btn--primary btn--sm"
              >
                {isSubmitting ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : null}
                Pull again
              </button>
              <button
                type="button"
                onClick={() => {
                  setSnapshot(null);
                  setError(null);
                  setReusedNotice(false);
                  navigate("/snapshot");
                }}
                className="btn btn--ghost btn--sm"
              >
                New snapshot
              </button>
            </div>
          </section>
        </div>
      )}

      {isLoggedIn && history.length > 0 && !running && (
        <div className="panel" style={{ marginTop: "1.25rem" }}>
          <div className="panel__head">
            <h2>Recent snapshots</h2>
            <span className="muted">All operators · click a row to open</span>
          </div>
          <div className="panel__body">
            <table className="data">
              <thead>
                <tr>
                  <th>Domain</th>
                  <th>Status</th>
                  <th>Credit</th>
                  <th>Date</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {history.slice(0, 20).map((row) => (
                  <tr
                    key={row.id}
                    onClick={() => navigate(`/snapshot/${row.id}`)}
                    style={{ cursor: "pointer" }}
                  >
                    <td>
                      <span className="domain">{row.prospect_domain}</span>
                      {row.thin_data ? (
                        <span className="muted" style={{ display: "block", marginTop: 2 }}>
                          Thin data
                        </span>
                      ) : null}
                    </td>
                    <td>
                      <span
                        className={`chip ${
                          row.status === "approved"
                            ? "chip--pass"
                            : row.status === "failed"
                              ? "chip--fail"
                              : row.status === "review"
                                ? "chip--warn"
                                : "chip--neutral"
                        }`}
                      >
                        {row.status}
                      </span>
                    </td>
                    <td className="tabular muted">
                      {row.api_cost_usd > 0
                        ? `$${Number(row.api_cost_usd).toFixed(4)}`
                        : "—"}
                    </td>
                    <td className="muted tabular">
                      {row.created_at
                        ? new Date(row.created_at).toLocaleDateString(undefined, {
                            year: "numeric",
                            month: "short",
                            day: "numeric",
                          })
                        : "—"}
                    </td>
                    <td>
                      <div className="row-actions">
                        <button
                          type="button"
                          className="btn btn--ghost btn--sm"
                          onClick={(e) => {
                            e.stopPropagation();
                            navigate(`/snapshot/${row.id}`);
                          }}
                        >
                          Open
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </motion.div>
  );
}
