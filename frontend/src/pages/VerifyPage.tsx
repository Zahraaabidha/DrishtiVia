import { useState } from "react";
import { verifyHash } from "../api/client";

const EXAMPLE_HASHES = [
  { label: "Seed record (Helmet)", hash: "abc123" },
  { label: "Seed record (Triple Riding)", hash: "def456" },
  { label: "Seed record (Red-Light)", hash: "ghi789" },
];

const COC_TABLE = [
  { layer: "Hash Algorithm",    proto: "SHA-256 ✅",            prod: "SHA-256 ✅" },
  { layer: "Signing",           proto: "RSA software key ✅",   prod: "RSA + HSM/TPM chip" },
  { layer: "Key Protection",    proto: "File on disk",          prod: "Infineon SLB9670 (tamper-erasure)" },
  { layer: "Timestamp",         proto: "System clock",          prod: "NTP + GPS satellite time" },
  { layer: "Blockchain Anchor", proto: "Mock TX ID ✅",         prod: "Polygon network (real)" },
  { layer: "Transmission",      proto: "Local SQLite",          prod: "TLS 1.3 → BTP write-once DB" },
  { layer: "VAHAN Lookup",      proto: "Mock database ✅",      prod: "Live BTP API credentials" },
];

export default function VerifyPage() {
  const [hash, setHash]       = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult]   = useState<any>(null);
  const [error, setError]     = useState<string | null>(null);

  async function verify(h = hash) {
    if (!h.trim()) return;
    setLoading(true); setError(null); setResult(null);
    try {
      const r = await verifyHash(h.trim());
      setResult(r);
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? "Verification failed — check backend is running");
    } finally { setLoading(false); }
  }

  return (
    <div>
      <div className="mb-7">
        <p className="text-[10px] font-bold tracking-[0.16em] uppercase text-neutral-400 mb-1">Evidence Verification</p>
        <h1 className="text-3xl font-semibold tracking-tight text-neutral-900" style={{ fontFamily: "'Outfit', sans-serif" }}>
          Evidence Integrity
        </h1>
        <p className="text-[13px] text-neutral-400 mt-1">
          Verify SHA-256 hash and RSA-PSS signature to validate chain-of-custody provenance
        </p>
      </div>

      <div className="grid grid-cols-3 gap-4">
        {/* Left: input + explainer */}
        <div className="col-span-1 flex flex-col gap-4">

          {/* How it works */}
          <div className="bg-neutral-900 text-white rounded-[4px] p-5">
            <p className="text-[10px] font-bold tracking-[0.16em] uppercase text-neutral-400 mb-3">How it works</p>
            <div className="flex flex-col gap-3">
              {[
                ["1", "Detection fires", "YOLOv8 confirms a violation with 3-of-5 temporal frames"],
                ["2", "Evidence generated", "Full frame + vehicle crop saved; all fields SHA-256 hashed"],
                ["3", "Hash stored", "Hash written to SQLite with RSA-PSS signature"],
                ["4", "You verify", "Paste the hash — any field tampering breaks the hash"],
              ].map(([n, t, d]) => (
                <div key={n} className="flex gap-3">
                  <div className="w-5 h-5 rounded-full bg-white/10 text-white text-[10px] font-bold flex items-center justify-center shrink-0">{n}</div>
                  <div>
                    <p className="text-[12px] font-semibold">{t}</p>
                    <p className="text-[11px] text-neutral-400">{d}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Example hashes */}
          <div className="bg-white rounded-[4px] p-5 border border-neutral-100 shadow-sm">
            <p className="text-[10px] font-bold tracking-[0.16em] uppercase text-neutral-400 mb-3">Example Hashes (seed data)</p>
            <div className="flex flex-col gap-2">
              {EXAMPLE_HASHES.map(e => (
                <button key={e.hash} onClick={() => { setHash(e.hash); verify(e.hash); }}
                  className="flex items-center justify-between p-2.5 rounded-[3px] bg-neutral-50 hover:bg-neutral-100 transition-colors text-left">
                  <div>
                    <p className="text-[12px] font-medium text-neutral-900">{e.label}</p>
                    <p className="text-[11px] font-mono text-neutral-400">{e.hash}</p>
                  </div>
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#999" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <polyline points="9 18 15 12 9 6"/>
                  </svg>
                </button>
              ))}
            </div>
            <p className="text-[10px] text-neutral-400 mt-3">These hashes come from the seed rows auto-inserted into violations.db on first run.</p>
          </div>
        </div>

        {/* Right: input + result */}
        <div className="col-span-2 flex flex-col gap-4">

          {/* Input */}
          <div className="bg-white rounded-[4px] p-5 border border-neutral-100 shadow-sm">
            <p className="text-[10px] font-bold tracking-[0.16em] uppercase text-neutral-400 mb-3">Enter Evidence Hash</p>
            <div className="flex gap-2 mb-2">
              <input type="text" value={hash} onChange={e => setHash(e.target.value)}
                placeholder="SHA-256 hash from evidence record…"
                onKeyDown={e => e.key === "Enter" && verify()}
                className="flex-1 text-[13px] font-mono border border-neutral-200 rounded-[3px] px-4 py-2.5 focus:outline-none focus:border-neutral-400 transition-colors"/>
              <button onClick={() => verify()} disabled={!hash.trim() || loading}
                className="px-5 py-2.5 rounded-full bg-neutral-900 text-white text-[13px] font-semibold hover:bg-neutral-700 disabled:opacity-40 transition-all">
                {loading ? "…" : "🔐 Verify"}
              </button>
            </div>
            <p className="text-[11px] text-neutral-400">The hash is stored in the <code className="font-mono bg-neutral-100 px-1 rounded">evidence_hash</code> column of the violations database. You can also find it in the Review Queue → violation detail panel.</p>
          </div>

          {error && (
            <div className="bg-red-50 border border-red-200 rounded-[4px] p-4 text-[12px] text-red-700">{error}</div>
          )}

          {result && (
            <div className={`rounded-[4px] p-5 border shadow-sm ${result.found ? "bg-white border-neutral-100" : "bg-red-50 border-red-200"}`}>
              {result.found ? (
                <>
                  <div className="flex items-center gap-2 mb-4">
                    <div className="w-8 h-8 rounded-full bg-green-100 flex items-center justify-center shrink-0">
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#16a34a" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                        <polyline points="20 6 9 17 4 12"/>
                      </svg>
                    </div>
                    <div>
                      <p className="text-[14px] font-bold text-green-800">Hash Verified — Record Authentic</p>
                      <p className="text-[11px] text-neutral-500">This evidence has not been tampered with since generation</p>
                    </div>
                  </div>

                  <div className="grid grid-cols-3 gap-3 mb-4">
                    {[
                      ["Plate",        result.record?.plate_number],
                      ["Violation",    result.record?.violation_type],
                      ["Severity",     result.record?.severity ?? result.record?.priority_level ?? "—"],
                      ["Confidence",   result.record?.confidence ? `${(result.record.confidence * 100).toFixed(1)}%` : "—"],
                      ["Priority",     result.record?.priority_score?.toFixed(1) ?? "—"],
                      ["Camera",       result.record?.camera_id ?? "—"],
                      ["Timestamp",    result.record?.timestamp ? new Date(result.record.timestamp * 1000).toLocaleString() : "—"],
                      ["Operator",     result.record?.operator_action ?? "Pending"],
                      ["Hash (first 16)", result.record?.evidence_hash?.slice(0, 16) + "…"],
                    ].map(([k, v]) => (
                      <div key={k} className="bg-neutral-50 rounded-[3px] p-3">
                        <p className="text-[10px] font-bold tracking-widest uppercase text-neutral-400 mb-0.5">{k}</p>
                        <p className="text-[12px] font-medium text-neutral-900 break-all">{v ?? "—"}</p>
                      </div>
                    ))}
                  </div>

                  {/* Snapshot availability */}
                  <div className="bg-neutral-50 rounded-[4px] p-3 flex items-center gap-3">
                    <div className={`w-2.5 h-2.5 rounded-full ${result.snapshots?.full ? "bg-green-500" : "bg-neutral-300"}`}/>
                    <p className="text-[12px] text-neutral-600">
                      Snapshot: {result.snapshots?.full ? "Full frame + crop available" : "Snapshot was not captured during this detection"}
                    </p>
                  </div>
                </>
              ) : (
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-full bg-red-100 flex items-center justify-center shrink-0">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#dc2626" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                      <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
                    </svg>
                  </div>
                  <div>
                    <p className="text-[14px] font-bold text-red-800">Hash Not Found</p>
                    <p className="text-[12px] text-red-600">No matching record in the database. Either the hash is incorrect, or the record has been deleted.</p>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Chain of custody table */}
          <div className="bg-white rounded-[4px] p-5 border border-neutral-100 shadow-sm">
            <p className="text-[10px] font-bold tracking-[0.16em] uppercase text-neutral-400 mb-4">Chain of Custody Layers</p>
            <div className="overflow-hidden rounded-[3px] border border-neutral-100">
              <table className="w-full text-[12px]">
                <thead>
                  <tr className="bg-neutral-50">
                    <th className="text-left px-4 py-2.5 text-[10px] font-bold tracking-widest uppercase text-neutral-400">Layer</th>
                    <th className="text-left px-4 py-2.5 text-[10px] font-bold tracking-widest uppercase text-neutral-400">Prototype</th>
                    <th className="text-left px-4 py-2.5 text-[10px] font-bold tracking-widest uppercase text-neutral-400">Production</th>
                  </tr>
                </thead>
                <tbody>
                  {COC_TABLE.map((row, i) => (
                    <tr key={i} className="border-t border-neutral-50">
                      <td className="px-4 py-2.5 font-medium text-neutral-700">{row.layer}</td>
                      <td className="px-4 py-2.5 text-neutral-600">{row.proto}</td>
                      <td className="px-4 py-2.5 text-neutral-500">{row.prod}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

