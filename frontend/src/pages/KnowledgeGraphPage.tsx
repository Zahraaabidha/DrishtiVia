import { useEffect, useRef, useState } from "react";
import { getGraph, cloneCheck, type GraphData } from "../api/client";

const SEVERITY_COLOR: Record<string, string> = {
  CRITICAL: "#ef4444",
  HIGH:     "#f97316",
  MEDIUM:   "#eab308",
  LOW:      "#94a3b8",
};

function GraphCanvas({ data }: { data: GraphData }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !data.edges.length) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const W = canvas.width = canvas.offsetWidth;
    const H = canvas.height = 480;

    ctx.clearRect(0, 0, W, H);

    // unique nodes
    const plates  = [...new Set(data.edges.map(e => e.plate_number))];
    const cameras = [...new Set(data.edges.map(e => e.camera_id))];
    const vtypes  = [...new Set(data.edges.map(e => e.violation_type))];

    function circlePos(items: string[], cx: number, cy: number, r: number) {
      return items.map((_, i) => {
        const a = (2 * Math.PI * i) / Math.max(items.length, 1) - Math.PI / 2;
        return { x: cx + r * Math.cos(a), y: cy + r * Math.sin(a) };
      });
    }

    const pPos = circlePos(plates,  W * 0.25, H * 0.5, Math.min(120, plates.length > 1 ? 150 : 0));
    const cPos = circlePos(cameras, W * 0.75, H * 0.35, Math.min(80, cameras.length > 1 ? 100 : 0));
    const vPos = circlePos(vtypes,  W * 0.55, H * 0.72, Math.min(90, vtypes.length > 1 ? 110 : 0));

    const pm: Record<string, {x: number; y: number}> = {};
    const cm: Record<string, {x: number; y: number}> = {};
    const vm: Record<string, {x: number; y: number}> = {};
    plates.forEach((p, i)  => { pm[p] = pPos[i]; });
    cameras.forEach((c, i) => { cm[c] = cPos[i]; });
    vtypes.forEach((v, i)  => { vm[v] = vPos[i]; });

    // draw edges
    ctx.strokeStyle = "rgba(100,100,100,0.12)";
    ctx.lineWidth = 1;
    for (const e of data.edges) {
      const p = pm[e.plate_number], c = cm[e.camera_id], v = vm[e.violation_type];
      if (p && c) {
        ctx.beginPath(); ctx.moveTo(p.x, p.y); ctx.lineTo(c.x, c.y); ctx.stroke();
      }
      if (p && v) {
        ctx.beginPath(); ctx.moveTo(p.x, p.y); ctx.lineTo(v.x, v.y); ctx.stroke();
      }
    }

    // draw nodes
    function drawNode(x: number, y: number, label: string, color: string, r: number) {
      ctx!.beginPath();
      ctx!.arc(x, y, r, 0, 2 * Math.PI);
      ctx!.fillStyle = color;
      ctx!.fill();
      ctx!.strokeStyle = "rgba(0,0,0,0.12)";
      ctx!.lineWidth = 1.5;
      ctx!.stroke();
      ctx!.fillStyle = "#111";
      ctx!.font = `${Math.min(11, 10)}px Inter, sans-serif`;
      ctx!.textAlign = "center";
      const shortLabel = label.length > 10 ? label.slice(0, 9) + "…" : label;
      ctx!.fillText(shortLabel, x, y + r + 13);
    }

    plates.forEach((p, i)  => drawNode(pPos[i].x, pPos[i].y, p, "#fecaca", 14));
    cameras.forEach((c, i) => drawNode(cPos[i].x, cPos[i].y, c.replace(/_/g, " "), "#bfdbfe", 18));
    vtypes.forEach((v, i)  => drawNode(vPos[i].x, vPos[i].y, v.split(" ")[0], "#fde68a", 14));
  }, [data]);

  return (
    <canvas ref={canvasRef} className="w-full rounded-[4px] bg-neutral-50"
      style={{ height: 480 }}/>
  );
}

export default function KnowledgeGraphPage() {
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [loading, setLoading]     = useState(true);
  const [clonePlate, setClonePlate] = useState("");
  const [cloneResult, setCloneResult] = useState<any>(null);
  const [checking, setChecking]   = useState(false);

  useEffect(() => {
    getGraph().then(setGraphData).finally(() => setLoading(false));
  }, []);

  async function runCloneCheck() {
    if (!clonePlate.trim()) return;
    setChecking(true);
    try {
      const r = await cloneCheck(clonePlate.trim().toUpperCase());
      setCloneResult(r);
    } catch {}
    setChecking(false);
  }

  return (
    <div>
      <div className="mb-7">
        <p className="text-[10px] font-bold tracking-[0.16em] uppercase text-neutral-400 mb-1">Graph Explorer</p>
        <h1 className="text-3xl font-semibold tracking-tight text-neutral-900" style={{ fontFamily: "'Outfit', sans-serif" }}>
          Knowledge Graph
        </h1>
        <p className="text-[13px] text-neutral-400 mt-1">
          Vehicle → Camera → Violation network · SQLite backend (Neo4j-ready)
        </p>
      </div>

      {loading ? (
        <div className="bg-white rounded-[4px] h-[480px] animate-pulse border border-neutral-100"/>
      ) : !graphData || graphData.edges.length === 0 ? (
        <div className="bg-white rounded-[4px] p-12 border border-neutral-100 text-center">
          <p className="text-[14px] text-neutral-400">No violations in DB yet — run detection to populate the graph.</p>
        </div>
      ) : (
        <div className="flex flex-col gap-4">
          {/* Canvas graph */}
          <div className="bg-white rounded-[4px] p-5 border border-neutral-100 shadow-sm">
            <p className="text-[10px] font-bold tracking-[0.16em] uppercase text-neutral-400 mb-3">
              Network · last 80 records
            </p>
            <div className="flex items-center gap-4 mb-3">
              {[["#fecaca","Vehicle Plates"],["#bfdbfe","Camera Nodes"],["#fde68a","Violation Types"]].map(([c, l]) => (
                <div key={l} className="flex items-center gap-1.5 text-[11px] text-neutral-600">
                  <span className="w-3 h-3 rounded-full inline-block" style={{ background: c }}/>
                  {l}
                </div>
              ))}
            </div>
            <GraphCanvas data={graphData}/>
          </div>

          <div className="grid grid-cols-2 gap-4">
            {/* Repeat offenders */}
            <div className="bg-white rounded-[4px] p-5 border border-neutral-100 shadow-sm">
              <p className="text-[10px] font-bold tracking-[0.16em] uppercase text-neutral-400 mb-4">Repeat Offenders (30d)</p>
              {graphData.repeat_offenders.length === 0 ? (
                <p className="text-[13px] text-neutral-400">No repeat offenders yet.</p>
              ) : graphData.repeat_offenders.map((o, i) => (
                <div key={i} className="flex items-start justify-between gap-2 py-2.5 border-b border-neutral-50 last:border-0">
                  <div className="min-w-0">
                    <p className="text-[13px] font-mono font-semibold text-neutral-900">{o.plate}</p>
                    <p className="text-[10px] text-neutral-400 truncate">{o.types}</p>
                  </div>
                  <span className="text-[13px] font-bold text-red-600 shrink-0">{o.count}×</span>
                </div>
              ))}
            </div>

            {/* Camera hotspots */}
            <div className="bg-white rounded-[4px] p-5 border border-neutral-100 shadow-sm">
              <p className="text-[10px] font-bold tracking-[0.16em] uppercase text-neutral-400 mb-4">Camera Hotspots</p>
              {graphData.hotspots.map((h, i) => (
                <div key={i} className="flex items-center justify-between py-2.5 border-b border-neutral-50 last:border-0">
                  <div>
                    <p className="text-[12px] font-medium text-neutral-900">{h.camera.replace(/_/g, " ")}</p>
                    <p className="text-[10px] text-neutral-400">Avg priority: {h.avg_priority}</p>
                  </div>
                  <span className="text-[13px] font-bold text-neutral-700">{h.count}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Plate cloning check */}
          <div className="bg-white rounded-[4px] p-5 border border-neutral-100 shadow-sm">
            <p className="text-[10px] font-bold tracking-[0.16em] uppercase text-neutral-400 mb-1">Plate Cloning Alert</p>
            <p className="text-[12px] text-neutral-500 mb-3">Detect if the same plate was seen at multiple camera locations within 30 minutes — a strong indicator of cloned plates.</p>
            <div className="flex gap-2 mb-4">
              <input type="text" placeholder="e.g. KA01AB1234" value={clonePlate}
                onChange={e => setClonePlate(e.target.value)}
                onKeyDown={e => e.key === "Enter" && runCloneCheck()}
                className="flex-1 text-[13px] font-mono border border-neutral-200 rounded-[3px] px-4 py-2.5 focus:outline-none focus:border-neutral-400"/>
              <button onClick={runCloneCheck} disabled={!clonePlate.trim() || checking}
                className="px-5 py-2.5 rounded-full bg-neutral-900 text-white text-[13px] font-semibold hover:bg-neutral-700 disabled:opacity-40 transition-all">
                {checking ? "…" : "Check"}
              </button>
            </div>

            {cloneResult && (
              <div className={`rounded-[4px] p-4 border ${cloneResult.clone_alert ? "bg-red-50 border-red-200" : "bg-green-50 border-green-200"}`}>
                {cloneResult.clone_alert ? (
                  <>
                    <p className="text-[13px] font-bold text-red-800 mb-2">
                      ⚠️ Clone Alert — {cloneResult.plate} seen at {cloneResult.unique_locations.length} locations in 30 min
                    </p>
                    <div className="flex flex-col gap-1">
                      {cloneResult.sightings.map((s: any, i: number) => (
                        <p key={i} className="text-[11px] text-red-700">
                          {new Date(s.timestamp * 1000).toLocaleTimeString()} · {s.camera_id.replace(/_/g, " ")} · {s.violation_type}
                        </p>
                      ))}
                    </div>
                  </>
                ) : (
                  <p className="text-[13px] font-semibold text-green-800">
                    ✓ No cloning detected for {cloneResult.plate} — {cloneResult.sightings.length} sighting(s) at single location
                  </p>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

