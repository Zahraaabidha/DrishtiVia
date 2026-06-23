import React, { useState, useRef, useEffect } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { searchViolations, type Violation } from "../../api/client";

const navLinks = [
  {
    label: "Home", to: "/",
    icon: <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>,
  },
  {
    label: "Dashboard", to: "/dashboard",
    icon: <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>,
  },
  {
    label: "Live Detect", to: "/detect",
    icon: <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="3"/></svg>,
  },
  {
    label: "Review Queue", to: "/review",
    icon: <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h11"/></svg>,
  },
  {
    label: "Analytics", to: "/analytics",
    icon: <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/><line x1="2" y1="20" x2="22" y2="20"/></svg>,
  },
  {
    label: "Knowledge Graph", to: "/graph",
    icon: <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/></svg>,
  },
  {
    label: "AI Agent", to: "/agent",
    icon: <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 2a2 2 0 012 2c0 .74-.4 1.39-1 1.73V7h1a7 7 0 017 7H3a7 7 0 017-7h1V5.73A2 2 0 0110 4a2 2 0 012-2z"/><path d="M5 14v6a1 1 0 001 1h12a1 1 0 001-1v-6"/><circle cx="9" cy="17" r="1"/><circle cx="15" cy="17" r="1"/></svg>,
  },
  {
    label: "Verify", to: "/verify",
    icon: <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>,
  },
  {
    label: "Model Perf.", to: "/models",
    icon: <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>,
  },
];

interface Props { children: React.ReactNode; }

const AppLayout: React.FC<Props> = ({ children }) => {
  const navigate = useNavigate();
  const [collapsed, setCollapsed] = useState(false);
  const [searchQ, setSearchQ]     = useState("");
  const [searchOpen, setSearchOpen] = useState(false);
  const [searchResults, setSearchResults] = useState<Violation[]>([]);
  const [searching, setSearching] = useState(false);
  const searchRef = useRef<HTMLDivElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (searchRef.current && !searchRef.current.contains(e.target as Node)) {
        setSearchOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  // Debounced search
  const handleSearch = (val: string) => {
    setSearchQ(val);
    if (!val.trim()) { setSearchResults([]); setSearchOpen(false); return; }
    setSearchOpen(true);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(async () => {
      setSearching(true);
      try {
        const res = await searchViolations(val.trim(), 8);
        setSearchResults(res.results);
      } catch { setSearchResults([]); }
      finally { setSearching(false); }
    }, 320);
  };

  const SEVERITY_DOT: Record<string, string> = {
    CRITICAL: "bg-red-500", HIGH: "bg-orange-500", MEDIUM: "bg-yellow-400", LOW: "bg-neutral-300",
  };

  return (
    <div className="flex h-screen overflow-hidden bg-[#F8F9FA] font-sans">
      {/* ── SIDEBAR ── */}
      <aside className={`flex flex-col shrink-0 transition-all duration-300 h-full ${collapsed ? "w-[68px]" : "w-[220px]"}`}
        style={{ background: "#fff", borderRight: "1px solid rgba(0,0,0,0.06)" }}>
        <div className="flex items-center gap-2.5 px-4 py-5 border-b border-neutral-100">
          <div className="w-8 h-8 rounded-[3px] bg-neutral-900 flex items-center justify-center shrink-0">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>
            </svg>
          </div>
          {!collapsed && (
            <span className="font-extrabold text-[13px] tracking-[0.14em] uppercase text-neutral-900"
              style={{ fontFamily: "'Outfit', sans-serif" }}>DrishtiVia</span>
          )}
        </div>

        <nav className="flex-1 flex flex-col gap-1 px-2 py-4">
          {!collapsed && (
            <p className="text-[10px] font-bold tracking-[0.18em] uppercase text-neutral-400 px-2 mb-1">Navigation</p>
          )}
          {navLinks.map(link => (
            <NavLink key={link.to} to={link.to} end={link.to === "/"}
              className={({ isActive }) =>
                `flex items-center gap-2.5 px-2.5 py-2 rounded-[4px] text-[13px] font-medium transition-all ${
                  isActive ? "bg-neutral-900 text-white" : "text-neutral-500 hover:bg-neutral-100 hover:text-neutral-900"
                }`
              }>
              <span className="shrink-0">{link.icon}</span>
              {!collapsed && <span>{link.label}</span>}
            </NavLink>
          ))}
        </nav>

        <div className="px-2 py-4 border-t border-neutral-100 flex flex-col gap-2">
          <button onClick={() => setCollapsed(c => !c)}
            className="flex items-center gap-2 px-2.5 py-2 rounded-[4px] text-[12px] text-neutral-400 hover:bg-neutral-100 hover:text-neutral-900 transition-all w-full">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              {collapsed
                ? <><polyline points="13 17 18 12 13 7"/><polyline points="6 17 11 12 6 7"/></>
                : <><polyline points="11 17 6 12 11 7"/><polyline points="18 17 13 12 18 7"/></>}
            </svg>
            {!collapsed && <span>Collapse</span>}
          </button>
          <div className="flex items-center gap-2 px-2.5 py-2">
            <div className="w-7 h-7 rounded-full bg-neutral-900 text-white text-[10px] font-bold flex items-center justify-center shrink-0">TO</div>
            {!collapsed && (
              <div className="min-w-0">
                <p className="text-[12px] font-semibold text-neutral-900 truncate">Traffic Operator</p>
                <p className="text-[10px] text-neutral-400 truncate">Bengaluru Control</p>
              </div>
            )}
          </div>
        </div>
      </aside>

      {/* ── MAIN ── */}
      <main className="flex-1 min-w-0 overflow-y-auto flex flex-col">
        {/* Top bar */}
        <header className="sticky top-0 z-30 flex items-center justify-between gap-4 px-8 py-4"
          style={{ background: "rgba(248,249,250,0.9)", backdropFilter: "blur(12px)", borderBottom: "1px solid rgba(0,0,0,0.05)" }}>

          {/* Live search */}
          <div ref={searchRef} className="relative flex-1 max-w-sm">
            <div className="flex items-center gap-2 bg-white border border-neutral-200 rounded-full px-4 py-2 focus-within:border-neutral-400 transition-colors">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#999" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
              </svg>
              <input
                type="text"
                value={searchQ}
                onChange={e => handleSearch(e.target.value)}
                placeholder="Search plate, violation type…"
                className="flex-1 text-[13px] bg-transparent outline-none text-neutral-700 placeholder:text-neutral-400"
              />
              {searching && (
                <svg className="animate-spin" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#999" strokeWidth="2"><circle cx="12" cy="12" r="10" strokeOpacity="0.25"/><path d="M12 2a10 10 0 0 1 10 10" stroke="#555"/></svg>
              )}
              {searchQ && !searching && (
                <button onClick={() => { setSearchQ(""); setSearchResults([]); setSearchOpen(false); }}
                  className="text-neutral-400 hover:text-neutral-600">
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                </button>
              )}
            </div>

            {/* Dropdown results */}
            {searchOpen && (
              <div className="absolute top-full mt-2 w-full bg-white rounded-[4px] shadow-lg border border-neutral-100 overflow-hidden z-50">
                {searchResults.length === 0 ? (
                  <div className="px-4 py-3 text-[12px] text-neutral-400">No results found for "{searchQ}"</div>
                ) : (
                  <>
                    <div className="px-4 py-2 border-b border-neutral-50">
                      <p className="text-[10px] font-bold tracking-widest uppercase text-neutral-400">{searchResults.length} result{searchResults.length !== 1 ? "s" : ""}</p>
                    </div>
                    {searchResults.map(v => (
                      <button key={v.id} onClick={() => { navigate("/review"); setSearchOpen(false); setSearchQ(""); }}
                        className="w-full flex items-center gap-3 px-4 py-2.5 hover:bg-neutral-50 transition-colors text-left border-b border-neutral-50 last:border-0">
                        <div className={`w-2 h-2 rounded-full shrink-0 ${SEVERITY_DOT[v.severity || v.priority_level] || "bg-neutral-300"}`}/>
                        <div className="min-w-0 flex-1">
                          <p className="text-[12px] font-semibold text-neutral-900 truncate">{v.violation_type}</p>
                          <p className="text-[11px] text-neutral-400 truncate">
                            {v.plate_number} · {v.camera_id} · {new Date(v.timestamp * 1000).toLocaleDateString()}
                          </p>
                        </div>
                        <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full shrink-0 ${
                          v.severity === "CRITICAL" || v.priority_level === "CRITICAL" ? "bg-red-100 text-red-700" :
                          v.severity === "HIGH"     || v.priority_level === "HIGH"     ? "bg-orange-100 text-orange-700" :
                          "bg-neutral-100 text-neutral-600"
                        }`}>{v.severity || v.priority_level}</span>
                      </button>
                    ))}
                    <button onClick={() => { navigate("/review"); setSearchOpen(false); }}
                      className="w-full px-4 py-2.5 text-[11px] font-semibold text-neutral-500 hover:bg-neutral-50 transition-colors text-center">
                      View all in Review Queue →
                    </button>
                  </>
                )}
              </div>
            )}
          </div>

          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-full bg-neutral-100 flex items-center justify-center cursor-pointer hover:bg-neutral-200 transition-colors">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#555" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/>
              </svg>
            </div>
            <div className="relative">
              <div className="w-8 h-8 rounded-full bg-neutral-100 flex items-center justify-center cursor-pointer hover:bg-neutral-200 transition-colors">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#555" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="12" cy="12" r="3"/><path d="M19.07 4.93a10 10 0 0 1 0 14.14M4.93 4.93a10 10 0 0 0 0 14.14"/>
                </svg>
              </div>
              <span className="absolute top-0 right-0 w-2 h-2 bg-red-500 rounded-full border border-white"/>
            </div>
          </div>
        </header>

        <div className="px-8 py-6">
          {children}
        </div>
      </main>
    </div>
  );
};

export default AppLayout;


