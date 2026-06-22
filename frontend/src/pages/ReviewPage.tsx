import { useEffect, useState, useCallback } from "react";
import { getViolations, postAction, snapshotUrl, reportUrl, type Violation, type ViolationFilters } from "../api/client";

// ── constants ──────────────────────────────────────────────────────────────────
const SEVERITY_COLOR: Record<string, string> = {
  CRITICAL: "bg-red-100 text-red-700 border border-red-200",
  HIGH:     "bg-orange-100 text-orange-700 border border-orange-200",
  MEDIUM:   "bg-yellow-100 text-yellow-700 border border-yellow-200",
  LOW:      "bg-neutral-100 text-neutral-600 border border-neutral-200",
};
const ACTION_COLOR: Record<string, string> = {
  CONFIRMED: "bg-green-100 text-green-700",
  DISMISSED: "bg-neutral-100 text-neutral-500",
  ESCALATED: "bg-amber-100 text-amber-700",
};

const STATUS_TABS = [
  { label: "Pending",   value: "pending" },
  { label: "Confirmed", value: "confirmed" },
  { label: "Escalated", value: "escalated" },
  { label: "All",       value: "all" },
];

const VIOLATION_TYPES = [
  "All Types",
  "Helmet Non-Compliance",
  "Seatbelt Non-Compliance",
  "Triple Riding",
  "Wrong-Side Driving",
  "Stop-Line Violation",
  "Red-Light Violation",
  "Illegal Parking",
];

const SEVERITIES = ["CRITICAL", "HIGH", "MEDIUM", "LOW"];

function fmtTs(ts: number) {
  const d = new Date(ts * 1000);
  return d.toLocaleString("en-IN", {
    day: "2-digit", month: "short", year: "numeric",
    hour: "2-digit", minute: "2-digit", hour12: false,
  });
}

// ── Detail modal ───────────────────────────────────────────────────────────────
function ViolationDetail({ v, onClose, onAction }: {
  v: Violation;
  onClose: () => void;
  onAction: (action: string) => void;
}) {
  const fullUrl = v.evidence_hash ? snapshotUrl(v.evidence_hash, "full") : null;
  const cropUrl = v.evidence_hash ? snapshotUrl(v.evidence_hash, "crop") : null;
  const [imgErr, setImgErr] = useState(false);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm"
         onClick={onClose}>
      <div className="bg-white rounded-[4px] shadow-2xl w-full max-w-2xl mx-4 overflow-hidden max-h-[90vh] overflow-y-auto"
           onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-neutral-100 sticky top-0 bg-white z-10">
          <div>
            <p className="text-[10px] font-bold tracking-widest uppercase text-neutral-400">Violation #{v.id}</p>
            <p className="text-[16px] font-semibold text-neutral-900">{v.violation_type}</p>
          </div>
          <button onClick={onClose}
            className="w-8 h-8 rounded-full bg-neutral-100 hover:bg-neutral-200 flex items-center justify-center transition-colors">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        </div>

        <div className="p-6 flex flex-col gap-5">
          {/* Snapshots */}
          {fullUrl && !imgErr ? (
            <div className="grid grid-cols-2 gap-3">
              <div>
                <p className="text-[10px] font-bold tracking-widest uppercase text-neutral-400 mb-2">Full Frame</p>
                <img src={fullUrl} onError={() => setImgErr(true)}
                  className="w-full rounded-[4px] object-cover max-h-48 bg-neutral-50"/>
              </div>
              <div>
                <p className="text-[10px] font-bold tracking-widest uppercase text-neutral-400 mb-2">Vehicle Crop</p>
                <img src={cropUrl ?? ""} onError={() => setImgErr(true)}
                  className="w-full rounded-[4px] object-contain max-h-48 bg-neutral-50"/>
              </div>
            </div>
          ) : (
            <div className="bg-neutral-50 rounded-[4px] p-5 text-center">
              <p className="text-[12px] text-neutral-400">No snapshot captured during detection.</p>
            </div>
          )}

          {/* Details grid */}
          <div className="grid grid-cols-3 gap-2">
            {[
              ["Plate Number",   v.plate_number],
              ["Violation Type", v.violation_type],
              ["Severity",       v.severity],
              ["Confidence",     `${((v.confidence ?? 0) * 100).toFixed(1)}%`],
              ["Priority Score", v.priority_score?.toFixed(1) ?? "—"],
              ["Priority Level", v.priority_level ?? "—"],
              ["Camera",         v.camera_id || "—"],
              ["Timestamp",      fmtTs(v.timestamp)],
              ["Evidence Hash",  v.evidence_hash ? v.evidence_hash.slice(0, 16) + "…" : "—"],
            ].map(([k, val]) => (
              <div key={k} className="bg-neutral-50 rounded-[3px] p-3">
                <p className="text-[9px] font-bold tracking-widest uppercase text-neutral-400 mb-0.5">{k}</p>
                <p className="text-[12px] font-medium text-neutral-900 break-all">{val}</p>
              </div>
            ))}
          </div>

          {/* Status badge */}
          <div className="flex items-center gap-2 flex-wrap">
            <span className={`text-[11px] font-bold px-3 py-1 rounded-full ${SEVERITY_COLOR[v.severity] ?? "bg-neutral-100 text-neutral-600"}`}>
              {v.severity}
            </span>
            {v.operator_action && (
              <span className={`text-[11px] font-semibold px-3 py-1 rounded-full ${ACTION_COLOR[v.operator_action] ?? ""}`}>
                {v.operator_action}
              </span>
            )}
          </div>

          {/* Actions */}
          <div className="flex items-center gap-2 pt-2 border-t border-neutral-100 flex-wrap">
            {!v.operator_action && (
              <>
                <button onClick={() => onAction("CONFIRMED")}
                  className="px-5 py-2 rounded-[3px] bg-green-600 text-white text-[12px] font-bold hover:bg-green-700 transition-colors">
                  Confirm
                </button>
                <button onClick={() => onAction("DISMISSED")}
                  className="px-5 py-2 rounded-[3px] bg-neutral-200 text-neutral-700 text-[12px] font-bold hover:bg-neutral-300 transition-colors">
                  Dismiss
                </button>
                <button onClick={() => onAction("ESCALATED")}
                  className="px-5 py-2 rounded-[3px] bg-amber-500 text-white text-[12px] font-bold hover:bg-amber-600 transition-colors">
                  Escalate
                </button>
              </>
            )}
            <a href={reportUrl(v.id)} target="_blank" rel="noopener noreferrer"
              className="px-5 py-2 rounded-[3px] bg-neutral-900 text-white text-[12px] font-bold hover:bg-neutral-700 transition-colors flex items-center gap-1.5 ml-auto">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                <polyline points="14 2 14 8 20 8"/>
              </svg>
              Generate Report
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Filter bar ─────────────────────────────────────────────────────────────────
interface Filters {
  violation_type: string;
  severities: string[];
  plate: string;
  sort: "newest" | "oldest";
}

function FilterBar({ filters, onChange }: { filters: Filters; onChange: (f: Filters) => void }) {
  const toggle = (sev: string) => {
    const next = filters.severities.includes(sev)
      ? filters.severities.filter(s => s !== sev)
      : [...filters.severities, sev];
    onChange({ ...filters, severities: next });
  };

  return (
    <div className="bg-white border border-neutral-100 rounded-[4px] p-4 mb-4 flex flex-wrap gap-4 items-end shadow-sm">
      {/* Violation type */}
      <div className="flex flex-col gap-1 min-w-[180px]">
        <p className="text-[10px] font-bold tracking-widest uppercase text-neutral-400">Violation Type</p>
        <select
          value={filters.violation_type}
          onChange={e => onChange({ ...filters, violation_type: e.target.value })}
          className="text-[12px] border border-neutral-200 rounded-[3px] px-2 py-1.5 bg-white text-neutral-700 focus:outline-none focus:border-neutral-400">
          {VIOLATION_TYPES.map(t => (
            <option key={t} value={t === "All Types" ? "" : t}>{t}</option>
          ))}
        </select>
      </div>

      {/* Severity chips */}
      <div className="flex flex-col gap-1">
        <p className="text-[10px] font-bold tracking-widest uppercase text-neutral-400">Severity</p>
        <div className="flex gap-1.5">
          {SEVERITIES.map(s => (
            <button key={s}
              onClick={() => toggle(s)}
              className={`text-[10px] font-bold px-2.5 py-1 rounded-full border transition-all ${
                filters.severities.includes(s)
                  ? SEVERITY_COLOR[s]
                  : "bg-white text-neutral-400 border-neutral-200 hover:border-neutral-400"
              }`}>
              {s}
            </button>
          ))}
        </div>
      </div>

      {/* Plate search */}
      <div className="flex flex-col gap-1 min-w-[140px]">
        <p className="text-[10px] font-bold tracking-widest uppercase text-neutral-400">Plate No.</p>
        <input
          type="text"
          placeholder="KA01AB1234"
          value={filters.plate}
          onChange={e => onChange({ ...filters, plate: e.target.value })}
          className="text-[12px] border border-neutral-200 rounded-[3px] px-2 py-1.5 bg-white text-neutral-700 font-mono focus:outline-none focus:border-neutral-400 uppercase"/>
      </div>

      {/* Sort */}
      <div className="flex flex-col gap-1">
        <p className="text-[10px] font-bold tracking-widest uppercase text-neutral-400">Sort</p>
        <div className="flex gap-1 border border-neutral-200 rounded-[3px] p-0.5 bg-neutral-50">
          {(["newest", "oldest"] as const).map(s => (
            <button key={s}
              onClick={() => onChange({ ...filters, sort: s })}
              className={`text-[11px] font-semibold px-3 py-1 rounded-[2px] transition-all ${
                filters.sort === s ? "bg-neutral-900 text-white" : "text-neutral-500 hover:text-neutral-800"
              }`}>
              {s === "newest" ? "Newest First" : "Oldest First"}
            </button>
          ))}
        </div>
      </div>

      {/* Clear */}
      {(filters.violation_type || filters.severities.length || filters.plate) && (
        <button
          onClick={() => onChange({ violation_type: "", severities: [], plate: "", sort: filters.sort })}
          className="text-[11px] font-semibold text-neutral-400 hover:text-neutral-700 underline underline-offset-2 self-end pb-0.5">
          Clear filters
        </button>
      )}
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────
const PAGE_SIZE = 50;

export default function ReviewPage() {
  const [tab, setTab]               = useState("pending");
  const [violations, setViolations] = useState<Violation[]>([]);
  const [total, setTotal]           = useState(0);
  const [offset, setOffset]         = useState(0);
  const [loading, setLoading]       = useState(true);
  const [acting, setActing]         = useState<number | null>(null);
  const [selected, setSelected]     = useState<Violation | null>(null);
  const [filters, setFilters]       = useState<Filters>({
    violation_type: "", severities: [], plate: "", sort: "newest"
  });

  const load = useCallback((reset = false) => {
    setLoading(true);
    const off = reset ? 0 : offset;
    getViolations({
      status:         tab,
      limit:          PAGE_SIZE,
      offset:         off,
      violation_type: filters.violation_type || undefined,
      severity:       filters.severities.length ? filters.severities.join(",") : undefined,
      plate:          filters.plate || undefined,
      sort:           filters.sort,
    }).then(r => {
      if (reset) {
        setViolations(r.violations);
        setOffset(0);
      } else {
        setViolations(v => [...v, ...r.violations]);
      }
      setTotal(r.total ?? r.count);
    }).finally(() => setLoading(false));
  }, [tab, filters, offset]);

  // Re-fetch when tab or filters change
  useEffect(() => {
    setOffset(0);
    setViolations([]);
    setLoading(true);
    getViolations({
      status:         tab,
      limit:          PAGE_SIZE,
      offset:         0,
      violation_type: filters.violation_type || undefined,
      severity:       filters.severities.length ? filters.severities.join(",") : undefined,
      plate:          filters.plate || undefined,
      sort:           filters.sort,
    }).then(r => {
      setViolations(r.violations);
      setTotal(r.total ?? r.count);
    }).finally(() => setLoading(false));
  }, [tab, filters]);

  async function doAction(id: number, action: string) {
    setActing(id);
    try {
      await postAction(id, action);
      setViolations(v => v.filter(x => x.id !== id));
      setTotal(t => t - 1);
      setSelected(null);
    } catch {}
    setActing(null);
  }

  function loadMore() {
    const newOff = offset + PAGE_SIZE;
    setOffset(newOff);
    setLoading(true);
    getViolations({
      status:         tab,
      limit:          PAGE_SIZE,
      offset:         newOff,
      violation_type: filters.violation_type || undefined,
      severity:       filters.severities.length ? filters.severities.join(",") : undefined,
      plate:          filters.plate || undefined,
      sort:           filters.sort,
    }).then(r => {
      setViolations(v => [...v, ...r.violations]);
    }).finally(() => setLoading(false));
  }

  const pendingCount = tab === "pending" ? total : undefined;

  return (
    <div>
      {selected && (
        <ViolationDetail
          v={selected}
          onClose={() => setSelected(null)}
          onAction={action => doAction(selected.id, action)}/>
      )}

      <div className="mb-6">
        <p className="text-[10px] font-bold tracking-[0.16em] uppercase text-neutral-400 mb-1">Operator Review</p>
        <h1 className="text-3xl font-semibold tracking-tight text-neutral-900" style={{ fontFamily: "'Outfit', sans-serif" }}>
          Review Queue
        </h1>
        <p className="text-[13px] text-neutral-400 mt-1">Click any row to view evidence snapshots and full violation details</p>
      </div>

      {/* Status tabs */}
      <div className="flex gap-1 p-1 bg-white rounded-[4px] border border-neutral-100 mb-4 w-fit">
        {STATUS_TABS.map(t => (
          <button key={t.value} onClick={() => setTab(t.value)}
            className={`px-4 py-1.5 rounded-[3px] text-[12px] font-semibold transition-all ${
              tab === t.value ? "bg-neutral-900 text-white" : "text-neutral-500 hover:text-neutral-900"
            }`}>
            {t.label}
            {t.value === tab && total > 0 && (
              <span className="ml-1.5 bg-neutral-700 text-white text-[10px] font-bold px-1.5 py-0.5 rounded-full">{total}</span>
            )}
          </button>
        ))}
      </div>

      {/* Filter bar */}
      <FilterBar filters={filters} onChange={f => setFilters(f)} />

      {/* Table */}
      {loading && violations.length === 0 ? (
        <div className="flex flex-col gap-2">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="bg-white rounded-[4px] h-12 animate-pulse border border-neutral-100"/>
          ))}
        </div>
      ) : violations.length === 0 ? (
        <div className="bg-white rounded-[4px] p-12 border border-neutral-100 text-center">
          <p className="text-[14px] text-neutral-400">No violations match the current filters.</p>
        </div>
      ) : (
        <div className="bg-white rounded-[4px] border border-neutral-100 shadow-sm overflow-hidden">
          {/* Table header */}
          <div className="grid gap-3 px-4 py-2.5 border-b border-neutral-100 bg-neutral-50"
               style={{ gridTemplateColumns: "40px 1fr 1fr 80px 90px 80px 160px 130px" }}>
            {["#", "Plate", "Type", "Sev.", "Conf.", "Camera", "Timestamp", "Actions"].map(h => (
              <p key={h} className="text-[9px] font-bold tracking-[0.14em] uppercase text-neutral-400">{h}</p>
            ))}
          </div>

          {violations.map(v => (
            <div key={v.id}
              onClick={() => setSelected(v)}
              className="grid gap-3 items-center px-4 py-3 border-b border-neutral-50 last:border-0 hover:bg-neutral-50 transition-colors cursor-pointer"
              style={{ gridTemplateColumns: "40px 1fr 1fr 80px 90px 80px 160px 130px" }}>
              {/* ID */}
              <p className="text-[11px] font-mono text-neutral-300">#{v.id}</p>

              {/* Plate */}
              <div className="flex items-center gap-1.5 min-w-0">
                <span className="text-[12px] font-mono font-semibold text-neutral-900 truncate">{v.plate_number}</span>
                {v.evidence_hash && (
                  <span className="w-1.5 h-1.5 rounded-full bg-green-400 shrink-0" title="Snapshot available"/>
                )}
              </div>

              {/* Violation type */}
              <p className="text-[12px] text-neutral-700 truncate">{v.violation_type}</p>

              {/* Severity */}
              <span className={`text-[9px] font-bold px-2 py-0.5 rounded-full w-fit ${SEVERITY_COLOR[v.severity] ?? "bg-neutral-100 text-neutral-600"}`}>
                {v.severity}
              </span>

              {/* Confidence */}
              <div className="flex items-center gap-1.5">
                <div className="flex-1 h-1 bg-neutral-100 rounded-full overflow-hidden">
                  <div className="h-full bg-neutral-400 rounded-full" style={{ width: `${Math.round((v.confidence ?? 0) * 100)}%` }}/>
                </div>
                <p className="text-[11px] font-mono text-neutral-500 shrink-0">{((v.confidence ?? 0) * 100).toFixed(0)}%</p>
              </div>

              {/* Camera */}
              <p className="text-[11px] text-neutral-400 truncate">{v.camera_id?.replace(/_/g, " ") || "—"}</p>

              {/* Timestamp */}
              <p className="text-[10px] font-mono text-neutral-500">{fmtTs(v.timestamp)}</p>

              {/* Actions */}
              <div className="flex items-center gap-1" onClick={e => e.stopPropagation()}>
                {v.operator_action ? (
                  <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${ACTION_COLOR[v.operator_action] ?? ""}`}>
                    {v.operator_action}
                  </span>
                ) : (
                  <>
                    <button disabled={acting === v.id} onClick={() => doAction(v.id, "CONFIRMED")}
                      title="Confirm"
                      className="w-6 h-6 rounded-[3px] bg-green-600 text-white text-[10px] font-bold hover:bg-green-700 disabled:opacity-40 transition-colors flex items-center justify-center">
                      ✓
                    </button>
                    <button disabled={acting === v.id} onClick={() => doAction(v.id, "DISMISSED")}
                      title="Dismiss"
                      className="w-6 h-6 rounded-[3px] bg-neutral-200 text-neutral-700 text-[10px] font-bold hover:bg-neutral-300 disabled:opacity-40 transition-colors flex items-center justify-center">
                      ✕
                    </button>
                    <button disabled={acting === v.id} onClick={() => doAction(v.id, "ESCALATED")}
                      title="Escalate"
                      className="w-6 h-6 rounded-[3px] bg-amber-500 text-white text-[10px] font-bold hover:bg-amber-600 disabled:opacity-40 transition-colors flex items-center justify-center">
                      ↑
                    </button>
                  </>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Load more / pagination */}
      {violations.length > 0 && violations.length < total && (
        <div className="mt-4 flex items-center justify-between">
          <p className="text-[12px] text-neutral-400">
            Showing {violations.length} of {total} violations
          </p>
          <button onClick={loadMore} disabled={loading}
            className="px-5 py-2 rounded-[3px] bg-neutral-900 text-white text-[12px] font-semibold hover:bg-neutral-700 disabled:opacity-40 transition-colors">
            {loading ? "Loading…" : `Load more (${total - violations.length} remaining)`}
          </button>
        </div>
      )}
      {violations.length > 0 && violations.length >= total && (
        <p className="text-[12px] text-neutral-400 mt-3 text-center">All {total} records loaded</p>
      )}
    </div>
  );
}
