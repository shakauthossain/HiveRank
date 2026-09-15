import { motion, AnimatePresence } from "framer-motion";
import { History, ChevronRight, Link as LinkIcon, Download } from "lucide-react";
import { API_BASE_URL as API_URL } from "../api";
import { formatCredit } from "../formatCredit";

export interface HistoryItem {
  id: string;
  url: string;
  date: string;
  type: "seo" | "speed" | "both" | "quick";
  seoGrade?: string;
  speedGrade?: string;
  ownerEmail?: string;
  apiCostUsd?: number;
}

interface HistoryPanelProps {
  isOpen: boolean;
  onClose: () => void;
  history: HistoryItem[];
  isLoggedIn: boolean;
  onItemClick: (item: HistoryItem) => void;
}

export default function HistoryPanel({
  isOpen,
  onClose,
  history,
  isLoggedIn,
  onItemClick,
}: HistoryPanelProps) {
  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black/40 z-90"
          />
          <motion.div
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            className="fixed top-0 right-0 bottom-0 w-full max-w-sm bg-bg-card border-l border-border-subtle z-100 flex flex-col shadow-2xl"
          >
            <div className="p-5 border-b border-border-subtle flex items-center justify-between">
              <h2 className="text-base font-semibold flex items-center gap-2">
                <History className="w-4 h-4 text-text-muted" />
                Audit History
              </h2>
              <button
                onClick={onClose}
                className="p-1.5 rounded-md hover:bg-bg-hover"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-5 space-y-3">
              {isLoggedIn ? (
                history.length > 0 ? (
                  history.map((item) => (
                    <div
                      key={item.id}
                      className="p-4 rounded-lg bg-bg-card border border-border-subtle hover:border-border-focus cursor-pointer transition-colors"
                      onClick={() => onItemClick(item)}
                    >
                      <div className="flex justify-between items-start mb-3">
                        <span className="font-medium text-sm truncate max-w-[150px]">
                          {item.url}
                        </span>
                        <span className="text-xs text-text-muted">
                          {item.date}
                        </span>
                      </div>
                      {item.ownerEmail && (
                        <p className="text-[11px] text-text-muted mb-2">
                          Run by {item.ownerEmail}
                        </p>
                      )}
                      <div className="flex justify-between items-center mt-3 pt-3 border-t border-border-subtle/40">
                        <div className="flex gap-2 flex-wrap">
                          <span className="text-[10px] uppercase font-bold text-pass">
                            SEO: {item.seoGrade}
                          </span>
                          <span className="text-[10px] uppercase font-bold text-warn">
                            Speed: {item.speedGrade}
                          </span>
                          <span className="text-[10px] uppercase font-bold text-text-muted">
                            Credit: {formatCredit(item.apiCostUsd)}
                          </span>
                        </div>
                        <div className="flex gap-2">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              const fullLink = `${API_URL}/reports/${item.id}_seo.html`;
                              navigator.clipboard.writeText(fullLink);
                              alert("Shareable link copied!");
                            }}
                            className="p-1 text-text-muted hover:text-accent"
                            title="Copy SEO Link"
                          >
                            <LinkIcon className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="text-center py-10">
                    <p className="text-sm text-text-muted">No audits yet.</p>
                  </div>
                )
              ) : (
                <div className="text-center py-10">
                  <p className="text-sm text-text-muted">
                    Please sign in to view history
                  </p>
                </div>
              )}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
