import React, { useState } from "react";
import { motion } from "framer-motion";
import { Loader2 } from "lucide-react";
import api, { setAuthToken } from "../api";
import HiveMark from "./HiveMark";

interface AuthModalProps {
  isOpen: boolean;
  onSuccess: () => void;
  onClose?: () => void;
}

export default function AuthModal({
  isOpen,
  onSuccess,
  onClose,
}: AuthModalProps) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const response = await api.post(
        `/token?email=${email}&password=${password}`,
      );
      setAuthToken(response.data.access_token);
      onSuccess();
    } catch (err: any) {
      setError(err.response?.data?.detail || "Login failed");
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center p-4"
      style={{ background: "rgba(11, 18, 32, 0.5)", backdropFilter: "blur(6px)" }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose?.();
      }}
    >
      <motion.div
        initial={{ opacity: 0, scale: 0.97 }}
        animate={{ opacity: 1, scale: 1 }}
        className="auth-card"
      >
        <HiveMark to="/" size="sm" />
        <h1>Sign in</h1>
        <p className="sub">
          Staff and clients with access. Dashboard unlocks audits, snapshots,
          and bulk.
        </p>

        <form className="stack" onSubmit={handleSubmit}>
          <div className="field">
            <label htmlFor="hr-email">Email</label>
            <input
              id="hr-email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="name@company.com"
              required
            />
          </div>
          <div className="field">
            <label htmlFor="hr-password">Password</label>
            <input
              id="hr-password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              required
            />
          </div>
          {error && (
            <p style={{ color: "var(--color-fail)", fontSize: "0.8125rem", margin: 0 }}>
              {error}
            </p>
          )}
          <button className="btn btn--primary btn--block" type="submit" disabled={loading}>
            {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : "Continue to dashboard"}
          </button>
        </form>
      </motion.div>
    </div>
  );
}
