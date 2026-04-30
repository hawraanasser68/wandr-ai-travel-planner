import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { streamChat, geocode, GeoResult } from "../api/client";
import { useChatStore } from "../store/chatStore";
import { useAuthStore } from "../store/auth";
import Layout from "../components/Layout";
import MarkdownRenderer from "../components/MarkdownRenderer";
import DestinationCards, { extractDestinations } from "../components/DestinationCards";
import MapPanel, { UserLocation } from "../components/MapPanel";
import BudgetCalculator from "../components/BudgetCalculator";
import FlightInfo from "../components/FlightInfo";

const TOOL_LABELS: Record<string, string> = {
  ml_classifier: "Style Classifier",
  rag_retriever: "Knowledge Base",
  weather:       "Live Weather",
  currency:      "Exchange Rate",
};

const TOOL_ICONS: Record<string, string> = {
  ml_classifier: "🧠",
  rag_retriever: "📚",
  weather:       "🌤",
  currency:      "💱",
};

const SUGGESTIONS = [
  { icon: "🏖", text: "Plan a relaxing 7-day beach holiday in Bali" },
  { icon: "🏔", text: "Adventure trip to Queenstown or Patagonia — which is better?" },
  { icon: "💎", text: "Luxury 5-night trip to Dubai or Santorini for 2 people" },
  { icon: "🏛", text: "Cultural tour of Kyoto and Florence — where to start?" },
  { icon: "💰", text: "Budget trip to Bangkok or Lisbon under $60/day" },
  { icon: "🌊", text: "Romantic getaway to the Maldives — what should I know?" },
];

export default function ChatPage() {
  const { messages, addMessage, appendToken, finalizeAssistant, clearMessages } = useChatStore();
  const token = useAuthStore((s) => s.token);
  const navigate = useNavigate();

  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [activeTools, setActiveTools] = useState<string[]>([]);
  const [error, setError] = useState("");

  const [emailOpen, setEmailOpen] = useState(false);
  const [emailValue, setEmailValue] = useState("");
  const [emailSending, setEmailSending] = useState(false);
  const [emailStatus, setEmailStatus] = useState<string>("");

  const [userLocation, setUserLocation] = useState<UserLocation | null>(null);
  const [geoCache, setGeoCache] = useState<Record<number, GeoResult[]>>({});

  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => { if (!token) navigate("/login"); }, [token, navigate]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, activeTools]);

  useEffect(() => {
    navigator.geolocation?.getCurrentPosition(
      async ({ coords: { latitude: lat, longitude: lng } }) => {
        try {
          const res = await fetch(
            `https://nominatim.openstreetmap.org/reverse?lat=${lat}&lon=${lng}&format=json`,
            { headers: { "User-Agent": "AITravelPlanner/1.0" } }
          );
          const data = await res.json();
          setUserLocation({ lat, lng, city: data.address?.country || "" });
        } catch { setUserLocation({ lat, lng }); }
      },
      () => {}
    );
  }, []);

  useEffect(() => {
    messages.forEach((msg, idx) => {
      if (msg.role === "assistant" && !msg.isStreaming && msg.content && geoCache[idx] === undefined) {
        const dests = extractDestinations(msg.content);
        setGeoCache((prev) => ({ ...prev, [idx]: [] }));
        if (dests.length > 0) {
          Promise.all(dests.map((d) => geocode(d))).then((results) => {
            setGeoCache((prev) => ({ ...prev, [idx]: results.filter(Boolean) as GeoResult[] }));
          });
        }
      }
    });
  }, [messages]); // eslint-disable-line react-hooks/exhaustive-deps

  // Derive sidebar data from the last finalized assistant message
  const lastAiIdx = messages.reduce((acc, m, i) =>
    m.role === "assistant" && !m.isStreaming && m.content ? i : acc, -1);
  const lastAiMsg = lastAiIdx >= 0 ? messages[lastAiIdx] : null;
  const lastAiGeo = lastAiIdx >= 0 ? (geoCache[lastAiIdx] ?? []) : [];
  const lastDestination = lastAiGeo[0]?.name ?? "";

  async function handleSend(query: string) {
    if (!query.trim() || streaming) return;
    setInput("");
    setError("");
    setActiveTools([]);
    setEmailOpen(false);
    setEmailStatus("");

    const history = messages
      .filter((m) => m.role === "user" || m.content.trim())
      .map((m) => ({ role: m.role, content: m.content }));
    addMessage({ role: "user", content: query });
    addMessage({ role: "assistant", content: "", isStreaming: true });
    setStreaming(true);

    const toolsThisRun: string[] = [];
    let doneCalled = false;
    try {
      for await (const chunk of streamChat(query, history)) {
        if (chunk.type === "token") appendToken(chunk.content);
        else if (chunk.type === "tool_call") { toolsThisRun.push(chunk.content); setActiveTools([...toolsThisRun]); }
        else if (chunk.type === "done") {
          finalizeAssistant([...new Set(toolsThisRun)], chunk.run_id ?? "");
          doneCalled = true;
        }
        else if (chunk.type === "error") setError(chunk.content);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      if (!doneCalled) finalizeAssistant([...new Set(toolsThisRun)], "");
      setStreaming(false);
      setActiveTools([]);
    }
  }

  function handleDestinationClick(dest: string) {
    handleSend(`Tell me more about ${dest} — what should I know before visiting?`);
  }

  async function sendEmail() {
    if (!emailValue.trim() || emailSending || !lastAiMsg?.runId) return;
    setEmailSending(true);
    try {
      const res = await fetch(`/agent/runs/${lastAiMsg.runId}/email`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}) },
        body: JSON.stringify({ email: emailValue.trim() }),
      });
      if (!res.ok) { const b = await res.json().catch(() => ({})); throw new Error(b.detail ?? "Failed"); }
      setEmailStatus(`Sent to ${emailValue.trim()}`);
      setEmailOpen(false);
      setEmailValue("");
    } catch (err: unknown) {
      setEmailStatus(err instanceof Error ? err.message : "Send failed");
    } finally {
      setEmailSending(false);
    }
  }

  return (
    <Layout>
      <div className="flex h-[calc(100vh-56px)]">

        {/* ── LEFT: Chat column ─────────────────────────────────────────────── */}
        <div className="flex-1 flex flex-col min-w-0 border-r border-slate-100">

          {/* Toolbar */}
          <div className="flex items-center justify-between px-5 py-2.5 border-b border-slate-100 bg-white/80"
               style={{ backdropFilter: "blur(12px)" }}>
            <p className="text-xs text-slate-400 hidden sm:flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 inline-block" />
              AI-powered · multi-turn · ask follow-ups anytime
              {userLocation?.city && <span className="text-indigo-500 font-medium">📍 {userLocation.city}</span>}
            </p>
            <div className="flex gap-1 ml-auto">
              <button onClick={() => navigate("/history")}
                className="text-xs text-slate-500 hover:text-indigo-600 flex items-center gap-1.5 px-3 py-1.5 rounded-lg hover:bg-indigo-50 transition font-medium">
                🕘 History
              </button>
              <button onClick={() => { clearMessages(); setGeoCache({}); setError(""); setEmailStatus(""); }}
                className="text-xs text-slate-500 hover:text-rose-500 flex items-center gap-1.5 px-3 py-1.5 rounded-lg hover:bg-rose-50 transition font-medium">
                ✕ New chat
              </button>
            </div>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto px-5 py-6 space-y-5 chat-scroll">

            {messages.length === 0 && (
              <div className="text-center mt-6">
                <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl shadow-lg mb-5"
                     style={{ background: "linear-gradient(135deg, #6366f1, #8b5cf6)" }}>
                  <span className="text-white text-3xl">🌍</span>
                </div>
                <h2 className="text-2xl font-bold text-slate-800 mb-1">Where do you want to go?</h2>
                <p className="text-sm text-slate-400 mb-8">Ask anything — I'll plan it, map it, and budget it for you.</p>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 max-w-xl mx-auto">
                  {SUGGESTIONS.map((s) => (
                    <button key={s.text} onClick={() => handleSend(s.text)}
                      className="flex items-start gap-3 text-left bg-white border border-slate-200 rounded-xl px-4 py-3 hover:border-indigo-300 hover:shadow-md transition-all group">
                      <span className="text-lg flex-shrink-0 mt-0.5">{s.icon}</span>
                      <span className="text-sm text-slate-600 group-hover:text-indigo-700 leading-snug">{s.text}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((msg, i) => (
              <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                {msg.role === "user" ? (
                  <div className="max-w-[75%] text-white rounded-2xl rounded-tr-sm px-4 py-3 text-sm leading-relaxed shadow-md"
                       style={{ background: "linear-gradient(135deg, #4f46e5, #7c3aed)" }}>
                    {msg.content}
                  </div>
                ) : (
                  <div className="w-full">
                    <div className="bg-white border border-slate-100 rounded-2xl rounded-tl-sm px-5 py-4 text-sm text-slate-700 shadow-sm">
                      {msg.isStreaming && !msg.content ? (
                        <div className="flex items-center gap-2 text-slate-400 text-xs py-1">
                          <span className="animate-spin text-indigo-500">⚙</span>
                          <span className="font-medium">Thinking…</span>
                        </div>
                      ) : (
                        <MarkdownRenderer content={msg.content} />
                      )}
                      {msg.isStreaming && msg.content && (
                        <span className="inline-block w-0.5 h-4 bg-indigo-400 ml-0.5 animate-pulse rounded" />
                      )}
                      {!msg.isStreaming && msg.toolsUsed && msg.toolsUsed.length > 0 && (
                        <div className="flex flex-wrap gap-1.5 mt-3 pt-3 border-t border-slate-100">
                          {msg.toolsUsed.map((t) => (
                            <span key={t} className="inline-flex items-center gap-1 text-xs rounded-full px-2.5 py-1 font-medium"
                                  style={{ background: "#eef2ff", color: "#4f46e5" }}>
                              {TOOL_ICONS[t] ?? "🔧"} {TOOL_LABELS[t] ?? t}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                    {!msg.isStreaming && msg.content && (
                      <DestinationCards markdown={msg.content} onSelect={handleDestinationClick} />
                    )}
                  </div>
                )}
              </div>
            ))}

            {/* Live tool indicator */}
            {streaming && activeTools.length > 0 && (
              <div className="flex justify-start">
                <div className="flex items-center gap-2 rounded-full px-4 py-2 text-xs font-medium shadow-sm"
                     style={{ background: "#fffbeb", border: "1px solid #fde68a", color: "#92400e" }}>
                  <span className="animate-spin">⚙</span>
                  {TOOL_ICONS[activeTools[activeTools.length - 1]] ?? "🔧"}{" "}
                  {TOOL_LABELS[activeTools[activeTools.length - 1]] ?? activeTools[activeTools.length - 1]}
                </div>
              </div>
            )}

            {error && (
              <div className="rounded-xl px-4 py-3 text-sm font-medium"
                   style={{ background: "#fff1f2", border: "1px solid #fecdd3", color: "#be123c" }}>
                ⚠ {error}
              </div>
            )}

            <div ref={bottomRef} />
          </div>

          {/* Input bar */}
          <form onSubmit={(e) => { e.preventDefault(); handleSend(input); }}
                className="border-t border-slate-100 bg-white px-5 py-4 flex gap-3">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={streaming}
              placeholder={messages.length > 0 ? "Ask a follow-up or a new question…" : "Where do you want to go?"}
              className="flex-1 border border-slate-200 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 focus:border-transparent disabled:bg-slate-50 transition bg-slate-50"
            />
            <button
              type="submit"
              disabled={streaming || !input.trim()}
              className="text-white rounded-xl px-6 py-3 text-sm font-semibold disabled:opacity-40 transition hover:opacity-90 flex items-center gap-2 flex-shrink-0"
              style={{ background: "linear-gradient(135deg, #4f46e5, #7c3aed)" }}
            >
              {streaming ? <span className="animate-spin">⚙</span> : <>Send <span>↑</span></>}
            </button>
          </form>
        </div>

        {/* ── RIGHT: Tools sidebar ──────────────────────────────────────────── */}
        <div className="hidden md:flex flex-col w-80 xl:w-96 bg-slate-50 overflow-y-auto chat-scroll flex-shrink-0">

          {!lastAiMsg ? (
            /* Empty sidebar — show tips */
            <div className="flex-1 flex flex-col items-center justify-center px-6 text-center">
              <div className="w-12 h-12 rounded-2xl flex items-center justify-center mb-4"
                   style={{ background: "linear-gradient(135deg, #e0e7ff, #ede9fe)" }}>
                <span className="text-2xl">🧭</span>
              </div>
              <p className="text-sm font-semibold text-slate-700 mb-1">Your trip tools</p>
              <p className="text-xs text-slate-400 leading-relaxed">
                Ask a travel question and your map, budget estimator, and flight search will appear here.
              </p>
            </div>
          ) : (
            <div className="p-4 space-y-4">

              {/* Section label */}
              <p className="text-xs font-semibold uppercase tracking-widest text-slate-400 px-1">
                Trip Tools
              </p>

              {/* Email this plan */}
              {lastAiMsg.runId && (
                <div className="bg-white rounded-2xl shadow-sm overflow-hidden"
                     style={{ border: "1px solid #e2e8f0" }}>
                  <div className="px-4 py-3 flex items-center gap-3"
                       style={{ background: "linear-gradient(135deg, #0f172a, #1e1b4b)" }}>
                    <span className="text-xl">✉️</span>
                    <div>
                      <p className="text-sm font-semibold text-white">Email this plan</p>
                      <p className="text-xs text-slate-400">Get a copy in your inbox</p>
                    </div>
                  </div>
                  <div className="px-4 py-3">
                    {emailStatus ? (
                      <p className={`text-sm font-medium flex items-center gap-2 ${emailStatus.startsWith("Sent") ? "text-emerald-600" : "text-rose-500"}`}>
                        {emailStatus.startsWith("Sent") ? "✓" : "✗"} {emailStatus}
                      </p>
                    ) : emailOpen ? (
                      <div className="space-y-2">
                        <input
                          type="email"
                          value={emailValue}
                          onChange={(e) => setEmailValue(e.target.value)}
                          onKeyDown={(e) => e.key === "Enter" && sendEmail()}
                          placeholder="your@email.com"
                          className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 bg-slate-50"
                          autoFocus
                        />
                        <div className="flex gap-2">
                          <button onClick={sendEmail} disabled={emailSending || !emailValue.trim()}
                            className="flex-1 text-white text-sm font-semibold py-2 rounded-lg disabled:opacity-40 transition hover:opacity-90"
                            style={{ background: "linear-gradient(135deg, #4f46e5, #7c3aed)" }}>
                            {emailSending ? "Sending…" : "Send"}
                          </button>
                          <button onClick={() => { setEmailOpen(false); setEmailValue(""); }}
                            className="px-3 py-2 rounded-lg bg-slate-100 text-slate-500 text-sm hover:bg-slate-200 transition">
                            ✕
                          </button>
                        </div>
                      </div>
                    ) : (
                      <button onClick={() => setEmailOpen(true)}
                        className="w-full text-sm font-semibold py-2.5 rounded-xl transition hover:opacity-90 text-white"
                        style={{ background: "linear-gradient(135deg, #4f46e5, #7c3aed)" }}>
                        Send to my email →
                      </button>
                    )}
                  </div>
                </div>
              )}

              {/* Find Flights */}
              <FlightInfo defaultDestination={lastDestination} />

              {/* Map */}
              {(lastAiGeo.length > 0 || userLocation) && (
                <div className="bg-white rounded-2xl shadow-sm overflow-hidden"
                     style={{ border: "1px solid #e2e8f0" }}>
                  <div className="px-4 py-2.5 flex items-center gap-2 border-b border-slate-100">
                    <span>🗺</span>
                    <span className="text-sm font-semibold text-slate-700">Destination Map</span>
                  </div>
                  <div className="p-0">
                    <MapPanel locations={lastAiGeo} userLocation={userLocation} onMarkerClick={handleDestinationClick} />
                  </div>
                </div>
              )}

              {/* Budget calculator */}
              <BudgetCalculator defaultDestination={lastDestination} />

            </div>
          )}
        </div>

      </div>
    </Layout>
  );
}
