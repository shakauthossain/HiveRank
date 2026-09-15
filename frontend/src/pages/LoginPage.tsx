import React, { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { Loader2 } from "lucide-react";
import api, { setAuthToken, isAuthenticated } from "../api";
import { setAdminSession } from "../adminSession";
import HiveMark from "../components/HiveMark";

interface LoginPageProps {
  onOperatorLogin: () => void;
  onAdminLogin: () => void;
}

export default function LoginPage({
  onOperatorLogin,
  onAdminLogin,
}: LoginPageProps) {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const nextPath = searchParams.get("next") || "/";

  const finishOperator = () => {
    onOperatorLogin();
    navigate(nextPath.startsWith("/admin") ? "/" : nextPath, { replace: true });
  };

  const finishAdmin = () => {
    onAdminLogin();
    navigate("/admin", { replace: true });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      try {
        const response = await api.post(
          `/token?email=${encodeURIComponent(email)}&password=${encodeURIComponent(password)}`,
        );
        setAuthToken(response.data.access_token);
        finishOperator();
        return;
      } catch {
        /* not an operator — try superadmin */
      }

      try {
        await api.get("/admin/stats", {
          auth: { username: email, password },
        });
        setAdminSession({ user: email, pass: password });
        finishAdmin();
        return;
      } catch {
        setError("Incorrect email or password");
      }
    } finally {
      setLoading(false);
    }
  };

  if (isAuthenticated()) {
    return (
    <div className="auth-page">
      <div className="auth-card">
        <HiveMark to="/" size="sm" />
        <h1>Already signed in</h1>
        <p className="sub">You’re on the operator dashboard.</p>
        <Link className="btn btn--primary btn--block" to="/">
          Go to dashboard
        </Link>
      </div>
    </div>
    );
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <HiveMark to="/" size="sm" />
        <h1>Sign in</h1>
        <p className="sub">
          Operators unlock audits, snapshots, and bulk. Superadmin unlocks
          Access (user management). Same form for both.
        </p>

        <form className="stack" onSubmit={handleSubmit}>
          <div className="field">
            <label htmlFor="login-email">Email</label>
            <input
              id="login-email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="name@company.com"
              autoComplete="username"
              required
            />
          </div>
          <div className="field">
            <label htmlFor="login-password">Password</label>
            <input
              id="login-password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              autoComplete="current-password"
              required
            />
          </div>
          {error && (
            <p
              style={{
                color: "var(--color-fail)",
                fontSize: "0.8125rem",
                margin: 0,
              }}
            >
              {error}
            </p>
          )}
          <button
            className="btn btn--primary btn--block"
            type="submit"
            disabled={loading}
          >
            {loading ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              "Continue"
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
