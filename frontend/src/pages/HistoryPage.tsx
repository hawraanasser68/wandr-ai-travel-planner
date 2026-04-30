import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getRuns, AgentRun } from "../api/client";
import { useChatStore } from "../store/chatStore";
import Layout from "../components/Layout";
import MarkdownRenderer from "../components/MarkdownRenderer";

const TOOL_LABELS: Record<string, string> = {
  ml_classifier: "Classifier",
  rag_retriever: "Knowledge Base",
  weather:       "Weather",
  currency:      "Exchange Rate",
};

const TOOL_ICONS: Record<string, string> = {
  ml_classifier: "🧠",
  rag_retriever: "📚",
  weather:       "🌤",
  currency:      "💱",
};

export default function HistoryPage() {
  const [runs, setRuns] = useState<AgentRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [error, setError] = useState("");

  const { clearMessages, addMessage } = useChatStore();
  const navigate = useNavigate();

  useEffect(() => {
    getRuns()
      .then(setRuns)
      .catch(() => setError("Could not load history."))
      .finally(() => setLoading(false));
  }, []);

  function restoreRun(run: AgentRun) {
    clearMessages();
    addMessage({ role: "user", content: run.query });
    addMessage({ role: "assistant", content: run.response ?? "", toolsUsed: run.tools_used });
    navigate("/chat");
  }

  return (
    <Layout>
      <div className="max-w-3xl mx-auto px-4 py-8">

        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold text-slate-800 tracking-tight">Past Trips</h1>
            <p className="text-sm text-slate-400 mt-1">Click any plan to restore it in the chat</p>
          </div>
          <button
            onClick={() => navigate("/chat")}
            className="flex items-center gap-1.5 text-sm font-medium text-indigo-600 hover:text-indigo-700 transition px-3 py-1.5 rounded-lg hover:bg-indigo-50"
          >
            ← Back to chat
          </button>
        </div>

        {loading && (
          <div className="text-center py-16">
            <div className="inline-flex items-center gap-2 text-slate-400 text-sm">
              <span className="animate-spin">⚙</span> Loading your trips…
            </div>
          </div>
        )}

        {error && (
          <div className="rounded-xl px-4 py-3 text-sm font-medium"
               style={{ background: "#fff1f2", border: "1px solid #fecdd3", color: "#be123c" }}>
            ⚠ {error}
          </div>
        )}

        {!loading && runs.length === 0 && !error && (
          <div className="text-center py-20">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl shadow-lg mb-5"
                 style={{ background: "linear-gradient(135deg, #6366f1, #8b5cf6)" }}>
              <span className="text-3xl">🗺</span>
            </div>
            <p className="text-lg font-semibold text-slate-700">No trips yet</p>
            <p className="text-sm text-slate-400 mt-1 mb-6">Your saved plans will appear here.</p>
            <button
              onClick={() => navigate("/chat")}
              className="text-white px-5 py-2.5 rounded-xl text-sm font-semibold transition hover:opacity-90"
              style={{ background: "linear-gradient(135deg, #4f46e5, #7c3aed)" }}
            >
              Plan your first trip →
            </button>
          </div>
        )}

        <div className="space-y-3">
          {runs.map((run) => (
            <div key={run.id}
              className="bg-white border border-slate-100 rounded-2xl shadow-sm overflow-hidden hover:shadow-md transition-shadow">

              <div className="flex items-start justify-between px-5 py-4 gap-3">
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold text-slate-800 truncate">{run.query}</p>
                  <div className="flex flex-wrap items-center gap-2 mt-1.5">
                    <span className="text-xs text-slate-400">
                      {new Date(run.created_at).toLocaleString(undefined, {
                        month: "short", day: "numeric", hour: "2-digit", minute: "2-digit"
                      })}
                    </span>
                    {run.tools_used.map((t) => (
                      <span key={t}
                        className="inline-flex items-center gap-1 text-xs rounded-full px-2 py-0.5 font-medium"
                        style={{ background: "#eef2ff", color: "#4f46e5" }}>
                        {TOOL_ICONS[t] ?? "🔧"} {TOOL_LABELS[t] ?? t}
                      </span>
                    ))}
                  </div>
                </div>
                <div className="flex gap-2 flex-shrink-0">
                  <button
                    onClick={() => restoreRun(run)}
                    className="text-xs font-semibold text-indigo-600 px-3 py-1.5 rounded-lg transition"
                    style={{ background: "#eef2ff" }}
                    onMouseEnter={(e) => (e.currentTarget.style.background = "#e0e7ff")}
                    onMouseLeave={(e) => (e.currentTarget.style.background = "#eef2ff")}
                  >
                    Restore
                  </button>
                  <button
                    onClick={() => setExpanded(expanded === run.id ? null : run.id)}
                    className="text-xs font-medium text-slate-500 px-3 py-1.5 rounded-lg bg-slate-50 hover:bg-slate-100 transition"
                  >
                    {expanded === run.id ? "Hide" : "View"}
                  </button>
                </div>
              </div>

              {expanded === run.id && run.response && (
                <div className="border-t border-slate-100 px-5 py-4 text-sm text-slate-700 max-h-96 overflow-y-auto chat-scroll"
                     style={{ background: "#fafafa" }}>
                  <MarkdownRenderer content={run.response} />
                </div>
              )}
            </div>
          ))}
        </div>

      </div>
    </Layout>
  );
}
