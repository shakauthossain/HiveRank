import React, { useState, useEffect, useCallback, useRef } from "react";

import { motion } from "framer-motion";
import {
  FileUp,
  ArrowRight,
  Activity,
  CheckCircle2,
  Download,
  Loader2,
  AlertCircle,
} from "lucide-react";
import { useNavigate, useLocation } from "react-router-dom";
import api, { API_BASE_URL } from "../api";

export interface BulkJobRow {
  id: number;
  input_filename: string;
  output_filename: string | null;
  status: string;
  total_count: number;
  processed_count: number;
  created_at: string | null;
}

interface BulkAuditPageProps {
  isLoggedIn: boolean;
  onAuthRequired: () => void;
  onJobComplete: () => void;
}

function parseJobIdFromPath(pathname: string): number | null {
  const m = pathname.match(/^\/bulk-audit\/(\d+)$/);
  if (!m) return null;
  const n = parseInt(m[1], 10);
  return Number.isFinite(n) ? n : null;
}

async function pollBulkUntilTerminal(
  jobId: number,
  onTick: (data: BulkJobRow & { status: string }) => void,
  opts: { intervalMs: number; isCancelled: () => boolean },
): Promise<void> {
  const { intervalMs, isCancelled } = opts;
  for (;;) {
    if (isCancelled()) return;
    const { data } = await api.get(`/bulk/status/${jobId}`);
    onTick(data);
    if (data.status === "completed" || data.status === "failed") {
      if (data.status === "failed") {
        throw new Error("Bulk job failed");
      }
      return;
    }
    await new Promise((r) => window.setTimeout(r, intervalMs));
  }
}

export default function BulkAuditPage({
  isLoggedIn,
  onAuthRequired,
  onJobComplete,
}: BulkAuditPageProps) {
  const navigate = useNavigate();
  const location = useLocation();
  const queueRunActiveRef = useRef(false);

  const [bulkFiles, setBulkFiles] = useState<File[]>([]);
  const [bulkJobId, setBulkJobId] = useState<number | null>(null);
  const [bulkStatus, setBulkStatus] = useState<
    (BulkJobRow & { status: string }) | null
  >(null);
  const [jobHistory, setJobHistory] = useState<BulkJobRow[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [queueIndex, setQueueIndex] = useState(0);
  const [queueTotal, setQueueTotal] = useState(0);
  const [queueError, setQueueError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [historyError, setHistoryError] = useState<string | null>(null);

  const fetchJobHistory = useCallback(async () => {
    if (!isLoggedIn) {
      setJobHistory([]);
      setHistoryError(null);
      return;
    }
    setHistoryLoading(true);
    setHistoryError(null);
    try {
      const response = await api.get<BulkJobRow[]>("/me/bulk-jobs");
      setJobHistory(response.data);
    } catch {
      console.error("Failed to load bulk job history");
      setHistoryError(
        "Could not refresh the list. Check that you are signed in and the API is up to date.",
      );
    } finally {
      setHistoryLoading(false);
    }
  }, [isLoggedIn]);

  useEffect(() => {
    fetchJobHistory();
  }, [fetchJobHistory]);

  useEffect(() => {
    const fromUrl = parseJobIdFromPath(location.pathname);
    if (fromUrl == null) {
      return undefined;
    }
    if (queueRunActiveRef.current) {
      return undefined;
    }

    let cancelled = false;
    const isCancelled = () => cancelled;

    (async () => {
      setBulkJobId(fromUrl);
      try {
        const { data: initial } = await api.get(`/bulk/status/${fromUrl}`);
        if (cancelled) return;
        setBulkStatus(initial);
        if (initial.status !== "completed" && initial.status !== "failed") {
          await pollBulkUntilTerminal(fromUrl, setBulkStatus, {
            intervalMs: 5000,
            isCancelled,
          });
        }
        if (!cancelled) {
          onJobComplete();
          fetchJobHistory();
        }
      } catch {
        if (!cancelled) {
          setBulkJobId(null);
          setBulkStatus(null);
          navigate("/bulk-audit", { replace: true });
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [location.pathname, navigate, onJobComplete, fetchJobHistory]);

  const downloadBulkCsv = async (
    jobId: number,
    outputFilename: string | null | undefined,
  ) => {
    const fallbackName = outputFilename || `bulk_result_${jobId}.csv`;
    const reportsUrl = `${API_BASE_URL.replace(/\/$/, "")}/reports/${encodeURIComponent(fallbackName)}`;

    const triggerBlobDownload = (blob: Blob, filename: string) => {
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      a.rel = "noopener";
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    };

    try {
      const res = await api.get(`/bulk/jobs/${jobId}/download`, {
        responseType: "blob",
      });
      const ctype = (res.headers["content-type"] || "").toLowerCase();
      if (ctype.includes("application/json")) {
        const text = await (res.data as Blob).text();
        throw new Error(text || "Download rejected");
      }
      const cd = res.headers["content-disposition"] as string | undefined;
      let filename = fallbackName;
      const m = cd?.match(/filename="?([^";]+)"?/i);
      if (m?.[1]) filename = m[1];
      const blob =
        res.data instanceof Blob ? res.data : new Blob([res.data as BlobPart]);
      triggerBlobDownload(blob, filename);
    } catch {
      console.warn(
        "Authenticated CSV download failed; falling back to /reports/ URL",
      );
      const a = document.createElement("a");
      a.href = reportsUrl;
      a.target = "_blank";
      a.rel = "noopener noreferrer";
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
    }
  };

  const resetToUpload = () => {
    queueRunActiveRef.current = false;
    setBulkJobId(null);
    setBulkFiles([]);
    setBulkStatus(null);
    setQueueIndex(0);
    setQueueTotal(0);
    setQueueError(null);
    navigate("/bulk-audit", { replace: true });
  };

  const handleBulkUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (bulkFiles.length === 0) return;
    if (!isLoggedIn) {
      onAuthRequired();
      return;
    }

    setIsSubmitting(true);
    setQueueError(null);
    setQueueTotal(bulkFiles.length);
    queueRunActiveRef.current = true;

    let hadError = false;
    try {
      for (let i = 0; i < bulkFiles.length; i++) {
        const file = bulkFiles[i];
        setQueueIndex(i + 1);
        const formData = new FormData();
        formData.append("file", file);

        const response = await api.post<{ job_id: number }>(
          "/analyze/bulk",
          formData,
        );
        const jobId = response.data.job_id;
        setBulkJobId(jobId);
        navigate(`/bulk-audit/${jobId}`, { replace: true });
        setBulkStatus(null);

        await pollBulkUntilTerminal(jobId, setBulkStatus, {
          intervalMs: 5000,
          isCancelled: () => false,
        });
        onJobComplete();
        await fetchJobHistory();
      }
    } catch (err) {
      hadError = true;
      setQueueError(
        err instanceof Error ? err.message : "Bulk processing stopped",
      );
    } finally {
      queueRunActiveRef.current = false;
      setIsSubmitting(false);
      if (!hadError) {
        setQueueTotal(0);
        setQueueIndex(0);
      }
    }
  };

  const showProgressCard = bulkJobId != null;
  const isQueueRun = queueTotal > 1;
  const currentFileLabel =
    queueTotal > 0 && queueIndex > 0 && bulkFiles[queueIndex - 1]
      ? bulkFiles[queueIndex - 1].name
      : (bulkStatus?.input_filename ?? "");

  return (
    <motion.div
      key="bulk"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0 }}
      className="space-y-10"
    >
      <div>
        <h2 className="text-3xl font-semibold mb-2">Bulk Analysis</h2>
        <p className="text-text-muted mb-2 italic">
          Upload one or more CSV/XLSX files (each must include a URL column). Files
          run one after another in order.
        </p>
      </div>

      {queueError && (
        <div className="flex items-center gap-2 rounded-xl border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-200">
          <AlertCircle className="w-4 h-4 shrink-0" />
          {queueError}
        </div>
      )}

      {!showProgressCard ? (
        <form onSubmit={handleBulkUpload} className="space-y-6">
          <div className="border-2 border-dashed border-border-subtle hover:border-accent rounded-2xl p-12 flex flex-col items-center justify-center transition-colors group cursor-pointer relative">
            <input
              type="file"
              accept=".csv,.xlsx"
              multiple
              onChange={(e) => {
                const list = e.target.files;
                setBulkFiles(list ? Array.from(list) : []);
              }}
              className="absolute inset-0 opacity-0 cursor-pointer"
            />
            <FileUp className="w-12 h-12 text-text-muted group-hover:text-accent mb-4 transition-colors" />
            <p className="text-lg font-medium text-text-main">
              {bulkFiles.length === 0
                ? "Click or drag files to upload"
                : `${bulkFiles.length} file${bulkFiles.length === 1 ? "" : "s"} selected`}
            </p>
            <p className="text-sm text-text-muted mt-2 text-center max-w-md">
              Supports .csv and .xlsx. Multiple files are processed sequentially
              (one completes before the next starts).
            </p>
          </div>
          {bulkFiles.length > 0 && (
            <ul className="text-sm text-text-muted space-y-1 border border-border-subtle rounded-xl p-4 bg-bg-card max-h-40 overflow-y-auto">
              {bulkFiles.map((f) => (
                <li key={`${f.name}-${f.size}`} className="truncate">
                  {f.name}
                </li>
              ))}
            </ul>
          )}
          {bulkFiles.length > 0 && (
            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full bg-accent text-accent-fg py-4 rounded-xl font-semibold flex items-center justify-center gap-2 disabled:opacity-60"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Running…
                </>
              ) : (
                <>
                  Start batch process <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          )}
        </form>
      ) : (
        <div className="bg-bg-card border border-border-subtle p-8 rounded-2xl relative overflow-hidden z-0">
          <div className="absolute inset-0 bg-gradient-to-br from-accent/5 via-transparent to-accent/10 opacity-60 z-[-1]" />
          <div className="flex flex-col items-center justify-center py-6">
            <div className="relative flex items-center justify-center mb-6">
              {bulkStatus?.status !== "completed" && (
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ repeat: Infinity, duration: 2, ease: "linear" }}
                  className="absolute -inset-4 border border-accent/40 border-t-accent rounded-full"
                />
              )}
              <div className="w-16 h-16 bg-bg-main rounded-full flex items-center justify-center shadow-lg border border-border-subtle z-10">
                {bulkStatus?.status === "completed" ? (
                  <CheckCircle2 className="w-8 h-8 text-pass" />
                ) : (
                  <Activity className="w-8 h-8 text-accent animate-pulse" />
                )}
              </div>
            </div>

            {isQueueRun && (
              <p className="text-xs font-bold uppercase tracking-widest text-text-muted mb-2">
                File {queueIndex} of {queueTotal}
                {currentFileLabel ? ` — ${currentFileLabel}` : ""}
              </p>
            )}

            <h3 className="text-2xl font-bold text-text-main capitalize mb-2">
              {bulkStatus?.status === "completed"
                ? isSubmitting && isQueueRun && queueIndex < queueTotal
                  ? "File complete — starting next…"
                  : "Processing complete"
                : "Analyzing batch…"}
            </h3>
            <p className="text-text-muted text-sm mb-8 text-center max-w-sm">
              {bulkStatus?.status === "completed"
                ? "This file’s URLs have been audited. Results CSV is ready when the job finished successfully."
                : "We are crawling your URLs and generating SEO and Core Web Vitals data."}
            </p>

            <div className="w-full max-w-md">
              <div className="flex justify-between text-xs font-bold uppercase text-text-muted mb-2">
                <span>Progress</span>
                <span>
                  {bulkStatus?.status === "completed"
                    ? "100"
                    : Math.round(
                        ((bulkStatus?.processed_count || 0) /
                          (bulkStatus?.total_count || 1)) *
                          100,
                      )}
                  %
                </span>
              </div>
              <div className="relative w-full h-3 bg-bg-main border border-border-subtle rounded-full overflow-hidden shadow-inner mb-4">
                <motion.div
                  className="absolute left-0 top-0 bottom-0 bg-gradient-to-r from-accent/80 to-accent"
                  initial={{ width: "5%" }}
                  animate={{
                    width:
                      bulkStatus?.status === "completed"
                        ? "100%"
                        : `${Math.max(
                            5,
                            ((bulkStatus?.processed_count || 0) /
                              (bulkStatus?.total_count || 1)) *
                              100,
                          )}%`,
                  }}
                  transition={{ duration: 0.8, ease: "easeInOut" }}
                />
                {bulkStatus?.status !== "completed" && (
                  <motion.div
                    className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent"
                    initial={{ x: "-100%" }}
                    animate={{ x: "100%" }}
                    transition={{
                      repeat: Infinity,
                      duration: 1.5,
                      ease: "linear",
                    }}
                  />
                )}
              </div>

              <div className="text-center text-xs font-bold text-text-muted mb-8 tracking-widest uppercase opacity-70">
                {bulkStatus?.processed_count || 0} /{" "}
                {bulkStatus?.total_count || 0} leads completed
              </div>
            </div>

            {bulkStatus?.status === "completed" && bulkJobId != null && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
                className="flex flex-col items-center gap-3"
              >
                <button
                  type="button"
                  onClick={() =>
                    downloadBulkCsv(bulkJobId, bulkStatus?.output_filename)
                  }
                  className="inline-flex items-center justify-center gap-3 bg-pass hover:bg-pass/90 text-bg-main px-8 py-3.5 rounded-xl font-bold shadow-lg transition-transform hover:-translate-y-0.5"
                >
                  <Download className="w-5 h-5" /> Download results CSV
                </button>
                {!isSubmitting &&
                  (queueTotal <= 1 || queueIndex >= queueTotal) && (
                    <button
                      type="button"
                      onClick={resetToUpload}
                      className="inline-flex items-center justify-center gap-3 bg-transparent border-2 border-border-focus/40 hover:border-accent text-text-main px-8 py-3.5 rounded-xl font-bold shadow-sm transition-all hover:bg-accent/5 hover:-translate-y-0.5"
                    >
                      Run another batch
                    </button>
                  )}
              </motion.div>
            )}
          </div>
        </div>
      )}

      {isLoggedIn && (
        <section className="space-y-4">
          <div className="flex items-center justify-between gap-4">
            <h3 className="text-lg font-semibold text-text-main">
              Previous bulk runs
            </h3>
            <button
              type="button"
              onClick={(e) => {
                e.preventDefault();
                void fetchJobHistory();
              }}
              className="text-sm text-accent hover:underline px-2 py-1 rounded-md border border-border-subtle hover:bg-bg-hover"
            >
              Refresh
            </button>
          </div>
          {historyError && (
            <p className="text-sm text-fail">{historyError}</p>
          )}
          <div className="border border-border-subtle rounded-2xl overflow-hidden bg-bg-card">
            {historyLoading && jobHistory.length === 0 ? (
              <div className="flex items-center justify-center gap-2 py-12 text-text-muted text-sm">
                <Loader2 className="w-4 h-4 animate-spin" />
                Loading history…
              </div>
            ) : jobHistory.length === 0 ? (
              <p className="py-10 text-center text-sm text-text-muted">
                No bulk runs yet. Completed jobs will appear here with a CSV
                download.
              </p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm text-left">
                  <thead className="bg-bg-main text-text-muted uppercase text-xs tracking-wide">
                    <tr>
                      <th className="px-4 py-3 font-semibold">Date</th>
                      <th className="px-4 py-3 font-semibold">File</th>
                      <th className="px-4 py-3 font-semibold">Status</th>
                      <th className="px-4 py-3 font-semibold">Progress</th>
                      <th className="px-4 py-3 font-semibold text-right">
                        Export
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border-subtle">
                    {jobHistory.map((row) => (
                      <tr
                        key={row.id}
                        className="hover:bg-bg-hover/50 transition-colors"
                      >
                        <td className="px-4 py-3 text-text-muted whitespace-nowrap">
                          {row.created_at
                            ? new Date(row.created_at).toLocaleString()
                            : "—"}
                        </td>
                        <td
                          className="px-4 py-3 max-w-[200px] truncate"
                          title={row.input_filename}
                        >
                          {row.input_filename}
                        </td>
                        <td className="px-4 py-3 capitalize">{row.status}</td>
                        <td className="px-4 py-3 text-text-muted whitespace-nowrap">
                          {row.processed_count} / {row.total_count}
                        </td>
                        <td className="px-4 py-3 text-right">
                          {row.status === "completed" && row.output_filename ? (
                            <button
                              type="button"
                              onClick={(e) => {
                                e.preventDefault();
                                e.stopPropagation();
                                void downloadBulkCsv(row.id, row.output_filename);
                              }}
                              className="inline-flex items-center gap-1.5 text-accent font-medium hover:underline"
                            >
                              <Download className="w-3.5 h-3.5" />
                              CSV
                            </button>
                          ) : (
                            <span className="text-text-muted">—</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </section>
      )}
    </motion.div>
  );
}
