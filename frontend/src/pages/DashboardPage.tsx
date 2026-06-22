import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getStats, getHealth, type Stats } from "../api/client";

function StatCard({ label, value, sub, accent }: { label: string; value: string | number; sub: string; accent?: string }) {
  return (
    <div className="bg-white rounded-[4px] p-5 border border-neutral-100 shadow-sm hover:shadow-md hover:-translate-y-0.5 transition-all">
      <p className="text-[10px] font-bold tracking-[0.16em] uppercase text-neutral-400 mb-2">{label}</p>
      <p className={`text-4xl font-semibold tracking-tight mb-1 ${accent ?? "text-neutral-900"}`}
        style={{ fontFamily: "'Outfit', sans-serif" }}>{value}</p>
      <p className="text-[12px] text-neutral-400">{sub}</p>
    </div>
  );
}

function ModelDot({ ok }: { ok: boolean }) {
  return <span className={`w-2 h-2 rounded-full ${ok ? "bg-green-500" : "bg-neutral-300"}`}/>;
}

export default function DashboardPage() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [health, setHealth] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([getStats(), getHealth()])
      .then(([s, h]) => { setStats(s); setHealth(h); })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  return (
    <div>
      {/* Page title */}
      <div className="mb-7">
        <p className="text-[10px] font-bold tracking-[0.16em] uppercase text-neutral-400 mb-1">Overview</p>
        <h1 className="text-3xl font-semibold tracking-tight text-neutral-900" style={{ fontFamily: "'Outfit', sans-serif" }}>
          Command Centre
        </h1>
        <p className="text-[13px] text-neutral-400 mt-1">Real-time traffic violation intelligence · Bengaluru Control Room</p>
      </div>

      {/* 4 stat tiles */}
      {loading ? (
        <div className="grid grid-cols-4 gap-4 mb-6">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="bg-white rounded-[4px] p-5 h-[120px] animate-pulse border border-neutral-100"/>
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-4 gap-4 mb-6">
          <StatCard label="Total Violations" value={stats?.total ?? 0} sub="All time · all cameras"/>
          <StatCard label="Pending Review" value={stats?.pending ?? 0} sub="Needs operator action" accent="text-amber-500"/>
          <StatCard label="Unique Plates" value={stats?.plates ?? 0} sub="Identified via OCR"/>
          <StatCard label="Models Active" value={`${health?.active_count ?? "–"}/4`} sub="YOLOv8 pipeline" accent="text-green-600"/>
        </div>
      )}

      {/* Main bento grid */}
      <div className="grid grid-cols-3 gap-4">
        {/* Top violations */}
        <div className="col-span-2 bg-white rounded-[4px] p-5 border border-neutral-100 shadow-sm">
          <p className="text-[10px] font-bold tracking-[0.16em] uppercase text-neutral-400 mb-4">Top Violation Types</p>
          {stats?.top_types?.length ? (
            <div className="flex flex-col gap-3">
              {stats.top_types.map((t, i) => {
                const max = stats.top_types[0].count;
                return (
                  <div key={i} className="flex items-center gap-3">
                    <span className="text-[12px] font-medium text-neutral-700 w-36 shrink-0">{t.type}</span>
                    <div className="flex-1 h-2 bg-neutral-100 rounded-full overflow-hidden">
                      <div className="h-full bg-neutral-900 rounded-full transition-all" style={{ width: `${(t.count / max) * 100}%` }}/>
                    </div>
                    <span className="text-[12px] text-neutral-500 w-8 text-right">{t.count}</span>
                  </div>
                );
              })}
            </div>
          ) : (
            <p className="text-[13px] text-neutral-400">No data yet — run a detection to populate.</p>
          )}
        </div>

        {/* Model status */}
        <div className="bg-white rounded-[4px] p-5 border border-neutral-100 shadow-sm">
          <p className="text-[10px] font-bold tracking-[0.16em] uppercase text-neutral-400 mb-4">Model Status</p>
          {[
            { name: "YOLOv8s Base", key: "base_yolo" },
            { name: "Helmet Detect", key: "helmet" },
            { name: "Seatbelt", key: "seatbelt" },
            { name: "Wrong-Side", key: "wrongside" },
          ].map(m => (
            <div key={m.key} className="flex items-center justify-between py-2 border-b border-neutral-50 last:border-0">
              <span className="text-[13px] text-neutral-700">{m.name}</span>
              <div className="flex items-center gap-1.5">
                <ModelDot ok={health?.models?.[m.key] ?? false}/>
                <span className={`text-[11px] font-medium ${health?.models?.[m.key] ? "text-green-600" : "text-neutral-400"}`}>
                  {health?.models?.[m.key] ? "Ready" : "Missing"}
                </span>
              </div>
            </div>
          ))}
        </div>

        {/* By camera */}
        <div className="bg-white rounded-[4px] p-5 border border-neutral-100 shadow-sm">
          <p className="text-[10px] font-bold tracking-[0.16em] uppercase text-neutral-400 mb-4">By Camera</p>
          {stats?.by_camera?.length ? (
            <div className="flex flex-col gap-2">
              {stats.by_camera.slice(0, 5).map((c, i) => (
                <div key={i} className="flex items-center justify-between">
                  <span className="text-[12px] text-neutral-700 truncate max-w-[120px]">{c.camera || "Unknown"}</span>
                  <span className="text-[12px] font-semibold text-neutral-900">{c.count}</span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-[13px] text-neutral-400">No camera data yet.</p>
          )}
        </div>

        {/* Quick actions */}
        <div className="col-span-2 bg-neutral-900 rounded-[4px] p-5 text-white">
          <p className="text-[10px] font-bold tracking-[0.16em] uppercase text-neutral-400 mb-1">Quick Actions</p>
          <p className="text-xl font-semibold mb-5" style={{ fontFamily: "'Outfit', sans-serif" }}>Start your workflow</p>
          <div className="grid grid-cols-3 gap-3">
            {[
              { label: "Live Detect", sub: "Run image analysis", to: "/detect" },
              { label: "Review Queue", sub: `${stats?.pending ?? 0} pending`, to: "/review" },
              { label: "Analytics", sub: "Charts & trends", to: "/analytics" },
            ].map(a => (
              <Link key={a.to} to={a.to}
                className="bg-white/10 hover:bg-white/20 rounded-[4px] p-3.5 transition-all">
                <p className="text-[13px] font-semibold mb-0.5">{a.label}</p>
                <p className="text-[11px] text-neutral-400">{a.sub}</p>
              </Link>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

