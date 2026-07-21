"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { authApi } from "@/app/api/api";
import { useAuthStore } from "@/app/stores/authStore";
import { Loader2, Terminal, UserPlus, LogIn } from "lucide-react";

type Mode = "login" | "register";

export default function LoginPage() {
  const router = useRouter();
  const setToken = useAuthStore((s) => s.setToken);
  const [mode, setMode] = useState<Mode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res = await authApi.login(email, password);
      setToken(res.access_token);
      router.push("/ai");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Authentication failed");
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setSuccess(null);
    try {
      await authApi.register({ email, password, full_name: fullName || undefined });
      setSuccess("Account created. Logging in...");
      const res = await authApi.login(email, password);
      setToken(res.access_token);
      router.push("/ai");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Registration failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-shell">
      <div className="login-panel">
        <div className="login-header">
          <Terminal size={20} strokeWidth={1.5} className="login-icon" />
          <span className="login-wordmark">OPSORA</span>
        </div>
        <p className="login-sub">Agent Control System</p>

        {/* Tab toggle */}
        <div style={{ display: "flex", gap: "2px", marginBottom: "18px", background: "var(--s1)", borderRadius: "var(--r-sm)", padding: "2px" }}>
          <button
            type="button"
            onClick={() => { setMode("login"); setError(null); setSuccess(null); }}
            style={{
              flex: 1, padding: "6px 0", fontSize: "12px", fontWeight: 600,
              fontFamily: "var(--mono)", letterSpacing: "0.5px",
              background: mode === "login" ? "var(--s3)" : "transparent",
              color: mode === "login" ? "var(--t1)" : "var(--t3)",
              border: "none", borderRadius: "3px", cursor: "pointer",
              transition: "all 0.1s",
            }}
          >
            LOGIN
          </button>
          <button
            type="button"
            onClick={() => { setMode("register"); setError(null); setSuccess(null); }}
            style={{
              flex: 1, padding: "6px 0", fontSize: "12px", fontWeight: 600,
              fontFamily: "var(--mono)", letterSpacing: "0.5px",
              background: mode === "register" ? "var(--s3)" : "transparent",
              color: mode === "register" ? "var(--t1)" : "var(--t3)",
              border: "none", borderRadius: "3px", cursor: "pointer",
              transition: "all 0.1s",
            }}
          >
            REGISTER
          </button>
        </div>

        {mode === "login" ? (
          <form onSubmit={handleLogin} className="login-form">
            <div className="login-field">
              <label className="data-label">email</label>
              <input
                className="input input-mono"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="operator@opsora.dev"
                required
                autoFocus
              />
            </div>
            <div className="login-field">
              <label className="data-label">password</label>
              <input
                className="input input-mono"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
                required
              />
            </div>
            {error && <div className="tag tag-err" role="alert">{error}</div>}
            <button
              type="submit"
              disabled={loading || !email || !password}
              className="btn btn-primary"
              style={{ width: "100%" }}
            >
              {loading ? <Loader2 size={14} className="anim-spin" /> : <LogIn size={14} />}
              {loading ? "Authenticating..." : "Unlock"}
            </button>
          </form>
        ) : (
          <form onSubmit={handleRegister} className="login-form">
            <div className="login-field">
              <label className="data-label">full name</label>
              <input
                className="input input-mono"
                type="text"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                placeholder="Your name"
                autoFocus
              />
            </div>
            <div className="login-field">
              <label className="data-label">email</label>
              <input
                className="input input-mono"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@company.com"
                required
              />
            </div>
            <div className="login-field">
              <label className="data-label">password</label>
              <input
                className="input input-mono"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="min 8 characters"
                required
                minLength={8}
              />
            </div>
            {error && <div className="tag tag-err" role="alert">{error}</div>}
            {success && <div className="tag tag-ok" role="status">{success}</div>}
            <button
              type="submit"
              disabled={loading || !email || !password || password.length < 8}
              className="btn btn-primary"
              style={{ width: "100%" }}
            >
              {loading ? <Loader2 size={14} className="anim-spin" /> : <UserPlus size={14} />}
              {loading ? "Creating account..." : "Create Account"}
            </button>
          </form>
        )}

        <p className="login-footer">
          Opsora Memori · restricted access
        </p>
      </div>
    </div>
  );
}
