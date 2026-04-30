import { useNavigate } from "react-router-dom";
import { useAuthStore } from "../store/auth";

export default function Layout({ children }: { children: React.ReactNode }) {
  const { email, clearAuth } = useAuthStore();
  const navigate = useNavigate();

  function logout() {
    clearAuth();
    navigate("/login");
  }

  return (
    <div className="min-h-screen flex flex-col bg-slate-50">
      <nav style={{ background: "linear-gradient(135deg, #0f172a 0%, #1e1b4b 60%, #0f172a 100%)" }}
           className="px-6 py-3.5 flex items-center justify-between shadow-xl">
        <button onClick={() => navigate("/chat")} className="flex items-center gap-3 group">
          <div className="w-8 h-8 rounded-xl flex items-center justify-center text-white text-sm shadow-lg transition group-hover:scale-110"
               style={{ background: "linear-gradient(135deg, #6366f1, #8b5cf6)" }}>
            ✈
          </div>
          <div className="flex items-baseline gap-2">
            <span className="font-bold text-white text-lg tracking-tight">Wandr</span>
            <span className="text-indigo-300 text-xs font-medium hidden sm:block">AI Travel Planner</span>
          </div>
        </button>

        {email && (
          <div className="flex items-center gap-2">
            <div className="hidden sm:flex items-center gap-2 rounded-full px-3 py-1.5 border border-white/10 bg-white/5">
              <div className="w-5 h-5 rounded-full flex items-center justify-center text-white text-xs font-bold"
                   style={{ background: "linear-gradient(135deg, #6366f1, #8b5cf6)" }}>
                {email[0].toUpperCase()}
              </div>
              <span className="text-white/70 text-xs max-w-[140px] truncate">{email}</span>
            </div>
            <button
              onClick={logout}
              className="text-white/50 hover:text-white text-xs font-medium transition px-3 py-1.5 rounded-lg hover:bg-white/10"
            >
              Sign out
            </button>
          </div>
        )}
      </nav>
      <main className="flex-1">{children}</main>
    </div>
  );
}
