import { useEffect, useRef, useState } from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";
import { getAnalytics } from "../api/client";

const DAYS_OPTS = [7, 14, 30];
const BAR_COLORS = ["#111111", "#6b7280", "#d1d5db", "#374151", "#9ca3af"];

// Known Bangalore camera hotspot coordinates
const CAMERA_COORDS: Record<string, [number, number]> = {
  silk_board_junction:  [12.9170, 77.6234],
  silk_board:           [12.9170, 77.6234],
  kr_circle:            [12.9767, 77.5713],
  kr_puram:             [12.9987, 77.6918],
  hebbal_flyover:       [13.0450, 77.5970],
  hebbal:               [13.0450, 77.5970],
  marathahalli_bridge:  [12.9591, 77.7003],
  marathahalli:         [12.9591, 77.7003],
  whitefield_01:        [12.9698, 77.7500],
  whitefield:           [12.9698, 77.7500],
  electronic_city:      [12.8398, 77.6770],
  koramangala:          [12.9352, 77.6245],
  mg_road:              [12.9758, 77.6073],
  indiranagar:          [12.9784, 77.6408],
  yeshwanthpur:         [13.0246, 77.5521],
};

function getCoords(cameraId: string): [number, number] {
  const key = (cameraId || "").toLowerCase().replace(/[\s-]/g, "_");
  for (const [k, v] of Object.entries(CAMERA_COORDS)) {
    if (key.includes(k) || k.includes(key)) return v;
  }
  return [12.9716 + (Math.random() - 0.5) * 0.08, 77.5946 + (Math.random() - 0.5) * 0.08];
}

interface Hotspot { camera: string; count: number; avg_priority: number; lat?: number; lng?: number; }

function BangaloreMap({ hotspots }: { hotspots: Hotspot[] }) {
  const mapRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<any>(null);

  useEffect(() => {
    if (!mapRef.current || mapInstanceRef.current) return;

    // Load Leaflet dynamically
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css";
    document.head.appendChild(link);

    const script = document.createElement("script");
    script.src = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js";
    script.onload = () => {
      const L = (window as any).L;
      if (!mapRef.current || mapInstanceRef.current) return;

      const map = L.map(mapRef.current, { zoomControl: true, attributionControl: false }).setView([12.9716, 77.5946], 12);
      mapInstanceRef.current = map;

      // Tile layer — CartoDB light
      L.tileLayer("https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png", {
        maxZoom: 18,
        subdomains: "abcd",
      }).addTo(map);

      L.control.attribution({ position: "bottomright", prefix: "© OpenStreetMap · CartoDB" }).addTo(map);

      // Plot hotspots
      hotspots.forEach(h => {
        const [lat, lng] = [h.lat ?? getCoords(h.camera)[0], h.lng ?? getCoords(h.camera)[1]];
        const radius = 12 + Math.min(h.count * 2, 30);
        const color  = h.count >= 20 ? "#ef4444" : h.count >= 10 ? "#f97316" : "#eab308";

        const circle = L.circleMarker([lat, lng], {
          radius, color, fillColor: color,
          fillOpacity: 0.5, weight: 2,
        }).addTo(map);

        circle.bindPopup(
          `<div style="font-family:Inter,sans-serif;font-size:12px">
            <strong style="font-size:13px">${h.camera}</strong><br/>
            <span style="color:#ef4444;font-weight:700">${h.count} violations</span><br/>
            Avg priority: ${h.avg_priority.toFixed(1)}
          </div>`,
          { maxWidth: 180 }
        );

        L.marker([lat, lng], {
          icon: L.divIcon({
            html: `<div style="font-size:10px;font-weight:700;color:#111;background:rgba(255,255,255,0.9);border-radius:8px;padding:1px 5px;border:1px solid #ddd;white-space:nowrap">${h.count}</div>`,
            className: "", iconAnchor: [16, 8],
          })
        }).addTo(map);
      });
    };
    document.head.appendChild(script);

    return () => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }
    };
  }, [hotspots]);

  return <div ref={mapRef} style={{ width: "100%", height: "100%", borderRadius: 16 }}/>;
}

export default function AnalyticsPage() {
  const [days, setDays]     = useState(7);
  const [data, setData]     = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    getAnalytics(days).then(setData).finally(() => setLoading(false));
  }, [days]);

  const vTypes = data?.by_day
    ? [...new Set((data.by_day as any[]).flatMap((d: any) => Object.keys(d).filter(k => k !== "day")))]
    : [];

  const hotspots: Hotspot[] = (data?.hotspots ?? []).map((h: any) => ({
    ...h,
    lat: h.lat ?? getCoords(h.camera)[0],
    lng: h.lng ?? getCoords(h.camera)[1],
  }));

  return (
    <div>
      <div className="mb-7">
        <p className="text-[10px] font-bold tracking-[0.16em] uppercase text-neutral-400 mb-1">Insights</p>
        <h1 className="text-3xl font-semibold tracking-tight text-neutral-900" style={{ fontFamily: "'Outfit', sans-serif" }}>
          Analytics
        </h1>
        <p className="text-[13px] text-neutral-400 mt-1">Violation trends, repeat offenders, Bengaluru hotspot map</p>
      </div>

      {/* Day selector */}
      <div className="flex gap-1 p-1 bg-white rounded-[4px] border border-neutral-100 mb-5 w-fit">
        {DAYS_OPTS.map(d => (
          <button key={d} onClick={() => setDays(d)}
            className={`px-4 py-1.5 rounded-[3px] text-[12px] font-semibold transition-all ${
              days === d ? "bg-neutral-900 text-white" : "text-neutral-500 hover:text-neutral-900"
            }`}>
            {d}d
          </button>
        ))}
      </div>

      {loading ? (
        <div className="bg-white rounded-[4px] h-[300px] animate-pulse border border-neutral-100 mb-4"/>
      ) : (
        <>
          <div className="grid grid-cols-3 gap-4 mb-4">
            {/* Bar chart */}
            <div className="col-span-2 bg-white rounded-[4px] p-5 border border-neutral-100 shadow-sm">
              <p className="text-[10px] font-bold tracking-[0.16em] uppercase text-neutral-400 mb-4">
                Violations by Day (last {days} days)
              </p>
              {data?.by_day?.length ? (
                <ResponsiveContainer width="100%" height={240}>
                  <BarChart data={data.by_day} barSize={14} barCategoryGap="40%">
                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" vertical={false}/>
                    <XAxis dataKey="day" tick={{ fontSize: 11, fill: "#999" }} axisLine={false} tickLine={false}/>
                    <YAxis tick={{ fontSize: 11, fill: "#999" }} axisLine={false} tickLine={false}/>
                    <Tooltip contentStyle={{ borderRadius: 12, border: "1px solid #f0f0f0", fontSize: 12 }} cursor={{ fill: "rgba(0,0,0,0.03)" }}/>
                    {vTypes.map((k, i) => (
                      <Bar key={String(k)} dataKey={String(k)} stackId="a" fill={BAR_COLORS[i % BAR_COLORS.length]}
                        radius={i === vTypes.length - 1 ? [4, 4, 0, 0] : [0, 0, 0, 0]}/>
                    ))}
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div className="flex items-center justify-center h-[240px]">
                  <p className="text-[13px] text-neutral-400">No data for this period.</p>
                </div>
              )}
            </div>

            {/* Repeat offenders */}
            <div className="bg-white rounded-[4px] p-5 border border-neutral-100 shadow-sm">
              <p className="text-[10px] font-bold tracking-[0.16em] uppercase text-neutral-400 mb-4">Repeat Offenders</p>
              {data?.repeat_offenders?.length ? (
                <div className="flex flex-col gap-3">
                  {data.repeat_offenders.map((o: any, i: number) => (
                    <div key={i} className="flex items-start justify-between gap-2 pb-3 border-b border-neutral-50 last:border-0">
                      <div className="min-w-0">
                        <p className="text-[13px] font-mono font-semibold text-neutral-900 truncate">{o.plate}</p>
                        <p className="text-[10px] text-neutral-400 truncate">{o.types}</p>
                      </div>
                      <span className="text-[12px] font-bold text-red-600 shrink-0">{o.count}×</span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-[13px] text-neutral-400">No repeat offenders in this period.</p>
              )}
            </div>
          </div>

          {/* Bangalore map */}
          <div className="bg-white rounded-[4px] border border-neutral-100 shadow-sm overflow-hidden">
            <div className="px-5 pt-5 pb-3 flex items-center justify-between">
              <div>
                <p className="text-[10px] font-bold tracking-[0.16em] uppercase text-neutral-400">Bengaluru Live Hotspot Map</p>
                <p className="text-[12px] text-neutral-500 mt-0.5">Camera locations with violation density · circle size = violation count</p>
              </div>
              <div className="flex items-center gap-3 text-[11px] text-neutral-500">
                <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full bg-yellow-400 inline-block"/>Low</span>
                <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full bg-orange-500 inline-block"/>Medium</span>
                <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full bg-red-500 inline-block"/>High</span>
              </div>
            </div>
            <div style={{ height: 420, padding: "0 20px 20px" }}>
              {hotspots.length > 0 ? (
                <BangaloreMap hotspots={hotspots}/>
              ) : (
                <div className="flex items-center justify-center h-full bg-neutral-50 rounded-[4px]">
                  <p className="text-[13px] text-neutral-400">No camera data yet. Run detections to populate hotspots.</p>
                </div>
              )}
            </div>
          </div>

          {/* Hotspot table */}
          {hotspots.length > 0 && (
            <div className="mt-4 bg-white rounded-[4px] p-5 border border-neutral-100 shadow-sm">
              <p className="text-[10px] font-bold tracking-[0.16em] uppercase text-neutral-400 mb-4">Camera Hotspot Summary</p>
              <div className="overflow-hidden rounded-[3px] border border-neutral-100">
                <table className="w-full text-[12px]">
                  <thead>
                    <tr className="bg-neutral-50">
                      <th className="text-left px-4 py-2.5 text-[10px] font-bold tracking-widest uppercase text-neutral-400">Camera</th>
                      <th className="text-left px-4 py-2.5 text-[10px] font-bold tracking-widest uppercase text-neutral-400">Violations</th>
                      <th className="text-left px-4 py-2.5 text-[10px] font-bold tracking-widest uppercase text-neutral-400">Avg Priority</th>
                      <th className="text-left px-4 py-2.5 text-[10px] font-bold tracking-widest uppercase text-neutral-400">Risk</th>
                    </tr>
                  </thead>
                  <tbody>
                    {hotspots.map((h, i) => (
                      <tr key={i} className="border-t border-neutral-50">
                        <td className="px-4 py-2.5 font-medium text-neutral-800">{h.camera}</td>
                        <td className="px-4 py-2.5 text-neutral-700 font-semibold">{h.count}</td>
                        <td className="px-4 py-2.5 text-neutral-600">{h.avg_priority.toFixed(1)}</td>
                        <td className="px-4 py-2.5">
                          <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                            h.count >= 20 ? "bg-red-100 text-red-700" :
                            h.count >= 10 ? "bg-orange-100 text-orange-700" :
                            "bg-yellow-50 text-yellow-700"
                          }`}>
                            {h.count >= 20 ? "HIGH" : h.count >= 10 ? "MEDIUM" : "LOW"}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

