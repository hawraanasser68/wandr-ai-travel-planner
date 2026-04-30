import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { login } from "../api/client";
import { useAuthStore } from "../store/auth";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const { setAuth } = useAuthStore();
  const navigate = useNavigate();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const { access_token } = await login(email, password);
      setAuth(access_token, email);
      navigate("/chat");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center relative overflow-hidden"
         style={{ background: "linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #0f172a 100%)" }}>

      {/* Ambient glow blobs */}
      <div className="absolute top-1/4 left-1/3 w-96 h-96 rounded-full pointer-events-none"
           style={{ background: "radial-gradient(circle, rgba(99,102,241,0.18) 0%, transparent 70%)" }} />
      <div className="absolute bottom-1/4 right-1/3 w-80 h-80 rounded-full pointer-events-none"
           style={{ background: "radial-gradient(circle, rgba(6,182,212,0.12) 0%, transparent 70%)" }} />

      <div className="relative w-full max-w-md mx-4">
        {/* Brand */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl shadow-2xl mb-4"
               style={{ background: "linear-gradient(135deg, #6366f1, #8b5cf6)" }}>
            <span className="text-white text-2xl">✈</span>
          </div>
          <h1 className="text-3xl font-bold text-white tracking-tight">Welcome back</h1>
          <p className="text-slate-400 mt-1.5 text-sm">Sign in to plan your next adventure</p>
        </div>

        {/* Glass card */}
        <div className="rounded-2xl p-8 shadow-2xl"
             style={{ background: "rgba(255,255,255,0.05)", backdropFilter: "blur(20px)", border: "1px solid rgba(255,255,255,0.1)" }}>

          {error && (
            <div className="rounded-xl px-4 py-3 mb-5 text-sm flex items-center gap-2"
                 style={{ background: "rgba(239,68,68,0.12)", border: "1px solid rgba(239,68,68,0.25)", color: "#fca5a5" }}>
              <span>⚠</span> {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="block text-sm font-medium mb-1.5" style={{ color: "#94a3b8" }}>Email address</label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                className="w-full rounded-xl px-4 py-2.5 text-sm text-white placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition"
                style={{ background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.1)" }}
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1.5" style={{ color: "#94a3b8" }}>Password</label>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full rounded-xl px-4 py-2.5 text-sm text-white placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition"
                style={{ background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.1)" }}
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 rounded-xl font-semibold text-white text-sm transition-all hover:opacity-90 disabled:opacity-50 mt-2"
              style={{ background: "linear-gradient(135deg, #6366f1, #4f46e5)" }}
            >
              {loading ? "Signing in…" : "Sign in →"}
            </button>
          </form>

          <p className="text-center text-sm mt-6" style={{ color: "#64748b" }}>
            No account?{" "}
            <Link to="/register" className="font-medium transition hover:opacity-80" style={{ color: "#818cf8" }}>
              Create one
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
