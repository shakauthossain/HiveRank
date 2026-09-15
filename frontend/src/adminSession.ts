/** Session helpers for superadmin Access unlock (HTTP Basic, not JWT). */

const UNLOCK_KEY = "hiverank_admin_unlocked";
const CREDS_KEY = "hiverank_admin_creds";

export type AdminCreds = { user: string; pass: string };

export function isAdminUnlocked(): boolean {
  try {
    return sessionStorage.getItem(UNLOCK_KEY) === "1";
  } catch {
    return false;
  }
}

export function getAdminCreds(): AdminCreds | null {
  try {
    const raw = sessionStorage.getItem(CREDS_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as AdminCreds;
    if (parsed?.user && parsed?.pass) return parsed;
  } catch {
    /* ignore */
  }
  return null;
}

export function setAdminSession(creds: AdminCreds): void {
  try {
    sessionStorage.setItem(UNLOCK_KEY, "1");
    sessionStorage.setItem(CREDS_KEY, JSON.stringify(creds));
  } catch {
    /* ignore */
  }
}

export function clearAdminSession(): void {
  try {
    sessionStorage.removeItem(UNLOCK_KEY);
    sessionStorage.removeItem(CREDS_KEY);
  } catch {
    /* ignore */
  }
}
