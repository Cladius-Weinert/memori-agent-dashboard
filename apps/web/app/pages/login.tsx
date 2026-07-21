/* Login page — email/password form */
"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { authApi } from "@/app/api/api";
import { useAuthStore } from "@/app/stores/authStore";
import { Lock, Loader2 } from "lucide-react";

export default function LoginPage() {
  const router = useRouter();
  const setToken = useAuthStore((s) => s.setToken);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handle = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res = await authApi.login(email, password);
      setToken(res.access_token);
      router.push("/");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex items-center justify-center min-h-screen bg-slate-950">
      <div className="w-full max-w-sm p-8 bg-slate-900 rounded-xl border border-slate-800 shadow-xl">
        <div className="flex items-center justify-center mb-6 gap-3">
          <Lock className="text-brand-500" size={24} />
          <h1 className="text-xl font-bold">Memori Dashboard</h1>
        </div>
        <form onSubmit={handle} className="space-y-4">
          <div>
            <label className="block text-sm text-slate-400 mb-1">Email</label>
            <input
              className="w-full px-3 py-2 bg-slate-800 rounded border border-slate-700 text-sm"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>
          <div>
            <label className="block text-sm text-slate-400 mb-1">Password</label>
            <input
              className="w-full px-3 py-2 bg-slate-800 rounded border border-slate-700 text-sm"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>
          {error && <p className="text-red-400 text-sm">{error}</p>}
          <button
            type="submit"
            disabled={loading || !email || !password}
            className="w-full py-2 bg-brand-600 hover:bg-brand-700 rounded font-medium text-sm disabled:opacity-50 flex items-center justify-center gap-2"
          >
            {loading && <Loader2 className="animate-spin" size={16} />}
            Sign in
          </button>
        </form>
      </div>
    </div>
  );
}