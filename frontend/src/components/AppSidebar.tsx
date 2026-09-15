import React from "react";
import { NavLink, useLocation } from "react-router-dom";
import { Activity, FileStack, LayoutList, Shield, UserRound, Zap } from "lucide-react";
import HiveMark from "./HiveMark";

export type NavPermissions = {
  analyze: boolean;
  snapshot: boolean;
  bulk: boolean;
  quick_audit: boolean;
  access: boolean;
};

interface AppSidebarProps {
  onRunTest: () => void;
  /** Show Access after SA unlock or user has can_access */
  showAccess?: boolean;
  /** Show Profile when an operator is signed in */
  showProfile?: boolean;
  permissions?: NavPermissions;
}

const DEFAULT_PERMS: NavPermissions = {
  analyze: true,
  snapshot: true,
  bulk: true,
  quick_audit: true,
  access: false,
};

export default function AppSidebar({
  onRunTest,
  showAccess = false,
  showProfile = false,
  permissions = DEFAULT_PERMS,
}: AppSidebarProps) {
  const { pathname } = useLocation();
  const auditsActive =
    (pathname === "/" || pathname.startsWith("/analyze")) &&
    !pathname.startsWith("/quick-audit");
  const quickActive = pathname.startsWith("/quick-audit");
  const perms = { ...DEFAULT_PERMS, ...permissions };

  return (
    <aside className="sidebar" id="sidebar">
      <HiveMark to="/" size="sm" />

      <nav className="sidebar__nav" aria-label="Main">
        {perms.analyze ? (
          <NavLink
            to="/"
            end
            className={() => `nav-link${auditsActive ? " is-active" : ""}`}
          >
            <Activity strokeWidth={1.5} />
            Audits
          </NavLink>
        ) : null}
        {perms.quick_audit ? (
          <NavLink
            to="/quick-audit"
            className={() => `nav-link${quickActive ? " is-active" : ""}`}
          >
            <Zap strokeWidth={1.5} />
            Quick Audit
          </NavLink>
        ) : null}
        {perms.snapshot ? (
          <NavLink
            to="/snapshot"
            className={({ isActive }) =>
              `nav-link${isActive ? " is-active" : ""}`
            }
          >
            <FileStack strokeWidth={1.5} />
            Snapshots
          </NavLink>
        ) : null}
        {perms.bulk ? (
          <NavLink
            to="/bulk-audit"
            className={({ isActive }) =>
              `nav-link${isActive ? " is-active" : ""}`
            }
          >
            <LayoutList strokeWidth={1.5} />
            Bulk Audit
          </NavLink>
        ) : null}
        {showAccess ? (
          <NavLink
            to="/admin"
            className={({ isActive }) =>
              `nav-link${isActive ? " is-active" : ""}`
            }
          >
            <Shield strokeWidth={1.5} />
            Access
          </NavLink>
        ) : null}
        {showProfile ? (
          <NavLink
            to="/profile"
            className={({ isActive }) =>
              `nav-link${isActive ? " is-active" : ""}`
            }
          >
            <UserRound strokeWidth={1.5} />
            Profile
          </NavLink>
        ) : null}
      </nav>

      <div className="sidebar__cta">
        <button type="button" className="btn btn--primary" onClick={onRunTest}>
          Run a test
        </button>
      </div>
    </aside>
  );
}
