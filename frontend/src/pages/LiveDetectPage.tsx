import { useRef, useState, useCallback, useEffect } from "react";
import {
  detectImage, uploadVideoForStream, videoStreamUrl, liveStreamUrl, saveViolation, snapshotUrl, postAction,
  type DetectImageResult, type DetectionViolation, type DetectOptions
} from "../api/client";

const SEVERITY_COLOR: Record<string, string> = {
  CRITICAL: "bg-red-100 text-red-700 border border-red-200",
  HIGH:     "bg-orange-100 text-orange-700 border border-orange-200",
  MEDIUM:   "bg-yellow-100 text-yellow-700 border border-yellow-200",
  LOW:      "bg-neutral-100 text-neutral-600",
};
const SEVERITY_PRIORITY: Record<string, number> = { CRITICAL: 4, HIGH: 3, MEDIUM: 2, LOW: 1 };
const ACCURACY_LABELS: Record<string, string> = {
  "Helmet Non-Compliance":   "Fine-tuned · mAP50 ~0.82 · thresholds 0.38/0.45",
  "Seatbelt Non-Compliance": "Fine-tuned · mAP50 0.901 · threshold 0.40",
  "Wrong-Side Driving":      "Fine-tuned · mAP50 0.975 · threshold 0.40",
  "Triple Riding":           "Geometric overlap + posture filter · base COCO model",
  "Illegal Parking":         "ByteTrack position history · stationary < 18px / 15 frames",
  "Stop-Line Violation":     "Geometric stop-line Y crossing · base model bbox",
  "Red-Light Violation":     "Stop-line + signal_red flag · base model bbox",
};
const CAMERA_LABELS = [
  "Silk Board Junction — Bengaluru",
  "KR Circle — Bengaluru",
  "Hebbal Flyover — Bengaluru",
  "Marathahalli Bridge — Bengaluru",
  "Whitefield Signal — Bengaluru",
];
const SCENE_TYPES = ["Junction", "Parking Area", "Highway"];
const FLOW_DIRS   = ["Left -> Right", "Right -> Left"];

type Mode = "image" | "video" | "stream";

function ViolationModal({ v, onClose }: { v: DetectionViolation; onClose: () => void }) {
  const [action, setAction] = useState<string | null>(null);

  const doAction = async (act: string) => {
    if (!v.db_id) return;
    await postAction(v.db_id, act).catch(() => {});
    setAction(act);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-[2px]"
      onClick={onClose}>
      <div className="bg-white rounded-[6px] shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto"
        onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between px-6 pt-5 pb-3 border-b border-neutral-100">
          <div>
            <p className="text-[10px] font-bold tracking-[0.14em] uppercase text-neutral-400">
              {v.db_id ? `Violation #${v.db_id}` : "Live Detection"}
            </p>
            <h2 className="text-[18px] font-bold text-neutral-900 mt-0.5">{v.type}</h2>
          </div>
          <button onClick={onClose}
            className="w-8 h-8 rounded-full border border-neutral-200 flex items-center justify-center text-neutral-500 hover:bg-neutral-50">
            ×
          </button>
        </div>

        {/* Evidence snapshots */}
        {v.evidence_hash ? (
          <div className="grid grid-cols-2 gap-3 p-6 pb-4">
            <div>
              <p className="text-[10px] font-bold tracking-widest uppercase text-neutral-400 mb-2">Full Frame</p>
              <div className="w-full rounded border border-neutral-100 bg-neutral-50 overflow-hidden" style={{ height: 200 }}>
                <img src={snapshotUrl(v.evidence_hash, "full")} alt="full frame"
                  loading="eager"
                  className="w-full h-full object-cover"
                  onError={e => { (e.target as HTMLImageElement).parentElement!.style.display = "none"; }}/>
              </div>
            </div>
            <div>
              <p className="text-[10px] font-bold tracking-widest uppercase text-neutral-400 mb-2">Vehicle Crop</p>
              <div className="w-full rounded border border-neutral-100 bg-neutral-50 overflow-hidden" style={{ height: 200 }}>
                <img src={snapshotUrl(v.evidence_hash, "crop")} alt="vehicle crop"
                  loading="eager"
                  className="w-full h-full object-contain"
                  onError={e => { (e.target as HTMLImageElement).parentElement!.style.display = "none"; }}/>
              </div>
            </div>
          </div>
        ) : (
          <div className="px-6 pt-5 pb-2">
            <p className="text-[11px] text-amber-600 bg-amber-50 rounded px-3 py-2">
              Evidence snapshots not yet saved — violation was detected but not confirmed to DB.
            </p>
          </div>
        )}

        {/* Metadata grid */}
        <div className="grid grid-cols-3 gap-2 px-6 pb-4">
          {[
            ["Violation Type", v.type],
            ["Severity",       v.severity],
            ["Confidence",     `${(v.confidence * 100).toFixed(1)}%`],
            ["Vehicle ID",     v.vehicle_id || "—"],
            ["Sightings",      v.sightings !== undefined ? `${v.sightings}×` : "—"],
            ["Frame",          v.frame !== undefined ? `f${v.frame}` : "—"],
            ["Evidence Hash",  v.evidence_hash ?? "Not saved"],
          ].map(([k, val]) => (
            <div key={k} className="bg-neutral-50 rounded-[3px] p-3 col-span-1 last:col-span-3">
              <p className="text-[9px] font-bold tracking-widest uppercase text-neutral-400 mb-0.5">{k}</p>
              <p className="text-[11px] font-medium text-neutral-900 break-all">{val}</p>
            </div>
          ))}
        </div>

        {v.description && (
          <p className="px-6 pb-4 text-[11px] text-neutral-500 italic">{v.description}</p>
        )}

        {/* Severity badge */}
        <div className="px-6 pb-4 flex gap-2 flex-wrap items-center">
          <span className={`text-[11px] font-bold px-3 py-1 rounded-full ${SEVERITY_COLOR[v.severity] ?? "bg-neutral-100 text-neutral-600"}`}>
            {v.severity}
          </span>
          {v.evidence_hash && (
            <span className="text-[10px] font-semibold text-green-700 bg-green-50 px-2.5 py-1 rounded-full">✓ Saved to DB</span>
          )}
        </div>

        {/* Actions — only if saved to DB */}
        {v.db_id && (
          <div className="flex items-center gap-3 px-6 pb-5 border-t border-neutral-100 pt-4">
            {action ? (
              <p className="text-[12px] font-semibold text-green-700 bg-green-50 px-4 py-2 rounded-full">
                ✓ Marked as {action}
              </p>
            ) : (
              <>
                <button onClick={() => doAction("CONFIRMED")}
                  className="px-5 py-2.5 bg-green-600 text-white text-[12px] font-semibold rounded hover:bg-green-700 transition-colors">
                  ✓ Confirm
                </button>
                <button onClick={() => doAction("DISMISSED")}
                  className="px-5 py-2.5 border border-neutral-300 text-neutral-700 text-[12px] font-semibold rounded hover:bg-neutral-50 transition-colors">
                  ✕ Dismiss
                </button>
                <button onClick={() => doAction("ESCALATED")}
                  className="px-5 py-2.5 bg-amber-500 text-white text-[12px] font-semibold rounded hover:bg-amber-600 transition-colors">
                  ↑ Escalate
                </button>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function ViolationCard({ v, flash }: { v: DetectionViolation; flash?: boolean }) {
  const [showModal, setShowModal] = useState(false);
  return (
    <>
      <div className={`rounded-[4px] border p-3.5 cursor-pointer hover:shadow-sm transition-all ${
        flash ? "animate-pulse" : ""
      } ${
        v.severity === "CRITICAL" ? "border-red-200 bg-red-50" :
        v.severity === "HIGH"     ? "border-orange-200 bg-orange-50" :
        v.severity === "MEDIUM"   ? "border-yellow-100 bg-yellow-50" : "border-neutral-100 bg-white"
      }`} onClick={() => setShowModal(true)}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <span className={`text-[10px] font-bold px-2.5 py-0.5 rounded-full ${SEVERITY_COLOR[v.severity] ?? "bg-neutral-100 text-neutral-600"}`}>
              {v.severity}
            </span>
            <span className="text-[13px] font-semibold text-neutral-900">{v.type}</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-[13px] font-bold text-neutral-700">{(v.confidence * 100).toFixed(1)}%</span>
            {v.evidence_hash && <span className="text-[9px] text-green-600 font-semibold">✓ Saved</span>}
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#999" strokeWidth="2"><path d="M9 18l6-6-6-6"/></svg>
          </div>
        </div>
        <p className="text-[10px] text-neutral-400 mt-1">Click to view evidence &amp; details</p>
      </div>
      {showModal && <ViolationModal v={v} onClose={() => setShowModal(false)} />}
    </>
  );
}

export default function LiveDetectPage() {
  const imgRef = useRef<HTMLInputElement>(null);
  const vidRef = useRef<HTMLInputElement>(null);
  const canvasRef      = useRef<HTMLCanvasElement>(null);
  const canvasWrap     = useRef<HTMLDivElement>(null);
  const esRef          = useRef<EventSource | null>(null);

  const [mode, setMode]         = useState<Mode>("image");
  const [imgFile, setImgFile]   = useState<File | null>(null);
  const [imgPreview, setImgPreview] = useState<string | null>(null);
  const [vidFile, setVidFile]   = useState<File | null>(null);
  const [streamUrl, setStreamUrl] = useState("");

  // Config
  const [stopLine, setStopLine] = useState(400);
  const [frameSkip, setFrameSkip] = useState(4);
  const [maxSecs, setMaxSecs]   = useState(45);
  const [camera, setCamera]     = useState(CAMERA_LABELS[0]);
  const [sceneType, setSceneType] = useState("Junction");
  const [signalRed, setSignalRed] = useState(false);
  const [stoplineEnabled, setStoplineEnabled] = useState(false);
  const [wrongSidePresent, setWrongSidePresent] = useState(false);
  const [flowDirection, setFlowDirection] = useState("Left -> Right");

  // State
  const [loading, setLoading]   = useState(false);
  const [progress, setProgress] = useState(0);
  const [uploadPct, setUploadPct] = useState(0);
  const [progressMsg, setProgressMsg] = useState("");
  const [imgResult, setImgResult] = useState<DetectImageResult | null>(null);
  const [liveViols, setLiveViols] = useState<DetectionViolation[]>([]);
  const [newFlash, setNewFlash]   = useState<string[]>([]);
  const [vidDone, setVidDone]     = useState(false);
  const [error, setError]         = useState<string | null>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [canvasReady, setCanvasReady] = useState(false);

  // Vehicle session log: vehicle_id -> list of violations it committed
  const [vehicleLog, setVehicleLog] = useState<Record<string, DetectionViolation[]>>({});

  function reset() {
    setImgResult(null); setLiveViols([]); setNewFlash([]);
    setError(null); setVidDone(false); setProgress(0); setUploadPct(0); setProgressMsg("");
    setCanvasReady(false); setVehicleLog({});
  }

  const detectOpts: DetectOptions & { frameSkip: number; maxSeconds: number; cameraId: string } = {
    stopLineY: stopLine, signalRed, stoplineEnabled,
    sceneType, wrongSidePresent, flowDirection,
    frameSkip, maxSeconds: maxSecs,
    cameraId: camera,
  };

  // Draw a base64 JPEG onto the canvas
  const drawFrame = useCallback((b64: string) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const img = new Image();
    img.onload = () => {
      canvas.width  = img.width;
      canvas.height = img.height;
      canvas.getContext("2d")?.drawImage(img, 0, 0);
    };
    img.src = `data:image/jpeg;base64,${b64}`;
  }, []);

  // Fullscreen toggle
  function toggleFullscreen() {
    if (!document.fullscreenElement) {
      canvasWrap.current?.requestFullscreen().catch(() => {});
    } else {
      document.exitFullscreen().catch(() => {});
    }
  }
  useEffect(() => {
    const handler = () => setIsFullscreen(!!document.fullscreenElement);
    document.addEventListener("fullscreenchange", handler);
    return () => document.removeEventListener("fullscreenchange", handler);
  }, []);

  // Stop any running stream
  function stopStream() {
    esRef.current?.close();
    esRef.current = null;
  }

  async function runImage() {
    if (!imgFile) return;
    setLoading(true); setError(null); setImgResult(null);
    try {
      const r = await detectImage(imgFile, detectOpts);
      setImgResult(r);
      // Save HIGH/CRITICAL violations from image to DB
      for (const v of r.violations) {
        if (v.severity === "HIGH" || v.severity === "CRITICAL") {
          saveViolation(v, camera, r.plate).catch(() => {});
        }
      }
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? e?.message ?? "Detection failed");
    } finally { setLoading(false); }
  }

  async function runVideo() {
    if (!vidFile) return;
    stopStream();
    reset();
    setLoading(true);
    setProgressMsg("Uploading video…");

    let sessionId: string;
    try {
      setUploadPct(0);
      sessionId = await uploadVideoForStream(vidFile, (pct) => {
        setUploadPct(pct);
        setProgressMsg(`Uploading… ${pct}%`);
      });
    } catch (e: any) {
      setError("Upload failed: " + (e?.message ?? "unknown"));
      setLoading(false);
      return;
    }

    setUploadPct(100);
    setProgressMsg("Connecting to analysis stream…");
    setCanvasReady(true);

    const url = videoStreamUrl(sessionId, detectOpts);
    const es  = new EventSource(url);
    esRef.current = es;

    es.onmessage = (evt) => {
      try {
        const data = JSON.parse(evt.data);

        if (data.done) {
          setVidDone(true);
          setLoading(false);
          setProgress(100);
          setProgressMsg(`Analysis complete · ${data.count ?? 0} violations detected`);
          es.close();
          return;
        }

        // Draw live frame with bounding boxes
        if (data.frame_b64) drawFrame(data.frame_b64);

        // Update progress
        setProgress(data.progress ?? 0);
        setProgressMsg(`Frame ${data.frame} / ${data.total} · ${data.confirmed_viols?.length ?? 0} confirmed violations`);

        // New confirmed violations — flash them and save to DB
        if (data.new_confirmed?.length) {
          const newTypes: string[] = data.new_confirmed.map((v: any) => v.type);
          setNewFlash(newTypes);
          setTimeout(() => setNewFlash([]), 1500);
          // Violations are persisted server-side (SQLite + evidence snapshots)
          // inside the stream loop — no client save needed.
        }

        // Update live violation list
        if (data.confirmed_viols?.length) {
          const sorted = [...data.confirmed_viols].sort(
            (a: DetectionViolation, b: DetectionViolation) =>
              (SEVERITY_PRIORITY[b.severity] ?? 0) - (SEVERITY_PRIORITY[a.severity] ?? 0)
          );
          setLiveViols(sorted);

          // Build vehicle session log: group by vehicle_id
          setVehicleLog(() => {
            const log: Record<string, DetectionViolation[]> = {};
            for (const v of data.confirmed_viols as DetectionViolation[]) {
              const vid = (v as any).vehicle_id ?? "Unknown";
              if (!log[vid]) log[vid] = [];
              // Avoid duplicates (same type already logged for this vehicle)
              if (!log[vid].some(x => x.type === v.type)) {
                log[vid].push(v);
              }
            }
            return log;
          });
        }
      } catch { /* ignore parse errors */ }
    };

    es.onerror = () => {
      if (es.readyState === EventSource.CLOSED) return;
      setError("Stream connection lost. The video may have finished processing.");
      setLoading(false);
      es.close();
    };
  }

  // Cleanup on unmount
  useEffect(() => () => stopStream(), []);

  const MODES: { id: Mode; label: string }[] = [
    { id: "image",  label: "📷 Image" },
    { id: "video",  label: "🎥 Video" },
    { id: "stream", label: "📡 Stream" },
  ];

  const sortedImgViols = [...(imgResult?.violations ?? [])].sort(
    (a, b) => (SEVERITY_PRIORITY[b.severity] ?? 0) - (SEVERITY_PRIORITY[a.severity] ?? 0)
  );

  return (
    <div>
      <div className="mb-7">
        <p className="text-[10px] font-bold tracking-[0.16em] uppercase text-neutral-400 mb-1">Detection Pipeline</p>
        <h1 className="text-3xl font-semibold tracking-tight text-neutral-900" style={{ fontFamily: "'Outfit', sans-serif" }}>
          Live Analysis
        </h1>
        <p className="text-[13px] text-neutral-400 mt-1">YOLOv8s + ByteTrack + 3 fine-tuned models · CLAHE dehazing · temporal 2-sighting confirmation</p>
      </div>

      {/* Mode tabs */}
      <div className="flex gap-1 p-1 bg-white rounded-[4px] border border-neutral-100 mb-5 w-fit">
        {MODES.map(m => (
          <button key={m.id} onClick={() => { setMode(m.id); reset(); stopStream(); }}
            className={`px-4 py-1.5 rounded-[3px] text-[12px] font-semibold transition-all ${
              mode === m.id ? "bg-neutral-900 text-white" : "text-neutral-500 hover:text-neutral-900"
            }`}>{m.label}</button>
        ))}
      </div>

      <div className="grid grid-cols-3 gap-4">
        {/* ── CONFIG PANEL ── */}
        <div className="col-span-1 flex flex-col gap-3">
          <div className="bg-white rounded-[4px] p-4 border border-neutral-100 shadow-sm flex flex-col gap-3">
            <p className="text-[10px] font-bold tracking-[0.16em] uppercase text-neutral-400">Scene Config</p>
            <div>
              <label className="text-[11px] text-neutral-500 mb-1 block">Camera</label>
              <select value={camera} onChange={e => setCamera(e.target.value)}
                className="w-full text-[12px] border border-neutral-200 rounded-[3px] px-3 py-2 focus:outline-none focus:border-neutral-400">
                {CAMERA_LABELS.map(k => <option key={k}>{k}</option>)}
              </select>
            </div>
            <div>
              <label className="text-[11px] text-neutral-500 mb-1 block">Scene Type</label>
              <div className="flex gap-1">
                {SCENE_TYPES.map(s => (
                  <button key={s} onClick={() => setSceneType(s)}
                    className={`flex-1 text-[11px] py-1.5 rounded-[3px] font-semibold transition-all ${
                      sceneType === s ? "bg-neutral-900 text-white" : "bg-neutral-100 text-neutral-600 hover:bg-neutral-200"
                    }`}>{s}</button>
                ))}
              </div>
            </div>
          </div>

          <div className="bg-white rounded-[4px] p-4 border border-neutral-100 shadow-sm flex flex-col gap-3">
            <p className="text-[10px] font-bold tracking-[0.16em] uppercase text-neutral-400">Violation Flags</p>

            {[
              { label: "Signal is RED", sub: "Flags crossing as Red-Light Violation", val: signalRed, set: setSignalRed, color: "bg-red-500" },
              { label: "Stop-line Detection", sub: "Enable Y-threshold crossing check", val: stoplineEnabled, set: setStoplineEnabled, color: "bg-neutral-900" },
              { label: "Wrong-Side Heuristic", sub: "Fallback if model not loaded", val: wrongSidePresent, set: setWrongSidePresent, color: "bg-neutral-900" },
            ].map(({ label, sub, val, set, color }) => (
              <label key={label} className="flex items-center justify-between cursor-pointer">
                <div>
                  <p className="text-[12px] font-medium text-neutral-900">{label}</p>
                  <p className="text-[10px] text-neutral-400">{sub}</p>
                </div>
                <div onClick={() => set((v: boolean) => !v)}
                  className={`w-10 h-5 rounded-full transition-colors relative ${val ? color : "bg-neutral-200"}`}>
                  <div className={`absolute top-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform ${val ? "translate-x-5" : "translate-x-0.5"}`}/>
                </div>
              </label>
            ))}

            {stoplineEnabled && (
              <div>
                <label className="text-[11px] text-neutral-500">Stop-line Y: <strong>{stopLine}px</strong></label>
                <input type="range" min={100} max={700} value={stopLine} onChange={e => setStopLine(+e.target.value)}
                  className="w-full accent-neutral-900 mt-1"/>
              </div>
            )}
            {wrongSidePresent && (
              <div>
                <label className="text-[11px] text-neutral-500 mb-1 block">Expected flow direction</label>
                <div className="flex gap-1">
                  {FLOW_DIRS.map(d => (
                    <button key={d} onClick={() => setFlowDirection(d)}
                      className={`flex-1 text-[10px] py-1.5 rounded-[3px] font-semibold transition-all ${
                        flowDirection === d ? "bg-neutral-900 text-white" : "bg-neutral-100 text-neutral-600"
                      }`}>{d}</button>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Mode-specific inputs */}
          {mode === "image" && (
            <>
              <div className="bg-white rounded-[4px] p-4 border border-neutral-100 shadow-sm">
                <p className="text-[10px] font-bold tracking-[0.16em] uppercase text-neutral-400 mb-3">Upload Image</p>
                <div className="border-2 border-dashed border-neutral-200 rounded-[4px] p-5 text-center cursor-pointer hover:border-neutral-400 transition-colors"
                  onClick={() => imgRef.current?.click()}
                  onDrop={e => { e.preventDefault(); const f=e.dataTransfer.files[0]; if(f){setImgFile(f);reset();setImgPreview(URL.createObjectURL(f));} }}
                  onDragOver={e => e.preventDefault()}>
                  <input ref={imgRef} type="file" accept="image/*" className="hidden"
                    onChange={e => { const f=e.target.files?.[0]; if(f){setImgFile(f);reset();setImgPreview(URL.createObjectURL(f));} }}/>
                  {imgPreview
                    ? <img src={imgPreview} className="w-full rounded-[4px] object-contain max-h-36"/>
                    : <p className="text-[12px] text-neutral-400">Drop image or click to upload</p>}
                </div>
              </div>
              <button onClick={runImage} disabled={!imgFile || loading}
                className="w-full py-3 rounded-full bg-neutral-900 text-white text-[13px] font-semibold hover:bg-neutral-700 disabled:opacity-40 disabled:cursor-not-allowed transition-all">
                {loading ? "Analysing…" : "▶  Run Detection"}
              </button>
            </>
          )}

          {mode === "video" && (
            <>
              <div className="bg-white rounded-[4px] p-4 border border-neutral-100 shadow-sm flex flex-col gap-3">
                <p className="text-[10px] font-bold tracking-[0.16em] uppercase text-neutral-400">Upload Video</p>

                {vidFile ? (
                  /* ── Selected state ── */
                  <div className="border-2 border-green-400 bg-green-50 rounded-[4px] p-4 flex items-start gap-3">
                    <div className="w-9 h-9 rounded-[4px] bg-green-500 flex items-center justify-center flex-shrink-0">
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                        <polygon points="23 7 16 12 23 17 23 7"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/>
                      </svg>
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-[13px] font-semibold text-green-900 truncate">{vidFile.name}</p>
                      <p className="text-[11px] text-green-600 mt-0.5">{(vidFile.size / 1024 / 1024).toFixed(1)} MB · ready to analyse</p>
                    </div>
                    <button onClick={() => { setVidFile(null); reset(); stopStream(); }}
                      className="text-green-400 hover:text-red-500 transition-colors ml-1 flex-shrink-0"
                      title="Remove">
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                        <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
                      </svg>
                    </button>
                  </div>
                ) : (
                  /* ── Empty drop zone ── */
                  <div className="border-2 border-dashed border-neutral-200 rounded-[4px] p-6 text-center cursor-pointer hover:border-neutral-400 hover:bg-neutral-50 transition-all"
                    onClick={() => vidRef.current?.click()}
                    onDrop={e => { e.preventDefault(); const f=e.dataTransfer.files[0]; if(f){setVidFile(f);reset();stopStream();} }}
                    onDragOver={e => e.preventDefault()}>
                    <svg className="mx-auto mb-2 text-neutral-300" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                      <polygon points="23 7 16 12 23 17 23 7"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/>
                    </svg>
                    <p className="text-[12px] text-neutral-400">Drop MP4 / AVI / MOV here</p>
                    <p className="text-[10px] text-neutral-300 mt-0.5">or click to browse</p>
                  </div>
                )}
                <input ref={vidRef} type="file" accept="video/*,.mp4,.avi,.mov" className="hidden"
                  onChange={e => { const f=e.target.files?.[0]; if(f){setVidFile(f);reset();stopStream();} }}/>
                <div>
                  <label className="text-[11px] text-neutral-500">Frame skip: <strong>{frameSkip}</strong> (lower = more thorough, slower)</label>
                  <input type="range" min={1} max={10} value={frameSkip} onChange={e => setFrameSkip(+e.target.value)} className="w-full accent-neutral-900 mt-1"/>
                </div>
                <div>
                  <label className="text-[11px] text-neutral-500">Max duration: <strong>{maxSecs}s</strong></label>
                  <input type="range" min={10} max={120} value={maxSecs} onChange={e => setMaxSecs(+e.target.value)} className="w-full accent-neutral-900 mt-1"/>
                </div>
              </div>
              <button onClick={loading ? stopStream : runVideo} disabled={!vidFile}
                className={`w-full py-3 rounded-full text-white text-[13px] font-semibold transition-all disabled:opacity-40 disabled:cursor-not-allowed ${
                  loading ? "bg-red-600 hover:bg-red-700" : "bg-neutral-900 hover:bg-neutral-700"
                }`}>
                {loading ? "⏹ Stop Analysis" : "▶  Analyse Video (Live)"}
              </button>
            </>
          )}

          {mode === "stream" && (
            <>
              <div className="bg-white rounded-[4px] p-4 border border-neutral-100 shadow-sm flex flex-col gap-3">
                <p className="text-[10px] font-bold tracking-[0.16em] uppercase text-neutral-400">Live Stream URL</p>
                <input type="text" placeholder="https://youtube.com/watch?v=… or rtsp://…"
                  value={streamUrl} onChange={e => setStreamUrl(e.target.value)}
                  className="text-[12px] border border-neutral-200 rounded-[3px] px-3 py-2.5 focus:outline-none focus:border-neutral-400 font-mono"/>
                <div className="bg-blue-50 border border-blue-100 rounded-[3px] p-3">
                  <p className="text-[11px] font-semibold text-blue-800 mb-1">Supported sources</p>
                  <ul className="text-[10px] text-blue-700 space-y-0.5 list-disc list-inside">
                    <li>YouTube live streams — paste the watch URL directly</li>
                    <li>RTSP camera feeds — rtsp://192.168.x.x/stream</li>
                    <li>HLS / .m3u8 URLs from any source</li>
                  </ul>
                  <p className="text-[10px] text-blue-500 mt-2">Requires <code className="bg-blue-100 px-1 rounded">yt-dlp</code> installed on the server for YouTube.</p>
                </div>
                <div>
                  <label className="text-[11px] text-neutral-500">Frame skip: <strong>{frameSkip}</strong></label>
                  <input type="range" min={1} max={10} value={frameSkip} onChange={e => setFrameSkip(+e.target.value)} className="w-full accent-neutral-900 mt-1"/>
                </div>
                <div>
                  <label className="text-[11px] text-neutral-500">Analyse duration: <strong>{maxSecs}s</strong></label>
                  <input type="range" min={10} max={120} value={maxSecs} onChange={e => setMaxSecs(+e.target.value)} className="w-full accent-neutral-900 mt-1"/>
                </div>
              </div>
              <button
                onClick={() => {
                  if (loading) { stopStream(); return; }
                  if (!streamUrl.trim()) return;
                  stopStream(); reset();
                  const isYT = streamUrl.includes("youtube.com") || streamUrl.includes("youtu.be");
                  setLoading(true); setCanvasReady(true);
                  setProgressMsg(isYT ? "Downloading stream via yt-dlp (up to 60s)…" : "Connecting to stream…");
                  const url = liveStreamUrl(streamUrl.trim(), detectOpts);
                  const es  = new EventSource(url);
                  esRef.current = es;
                  es.onmessage = (evt) => {
                    try {
                      const data = JSON.parse(evt.data);
                      if (data.error) { setError(data.error); setLoading(false); es.close(); return; }
                      if (data.status) { setProgressMsg(data.msg ?? "Preparing…"); return; }
                      if (data.done) { setLoading(false); setProgressMsg(`Stream ended · ${liveViols.length} violation${liveViols.length !== 1 ? "s" : ""} confirmed`); es.close(); return; }
                      if (data.frame_b64) drawFrame(data.frame_b64);
                      setProgress(data.progress ?? 0);
                      setProgressMsg(`Analysing · ${data.confirmed_viols?.length ?? 0} violations confirmed so far`);
                      if (data.new_confirmed?.length) {
                        setNewFlash(data.new_confirmed.map((v: DetectionViolation) => v.type));
                        setTimeout(() => setNewFlash([]), 1500);
                        // Persisted server-side (SQLite + evidence snapshots).
                      }
                      if (data.confirmed_viols?.length) {
                        setLiveViols([...data.confirmed_viols].sort((a: DetectionViolation, b: DetectionViolation) =>
                          (SEVERITY_PRIORITY[b.severity] ?? 0) - (SEVERITY_PRIORITY[a.severity] ?? 0)));
                      }
                    } catch { /* ignore */ }
                  };
                  es.onerror = () => { setError("Stream lost or URL unreachable."); setLoading(false); es.close(); };
                }}
                disabled={!streamUrl.trim() && !loading}
                className={`w-full py-3 rounded-full text-white text-[13px] font-semibold transition-all disabled:opacity-40 disabled:cursor-not-allowed ${
                  loading ? "bg-red-600 hover:bg-red-700" : "bg-neutral-900 hover:bg-neutral-700"
                }`}>
                {loading ? "⏹ Stop Stream" : "📡 Start Live Analysis"}
              </button>
            </>
          )}

          {error && (
            <div className="bg-red-50 border border-red-200 rounded-[4px] p-3 text-[12px] text-red-700">{error}</div>
          )}
        </div>

        {/* ── RESULTS PANEL ── */}
        <div className="col-span-2 flex flex-col gap-4">

          {/* IMAGE results */}
          {mode === "image" && imgResult && (
            <>
              <div className="bg-white rounded-[4px] p-5 border border-neutral-100 shadow-sm">
                <p className="text-[10px] font-bold tracking-[0.16em] uppercase text-neutral-400 mb-3">Annotated Output</p>
                <img src={`data:image/jpeg;base64,${imgResult.annotated_b64}`}
                  className="w-full rounded-[4px] object-contain max-h-72"/>
              </div>
              <div className="grid grid-cols-3 gap-3">
                <div className="bg-white rounded-[4px] p-4 border border-neutral-100 shadow-sm">
                  <p className="text-[10px] font-bold tracking-widest uppercase text-neutral-400 mb-1">Plate</p>
                  <p className="text-lg font-bold font-mono text-neutral-900">{imgResult.plate}</p>
                </div>
                <div className="bg-white rounded-[4px] p-4 border border-neutral-100 shadow-sm">
                  <p className="text-[10px] font-bold tracking-widest uppercase text-neutral-400 mb-1">Violations</p>
                  <p className="text-3xl font-semibold text-neutral-900" style={{ fontFamily: "'Outfit', sans-serif" }}>{imgResult.count}</p>
                </div>
                <div className="bg-white rounded-[4px] p-4 border border-neutral-100 shadow-sm">
                  <p className="text-[10px] font-bold tracking-widest uppercase text-neutral-400 mb-1">Camera</p>
                  <p className="text-[11px] font-medium text-neutral-700">{camera.split("—")[0].trim()}</p>
                </div>
              </div>
              {sortedImgViols.length > 0 && (
                <div className="bg-white rounded-[4px] p-5 border border-neutral-100 shadow-sm">
                  <p className="text-[10px] font-bold tracking-[0.16em] uppercase text-neutral-400 mb-3">Detections — click to expand</p>
                  <div className="flex flex-col gap-2">
                    {sortedImgViols.map((v, i) => <ViolationCard key={i} v={v}/>)}
                  </div>
                </div>
              )}
            </>
          )}

          {/* Upload progress / connecting (before canvas is ready) */}
          {(mode === "video" || mode === "stream") && loading && !canvasReady && (
            <div className="bg-white rounded-[4px] p-5 border border-neutral-100 shadow-sm flex flex-col items-center justify-center min-h-[200px] gap-4">
              <div className="w-full">
                <div className="flex items-center justify-between mb-2">
                  <p className="text-[12px] font-medium text-neutral-700">{mode === "stream" ? "Resolving stream URL…" : "Uploading video to server…"}</p>
                  <span className="text-[12px] font-bold text-neutral-900">{mode === "stream" ? "" : `${uploadPct}%`}</span>
                </div>
                <div className="h-2 bg-neutral-100 rounded-full overflow-hidden">
                  <div className="h-full bg-neutral-900 rounded-full transition-all duration-150" style={{ width: `${uploadPct}%` }}/>
                </div>
                <p className="text-[10px] text-neutral-400 mt-2">
                  {vidFile ? `${vidFile.name} · ${(vidFile.size / 1024 / 1024).toFixed(1)} MB` : ""}
                </p>
              </div>
            </div>
          )}

          {/* VIDEO / STREAM live canvas */}
          {(mode === "video" || mode === "stream") && canvasReady && (
            <>
              {/* Progress bar — video only. Stream has no end so no % bar. */}
              {mode === "video" ? (
                <div className="bg-white rounded-[4px] p-4 border border-neutral-100 shadow-sm">
                  <div className="flex items-center justify-between mb-2">
                    <p className="text-[11px] text-neutral-500">{progressMsg || "Initialising…"}</p>
                    <span className="text-[11px] font-bold text-neutral-700">{progress}%</span>
                  </div>
                  <div className="h-1.5 bg-neutral-100 rounded-full overflow-hidden">
                    <div className="h-full bg-neutral-900 rounded-full transition-all duration-300" style={{ width: `${progress}%` }}/>
                  </div>
                </div>
              ) : (
                <div className="bg-white rounded-[4px] px-4 py-3 border border-neutral-100 shadow-sm flex items-center gap-3">
                  <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse shrink-0"/>
                  <p className="text-[12px] text-neutral-600 font-medium">
                    {progressMsg || "Connected — analysing live frames…"}
                  </p>
                  <span className="ml-auto text-[11px] font-semibold text-neutral-400">
                    {liveViols.length > 0 ? `${liveViols.length} violation${liveViols.length > 1 ? "s" : ""} confirmed` : "Monitoring…"}
                  </span>
                </div>
              )}

              {/* Live canvas with fullscreen */}
              <div ref={canvasWrap} className="relative bg-neutral-900 rounded-[4px] overflow-hidden shadow-sm"
                style={{ minHeight: 300 }}>
                <canvas ref={canvasRef} className="w-full h-auto block" style={{ maxHeight: isFullscreen ? "100vh" : 480 }}/>

                {/* Fullscreen button */}
                <button onClick={toggleFullscreen}
                  className="absolute top-3 right-3 w-8 h-8 rounded-full bg-black/50 text-white flex items-center justify-center hover:bg-black/70 transition-colors z-10"
                  title={isFullscreen ? "Exit fullscreen" : "Fullscreen"}>
                  {isFullscreen ? (
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M8 3v3a2 2 0 0 1-2 2H3m18 0h-3a2 2 0 0 1-2-2V3m0 18v-3a2 2 0 0 1 2-2h3M3 16h3a2 2 0 0 1 2 2v3"/>
                    </svg>
                  ) : (
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3"/>
                    </svg>
                  )}
                </button>

                {/* LIVE badge */}
                {loading && (
                  <div className="absolute top-3 left-3 flex items-center gap-1.5 bg-red-600 text-white text-[10px] font-bold px-2.5 py-1 rounded-full">
                    <span className="w-1.5 h-1.5 rounded-full bg-white animate-pulse"/>
                    LIVE
                  </div>
                )}

                {vidDone && mode === "video" && (
                  <div className="absolute top-3 left-3 bg-green-600 text-white text-[10px] font-bold px-2.5 py-1 rounded-full">
                    ✓ ANALYSIS COMPLETE
                  </div>
                )}
              </div>

              {/* Live violations */}
              {liveViols.length > 0 && (
                <div className="bg-white rounded-[4px] p-5 border border-neutral-100 shadow-sm">
                  <div className="flex items-center justify-between mb-3">
                    <p className="text-[10px] font-bold tracking-[0.16em] uppercase text-neutral-400">
                      Confirmed Violations · 2-Sighting Temporal Filter
                    </p>
                    <span className="text-[11px] font-bold text-neutral-900 bg-neutral-100 px-2 py-0.5 rounded-full">{liveViols.length}</span>
                  </div>
                  <div className="flex flex-col gap-2">
                    {liveViols.map((v, i) => (
                      <ViolationCard key={i} v={v} flash={newFlash.includes(v.type)}/>
                    ))}
                  </div>
                </div>
              )}

              {liveViols.length === 0 && loading && (
                <div className="bg-white rounded-[4px] p-6 border border-neutral-100 shadow-sm text-center">
                  <p className="text-[12px] text-neutral-400">Waiting for detections (confirms on 2nd sighting or confidence ≥ 65%)…</p>
                </div>
              )}

              {vidDone && liveViols.length === 0 && (
                <div className="bg-white rounded-[4px] p-6 border border-neutral-100 shadow-sm text-center">
                  <p className="text-[13px] text-neutral-400">No violations detected. Try lower frame-skip or a longer clip.</p>
                </div>
              )}

              {/* ── Vehicle Session Summary Table ── */}
              {Object.keys(vehicleLog).length > 0 && (
                <div className="bg-white rounded-[4px] border border-neutral-100 shadow-sm overflow-hidden">
                  <div className="px-5 py-3.5 border-b border-neutral-100 flex items-center justify-between">
                    <div>
                      <p className="text-[10px] font-bold tracking-[0.16em] uppercase text-neutral-400">Session Vehicle Log</p>
                      <p className="text-[12px] text-neutral-500 mt-0.5">
                        Every vehicle detected this session with confirmed violations
                      </p>
                    </div>
                    <span className="text-[11px] font-bold bg-neutral-100 text-neutral-700 px-2.5 py-1 rounded-full">
                      {Object.keys(vehicleLog).length} vehicles
                    </span>
                  </div>

                  {/* Table header */}
                  <div className="grid px-5 py-2 bg-neutral-50 border-b border-neutral-100"
                       style={{ gridTemplateColumns: "80px 1fr 90px 80px 90px" }}>
                    {["Vehicle ID", "Violation(s)", "Severity", "Conf.", "Frame"].map(h => (
                      <p key={h} className="text-[9px] font-bold tracking-[0.14em] uppercase text-neutral-400">{h}</p>
                    ))}
                  </div>

                  {Object.entries(vehicleLog)
                    .sort(([a], [b]) => {
                      // Sort by worst severity across violations
                      const worstSev = (viols: DetectionViolation[]) =>
                        Math.max(...viols.map(v => SEVERITY_PRIORITY[v.severity] ?? 0));
                      return worstSev(vehicleLog[b]) - worstSev(vehicleLog[a]);
                    })
                    .map(([vid, viols]) => (
                      viols.map((v, vi) => (
                        <div key={`${vid}-${vi}`}
                          className="grid px-5 py-2.5 border-b border-neutral-50 last:border-0 hover:bg-neutral-50 transition-colors"
                          style={{ gridTemplateColumns: "80px 1fr 90px 80px 90px" }}>
                          {/* Vehicle ID — only show on first row for this vehicle */}
                          <div>
                            {vi === 0 ? (
                              <span className="text-[11px] font-bold font-mono bg-neutral-900 text-white px-2 py-0.5 rounded-[3px]">
                                {vid}
                              </span>
                            ) : (
                              <span className="text-[10px] text-neutral-300 pl-1">↳</span>
                            )}
                          </div>

                          {/* Violation type */}
                          <p className="text-[12px] text-neutral-800 font-medium truncate">{v.type}</p>

                          {/* Severity */}
                          <span className={`text-[9px] font-bold px-2 py-0.5 rounded-full w-fit self-center ${SEVERITY_COLOR[v.severity] ?? "bg-neutral-100 text-neutral-600"}`}>
                            {v.severity}
                          </span>

                          {/* Confidence */}
                          <p className="text-[12px] font-mono text-neutral-600 self-center">
                            {(v.confidence * 100).toFixed(0)}%
                          </p>

                          {/* Frame */}
                          <p className="text-[11px] text-neutral-400 self-center font-mono">
                            {(v as any).frame != null ? `f${(v as any).frame}` : "—"}
                          </p>
                        </div>
                      ))
                    ))
                  }
                </div>
              )}
            </>
          )}

          {/* Empty / idle state */}
          {!canvasReady && !imgResult && !loading && (
            <div className="bg-white rounded-[4px] border border-neutral-100 shadow-sm flex flex-col items-center justify-center text-center min-h-[360px] gap-4">
              <svg className="text-neutral-200" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="3"/>
                <line x1="12" y1="2" x2="12" y2="5"/><line x1="12" y1="19" x2="12" y2="22"/>
                <line x1="2" y1="12" x2="5" y2="12"/><line x1="19" y1="12" x2="22" y2="12"/>
              </svg>
              <div>
                <p className="text-[14px] text-neutral-400">
                  {mode === "image"  && "Upload an image and click Run Detection"}
                  {mode === "video"  && "Upload a video and click Analyse Video (Live) — bounding boxes stream in real time"}
                  {mode === "stream" && "See stream setup instructions on the left"}
                </p>
                <p className="text-[11px] text-neutral-300 mt-1">Configure scene type and violation flags before running</p>
              </div>
            </div>
          )}

          {/* Image loading spinner */}
          {mode === "image" && loading && (
            <div className="bg-white rounded-[4px] border border-neutral-100 shadow-sm flex flex-col items-center justify-center min-h-[360px] gap-4">
              <div className="w-10 h-10 border-2 border-neutral-900 border-t-transparent rounded-full animate-spin"/>
              <p className="text-[13px] text-neutral-500">Running detection pipeline…</p>
              <p className="text-[11px] text-neutral-300">CLAHE + YOLO + fine-tuned models active</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

