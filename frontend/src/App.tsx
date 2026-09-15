import React, { useState, useEffect, useRef } from "react";
import { AnimatePresence } from "framer-motion";
import { History, LogOut } from "lucide-react";
import {
  useNavigate,
  useLocation,
  Link,
  Routes,
  Route,
} from "react-router-dom";

import api, { logout, isAuthenticated } from "./api";
import {
  clearAdminSession,
  isAdminUnlocked as readAdminUnlocked,
} from "./adminSession";
import HistoryPanel from "./components/HistoryPanel";
import HiveMark from "./components/HiveMark";
import AppSidebar from "./components/AppSidebar";
import type { NavPermissions } from "./components/AppSidebar";
import type { HistoryItem } from "./components/HistoryPanel";
import AdminPage from "./pages/AdminPage";
import BulkAuditPage from "./pages/BulkAuditPage";
import AnalyzePage from "./pages/AnalyzePage";
import QuickAuditPage from "./pages/QuickAuditPage";
import SnapshotPage from "./pages/SnapshotPage";
import ProfilePage from "./pages/ProfilePage";
import LoginPage from "./pages/LoginPage";
import type { AnalysisType, Status } from "./pages/AnalyzePage";
import { formatCredit } from "./formatCredit";

const PROGRESS_STEP_COUNT = 5;
const QUICK_PROGRESS_STEP_COUNT = 4;
const APP_TITLE = import.meta.env.VITE_APP_TITLE || "HiveRank";

const DEFAULT_PERMS: NavPermissions = {
  analyze: true,
  snapshot: true,
  bulk: true,
  quick_audit: true,
  access: false,
};
export default function App() {
  const navigate = useNavigate();
  const location = useLocation();
  const runDockRef = useRef<HTMLDivElement | null>(null);

  const [url, setUrl] = useState("");
  const [analysisType, setAnalysisType] = useState<AnalysisType>("both");
  const [status, setStatus] = useState<Status>("idle");
  const [activeStep, setActiveStep] = useState(0);
  const [auditData, setAuditData] = useState<any>(null);
  const [viewingDetails, setViewingDetails] = useState<"seo" | "speed" | null>(
    null,
  );
  const [isLoggedIn, setIsLoggedIn] = useState(isAuthenticated());
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [userEmail, setUserEmail] = useState<string>("");
  const [userDisplayName, setUserDisplayName] = useState<string>("");
  const [userRole, setUserRole] = useState<string>("Operator");
  const [userCredit, setUserCredit] = useState<number>(0);
  const [userQuotaLine, setUserQuotaLine] = useState<string>("");
  const [permissions, setPermissions] =
    useState<NavPermissions>(DEFAULT_PERMS);
  const [reusedNotice, setReusedNotice] = useState(false);
  const [adminUnlocked, setAdminUnlocked] = useState(() => readAdminUnlocked());

  const unlockAdminNav = () => {
    setAdminUnlocked(true);
  };

  const showAccessNav = adminUnlocked || permissions.access;

  const requireAuth = () => {
    const path = location.pathname + location.search;
    const next = encodeURIComponent(path || "/");
    navigate(`/login?next=${next}`);
  };

  useEffect(() => {
    if (isLoggedIn) {
      fetchHistory();
      fetchMe();
    } else {
      setPermissions(DEFAULT_PERMS);
      setUserRole("Operator");
    }
  }, [isLoggedIn]);

  useEffect(() => {
    if (!isLoggedIn) return;
    const path = location.pathname;
    const home =
      permissions.analyze
        ? "/"
        : permissions.quick_audit
          ? "/quick-audit"
          : permissions.bulk
            ? "/bulk-audit"
            : permissions.snapshot
              ? "/snapshot"
              : "/login";

    if (path.startsWith("/snapshot") && !permissions.snapshot) {
      navigate(home);
      return;
    }
    if (path.startsWith("/bulk-audit") && !permissions.bulk) {
      navigate(home);
      return;
    }
    if (path.startsWith("/admin") && !showAccessNav) {
      navigate(home === "/login" ? "/" : home);
      return;
    }
    if (path.startsWith("/quick-audit") && !permissions.quick_audit) {
      navigate(permissions.analyze ? "/" : home);
      return;
    }
    if (
      (path === "/" || path.startsWith("/analyze")) &&
      !permissions.analyze &&
      !path.startsWith("/admin")
    ) {
      navigate(
        permissions.quick_audit
          ? "/quick-audit"
          : permissions.snapshot
            ? "/snapshot"
            : permissions.bulk
              ? "/bulk-audit"
              : showAccessNav
                ? "/admin"
                : "/login",
      );
    }
  }, [isLoggedIn, permissions, location.pathname, showAccessNav]);

  useEffect(() => {
    const matchQuick = location.pathname.match(
      /^\/quick-audit\/(.+)\/([^/]+)$/,
    );
    const matchReport = location.pathname.match(/^\/analyze\/(.+)\/([^/]+)$/);
    if (matchQuick) {
      const domain = matchQuick[1];
      const reportId = matchQuick[2];
      if (!auditData || auditData.id !== reportId) {
        loadReport(reportId, domain, "quick");
      }
    } else if (matchReport) {
      const domain = matchReport[1];
      const reportId = matchReport[2];
      if (!auditData || auditData.id !== reportId) {
        loadReport(reportId, domain, "audit");
      }
    } else if (
      location.pathname === "/" ||
      location.pathname === "" ||
      location.pathname === "/quick-audit"
    ) {
      if (status === "complete" && auditData) {
        resetState();
      }
    }
  }, [location.pathname]);

  useEffect(() => {
    const onScroll = () => {
      document
        .getElementById("siteHeader")
        ?.classList.toggle("is-scrolled", window.scrollY > 8);
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const fetchMe = async () => {
    try {
      const { data } = await api.get<{
        email: string;
        display_name?: string | null;
        role?: string;
        permissions?: NavPermissions;
        credit_used_usd?: number;
        audit_count?: number;
        quick_audit_count?: number;
        snapshot_count?: number;
        monthly_audit_limit?: number | null;
        monthly_quick_audit_limit?: number | null;
        monthly_snapshot_limit?: number | null;
      }>("/me");
      setUserEmail(data.email || "");
      setUserDisplayName((data.display_name || "").trim());
      setUserRole(data.role || "Operator");
      setUserCredit(
        typeof data.credit_used_usd === "number" ? data.credit_used_usd : 0,
      );
      const bits: string[] = [];
      const fmt = (used: number, lim: number | null | undefined, tag: string) => {
        if (lim == null) return;
        bits.push(`${tag} ${used}/${lim}`);
      };
      fmt(data.audit_count || 0, data.monthly_audit_limit, "A");
      fmt(data.quick_audit_count || 0, data.monthly_quick_audit_limit, "Q");
      fmt(data.snapshot_count || 0, data.monthly_snapshot_limit, "S");
      setUserQuotaLine(bits.join(" · "));
      if (data.permissions) {
        setPermissions({ ...DEFAULT_PERMS, ...data.permissions });
        if (data.permissions.access) setAdminUnlocked(true);
      }
    } catch {
      setUserEmail("");
      setUserDisplayName("");
      setUserRole("Operator");
      setUserCredit(0);
      setUserQuotaLine("");
      setPermissions(DEFAULT_PERMS);
    }
  };

  const fetchHistory = async () => {
    try {
      const response = await api.get("/me/audits");
      setHistory(
        response.data.map((a: any) => ({
          id: a.report_id,
          url: a.url,
          date: a.created_at
            ? new Date(a.created_at).toLocaleDateString()
            : "",
          type: (a.type === "quick" ? "quick" : "both") as AnalysisType,
          seoGrade: a.seo_score,
          speedGrade: a.speed_score,
          ownerEmail: a.owner_email || undefined,
          apiCostUsd:
            typeof a.api_cost_usd === "number" ? a.api_cost_usd : undefined,
        })),
      );
    } catch {
      console.error("Failed to fetch history");
    }
  };

  const loadReport = async (
    reportId: string,
    domain: string,
    kind: "audit" | "quick" = "audit",
  ) => {
    setStatus("analyzing");
    try {
      const response = await api.get(`/audits/${reportId}`);
      if (response.data?.type === "quick" && kind !== "quick") {
        navigate(`/quick-audit/${domain}/${reportId}`, { replace: true });
        return;
      }
      if (response.data?.type !== "quick" && kind === "quick") {
        navigate(`/analyze/${domain}/${reportId}`, { replace: true });
        return;
      }
      setAuditData(response.data);
      setUrl(response.data.url);
      setStatus("complete");
      setReusedNotice(false);
      document.title =
        kind === "quick" ? `Quick Audit: ${domain}` : `Audit: ${domain}`;
    } catch {
      console.error("Failed to load report");
      setStatus("idle");
    }
  };

  const handleAnalyze = async (
    e: React.FormEvent,
    opts?: { force?: boolean; reportType?: AnalysisType },
  ) => {
    e.preventDefault();
    if (!url) return;

    const force = Boolean(opts?.force);
    const isQuickRoute = location.pathname.startsWith("/quick-audit");
    const reportType: AnalysisType =
      opts?.reportType ||
      (isQuickRoute ? "quick" : analysisType === "quick" ? "both" : analysisType);

    setStatus("analyzing");
    setActiveStep(0);
    setReusedNotice(false);

    const stepCount =
      reportType === "quick" ? QUICK_PROGRESS_STEP_COUNT : PROGRESS_STEP_COUNT;
    const tickMs = reportType === "quick" ? 900 : 1800;
    const interval = setInterval(() => {
      setActiveStep((prev) => {
        if (prev < stepCount - 1) return prev + 1;
        clearInterval(interval);
        return prev;
      });
    }, tickMs);

    try {
      const response = await api.post("/analyze", {
        url,
        report_type: reportType,
        force,
      });
      clearInterval(interval);
      const domain = url
        .replace(/^(?:https?:\/\/)?(?:www\.)?/i, "")
        .split("/")[0];
      setAuditData(response.data);
      setStatus("complete");
      setReusedNotice(Boolean(response.data?.reused));
      navigate(
        reportType === "quick"
          ? `/quick-audit/${domain}/${response.data.id}`
          : `/analyze/${domain}/${response.data.id}`,
      );
      if (isLoggedIn) {
        fetchHistory();
        fetchMe();
      }
    } catch (err) {
      clearInterval(interval);
      console.error("Analysis failed", err);
      const detail = (err as { response?: { data?: { detail?: string } } })
        ?.response?.data?.detail;
      if (typeof detail === "string" && detail.trim()) {
        window.alert(detail);
      }
      setStatus("idle");
    }
  };

  const handleForceRerun = async () => {
    const fakeEvent = { preventDefault() {} } as React.FormEvent;
    const isQuick =
      location.pathname.startsWith("/quick-audit") ||
      auditData?.type === "quick";
    await handleAnalyze(fakeEvent, {
      force: true,
      reportType: isQuick ? "quick" : undefined,
    });
  };

  const resetState = () => {
    setStatus("idle");
    setUrl("");
    setViewingDetails(null);
    setActiveStep(0);
    setAuditData(null);
    setReusedNotice(false);
    document.title = APP_TITLE;
  };

  const reset = () => {
    resetState();
    navigate(location.pathname.startsWith("/quick-audit") ? "/quick-audit" : "/");
  };

  const focusRunDock = () => {
    const target =
      location.pathname.startsWith("/quick-audit") ||
      (!permissions.analyze && permissions.quick_audit)
        ? "/quick-audit"
        : "/";
    navigate(target);
    window.setTimeout(() => {
      runDockRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
      const input = document.getElementById(
        target === "/quick-audit" ? "quick-audit-url" : "hiverank-url",
      ) as HTMLInputElement | null;
      input?.focus();
    }, 50);
  };

  const handleSignOut = () => {
    logout();
    clearAdminSession();
    setIsLoggedIn(false);
    setHistory([]);
    setUserEmail("");
    setUserDisplayName("");
    setUserRole("Operator");
    setUserCredit(0);
    setUserQuotaLine("");
    setPermissions(DEFAULT_PERMS);
    setAdminUnlocked(false);
    navigate("/");
  };

  const isLoginPage = location.pathname === "/login";

  const isLanding =
    !isLoggedIn &&
    !isLoginPage &&
    (location.pathname === "/" || location.pathname === "") &&
    status === "idle";

  const showDashboardChrome =
    (isLoggedIn || adminUnlocked || permissions.access) && !isLoginPage;

  const pageMeta = (() => {
    if (location.pathname.startsWith("/snapshot"))
      return {
        title: "Snapshots",
        meta: "Sales leave-behinds · review before send",
      };
    if (location.pathname.startsWith("/bulk-audit"))
      return { title: "Bulk Audit", meta: "CSV upload · batch SEO + speed" };
    if (location.pathname.startsWith("/login"))
      return { title: "Sign in", meta: "Operator or superadmin" };
    if (location.pathname.startsWith("/admin"))
      return { title: "Access", meta: "Users and who can run what" };
    if (location.pathname.startsWith("/profile"))
      return {
        title: "Profile",
        meta: "Name and password · email is fixed",
      };
    if (location.pathname.startsWith("/quick-audit")) {
      if (status === "complete")
        return { title: "Quick Audit results", meta: url || "Latest run" };
      if (status === "analyzing")
        return { title: "Quick Audit", meta: "Building 4-slide deck…" };
      return {
        title: "Quick Audit",
        meta: "4-slide deck · visibility · backlinks · CWV",
      };
    }
    if (status === "complete")
      return { title: "Audit results", meta: url || "Latest run" };
    if (status === "analyzing")
      return { title: "Running scan", meta: "Please wait…" };
    return {
      title: "Audits",
      meta: "Shared team history · Full Audit · SEO · Speed",
    };
  })();

  const routes = (
    <AnimatePresence mode="wait">
      <Routes
        location={location}
        {...({ key: location.pathname.split("/")[1] || "/" } as any)}
      >
        <Route
          path="/login"
          element={
            <LoginPage
              onOperatorLogin={() => setIsLoggedIn(true)}
              onAdminLogin={unlockAdminNav}
            />
          }
        />
        <Route
          path="/admin"
          element={
            <AdminPage
              onAdminUnlocked={unlockAdminNav}
              onAdminLocked={() => setAdminUnlocked(false)}
            />
          }
        />
        <Route
          path="/snapshot/*"
          element={
            <SnapshotPage
              isLoggedIn={isLoggedIn}
              onAuthRequired={requireAuth}
            />
          }
        />
        <Route
          path="/bulk-audit/*"
          element={
            <BulkAuditPage
              isLoggedIn={isLoggedIn}
              onAuthRequired={requireAuth}
              onJobComplete={fetchHistory}
            />
          }
        />
        <Route
          path="/profile"
          element={
            <ProfilePage
              isLoggedIn={isLoggedIn}
              onAuthRequired={requireAuth}
              onProfileUpdated={fetchMe}
            />
          }
        />
        <Route
          path="/quick-audit/*"
          element={
            <QuickAuditPage
              url={url}
              setUrl={setUrl}
              status={status}
              activeStep={activeStep}
              auditData={auditData}
              isLoggedIn={isLoggedIn}
              history={history}
              onAnalyze={handleAnalyze}
              onReset={reset}
              onForceRerun={handleForceRerun}
              reusedNotice={reusedNotice}
              runDockRef={runDockRef}
            />
          }
        />
        <Route
          path="*"
          element={
            <AnalyzePage
              url={url}
              setUrl={setUrl}
              analysisType={analysisType}
              setAnalysisType={setAnalysisType}
              status={status}
              activeStep={activeStep}
              auditData={auditData}
              viewingDetails={viewingDetails}
              setViewingDetails={setViewingDetails}
              isLoggedIn={isLoggedIn}
              history={history}
              onAnalyze={handleAnalyze}
              onReset={reset}
              onForceRerun={handleForceRerun}
              reusedNotice={reusedNotice}
              variant={isLanding ? "landing" : "dashboard"}
              runDockRef={runDockRef}
            />
          }
        />
      </Routes>
    </AnimatePresence>
  );

  const accountBlock = (
    <div className="topbar__account">
      <Link
        to={isLoggedIn ? "/profile" : "/login"}
        className="topbar__account-meta topbar__account-link"
        title={isLoggedIn ? "Open profile" : "Sign in"}
      >
        <strong>
          {isLoggedIn
            ? userDisplayName || userEmail || "Signed in"
            : adminUnlocked
              ? "Superadmin"
              : "Signed in"}
        </strong>
        <span>
          {isLoggedIn
            ? `${userRole} · ${formatCredit(userCredit)}${
                userQuotaLine ? ` · ${userQuotaLine}` : ""
              }`
            : adminUnlocked
              ? "Access"
              : "Operator"}
        </span>
      </Link>
      <button
        type="button"
        className="btn btn--ghost btn--sm"
        onClick={handleSignOut}
      >
        <LogOut className="w-3.5 h-3.5" /> Sign out
      </button>
    </div>
  );

  return (
    <>
      {isLoginPage ? (
        routes
      ) : isLanding ? (
        <div className="hr-landing">
          <header className="site-header" id="siteHeader">
            <HiveMark onClick={reset} />
            <div className="site-header__actions">
              <button
                type="button"
                className="btn btn--ghost btn--sm"
                onClick={() => navigate("/login")}
              >
                Sign in
              </button>
            </div>
          </header>
          {routes}
          <footer className="landing-foot">
            <div className="landing-foot__inner">
              <div>
                <strong>HiveRank</strong>
                <div>Site health · rankings signal · speed</div>
              </div>
              <div>
                Staff dashboard after sign-in · Snapshots &amp; bulk for
                operators
              </div>
            </div>
          </footer>
        </div>
      ) : showDashboardChrome ? (
        <div className="app">
          <AppSidebar
            onRunTest={focusRunDock}
            showAccess={showAccessNav}
            showProfile={isLoggedIn}
            permissions={
              isLoggedIn
                ? permissions
                : {
                    analyze: true,
                    snapshot: true,
                    bulk: true,
                    quick_audit: true,
                    access: true,
                  }
            }
          />
          <div className="main">
            <div className="mobile-nav">
              {(
                [
                  ...(permissions.analyze || !isLoggedIn
                    ? ([
                        [
                          "/",
                          "Audits",
                          location.pathname === "/" ||
                            location.pathname.startsWith("/analyze"),
                        ],
                      ] as const)
                    : []),
                  ...(permissions.quick_audit || !isLoggedIn
                    ? ([
                        [
                          "/quick-audit",
                          "Quick",
                          location.pathname.startsWith("/quick-audit"),
                        ],
                      ] as const)
                    : []),
                  ...(permissions.snapshot || !isLoggedIn
                    ? ([
                        [
                          "/snapshot",
                          "Snapshots",
                          location.pathname.startsWith("/snapshot"),
                        ],
                      ] as const)
                    : []),
                  ...(permissions.bulk || !isLoggedIn
                    ? ([
                        [
                          "/bulk-audit",
                          "Bulk",
                          location.pathname.startsWith("/bulk-audit"),
                        ],
                      ] as const)
                    : []),
                  ...(showAccessNav
                    ? ([
                        [
                          "/admin",
                          "Access",
                          location.pathname.startsWith("/admin"),
                        ],
                      ] as const)
                    : []),
                  ...(isLoggedIn
                    ? ([
                        [
                          "/profile",
                          "Profile",
                          location.pathname.startsWith("/profile"),
                        ],
                      ] as const)
                    : []),
                ] as const
              ).map(([to, label, active]) => (
                <Link
                  key={to}
                  to={to}
                  className={`nav-link${active ? " is-active" : ""}`}
                >
                  {label}
                </Link>
              ))}
            </div>

            <header className="topbar">
              <div>
                <h1>{pageMeta.title}</h1>
                <div className="topbar__meta">{pageMeta.meta}</div>
              </div>
              <div
                style={{
                  display: "flex",
                  gap: "0.65rem",
                  alignItems: "center",
                  flexWrap: "wrap",
                  justifyContent: "flex-end",
                }}
              >
                <button
                  type="button"
                  className="btn btn--ghost btn--sm"
                  onClick={() => setIsHistoryOpen(true)}
                  aria-label="History"
                >
                  <History className="w-4 h-4" />
                </button>
                <button
                  type="button"
                  className="btn btn--primary btn--sm topbar-run-mobile"
                  onClick={focusRunDock}
                >
                  Run a test
                </button>
                {accountBlock}
              </div>
            </header>

            <div className="content">{routes}</div>
          </div>
        </div>
      ) : (
        <div className="hr-landing">
          <header className="site-header" id="siteHeader">
            <HiveMark onClick={reset} />
            <div className="site-header__actions">
              <button
                type="button"
                className="btn btn--primary btn--sm"
                onClick={() => navigate("/login")}
              >
                Sign in
              </button>
            </div>
          </header>
          <div className="content" style={{ maxWidth: 960, margin: "0 auto" }}>
            {routes}
          </div>
        </div>
      )}

      <HistoryPanel
        isOpen={isHistoryOpen}
        onClose={() => setIsHistoryOpen(false)}
        history={history}
        isLoggedIn={isLoggedIn}
        onItemClick={(item) => {
          const domain = item.url
            .replace(/^(?:https?:\/\/)?(?:www\.)?/i, "")
            .split("/")[0];
          navigate(
            item.type === "quick"
              ? `/quick-audit/${domain}/${item.id}`
              : `/analyze/${domain}/${item.id}`,
          );
          setIsHistoryOpen(false);
        }}
      />
    
    </>
  );
}
