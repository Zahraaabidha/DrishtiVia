import { RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer, Tooltip } from "recharts";

const MODELS = [
  {
    name: "Helmet Non-Compliance",
    color: "#e63946",
    colorLight: "#fde8ea",
    mAP50:     0.788,
    precision: 0.845,
    recall:    0.626,
    trainImages: 629,
    valImages:   158,
    classes: ["with_helmet", "without_helmet"],
    notes: "Trained on Indian roads dataset. Covers full-face, half-face, and no-helmet scenarios. Robust against auto-rickshaw riders and pillion passengers.",
  },
  {
    name: "Seatbelt Non-Compliance",
    color: "#f77f00",
    colorLight: "#fff1e0",
    mAP50:     0.911,
    precision: 0.912,
    recall:    0.842,
    trainImages: 660,
    valImages:   165,
    classes: ["with_seatbelt", "without_seatbelt"],
    notes: "Best-performing model. Trained on dashcam and CCTV angles with varied lighting. High precision reduces false positives in review queue.",
  },
  {
    name: "Wrong-Side Driving",
    color: "#2b9348",
    colorLight: "#e8f5e9",
    mAP50:     0.977,
    precision: 0.943,
    recall:    0.961,
    trainImages: 608,
    valImages:   152,
    classes: ["wrong_side"],
    notes: "Highest accuracy model. Detects contraflow vehicles on one-way roads and divided highways. Near-perfect recall reduces missed violations.",
  },
];

function StatBar({ value, max = 1, color }: { value: number; max?: number; color: string }) {
  const pct = Math.round((value / max) * 100);
  return (
    <div className="flex items-center gap-3">
      <div className="flex-1 h-1.5 bg-neutral-100 rounded-full overflow-hidden">
        <div className="h-full rounded-full transition-all duration-500" style={{ width: `${pct}%`, background: color }} />
      </div>
      <span className="text-[12px] font-mono font-bold text-neutral-700 w-12 text-right">{(value * 100).toFixed(1)}%</span>
    </div>
  );
}

function ModelCard({ model }: { model: typeof MODELS[0] }) {
  const radarData = [
    { metric: "mAP50",     value: +(model.mAP50 * 100).toFixed(1) },
    { metric: "Precision", value: +(model.precision * 100).toFixed(1) },
    { metric: "Recall",    value: +(model.recall * 100).toFixed(1) },
  ];

  return (
    <div className="bg-white border border-neutral-100 rounded-[4px] shadow-sm overflow-hidden">
      {/* Card header */}
      <div className="px-6 pt-5 pb-4 border-b border-neutral-100" style={{ borderLeftColor: model.color, borderLeftWidth: 3 }}>
        <p className="text-[10px] font-bold tracking-[0.16em] uppercase text-neutral-400 mb-1">Fine-tuned YOLOv8s</p>
        <h2 className="text-[17px] font-semibold text-neutral-900" style={{ fontFamily: "'Outfit', sans-serif" }}>
          {model.name}
        </h2>
      </div>

      <div className="p-6 grid grid-cols-[1fr_180px] gap-6">
        {/* Left: metrics */}
        <div className="flex flex-col gap-5">
          {/* Key stats */}
          <div className="grid grid-cols-3 gap-3">
            {[
              { label: "mAP@50",    value: model.mAP50 },
              { label: "Precision", value: model.precision },
              { label: "Recall",    value: model.recall },
            ].map(({ label, value }) => (
              <div key={label} className="rounded-[4px] p-3" style={{ background: model.colorLight }}>
                <p className="text-[10px] font-bold tracking-widest uppercase text-neutral-400 mb-1">{label}</p>
                <p className="text-[22px] font-bold" style={{ color: model.color }}>
                  {(value * 100).toFixed(1)}<span className="text-[13px] font-semibold">%</span>
                </p>
              </div>
            ))}
          </div>

          {/* Bar chart metrics */}
          <div className="flex flex-col gap-2.5">
            <p className="text-[10px] font-bold tracking-[0.14em] uppercase text-neutral-400">Performance Breakdown</p>
            {[
              { label: "mAP@50",    value: model.mAP50 },
              { label: "Precision", value: model.precision },
              { label: "Recall",    value: model.recall },
            ].map(({ label, value }) => (
              <div key={label}>
                <p className="text-[11px] text-neutral-500 mb-1">{label}</p>
                <StatBar value={value} color={model.color} />
              </div>
            ))}
          </div>

          {/* Training info */}
          <div className="grid grid-cols-2 gap-3">
            <div className="bg-neutral-50 rounded-[3px] p-3">
              <p className="text-[10px] font-bold tracking-widest uppercase text-neutral-400 mb-0.5">Training Images</p>
              <p className="text-[15px] font-bold text-neutral-900">{model.trainImages.toLocaleString()}</p>
            </div>
            <div className="bg-neutral-50 rounded-[3px] p-3">
              <p className="text-[10px] font-bold tracking-widest uppercase text-neutral-400 mb-0.5">Validation Images</p>
              <p className="text-[15px] font-bold text-neutral-900">{model.valImages.toLocaleString()}</p>
            </div>
          </div>

          {/* Classes */}
          <div>
            <p className="text-[10px] font-bold tracking-[0.14em] uppercase text-neutral-400 mb-2">Output Classes</p>
            <div className="flex gap-2 flex-wrap">
              {model.classes.map(c => (
                <span key={c} className="text-[11px] font-mono px-2.5 py-1 rounded-[3px] bg-neutral-100 text-neutral-700">{c}</span>
              ))}
            </div>
          </div>

          {/* Notes */}
          <p className="text-[12px] text-neutral-500 leading-relaxed">{model.notes}</p>
        </div>

        {/* Right: radar chart */}
        <div className="flex flex-col items-center justify-center">
          <p className="text-[10px] font-bold tracking-[0.14em] uppercase text-neutral-400 mb-2">Metric Radar</p>
          <ResponsiveContainer width="100%" height={160}>
            <RadarChart data={radarData}>
              <PolarGrid stroke="#e5e7eb" />
              <PolarAngleAxis dataKey="metric" tick={{ fontSize: 10, fill: "#9ca3af" }} />
              <PolarRadiusAxis angle={90} domain={[0, 100]} tick={false} axisLine={false} />
              <Radar dataKey="value" stroke={model.color} fill={model.color} fillOpacity={0.25} strokeWidth={2} />
              <Tooltip
                formatter={(v: number) => [`${v}%`, ""]}
                contentStyle={{ fontSize: 11, borderRadius: 3, border: "1px solid #e5e7eb" }}
              />
            </RadarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}

const COMPARISON = [
  { metric: "mAP@50",    Helmet: 78.8, Seatbelt: 91.1, WrongSide: 97.7 },
  { metric: "Precision", Helmet: 84.5, Seatbelt: 91.2, WrongSide: 94.3 },
  { metric: "Recall",    Helmet: 62.6, Seatbelt: 84.2, WrongSide: 96.1 },
];

export default function ModelPerformancePage() {
  return (
    <div>
      <div className="mb-7">
        <p className="text-[10px] font-bold tracking-[0.16em] uppercase text-neutral-400 mb-1">AI Models</p>
        <h1 className="text-3xl font-semibold tracking-tight text-neutral-900" style={{ fontFamily: "'Outfit', sans-serif" }}>
          Model Performance
        </h1>
        <p className="text-[13px] text-neutral-400 mt-1">
          Three fine-tuned YOLOv8s classifiers trained on Indian traffic datasets — Helmet, Seatbelt, Wrong-Side
        </p>
      </div>

      {/* Summary comparison table */}
      <div className="bg-white border border-neutral-100 rounded-[4px] shadow-sm mb-6 overflow-hidden">
        <div className="px-6 py-4 border-b border-neutral-100">
          <p className="text-[10px] font-bold tracking-[0.16em] uppercase text-neutral-400">Cross-Model Comparison</p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-[12px]">
            <thead>
              <tr className="bg-neutral-50 border-b border-neutral-100">
                <th className="text-left px-6 py-3 text-[10px] font-bold tracking-widest uppercase text-neutral-400 font-semibold">Metric</th>
                {MODELS.map(m => (
                  <th key={m.name} className="text-center px-6 py-3 text-[10px] font-bold tracking-widest uppercase font-semibold" style={{ color: m.color }}>
                    {m.name.split(" ")[0]}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {COMPARISON.map((row, i) => (
                <tr key={row.metric} className={i % 2 === 0 ? "bg-white" : "bg-neutral-50/50"}>
                  <td className="px-6 py-3 font-semibold text-neutral-600">{row.metric}</td>
                  <td className="px-6 py-3 text-center font-mono font-bold" style={{ color: MODELS[0].color }}>{row.Helmet}%</td>
                  <td className="px-6 py-3 text-center font-mono font-bold" style={{ color: MODELS[1].color }}>{row.Seatbelt}%</td>
                  <td className="px-6 py-3 text-center font-mono font-bold" style={{ color: MODELS[2].color }}>{row.WrongSide}%</td>
                </tr>
              ))}
              <tr className="bg-neutral-50 border-t border-neutral-100">
                <td className="px-6 py-3 font-semibold text-neutral-600">Training Images</td>
                {MODELS.map(m => (
                  <td key={m.name} className="px-6 py-3 text-center font-mono font-bold text-neutral-700">{m.trainImages}</td>
                ))}
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* Individual model cards */}
      <div className="flex flex-col gap-5">
        {MODELS.map(m => (
          <ModelCard key={m.name} model={m} />
        ))}
      </div>

      {/* Architecture note */}
      <div className="mt-6 bg-white border border-neutral-100 rounded-[4px] p-5 shadow-sm">
        <p className="text-[10px] font-bold tracking-[0.16em] uppercase text-neutral-400 mb-2">Architecture</p>
        <p className="text-[12px] text-neutral-600 leading-relaxed">
          All three models share the <strong>YOLOv8s backbone</strong> (Small variant, 11.2M parameters) fine-tuned on domain-specific datasets curated from Bangalore traffic cameras, dashcam footage, and publicly available Indian road datasets.
          The base COCO model runs in parallel for vehicle tracking via <strong>ByteTrack</strong> (persist=True), providing track IDs used to correlate violations across frames.
          Inference runs on CPU (or GPU if CUDA available) with <strong>CLAHE + dark-channel dehazing</strong> preprocessing to handle Bangalore's dust/rain/haze conditions.
        </p>
      </div>
    </div>
  );
}
