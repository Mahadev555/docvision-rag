import { NavLink } from "react-router-dom";
import { useEffect, useState } from "react";
import { getHealth } from "../api.js";

const NAV_ITEMS = [
  { to: "/chat", label: "Chat", icon: ChatIcon },
  { to: "/upload", label: "Upload", icon: UploadIcon },
  { to: "/dashboard", label: "Dashboard", icon: DashboardIcon },
];

export default function Sidebar() {
  const [health, setHealth] = useState(null);

  useEffect(() => {
    let cancelled = false;
    const check = () => {
      getHealth()
        .then((data) => !cancelled && setHealth(data))
        .catch(() => !cancelled && setHealth({ status: "error" }));
    };
    check();
    const interval = setInterval(check, 20000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  const isOk = health?.status === "ok";

  return (
    <aside className="flex h-screen w-60 flex-col border-r border-slate-200 bg-slate-50">
      <div className="flex items-center gap-2.5 px-5 py-5">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-accent-600">
          <EyeIcon />
        </div>
        <div>
          <div className="text-sm font-bold tracking-tight text-slate-900">DocVision</div>
          <div className="text-[11px] text-slate-500">Multimodal RAG</div>
        </div>
      </div>

      <nav className="flex-1 space-y-0.5 px-3 pt-2">
        {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `flex items-center gap-2.5 rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                isActive
                  ? "bg-white text-accent-700 shadow-sm ring-1 ring-slate-200"
                  : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
              }`
            }
          >
            <Icon />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="border-t border-slate-200 px-4 py-3.5">
        <div className="flex items-center gap-2 rounded-md bg-white px-3 py-2 text-xs ring-1 ring-slate-200">
          <span
            className={`h-1.5 w-1.5 rounded-full ${
              health == null ? "bg-slate-300" : isOk ? "bg-emerald-500" : "bg-rose-500"
            } ${health == null ? "dot-pulse" : ""}`}
          />
          <span className="text-slate-500">
            {health == null ? "Checking API..." : isOk ? "API online" : "API unreachable"}
          </span>
        </div>
      </div>
    </aside>
  );
}

function UploadIcon() {
  return (
    <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
      <polyline points="17 8 12 3 7 8" />
      <line x1="12" y1="3" x2="12" y2="15" />
    </svg>
  );
}

function ChatIcon() {
  return (
    <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
    </svg>
  );
}

function DashboardIcon() {
  return (
    <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="3" width="7" height="9" rx="1" />
      <rect x="14" y="3" width="7" height="5" rx="1" />
      <rect x="14" y="12" width="7" height="9" rx="1" />
      <rect x="3" y="16" width="7" height="5" rx="1" />
    </svg>
  );
}

function EyeIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  );
}
