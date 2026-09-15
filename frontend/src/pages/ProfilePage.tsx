import React, { useEffect, useState } from "react";
import { Loader2, Lock, UserRound } from "lucide-react";
import api from "../api";

interface ProfilePageProps {
  isLoggedIn: boolean;
  onAuthRequired: () => void;
  onProfileUpdated?: () => void;
}

type MeResponse = {
  email: string;
  display_name?: string | null;
  role?: string;
};

function apiErrorMessage(err: any, fallback: string) {
  const detail = err?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail[0]?.msg) return String(detail[0].msg);
  return fallback;
}

export default function ProfilePage({
  isLoggedIn,
  onAuthRequired,
  onProfileUpdated,
}: ProfilePageProps) {
  const [email, setEmail] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(true);
  const [savingName, setSavingName] = useState(false);
  const [savingPassword, setSavingPassword] = useState(false);
  const [nameMsg, setNameMsg] = useState<{ ok: boolean; text: string } | null>(
    null,
  );
  const [passwordMsg, setPasswordMsg] = useState<{
    ok: boolean;
    text: string;
  } | null>(null);

  useEffect(() => {
    if (!isLoggedIn) {
      onAuthRequired();
      return;
    }
    let cancelled = false;
    (async () => {
      setLoading(true);
      try {
        const { data } = await api.get<MeResponse>("/me");
        if (cancelled) return;
        setEmail(data.email || "");
        setDisplayName(data.display_name || "");
      } catch {
        if (!cancelled) onAuthRequired();
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- only re-fetch on login state
  }, [isLoggedIn]);

  const saveName = async (e: React.FormEvent) => {
    e.preventDefault();
    setNameMsg(null);
    setSavingName(true);
    try {
      await api.patch("/me", { display_name: displayName.trim() });
      setNameMsg({ ok: true, text: "Name saved." });
      onProfileUpdated?.();
    } catch (err: any) {
      setNameMsg({
        ok: false,
        text: apiErrorMessage(err, "Could not save name."),
      });
    } finally {
      setSavingName(false);
    }
  };

  const savePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setPasswordMsg(null);
    if (newPassword.length < 5) {
      setPasswordMsg({
        ok: false,
        text: "New password must be at least 5 characters.",
      });
      return;
    }
    if (newPassword !== confirmPassword) {
      setPasswordMsg({ ok: false, text: "New passwords do not match." });
      return;
    }
    setSavingPassword(true);
    try {
      await api.patch("/me", {
        current_password: currentPassword,
        new_password: newPassword,
      });
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      setPasswordMsg({ ok: true, text: "Password updated." });
    } catch (err: any) {
      setPasswordMsg({
        ok: false,
        text: apiErrorMessage(err, "Could not update password."),
      });
    } finally {
      setSavingPassword(false);
    }
  };

  if (!isLoggedIn) return null;

  if (loading) {
    return (
      <div className="profile-page">
        <div className="profile-page__loading panel">
          <Loader2 className="w-5 h-5 animate-spin" />
          Loading profile…
        </div>
      </div>
    );
  }

  return (
    <div className="profile-page">
      <section className="profile-card panel">
        <header className="profile-card__head">
          <span className="profile-card__icon" aria-hidden>
            <UserRound strokeWidth={1.75} />
          </span>
          <div>
            <h2>Account</h2>
            <p>Your sign-in email stays fixed. Update how your name shows.</p>
          </div>
        </header>

        <form className="profile-card__form" onSubmit={saveName}>
          <div className="field">
            <label htmlFor="profile-email">Email</label>
            <input
              id="profile-email"
              type="email"
              value={email}
              readOnly
              disabled
              aria-readonly="true"
            />
            <p className="profile-hint">
              Ask Access if you need a different login address.
            </p>
          </div>

          <div className="field">
            <label htmlFor="profile-name">Display name</label>
            <input
              id="profile-name"
              type="text"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              placeholder="How you appear in the app"
              autoComplete="name"
              maxLength={80}
            />
          </div>

          <div className="profile-card__footer">
            {nameMsg ? (
              <p
                className={`profile-msg${nameMsg.ok ? " is-ok" : " is-err"}`}
                role="status"
              >
                {nameMsg.text}
              </p>
            ) : (
              <span className="profile-card__spacer" />
            )}
            <button
              type="submit"
              className="btn btn--primary"
              disabled={savingName}
            >
              {savingName ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" /> Saving…
                </>
              ) : (
                "Save name"
              )}
            </button>
          </div>
        </form>
      </section>

      <section className="profile-card panel">
        <header className="profile-card__head">
          <span className="profile-card__icon" aria-hidden>
            <Lock strokeWidth={1.75} />
          </span>
          <div>
            <h2>Password</h2>
            <p>Use at least 5 characters. You’ll stay signed in after updating.</p>
          </div>
        </header>

        <form className="profile-card__form" onSubmit={savePassword}>
          <div className="field">
            <label htmlFor="profile-current-pw">Current password</label>
            <input
              id="profile-current-pw"
              type="password"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              autoComplete="current-password"
              required
            />
          </div>

          <div className="field">
            <label htmlFor="profile-new-pw">New password</label>
            <input
              id="profile-new-pw"
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              autoComplete="new-password"
              required
              minLength={5}
            />
          </div>

          <div className="field">
            <label htmlFor="profile-confirm-pw">Confirm new password</label>
            <input
              id="profile-confirm-pw"
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              autoComplete="new-password"
              required
              minLength={5}
            />
          </div>

          <div className="profile-card__footer">
            {passwordMsg ? (
              <p
                className={`profile-msg${passwordMsg.ok ? " is-ok" : " is-err"}`}
                role="status"
              >
                {passwordMsg.text}
              </p>
            ) : (
              <span className="profile-card__spacer" />
            )}
            <button
              type="submit"
              className="btn btn--primary"
              disabled={savingPassword}
            >
              {savingPassword ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" /> Updating…
                </>
              ) : (
                "Update password"
              )}
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}
