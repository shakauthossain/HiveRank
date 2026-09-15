import React, { useCallback, useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Lock,
  Loader2,
  Users,
  UserPlus,
  Trash2,
} from "lucide-react";
import { Link } from "react-router-dom";
import api, { isAuthenticated, setAuthToken } from "../api";
import { formatCredit } from "../formatCredit";
import {
  getAdminCreds,
  setAdminSession,
  clearAdminSession,
  type AdminCreds,
} from "../adminSession";

export type UserPermissions = {
  analyze: boolean;
  snapshot: boolean;
  bulk: boolean;
  quick_audit: boolean;
  access: boolean;
};

type AdminUser = {
  id: number;
  email: string;
  display_name?: string | null;
  audit_count: number;
  quick_audit_count?: number;
  snapshot_count?: number;
  monthly_audit_limit?: number | null;
  monthly_quick_audit_limit?: number | null;
  monthly_snapshot_limit?: number | null;
  credit_used_usd?: number;
  permissions: UserPermissions;
  role: string;
};

const DEFAULT_PERMS: UserPermissions = {
  analyze: true,
  snapshot: true,
  bulk: true,
  quick_audit: true,
  access: false,
};

function roleChipClass(role: string) {
  if (role === "Access admin" || role === "Superadmin") return "chip chip--pass";
  if (role === "Operator") return "chip chip--neutral";
  if (role === "Quick Audit only") return "chip chip--warn";
  if (role === "Analyze only" || role === "Analyze + Quick") return "chip chip--muted";
  if (role === "No access") return "chip chip--fail";
  return "chip chip--warn";
}

export default function AdminPage({
  onAdminUnlocked,
  onAdminLocked,
}: {
  onAdminUnlocked?: () => void;
  onAdminLocked?: () => void;
} = {}) {
  const [adminEmail, setAdminEmail] = useState("");
  const [adminPass, setAdminPass] = useState("");
  const [adminName, setAdminName] = useState("");
  const [adminPreset, setAdminPreset] = useState("operator");
  const [adminStatus, setAdminStatus] = useState("");
  const [isAdminAuthOpen, setIsAdminAuthOpen] = useState(false);
  const [adminAuthUser, setAdminAuthUser] = useState("");
  const [adminAuthPass, setAdminAuthPass] = useState("");
  const [adminAuthLoading, setAdminAuthLoading] = useState(false);
  const [adminUsers, setAdminUsers] = useState<AdminUser[]>([]);
  const [adminStats, setAdminStats] = useState<{
    total_users: number;
    total_audits: number;
    total_bulk_jobs: number;
  } | null>(null);
  const [adminLoggedIn, setAdminLoggedIn] = useState(false);
  const [savedAdminCreds, setSavedAdminCreds] = useState<AdminCreds | null>(
    null,
  );
  const [hydrating, setHydrating] = useState(true);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [draftPerms, setDraftPerms] = useState<UserPermissions>(DEFAULT_PERMS);
  const [draftName, setDraftName] = useState("");
  /** Empty string = unlimited (monthly) */
  const [draftAuditLimit, setDraftAuditLimit] = useState("");
  const [draftQuickLimit, setDraftQuickLimit] = useState("");
  const [draftSnapshotLimit, setDraftSnapshotLimit] = useState("");
  const [savingPerms, setSavingPerms] = useState(false);
  const [showAddUser, setShowAddUser] = useState(false);
  const [adminAuditLimit, setAdminAuditLimit] = useState("");
  const [adminQuickLimit, setAdminQuickLimit] = useState("");
  const [adminSnapshotLimit, setAdminSnapshotLimit] = useState("");

  const authConfig = useCallback(() => {
    // Prefer operator JWT (Access-admin users). Basic is only for env superadmin
    // and must not overwrite Bearer when a JWT session already exists.
    if (isAuthenticated()) {
      return {};
    }
    if (savedAdminCreds) {
      return {
        auth: {
          username: savedAdminCreds.user,
          password: savedAdminCreds.pass,
        },
      };
    }
    return {};
  }, [savedAdminCreds]);

  const fetchAdminData = useCallback(
    async (creds?: AdminCreds | null) => {
      const cfg =
        isAuthenticated()
          ? {}
          : creds
            ? { auth: { username: creds.user, password: creds.pass } }
            : authConfig();
      try {
        const [usersRes, statsRes] = await Promise.all([
          api.get<AdminUser[]>("/admin/users", cfg),
          api.get("/admin/stats", cfg),
        ]);
        setAdminUsers(usersRes.data);
        setAdminStats(statsRes.data);
        setSelectedId((prev) => {
          if (prev && usersRes.data.some((u) => u.id === prev)) return prev;
          return usersRes.data[0]?.id ?? null;
        });
      } catch (err) {
        console.error("Failed to fetch admin data");
        throw err;
      }
    },
    [authConfig],
  );

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const creds = getAdminCreds();
      try {
        // 1) Operator JWT with can_access — preferred
        if (isAuthenticated()) {
          await api.get("/admin/stats");
          if (cancelled) return;
          // Drop stale Basic session so it cannot override Bearer later
          clearAdminSession();
          setSavedAdminCreds(null);
          setAdminLoggedIn(true);
          onAdminUnlocked?.();
          await fetchAdminData(null);
          return;
        }
        // 2) Env superadmin Basic stored in session
        if (creds) {
          await api.get("/admin/stats", {
            auth: { username: creds.user, password: creds.pass },
          });
          if (cancelled) return;
          setSavedAdminCreds(creds);
          setAdminLoggedIn(true);
          onAdminUnlocked?.();
          await fetchAdminData(creds);
        }
      } catch {
        if (creds) clearAdminSession();
        /* show gate */
      } finally {
        if (!cancelled) setHydrating(false);
      }
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const selected = adminUsers.find((u) => u.id === selectedId) || null;

  useEffect(() => {
    if (!selected) {
      setDraftPerms(DEFAULT_PERMS);
      setDraftName("");
      setDraftAuditLimit("");
      setDraftQuickLimit("");
      setDraftSnapshotLimit("");
      return;
    }
    setDraftPerms({ ...DEFAULT_PERMS, ...selected.permissions });
    setDraftName(selected.display_name || "");
    setDraftAuditLimit(
      selected.monthly_audit_limit == null
        ? ""
        : String(selected.monthly_audit_limit),
    );
    setDraftQuickLimit(
      selected.monthly_quick_audit_limit == null
        ? ""
        : String(selected.monthly_quick_audit_limit),
    );
    setDraftSnapshotLimit(
      selected.monthly_snapshot_limit == null
        ? ""
        : String(selected.monthly_snapshot_limit),
    );
  }, [selected]);

  const parseQuotaLimit = (raw: string, label: string): number | null => {
    const t = raw.trim();
    if (!t) return null;
    const n = Number.parseInt(t, 10);
    if (!Number.isFinite(n) || n < 0) {
      throw new Error(`${label} must be a whole number ≥ 0`);
    }
    return n;
  };

  const formatQuota = (used: number, limit?: number | null) => {
    if (limit == null) return `${used}/∞`;
    return `${used}/${limit}`;
  };

  const quotaCell = (u: AdminUser) => {
    const parts = [
      `A ${formatQuota(u.audit_count || 0, u.monthly_audit_limit)}`,
      `Q ${formatQuota(u.quick_audit_count || 0, u.monthly_quick_audit_limit)}`,
      `S ${formatQuota(u.snapshot_count || 0, u.monthly_snapshot_limit)}`,
    ];
    return parts.join(" · ");
  };
  const unlockWithBasic = async (creds: AdminCreds) => {
    setAdminSession(creds);
    setSavedAdminCreds(creds);
    setAdminLoggedIn(true);
    setIsAdminAuthOpen(false);
    onAdminUnlocked?.();
    await fetchAdminData(creds);
  };

  const unlockWithJwt = async () => {
    clearAdminSession();
    setSavedAdminCreds(null);
    setAdminLoggedIn(true);
    setIsAdminAuthOpen(false);
    onAdminUnlocked?.();
    await fetchAdminData(null);
  };

  const handleAdminAuthSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setAdminAuthLoading(true);
    setAdminStatus("");
    try {
      // Env superadmin Basic (ADMIN_EMAIL / ADMIN_PASSWORD)
      try {
        await api.get("/admin/stats", {
          auth: { username: adminAuthUser, password: adminAuthPass },
        });
        await unlockWithBasic({ user: adminAuthUser, pass: adminAuthPass });
        return;
      } catch {
        /* try operator token next */
      }

      // Operator Access-admin: exchange email/password for JWT, then use Bearer
      const response = await api.post(
        `/token?email=${encodeURIComponent(adminAuthUser)}&password=${encodeURIComponent(adminAuthPass)}`,
      );
      setAuthToken(response.data.access_token);
      await api.get("/admin/stats");
      await unlockWithJwt();
    } catch {
      setAdminStatus(
        "Invalid credentials. Use env superadmin (admin@seo.com) or an Access-admin operator.",
      );
    } finally {
      setAdminAuthLoading(false);
    }
  };

  const handleAdminCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!adminEmail || !adminPass) return;
    if (!adminLoggedIn && !savedAdminCreds && !isAuthenticated()) {
      setIsAdminAuthOpen(true);
      return;
    }
    try {
      const params = new URLSearchParams({
        email: adminEmail,
        password: adminPass,
        preset: adminPreset,
      });
      if (adminName.trim()) params.set("display_name", adminName.trim());
      try {
        const a = parseQuotaLimit(adminAuditLimit, "Audit monthly limit");
        const q = parseQuotaLimit(adminQuickLimit, "Quick Audit monthly limit");
        const s = parseQuotaLimit(
          adminSnapshotLimit,
          "Snapshot monthly limit",
        );
        if (a != null) params.set("monthly_audit_limit", String(a));
        if (q != null) params.set("monthly_quick_audit_limit", String(q));
        if (s != null) params.set("monthly_snapshot_limit", String(s));
      } catch (err) {
        setAdminStatus(
          err instanceof Error ? err.message : "Invalid monthly limit",
        );
        return;
      }
      await api.post(`/admin/create-user?${params.toString()}`, {}, authConfig());
      setAdminStatus(`Created ${adminEmail}`);
      setAdminEmail("");
      setAdminPass("");
      setAdminName("");
      setAdminAuditLimit("");
      setAdminQuickLimit("");
      setAdminSnapshotLimit("");
      setAdminPreset("operator");
      setShowAddUser(false);
      await fetchAdminData();
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })
        ?.response?.data?.detail;
      setAdminStatus(typeof detail === "string" ? detail : "Could not create user");
    }
  };

  const handleSavePermissions = async () => {
    if (!selected) return;
    setSavingPerms(true);
    setAdminStatus("");
    let monthlyAudit: number | null = null;
    let monthlyQuick: number | null = null;
    let monthlySnapshot: number | null = null;
    try {
      monthlyAudit = parseQuotaLimit(draftAuditLimit, "Audit monthly limit");
      monthlyQuick = parseQuotaLimit(
        draftQuickLimit,
        "Quick Audit monthly limit",
      );
      monthlySnapshot = parseQuotaLimit(
        draftSnapshotLimit,
        "Snapshot monthly limit",
      );
    } catch (err) {
      setAdminStatus(
        err instanceof Error ? err.message : "Invalid monthly limit",
      );
      setSavingPerms(false);
      return;
    }
    try {
      const { data } = await api.patch(
        `/admin/users/${selected.id}/permissions`,
        {
          can_analyze: draftPerms.analyze,
          can_snapshot: draftPerms.snapshot,
          can_bulk: draftPerms.bulk,
          can_quick_audit: draftPerms.quick_audit,
          can_access: draftPerms.access,
          display_name: draftName,
          monthly_audit_limit: monthlyAudit,
          monthly_quick_audit_limit: monthlyQuick,
          monthly_snapshot_limit: monthlySnapshot,
        },
        authConfig(),
      );
      setAdminUsers((rows) =>
        rows.map((u) =>
          u.id === selected.id
            ? {
                ...u,
                display_name: data.display_name,
                permissions: data.permissions,
                role: data.role,
                audit_count: data.audit_count ?? u.audit_count,
                quick_audit_count: data.quick_audit_count ?? u.quick_audit_count,
                snapshot_count: data.snapshot_count ?? u.snapshot_count,
                monthly_audit_limit: data.monthly_audit_limit,
                monthly_quick_audit_limit: data.monthly_quick_audit_limit,
                monthly_snapshot_limit: data.monthly_snapshot_limit,
              }
            : u,
        ),
      );
      setAdminStatus(`Saved access for ${selected.email}`);
    } catch {
      setAdminStatus("Could not save permissions");
    } finally {
      setSavingPerms(false);
    }
  };

  const handleDeleteUser = async (userId: number) => {
    if (!window.confirm("Delete this user? Their audits and bulk jobs go too.")) {
      return;
    }
    try {
      await api.delete(`/admin/users/${userId}`, authConfig());
      setAdminUsers((rows) => rows.filter((u) => u.id !== userId));
      if (selectedId === userId) setSelectedId(null);
      setAdminStatus("User deleted");
      const stats = await api.get("/admin/stats", authConfig());
      setAdminStats(stats.data);
    } catch {
      setAdminStatus("Could not delete user");
    }
  };

  const togglePerm = (key: keyof UserPermissions) => {
    setDraftPerms((p) => ({ ...p, [key]: !p[key] }));
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="access-page"
    >
      <AnimatePresence>
        {isAdminAuthOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40">
            <motion.div
              initial={{ opacity: 0, scale: 0.96 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.96 }}
              className="auth-card"
            >
              <h2 className="text-lg font-semibold mb-2">Confirm admin</h2>
              <form onSubmit={handleAdminAuthSubmit} className="stack">
                <div className="field">
                  <label>Admin email</label>
                  <input
                    value={adminAuthUser}
                    onChange={(e) => setAdminAuthUser(e.target.value)}
                    required
                  />
                </div>
                <div className="field">
                  <label>Password</label>
                  <input
                    type="password"
                    value={adminAuthPass}
                    onChange={(e) => setAdminAuthPass(e.target.value)}
                    required
                  />
                </div>
                <button type="submit" className="btn btn--primary btn--block">
                  {adminAuthLoading ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    "Authorize"
                  )}
                </button>
              </form>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {!adminLoggedIn ? (
        <div className="max-w-md mx-auto">
          {hydrating ? (
            <div className="flex items-center gap-2 text-text-muted text-sm py-8">
              <Loader2 className="w-4 h-4 animate-spin" />
              Checking Access session…
            </div>
          ) : (
            <>
              <h2 className="font-display text-2xl font-semibold mb-2 flex items-center gap-3">
                <Lock className="w-6 h-6 text-accent" />
                Access
              </h2>
              <div className="bg-bg-card p-6 border border-border-subtle rounded-xl">
                <p className="text-sm text-text-muted mb-6">
                  Sign in as an Access-admin operator (e.g.{" "}
                  <code>shakaut@notionhive.com</code>) or env superadmin (
                  <code>admin@seo.com</code>). Or use{" "}
                  <Link to="/login?next=/admin" className="text-accent font-medium">
                    /login
                  </Link>
                  .
                </p>
                <form onSubmit={handleAdminAuthSubmit} className="space-y-4">
                  <input
                    type="text"
                    placeholder="Admin Email"
                    value={adminAuthUser}
                    onChange={(e) => setAdminAuthUser(e.target.value)}
                    className="w-full bg-bg-main border border-border-subtle p-3 rounded-lg outline-none focus:border-border-focus"
                    required
                  />
                  <input
                    type="password"
                    placeholder="Admin Password"
                    value={adminAuthPass}
                    onChange={(e) => setAdminAuthPass(e.target.value)}
                    className="w-full bg-bg-main border border-border-subtle p-3 rounded-lg outline-none focus:border-border-focus"
                    required
                  />
                  <button
                    type="submit"
                    disabled={adminAuthLoading}
                    className="btn btn--primary btn--block"
                  >
                    {adminAuthLoading ? (
                      <Loader2 className="w-5 h-5 animate-spin" />
                    ) : (
                      "Sign in as admin"
                    )}
                  </button>
                  {adminStatus && (
                    <p className="text-sm text-fail">{adminStatus}</p>
                  )}
                </form>
              </div>
            </>
          )}
        </div>
      ) : (
        <div className="space-y-5">
          <div className="banner">
            <div>
              <strong>Who can run what.</strong> Toggle Analyze, Snapshot, Bulk,
              or Access admin per user. Changes save to the database.
            </div>
            <button
              type="button"
              className="btn btn--ghost btn--sm"
              onClick={() => {
                setAdminLoggedIn(false);
                setSavedAdminCreds(null);
                setAdminUsers([]);
                setAdminStats(null);
                clearAdminSession();
                onAdminLocked?.();
              }}
            >
              Sign out Access
            </button>
          </div>

          {adminStats && (
            <div className="stats">
              <div className="stat">
                <p className="stat__label">Users</p>
                <p className="stat__value">{adminStats.total_users}</p>
              </div>
              <div className="stat">
                <p className="stat__label">Audits</p>
                <p className="stat__value">{adminStats.total_audits}</p>
              </div>
              <div className="stat">
                <p className="stat__label">Bulk jobs</p>
                <p className="stat__value">{adminStats.total_bulk_jobs}</p>
              </div>
            </div>
          )}

          <div className="split split--access">
            <div className="panel">
              <div className="panel__head">
                <h2>Users</h2>
                <button
                  type="button"
                  className="btn btn--primary btn--sm"
                  onClick={() => setShowAddUser((v) => !v)}
                >
                  <UserPlus className="w-3.5 h-3.5" />
                  Add user
                </button>
              </div>
              <div className="panel__body access-users">
                {adminUsers.length === 0 ? (
                  <div className="empty">No users yet.</div>
                ) : (
                  <table className="data">
                    <thead>
                      <tr>
                        <th>Name</th>
                        <th>Email</th>
                        <th>Role</th>
                        <th className="tabular">This month</th>
                        <th className="tabular">Credit used</th>
                        <th />
                      </tr>
                    </thead>
                    <tbody>
                      {adminUsers.map((u) => (
                        <tr
                          key={u.id}
                          className={
                            selectedId === u.id ? "is-selected" : undefined
                          }
                          onClick={() => setSelectedId(u.id)}
                        >
                          <td>
                            <span className="domain">
                              {u.display_name || u.email.split("@")[0]}
                            </span>
                          </td>
                          <td className="muted">{u.email}</td>
                          <td>
                            <span className={roleChipClass(u.role)}>{u.role}</span>
                          </td>
                          <td className="tabular access-month-cell">
                            {quotaCell(u)}
                          </td>
                          <td className="tabular muted">
                            {formatCredit(u.credit_used_usd)}
                          </td>
                          <td className="access-row-actions">
                            <div className="row-actions">
                              <button
                                type="button"
                                className="btn btn--ghost btn--sm"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setSelectedId(u.id);
                                }}
                              >
                                Edit
                              </button>
                              <button
                                type="button"
                                className="btn btn--ghost btn--sm"
                                title="Delete user"
                                aria-label={`Delete ${u.email}`}
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleDeleteUser(u.id);
                                }}
                              >
                                <Trash2 className="w-3.5 h-3.5" />
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            </div>

            <div className="panel access-edit">
              <div className="panel__head">
                <h2>
                  {selected
                    ? selected.display_name || selected.email.split("@")[0]
                    : "Select a user"}
                </h2>
                {selected ? (
                  <span className="muted">{selected.email}</span>
                ) : null}
              </div>
              {selected ? (
                <div className="access-edit__body">
                  <div className="access-user-meta">
                    <div>
                      <p className="stat__label">Audits</p>
                      <p className="stat__value">
                        {formatQuota(
                          selected.audit_count || 0,
                          selected.monthly_audit_limit,
                        )}
                      </p>
                    </div>
                    <div>
                      <p className="stat__label">Quick</p>
                      <p className="stat__value">
                        {formatQuota(
                          selected.quick_audit_count || 0,
                          selected.monthly_quick_audit_limit,
                        )}
                      </p>
                    </div>
                    <div>
                      <p className="stat__label">Snapshots</p>
                      <p className="stat__value">
                        {formatQuota(
                          selected.snapshot_count || 0,
                          selected.monthly_snapshot_limit,
                        )}
                      </p>
                    </div>
                    <div>
                      <p className="stat__label">Credit</p>
                      <p className="stat__value">
                        {formatCredit(selected.credit_used_usd)}
                      </p>
                    </div>
                  </div>

                  <div className="access-edit__role">
                    <span className={roleChipClass(selected.role)}>
                      {selected.role}
                    </span>
                    <span className="muted">This month (UTC)</span>
                  </div>

                  <div className="field">
                    <label htmlFor="access-display-name">Display name</label>
                    <input
                      id="access-display-name"
                      value={draftName}
                      onChange={(e) => setDraftName(e.target.value)}
                      placeholder="Optional"
                    />
                  </div>

                  <div className="access-quota-fields">
                    <div className="field">
                      <label htmlFor="access-audit-limit">Audits / month</label>
                      <input
                        id="access-audit-limit"
                        type="number"
                        min={0}
                        step={1}
                        inputMode="numeric"
                        value={draftAuditLimit}
                        onChange={(e) => setDraftAuditLimit(e.target.value)}
                        placeholder="Unlimited"
                      />
                    </div>
                    <div className="field">
                      <label htmlFor="access-quick-limit">
                        Quick Audits / month
                      </label>
                      <input
                        id="access-quick-limit"
                        type="number"
                        min={0}
                        step={1}
                        inputMode="numeric"
                        value={draftQuickLimit}
                        onChange={(e) => setDraftQuickLimit(e.target.value)}
                        placeholder="Unlimited"
                      />
                    </div>
                    <div className="field">
                      <label htmlFor="access-snapshot-limit">
                        Snapshots / month
                      </label>
                      <input
                        id="access-snapshot-limit"
                        type="number"
                        min={0}
                        step={1}
                        inputMode="numeric"
                        value={draftSnapshotLimit}
                        onChange={(e) => setDraftSnapshotLimit(e.target.value)}
                        placeholder="Unlimited"
                      />
                    </div>
                  </div>
                  <p className="profile-hint">
                    Blank = unlimited. 0 = blocked. Reuses don’t count. Resets
                    each UTC month.
                  </p>

                  <p className="access-edit__section-label">Modules</p>
                  <div className="perm-grid">
                    {(
                      [
                        ["analyze", "Analyze", "Full Audit · SEO · Speed"],
                        [
                          "quick_audit",
                          "Quick Audit",
                          "4-slide Quick Audit deck",
                        ],
                        ["snapshot", "Snapshot", "Pull, review, approve"],
                        ["bulk", "Bulk Audit", "CSV batch jobs"],
                        ["access", "Access admin", "Manage users"],
                      ] as const
                    ).map(([key, title, sub]) => (
                      <label className="perm" key={key}>
                        <span className="perm__copy">
                          <strong>{title}</strong>
                          <span>{sub}</span>
                        </span>
                        <span className="toggle">
                          <input
                            type="checkbox"
                            checked={draftPerms[key]}
                            onChange={() => togglePerm(key)}
                          />
                          <span className="toggle__track" />
                        </span>
                      </label>
                    ))}
                  </div>

                  <div className="access-save-row">
                    <button
                      type="button"
                      className="btn btn--primary"
                      onClick={handleSavePermissions}
                      disabled={savingPerms}
                    >
                      {savingPerms ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : null}
                      Save access
                    </button>
                  </div>
                </div>
              ) : (
                <div className="empty">Pick a user to edit permissions.</div>
              )}
            </div>
          </div>

          {showAddUser && (
            <div className="panel">
              <div className="panel__head">
                <h2>Add user</h2>
                <button
                  type="button"
                  className="btn btn--ghost btn--sm"
                  onClick={() => setShowAddUser(false)}
                >
                  Close
                </button>
              </div>
              <form className="form-grid form-grid--2" onSubmit={handleAdminCreate}>
                <div className="field">
                  <label htmlFor="newName">Name</label>
                  <input
                    id="newName"
                    value={adminName}
                    onChange={(e) => setAdminName(e.target.value)}
                    placeholder="Full name"
                  />
                </div>
                <div className="field">
                  <label htmlFor="newEmail">Email</label>
                  <input
                    id="newEmail"
                    type="email"
                    value={adminEmail}
                    onChange={(e) => setAdminEmail(e.target.value)}
                    placeholder="name@company.com"
                    required
                  />
                </div>
                <div className="field">
                  <label htmlFor="newPass">Temp password</label>
                  <input
                    id="newPass"
                    type="text"
                    value={adminPass}
                    onChange={(e) => setAdminPass(e.target.value)}
                    placeholder="Temporary password"
                    required
                  />
                </div>
                <div className="field">
                  <label htmlFor="newRole">Starting access</label>
                  <select
                    id="newRole"
                    value={adminPreset}
                    onChange={(e) => setAdminPreset(e.target.value)}
                  >
                    <option value="analyze_only">Analyze only</option>
                    <option value="quick_only">Quick Audit only</option>
                    <option value="operator">
                      Operator (Analyze + Quick + Snapshot + Bulk)
                    </option>
                    <option value="access_admin">Access admin</option>
                  </select>
                </div>
                <div className="field">
                  <label htmlFor="newAuditLimit">Audit / month</label>
                  <input
                    id="newAuditLimit"
                    type="number"
                    min={0}
                    step={1}
                    inputMode="numeric"
                    value={adminAuditLimit}
                    onChange={(e) => setAdminAuditLimit(e.target.value)}
                    placeholder="Unlimited"
                  />
                </div>
                <div className="field">
                  <label htmlFor="newQuickLimit">Quick Audit / month</label>
                  <input
                    id="newQuickLimit"
                    type="number"
                    min={0}
                    step={1}
                    inputMode="numeric"
                    value={adminQuickLimit}
                    onChange={(e) => setAdminQuickLimit(e.target.value)}
                    placeholder="Unlimited"
                  />
                </div>
                <div className="field">
                  <label htmlFor="newSnapshotLimit">Snapshot / month</label>
                  <input
                    id="newSnapshotLimit"
                    type="number"
                    min={0}
                    step={1}
                    inputMode="numeric"
                    value={adminSnapshotLimit}
                    onChange={(e) => setAdminSnapshotLimit(e.target.value)}
                    placeholder="Unlimited"
                  />
                </div>
                <div style={{ gridColumn: "1 / -1" }}>
                  <button type="submit" className="btn btn--primary">
                    Create user
                  </button>
                </div>
              </form>
            </div>
          )}

          {adminStatus && (
            <p className="text-sm" style={{ color: "var(--color-hive-dark)" }}>
              {adminStatus}
            </p>
          )}
        </div>
      )}
    </motion.div>
  );
}
