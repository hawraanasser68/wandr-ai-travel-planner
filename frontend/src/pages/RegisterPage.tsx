import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { register } from "../api/client";
import { useAuthStore } from "../store/auth";

export default function RegisterPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [webhookEmail, setWebhookEmail] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const { setAuth } = useAuthStore();
  const navigate = useNavigate();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const { access_token } = await register(email, password, webhookEmail || undefined);
      setAuth(access_token, email);
      navigate("/chat");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Registration failed");
    } finally {
      setLoading(false);
    }
  }

  const inputClass = "w-full rounded-xl px-4 py-2.5 text-sm text-white placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition";
  const inputStyle = { background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.1)" };
  const labelClass = "block text-sm font-medium mb-1.5";
  const labelStyle = { color: "#94a3b8" };

  return (
    <div className="min-h-screen flex items-center justify-center relative overflow-hidden"
         style={{ background: "linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #0f172a 100%)" }}>

      <div className="absolute top-1/4 left-1/3 w-96 h-96 rounded-full pointer-events-none"
           style={{ background: "radial-gradient(circle, rgba(99,102,241,0.18) 0%, transparent 70%)" }} />
      <div className="absolute bottom-1/3 right-1/4 w-72 h-72 rounded-full pointer-events-none"
           style={{ background: "radial-gradient(circle, rgba(139,92,246,0.12) 0%, transparent 70%)" }} />

      <div className="relative w-full max-w-md mx-4">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl shadow-2xl mb-4"
               style={{ background: "linear-gradient(135deg, #6366f1, #8b5cf6)" }}>
            <span className="text-white text-2xl">✈</span>
          </div>
          <h1 className="text-3xl font-bold text-white tracking-tight">Create account</h1>
          <p className="text-slate-400 mt-1.5 text-sm">Start planning your dream trip today</p>
        </div>

        <div className="rounded-2xl p-8 shadow-2xl"
             style={{ background: "rgba(255,255,255,0.05)", backdropFilter: "blur(20px)", border: "1px solid rgba(255,255,255,0.1)" }}>

          {error && (
            <div className="rounded-xl px-4 py-3 mb-5 text-sm flex items-center gap-2"
                 style={{ background: "rgba(239,68,68,0.12)", border: "1px solid rgba(239,68,68,0.25)", color: "#fca5a5" }}>
              <span>⚠</span> {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className={labelClass} style={labelStyle}>Email address</label>
              <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com" className={inputClass} style={inputStyle} />
            </div>
            <div>
              <label className={labelClass} style={labelStyle}>
                Password <span style={{ color: "#475569", fontWeight: 400 }}>(min 8 chars)</span>
              </label>
              <input type="password" required minLength={8} value={password} onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••" className={inputClass} style={inputStyle} />
            </div>
            <div>
              <label className={labelClass} style={labelStyle}>
                Trip summary email{" "}
                <span style={{ color: "#475569", fontWeight: 400 }}>(optional)</span>
              </label>
              <input type="email" value={webhookEmail} onChange={(e) => setWebhookEmail(e.target.value)}
                placeholder="receive your plans by email" className={inputClass} style={inputStyle} />
            </div>
            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 rounded-xl font-semibold text-white text-sm transition-all hover:opacity-90 disabled:opacity-50 mt-1"
              style={{ background: "linear-gradient(135deg, #6366f1, #4f46e5)" }}
            >
              {loading ? "Creating account…" : "Create account →"}
            </button>
          </form>

          <p className="text-center text-sm mt-6" style={{ color: "#64748b" }}>
            Already have an account?{" "}
            <Link to="/login" className="font-medium transition hover:opacity-80" style={{ color: "#818cf8" }}>
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
