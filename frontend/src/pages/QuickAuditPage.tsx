import React, { type RefObject } from "react";
import { API_BASE_URL as API_URL } from "../api";
import { motion, AnimatePresence } from "framer-motion";
import {
  Download,
  Globe,
  CheckCircle2,
  Loader2,
} from "lucide-react";
import { useNavigate } from "react-router-dom";
import type { HistoryItem } from "../components/HistoryPanel";
import type { Status } from "./AnalyzePage";
import { formatCredit } from "../formatCredit";

const PROGRESS_STEPS = [
  "Visibility & backlinks",
  "Mobile PageSpeed",
  "Desktop PageSpeed",
  "Building 4-slide deck",
];

interface QuickAuditPageProps {
  url: string;
  setUrl: (v: string) => void;
  status: Status;
  activeStep: number;
  auditData: any;
  isLoggedIn: boolean;
  history: HistoryItem[];
  onAnalyze: (e: React.FormEvent, opts?: { force?: boolean }) => Promise<void>;
  onReset: () => void;
  onForceRerun?: () => Promise<void> | void;
  reusedNotice?: boolean;
  runDockRef?: RefObject<HTMLDivElement | null>;
}

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

function toneClass(tone?: string) {
  if (tone === "pass") return "text-pass";
  if (tone === "warn" || tone === "warning") return "text-warn";
  if (tone === "fail") return "text-fail";
  return "text-text-muted";
}

export default function QuickAuditPage({
  url,
  setUrl,
  status,
  activeStep,
  auditData,
  isLoggedIn,
  history,
  onAnalyze,
  onReset,
  onForceRerun,
  reusedNotice = false,
  runDockRef,
}: QuickAuditPageProps) {
  const navigate = useNavigate();
  const quickHistory = history.filter((h) => h.type === "quick");
  const health = auditData?.quick?.health;
  const performance = auditData?.quick?.performance_slide;
  const healthCards = (health?.cards || []).filter(
    (c: { key?: string }) => c.key !== "site_health",
  );
  const perfCards = performance?.cards || [];

  const openHistoryItem = (item: HistoryItem) => {
    navigate(`/quick-audit/${extractDomain(item.url)}/${item.id}`);
  };

  return (
    <AnimatePresence mode="wait">
      {status === "idle" && (
        <motion.div
          key="idle"
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0 }}
        >
          <div ref={runDockRef} className="run-dock">
            <p className="run-dock__label">Quick Audit</p>
            <p className="run-dock__sub">
              4-slide deck — visibility, backlinks, and Core Web Vitals via
              DataForSEO Lighthouse. No full site crawl (~30–45s · ~$0.03–$0.05).
            </p>
            <form onSubmit={onAnalyze}>
              <div className="url-row">
                <div className="field">
                  <label htmlFor="quick-audit-url">Website URL</label>
                  <input
                    id="quick-audit-url"
                    type="text"
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                    placeholder="https://prospect.com"
                    required
                    autoComplete="url"
                  />
                </div>
                <button type="submit" className="btn btn--primary">
                  Run Quick Audit →
                </button>
              </div>
              <p className="analyze-hint">
                Cover · SEO Health · Performance &amp; CWV · Priorities.
              </p>
            </form>
          </div>

          {isLoggedIn && quickHistory.length > 0 && (
            <div className="panel" style={{ marginTop: "1.25rem" }}>
              <div className="panel__head">
                <h2>Recent Quick Audits</h2>
                <span className="muted">All operators · click a row to open</span>
              </div>
              <div className="panel__body">
                <table className="data">
                  <thead>
                    <tr>
                      <th>Domain</th>
                      <th>Credit</th>
                      <th>Run by</th>
                      <th>Date</th>
                      <th />
                    </tr>
                  </thead>
                  <tbody>
                    {quickHistory.slice(0, 20).map((item) => (
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
              Running Quick Audit…
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

      {status === "complete" && (
        <motion.div
          key="complete"
          variants={{
            hidden: { opacity: 0 },
            show: { opacity: 1, transition: { staggerChildren: 0.08 } },
          }}
          initial="hidden"
          animate="show"
          className="my-6 w-full"
        >
          {reusedNotice && (
            <div className="banner" style={{ marginBottom: "1rem" }}>
              <div>
                <strong>Already audited.</strong> Opened the latest shared Quick
                Audit for this domain.{" "}
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
                Quick Audit Results
              </h2>
              <p className="text-text-muted flex items-center gap-2 text-sm">
                <Globe className="w-4 h-4" /> {url}
                {auditData?.quick?.api_cost_usd != null
                  ? ` · DFS ~$${Number(auditData.quick.api_cost_usd).toFixed(4)}`
                  : ""}
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
              <a
                href={
                  auditData?.quick_report_url?.startsWith("http")
                    ? auditData.quick_report_url
                    : `${API_URL}${auditData?.quick_report_url || `/reports/${auditData?.id}_quick.pptx`}`
                }
                className="btn btn--primary btn--sm"
                download
              >
                <Download className="w-4 h-4" />
                PPTX
              </a>
            </div>
          </div>

          {healthCards.length > 0 && (
            <motion.section
              variants={itemVariants}
              className="snap-section"
              style={{ marginBottom: "1.25rem" }}
            >
              <div className="snap-section__head">
                <h3>SEO Health Snapshot</h3>
                <p className="muted">
                  {health?.subtitle ||
                    "Visibility, authority, and CWV signals."}
                </p>
              </div>
              <div className="snap-metrics snap-metrics--4">
                {healthCards.map((card: any) => (
                  <div
                    key={card.key || card.label}
                    className="snap-metric snap-metric--tall"
                  >
                    <p
                      className={`snap-metric__value snap-metric__value--lg ${toneClass(card.tone)}`}
                    >
                      {card.value ?? "—"}
                    </p>
                    <p className="snap-metric__label">{card.label}</p>
                    <p className="snap-metric__sub">{card.subtext}</p>
                  </div>
                ))}
              </div>
            </motion.section>
          )}

          {perfCards.length > 0 && (
            <motion.section
              variants={itemVariants}
              className="snap-section"
              style={{ marginBottom: "1.25rem" }}
            >
              <div className="snap-section__head">
                <h3>Performance &amp; Core Web Vitals</h3>
                <p className="muted">
                  {performance?.takeaway ||
                    "Mobile and desktop PageSpeed lab scores."}
                </p>
              </div>
              <div className="snap-metrics snap-metrics--4">
                {perfCards.map((card: any) => (
                  <div key={card.label} className="snap-metric">
                    <p
                      className={`snap-metric__value ${toneClass(card.tone)}`}
                    >
                      {card.value ?? "—"}
                    </p>
                    <p className="snap-metric__label">{card.label}</p>
                    <p className="snap-metric__sub">{card.subtext}</p>
                  </div>
                ))}
              </div>
              {Array.isArray(performance?.rows) &&
                performance.rows.length > 0 && (
                  <div
                    className="panel__body"
                    style={{ marginTop: "1rem", padding: 0 }}
                  >
                    <table className="data">
                      <thead>
                        <tr>
                          <th>Metric</th>
                          <th>Mobile (field)</th>
                          <th>Desktop (field)</th>
                          <th>Lab</th>
                        </tr>
                      </thead>
                      <tbody>
                        {performance.rows.map((row: any) => (
                          <tr key={row.metric}>
                            <td>{row.metric}</td>
                            <td className={toneClass(row.mobile?.tone)}>
                              {row.mobile?.text ?? "—"}
                            </td>
                            <td className={toneClass(row.desktop?.tone)}>
                              {row.desktop?.text ?? "—"}
                            </td>
                            <td className={toneClass(row.lab?.tone)}>
                              {row.lab?.text ?? "—"}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
            </motion.section>
          )}

          {(auditData?.quick?.top_fixes || []).length > 0 && (
            <motion.section variants={itemVariants} className="snap-section">
              <div className="snap-section__head">
                <h3>Starting priorities</h3>
                <p className="muted">
                  Operator starting points for the leave-behind.
                </p>
              </div>
              <ol
                className="space-y-2"
                style={{ paddingLeft: "1.1rem", margin: 0 }}
              >
                {(auditData.quick.top_fixes as string[])
                  .slice(0, 5)
                  .map((fix: string) => (
                    <li key={fix} className="text-sm text-text-main">
                      {fix}
                    </li>
                  ))}
              </ol>
            </motion.section>
          )}

          {!auditData?.quick && (
            <div className="empty">
              No Quick Audit payload on this result. Run again to refresh.
            </div>
          )}
        </motion.div>
      )}
    </AnimatePresence>
  );
}
