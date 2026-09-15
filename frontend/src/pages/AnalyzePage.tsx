import React, { type RefObject } from "react";

import { API_BASE_URL as API_URL } from "../api";
import { motion, AnimatePresence } from "framer-motion";
import {
  Search,
  Zap,
  Download,
  Globe,
  CheckCircle2,
  ArrowLeft,
  AlertCircle,
  CheckCircle,
  Loader2,
  ExternalLink,
} from "lucide-react";
import { useNavigate } from "react-router-dom";
import { CircularProgress } from "../components/CircularProgress";
import type { HistoryItem } from "../components/HistoryPanel";
import { formatCredit } from "../formatCredit";

export type AnalysisType = "seo" | "speed" | "both" | "quick";
export type Status = "idle" | "analyzing" | "complete";

const PROGRESS_STEPS = [
  "Connecting to server",
  "Fetching performance metrics",
  "Analyzing core web vitals",
  "Evaluating content structure",
  "Compiling report",
];

const MODE_HINTS: Record<Exclude<AnalysisType, "quick">, string> = {
  both: "Technical SEO, on-page signals, and Core Web Vitals in one pass.",
  seo: "On-page and technical SEO signals for this URL.",
  speed: "PageSpeed lab metrics and Core Web Vitals.",
};

const MODE_TABS: { type: Exclude<AnalysisType, "quick">; label: string }[] = [
  { type: "both", label: "Full Audit" },
  { type: "seo", label: "SEO" },
  { type: "speed", label: "Speed" },
];

interface AnalyzePageProps {
  url: string;
  setUrl: (v: string) => void;
  analysisType: AnalysisType;
  setAnalysisType: (v: AnalysisType) => void;
  status: Status;
  activeStep: number;
  auditData: any;
  viewingDetails: "seo" | "speed" | null;
  setViewingDetails: (v: "seo" | "speed" | null) => void;
  isLoggedIn: boolean;
  history: HistoryItem[];
  onAnalyze: (e: React.FormEvent, opts?: { force?: boolean }) => Promise<void>;
  onReset: () => void;
  onForceRerun?: () => Promise<void> | void;
  reusedNotice?: boolean;
  variant?: "landing" | "dashboard";
  runDockRef?: RefObject<HTMLDivElement | null>;
}

const containerVariants = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.1 } },
};

const itemVariants = {
  hidden: { opacity: 0, y: 10 },
  show: {
    opacity: 1,
    y: 0,
    transition: { type: "spring", stiffness: 300, damping: 24 },
  },
};

function extractDomain(rawUrl: string) {
  return rawUrl.replace(/^(?:https?:\/\/)?(?:www\.)?/i, "").split("/")[0];
}

function typeLabel(type: AnalysisType) {
  if (type === "both") return "Full Audit";
  if (type === "seo") return "SEO";
  if (type === "quick") return "Quick Audit";
  return "Speed";
}

interface AnalyzeComposeProps {
  url: string;
  setUrl: (v: string) => void;
  analysisType: AnalysisType;
  setAnalysisType: (v: AnalysisType) => void;
}

function AnalyzeCompose({
  url,
  setUrl,
  analysisType,
  setAnalysisType,
}: AnalyzeComposeProps) {
  const activeType: Exclude<AnalysisType, "quick"> =
    analysisType === "quick" ? "both" : analysisType;

  return (
    <>
      <div className="mode-tabs" role="tablist" aria-label="Analysis type">
        {MODE_TABS.map(({ type, label }) => (
          <button
            key={type}
            type="button"
            role="tab"
            aria-selected={activeType === type}
            className={`mode-tab${activeType === type ? " is-active" : ""}`}
            onClick={() => setAnalysisType(type)}
          >
            {label}
          </button>
        ))}
      </div>

      <div className="url-row">
        <div className="field">
          <label htmlFor="hiverank-url">Website URL</label>
          <input
            id="hiverank-url"
            type="text"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://prospect.com"
            required
            autoComplete="url"
          />
        </div>
        <button type="submit" className="btn btn--primary">
          Analyze →
        </button>
      </div>

      <p className="analyze-hint">{MODE_HINTS[activeType]}</p>
    </>
  );
}

export default function AnalyzePage({
  url,
  setUrl,
  analysisType,
  setAnalysisType,
  status,
  activeStep,
  auditData,
  viewingDetails,
  setViewingDetails,
  isLoggedIn,
  history,
  onAnalyze,
  onReset,
  onForceRerun,
  reusedNotice = false,
  variant = "dashboard",
  runDockRef,
}: AnalyzePageProps) {
  const navigate = useNavigate();
  const auditHistory = history.filter((h) => h.type !== "quick");

  const openHistoryItem = (item: HistoryItem) => {
    if (item.type === "quick") {
      navigate(`/quick-audit/${extractDomain(item.url)}/${item.id}`);
      return;
    }
    navigate(`/analyze/${extractDomain(item.url)}/${item.id}`);
  };

  return (
    <AnimatePresence mode="wait">
      {/* ── IDLE: landing hero ─────────────────────────────────────────── */}
      {status === "idle" && variant === "landing" && (
        <motion.main
          key="idle-landing"
          className="hero"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
        >
          <div className="hero__rail" aria-hidden="true" />
          <div className="hero__grid" aria-hidden="true" />
          <div className="hero__inner">
            <h1 className="hero__brand">HiveRank</h1>
            <p className="hero__lead">
              Know where you stand. Climb with clarity. Paste a URL for a full
              audit, SEO check, or speed test — Notionhive operators review what
              leaves the hive.
            </p>

            <form
              className="analyze-panel"
              ref={runDockRef}
              onSubmit={onAnalyze}
            >
              <AnalyzeCompose
                url={url}
                setUrl={setUrl}
                analysisType={analysisType}
                setAnalysisType={setAnalysisType}
              />
            </form>

            <p className="hero__endorsed">HiveRank by Notionhive</p>
          </div>
        </motion.main>
      )}

      {/* ── IDLE: dashboard run dock + history ───────────────────────────── */}
      {status === "idle" && variant === "dashboard" && (
        <motion.div
          key="idle-dashboard"
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0 }}
        >
          <div ref={runDockRef} className="run-dock">
            <p className="run-dock__label">Run a test</p>
            <p className="run-dock__sub">
              Paste a URL — Full Audit, SEO, or Speed.
            </p>
            <form onSubmit={onAnalyze}>
              <AnalyzeCompose
                url={url}
                setUrl={setUrl}
                analysisType={analysisType}
                setAnalysisType={setAnalysisType}
              />
            </form>
          </div>

          {isLoggedIn && auditHistory.length > 0 && (
            <div className="panel" style={{ marginTop: "1.25rem" }}>
              <div className="panel__head">
                <h2>Recent audits</h2>
                <span className="muted">All operators · click a row to open</span>
              </div>
              <div className="panel__body">
                <table className="data">
                  <thead>
                    <tr>
                      <th>Domain</th>
                      <th>Type</th>
                      <th>SEO</th>
                      <th>Speed</th>
                      <th>Credit</th>
                      <th>Run by</th>
                      <th>Date</th>
                      <th />
                    </tr>
                  </thead>
                  <tbody>
                    {auditHistory.slice(0, 20).map((item) => (
                      <tr
                        key={item.id}
                        onClick={() => openHistoryItem(item)}
                        style={{ cursor: "pointer" }}
                      >
                        <td>
                          <span className="domain" title={item.url}>
                            {extractDomain(item.url)}
                          </span>
                        </td>
                        <td>
                          <span className="chip chip--neutral">
                            {typeLabel(item.type)}
                          </span>
                        </td>
                        <td className="tabular">{item.seoGrade ?? "—"}</td>
                        <td className="tabular">{item.speedGrade ?? "—"}</td>
                        <td className="tabular muted">
                          {formatCredit(item.apiCostUsd)}
                        </td>
                        <td className="muted">
                          {item.ownerEmail
                            ? item.ownerEmail.split("@")[0]
                            : "—"}
                        </td>
                        <td className="muted tabular">{item.date}</td>
                        <td>
                          <div className="row-actions">
                            <button
                              type="button"
                              className="btn btn--ghost btn--sm"
                              onClick={(e) => {
                                e.stopPropagation();
                                openHistoryItem(item);
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
      )}

      {/* ── ANALYZING ────────────────────────────────────────────────────── */}
      {status === "analyzing" && (
        <motion.div
          key="analyzing"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="my-8 max-w-xl"
        >
          <div className="flex items-center gap-4 mb-8">
            <Loader2 className="w-6 h-6 text-text-muted animate-spin" />
            <h2 className="text-2xl font-semibold tracking-tight text-text-main">
              Running Expert Scan...
            </h2>
          </div>
          <div className="w-full space-y-4">
            {PROGRESS_STEPS.map((step, index) => (
              <div
                key={step}
                className={`flex items-center gap-4 p-3 rounded-lg ${
                  index <= activeStep ? "opacity-100" : "opacity-30"
                }`}
              >
                <div
                  className={`w-6 h-6 rounded-full flex items-center justify-center shrink-0 ${
                    index < activeStep
                      ? "bg-pass text-bg-main"
                      : "border-2 border-accent"
                  }`}
                >
                  {index < activeStep ? (
                    <CheckCircle2 className="w-4 h-4" />
                  ) : (
                    index + 1
                  )}
                </div>
                <span className="text-base text-text-main">{step}</span>
              </div>
            ))}
          </div>
        </motion.div>
      )}

      {/* ── COMPLETE — summary cards ─────────────────────────────────────── */}
      {status === "complete" && !viewingDetails && (
        <motion.div
          key="complete"
          variants={containerVariants}
          initial="hidden"
          animate="show"
          className="my-6 w-full"
        >
          {reusedNotice && (
            <div className="banner" style={{ marginBottom: "1rem" }}>
              <div>
                <strong>Already audited.</strong> Opened the latest shared result
                for this domain so the team does not re-run the same site.{" "}
                {onForceRerun && (
                  <button
                    type="button"
                    className="btn btn--ghost btn--sm"
                    style={{ marginLeft: "0.5rem" }}
                    onClick={() => onForceRerun()}
                  >
                    Run again
                  </button>
                )}
              </div>
            </div>
          )}

          <div className="flex items-center justify-between mb-8 pb-6 border-b border-border-subtle gap-3 flex-wrap">
            <div>
              <h2 className="text-3xl font-semibold text-text-main mb-2">
                Audit Results
              </h2>
              <p className="text-text-muted flex items-center gap-2 text-sm">
                <Globe className="w-4 h-4" /> {url}
              </p>
            </div>
            <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
              {onForceRerun && (
                <button
                  type="button"
                  onClick={() => onForceRerun()}
                  className="btn btn--primary btn--sm"
                >
                  Run again
                </button>
              )}
              <button
                type="button"
                onClick={onReset}
                className="btn btn--ghost btn--sm"
              >
                New URL
              </button>
            </div>
          </div>

          <div className="grid md:grid-cols-2 gap-6">
            {auditData?.seo && (
              <motion.div
                variants={itemVariants}
                className="bg-bg-card border border-border-subtle rounded-xl p-6 hover:border-border-focus flex flex-col"
              >
                <div className="flex justify-between items-start mb-8">
                  <div className="flex items-center gap-3">
                    <Search className="w-5 h-5 text-accent" />
                    <h3 className="text-lg font-semibold">SEO Engine</h3>
                  </div>
                  <div className="text-4xl font-bold text-pass">
                    {auditData.seo.seo_score || "N/A"}
                  </div>
                </div>
                <div className="space-y-4 mb-8 flex-1">
                  <div className="relative h-1.5 w-full rounded-full overflow-hidden bg-bg-hover">
                    <div
                      className="absolute inset-y-0 left-0 bg-pass transition-all duration-500"
                      style={{
                        width: `${auditData.seo.seo_score || 0}%`,
                      }}
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-2 pb-2 border-b border-border-subtle">
                    <div className="text-[10px] font-bold text-text-muted uppercase">
                      Priority Fixes
                    </div>
                    <div className="text-[10px] font-bold text-text-muted uppercase text-right">
                      Status
                    </div>
                  </div>

                  {(auditData.seo.seo_tests || [])
                    .filter((t: any) => t.status === "fail")
                    .slice(0, 3)
                    .map((test: any) => (
                      <div
                        key={test.title}
                        className="flex justify-between items-start py-1"
                      >
                        <div className="flex flex-col gap-0.5 max-w-[80%]">
                          <span className="text-text-main text-xs font-semibold capitalize whitespace-nowrap overflow-hidden text-ellipsis">
                            {test.title.split("?")[0].trim()}
                          </span>
                          <span className="text-text-muted text-[11px] line-clamp-1">
                            Critical SEO optimization required.
                          </span>
                        </div>
                        <span className="text-xs font-extrabold text-fail shrink-0">
                          CRITICAL
                        </span>
                      </div>
                    ))}

                  {auditData.seo.seo_tests?.filter(
                    (t: any) => t.status === "fail",
                  ).length === 0 && (
                    <div className="flex items-center gap-2 text-pass py-2">
                      <CheckCircle className="w-4 h-4" />
                      <span className="text-xs font-semibold">
                        No critical issues found!
                      </span>
                    </div>
                  )}
                </div>
                <div className="flex gap-2 mt-auto">
                  <a
                    href={`${API_URL}/reports/${auditData.id}_seo.html`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="btn btn--ghost"
                    style={{ flex: 1 }}
                  >
                    Open report <ExternalLink className="w-3.5 h-3.5" />
                  </a>
                  <a
                    href={`${API_URL}/reports/${auditData.id}_seo.pdf`}
                    className="btn btn--primary"
                    title="Download SEO report as PDF"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    <Download className="w-4 h-4" />
                    PDF
                  </a>
                </div>
              </motion.div>
            )}

            {auditData?.speed && (
              <motion.div
                variants={itemVariants}
                className="bg-bg-card border border-border-subtle rounded-xl p-6 hover:border-border-focus flex flex-col"
              >
                <div className="flex justify-between items-start mb-6">
                  <div className="flex items-center gap-3">
                    <Zap className="w-5 h-5 text-warn" />
                    <h3 className="text-lg font-semibold">Page Experience</h3>
                  </div>
                  <div className="flex gap-4">
                    <div className="text-center">
                      <div className="text-[10px] uppercase font-bold text-text-muted mb-0.5">
                        Mobile
                      </div>
                      <div className="text-3xl font-bold text-pass leading-tight">
                        {auditData.speed.mobile?.perf_score ||
                          auditData.speed.perf_score ||
                          "N/A"}
                      </div>
                    </div>
                    <div className="text-center">
                      <div className="text-[10px] uppercase font-bold text-text-muted mb-0.5">
                        Desktop
                      </div>
                      <div className="text-3xl font-bold text-accent leading-tight">
                        {auditData.speed.desktop?.perf_score || "N/A"}
                      </div>
                    </div>
                  </div>
                </div>
                <div className="space-y-4 mb-8 flex-1">
                  <div className="relative h-1.5 w-full rounded-full bg-bg-hover overflow-hidden">
                    <div
                      className="absolute inset-y-0 left-0 bg-pass transition-all duration-500"
                      style={{
                        width: `${auditData.speed.mobile?.perf_score || auditData.speed.perf_score || 0}%`,
                      }}
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-2 pb-2 border-b border-border-subtle">
                    <div className="text-[10px] font-bold text-text-muted uppercase">
                      Core Vitals (Mobile)
                    </div>
                    <div className="text-[10px] font-bold text-text-muted uppercase text-right">
                      Value
                    </div>
                  </div>

                  <div className="flex justify-between items-start py-1">
                    <div className="flex flex-col gap-0.5">
                      <span className="text-text-main text-xs font-semibold uppercase">
                        FCP
                      </span>
                      <span className="text-text-muted text-[11px]">
                        First Contentful Paint
                      </span>
                    </div>
                    <span className="text-xs font-extrabold text-text-main shrink-0">
                      {auditData.speed.mobile?.fcp ||
                        auditData.speed.metrics?.fcp}
                    </span>
                  </div>

                  <div className="flex justify-between items-start py-1">
                    <div className="flex flex-col gap-0.5">
                      <span className="text-text-main text-xs font-semibold uppercase">
                        LCP
                      </span>
                      <span className="text-text-muted text-[11px]">
                        Largest Contentful Paint
                      </span>
                    </div>
                    <span className="text-xs font-extrabold text-text-main shrink-0">
                      {auditData.speed.mobile?.lcp ||
                        auditData.speed.metrics?.lcp}
                    </span>
                  </div>

                  <div className="flex justify-between items-start py-1">
                    <div className="flex flex-col gap-0.5">
                      <span className="text-text-main text-xs font-semibold uppercase">
                        CLS
                      </span>
                      <span className="text-text-muted text-[11px]">
                        Cumulative Layout Shift
                      </span>
                    </div>
                    <span className="text-xs font-extrabold text-text-main shrink-0">
                      {auditData.speed.mobile?.cls ||
                        auditData.speed.metrics?.cls}
                    </span>
                  </div>
                </div>
                <div className="flex gap-2 mt-auto">
                  <a
                    href={`${API_URL}/reports/${auditData.id}_speed.html`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="btn btn--ghost"
                    style={{ flex: 1 }}
                  >
                    Open report <ExternalLink className="w-3.5 h-3.5" />
                  </a>
                  <a
                    href={`${API_URL}/reports/${auditData.id}_speed.pdf`}
                    className="btn btn--primary"
                    title="Download speed report as PDF"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    <Download className="w-4 h-4" />
                    PDF
                  </a>
                </div>
              </motion.div>
            )}
          </div>
        </motion.div>
      )}

      {/* ── SEO DEEP DIVE ────────────────────────────────────────────────── */}
      {status === "complete" && viewingDetails === "seo" && auditData?.seo && (
        <motion.div
          key="details-seo"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="my-6 w-full"
        >
          <button
            type="button"
            onClick={() => setViewingDetails(null)}
            className="flex items-center gap-2 text-sm font-medium text-text-muted mb-6"
          >
            <ArrowLeft className="w-4 h-4" /> Back
          </button>
          <div className="flex items-center justify-between mb-8 pb-6 border-b border-border-subtle">
            <h2 className="text-2xl font-semibold">Technical SEO Scan</h2>
            <div className="text-4xl font-bold text-pass">
              {auditData.seo.seo_score || "N/A"}
            </div>
          </div>

          <div className="grid md:grid-cols-3 gap-4 mb-10">
            <CircularProgress
              value={parseInt(auditData.seo.seo_score) || 0}
              label="SEO Health"
              colorClass="text-pass"
            />
          </div>

          <div className="space-y-3">
            {(auditData.seo.seo_tests || []).map((test: any) => (
              <div
                key={test.title}
                className="flex items-start gap-4 p-5 bg-bg-card border border-border-subtle rounded-xl"
              >
                {test.status === "pass" || test.status === "check" ? (
                  <CheckCircle className="text-pass shrink-0 mt-0.5" />
                ) : test.status === "warning" ? (
                  <AlertCircle className="text-warn shrink-0 mt-0.5" />
                ) : (
                  <AlertCircle className="text-fail shrink-0 mt-0.5" />
                )}
                <div>
                  <div className="font-medium text-text-main capitalize">
                    {test.title}
                  </div>
                  <div className="text-text-muted text-sm mt-1">
                    {test.content || "Test evaluated on the target URL."}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </motion.div>
      )}

      {/* ── SPEED DEEP DIVE ──────────────────────────────────────────────── */}
      {status === "complete" &&
        viewingDetails === "speed" &&
        auditData?.speed && (
          <motion.div
            key="details-speed"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="my-6 w-full"
          >
            <button
              type="button"
              onClick={() => setViewingDetails(null)}
              className="flex items-center gap-2 text-sm font-medium text-text-muted mb-6"
            >
              <ArrowLeft className="w-4 h-4" /> Back
            </button>
            <div className="flex items-center justify-between mb-8 pb-6 border-b border-border-subtle">
              <h2 className="text-2xl font-semibold">Performance Audit</h2>
              <div className="text-4xl font-bold text-pass">
                {auditData.speed.mobile?.perf_score ||
                  auditData.speed.perf_score ||
                  "N/A"}
              </div>
            </div>

            <div className="grid md:grid-cols-3 gap-4 mb-10">
              <div className="p-4 bg-bg-card border border-border-subtle rounded-xl text-center">
                <div className="text-xs text-text-muted uppercase font-bold mb-1">
                  FCP
                </div>
                <div className="text-xl font-bold">
                  {auditData.speed.mobile?.fcp ||
                    auditData.speed.metrics?.fcp ||
                    "N/A"}
                </div>
              </div>
              <div className="p-4 bg-bg-card border border-border-subtle rounded-xl text-center">
                <div className="text-xs text-text-muted uppercase font-bold mb-1">
                  LCP
                </div>
                <div className="text-xl font-bold">
                  {auditData.speed.mobile?.lcp ||
                    auditData.speed.metrics?.lcp ||
                    "N/A"}
                </div>
              </div>
              <div className="p-4 bg-bg-card border border-border-subtle rounded-xl text-center">
                <div className="text-xs text-text-muted uppercase font-bold mb-1">
                  CLS
                </div>
                <div className="text-xl font-bold">
                  {auditData.speed.mobile?.cls ||
                    auditData.speed.metrics?.cls ||
                    "N/A"}
                </div>
              </div>
            </div>

            <div className="space-y-3">
              {(
                auditData.speed.mobile?.speed_tests ||
                auditData.speed.speed_tests ||
                []
              ).map((test: any) => (
                <div
                  key={test.title}
                  className="flex items-start gap-4 p-5 bg-bg-card border border-border-subtle rounded-xl"
                >
                  {test.status === "pass" ? (
                    <CheckCircle className="text-pass shrink-0 mt-0.5" />
                  ) : test.status === "warning" ? (
                    <AlertCircle className="text-warn shrink-0 mt-0.5" />
                  ) : (
                    <AlertCircle className="text-fail shrink-0 mt-0.5" />
                  )}
                  <div className="flex-1">
                    <div className="font-medium text-text-main capitalize">
                      {test.title}
                    </div>
                    <div className="text-text-muted text-sm mt-1">
                      {test.content
                        ?.replace(/\[Learn more\]\(.*\)/, "")
                        .trim() ||
                        "Optimization test for page loading performance."}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </motion.div>
        )}
    </AnimatePresence>
  );
}
