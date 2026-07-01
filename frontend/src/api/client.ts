import axios from "axios";

// In production (Vercel), set VITE_API_URL to your HF Space URL, e.g.:
// https://yourusername-drishtivia.hf.space
// In dev, leave it unset — Vite's proxy forwards /api to localhost:8000.
const API_BASE = (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/$/, "") ?? "";

const api = axios.create({ baseURL: `${API_BASE}/api` });

export interface Stats {
  total: number;
  pending: number;
  plates: number;
  confirmed: number;
  top_types: { type: string; count: number }[];
  by_camera: { camera: string; count: number }[];
}

export interface Violation {
  id: number;
  timestamp: number;
  plate_number: string;
  violation_type: string;
  severity: string;
  confidence: number;
  priority_score: number;
  priority_level: string;
  camera_id: string;
  evidence_hash: string;
  operator_action: string | null;
  snapshot_path: string | null;
}

export interface AnalyticsResult {
  by_day: Record<string, number | string>[];
  repeat_offenders: { plate: string; count: number; types: string }[];
  hotspots?: { camera: string; count: number; avg_priority: number; lat?: number; lng?: number }[];
}

export interface DetectionViolation {
  type: string;
  severity: string;
  confidence: number;
  bbox: number[];
  vehicle_id?: string;
  vehicle_category?: string;
  track_id?: number;
  description?: string;
  note?: string;
  frame?: number;
  sightings?: number;
  evidence_hash?: string;
  db_id?: number;
}

export interface DetectImageResult {
  violations: DetectionViolation[];
  plate: string;
  count: number;
  original_b64: string;
  annotated_b64: string;
}

export interface DetectVideoResult {
  total_frames: number;
  frames_analysed: number;
  violations: DetectionViolation[];
  count: number;
  temporal_counts?: Record<string, number>;
}

export interface DetectOptions {
  stopLineY?: number;
  signalRed?: boolean;
  stoplineEnabled?: boolean;
  sceneType?: string;
  wrongSidePresent?: boolean;
  flowDirection?: string;
  frameSkip?: number;
  maxSeconds?: number;
}

export interface GraphData {
  edges: {
    plate_number: string; camera_id: string;
    violation_type: string; priority_score: number;
    priority_level: string; timestamp: number;
  }[];
  repeat_offenders: { plate: string; count: number; types: string }[];
  hotspots: { camera: string; count: number; avg_priority: number }[];
}

export const getHealth    = () => api.get("/health").then(r => r.data);
export const getStats     = () => api.get<Stats>("/stats").then(r => r.data);
export interface ViolationFilters {
  status?: string;
  limit?: number;
  offset?: number;
  violation_type?: string;
  severity?: string;
  plate?: string;
  from_ts?: number;
  to_ts?: number;
  sort?: "newest" | "oldest";
}
export const getViolations = (filters: ViolationFilters = {}) =>
  api.get<{ violations: Violation[]; count: number; total: number }>("/violations", {
    params: { status: "all", limit: 100, ...filters }
  }).then(r => r.data);
export const postAction   = (id: number, action: string) =>
  api.post(`/violations/${id}/action`, { action }).then(r => r.data);
export const getAnalytics = (days = 7) =>
  api.get<AnalyticsResult>("/analytics", { params: { days } }).then(r => r.data);
export const getGraph     = () => api.get<GraphData>("/graph").then(r => r.data);
export const cloneCheck   = (plate: string) =>
  api.get(`/graph/clone/${plate}`).then(r => r.data);
export const detectImage  = (file: File, opts: DetectOptions = {}): Promise<DetectImageResult> => {
  const fd = new FormData();
  fd.append("file", file);
  const p = new URLSearchParams({
    stop_line_y:        String(opts.stopLineY ?? 400),
    signal_red:         String(opts.signalRed ?? false),
    stopline_enabled:   String(opts.stoplineEnabled ?? false),
    scene_type:         opts.sceneType ?? "Junction",
    wrong_side_present: String(opts.wrongSidePresent ?? false),
    flow_direction:     opts.flowDirection ?? "Left → Right",
  });
  return api.post(`/detect/image?${p}`, fd).then(r => r.data);
};
export const detectVideo  = (file: File, opts: DetectOptions = {}): Promise<DetectVideoResult> => {
  const fd = new FormData();
  fd.append("file", file);
  const p = new URLSearchParams({
    stop_line_y:        String(opts.stopLineY ?? 400),
    frame_skip:         String(opts.frameSkip ?? 6),
    max_seconds:        String(opts.maxSeconds ?? 60),
    signal_red:         String(opts.signalRed ?? false),
    stopline_enabled:   String(opts.stoplineEnabled ?? false),
    scene_type:         opts.sceneType ?? "Junction",
    wrong_side_present: String(opts.wrongSidePresent ?? false),
    flow_direction:     opts.flowDirection ?? "Left → Right",
  });
  return api.post(`/detect/video?${p}`, fd, { timeout: 300_000 }).then(r => r.data);
};
export const verifyHash   = (evidence_hash: string) =>
  api.post("/verify", { evidence_hash }).then(r => r.data);
export const snapshotUrl  = (hash: string, kind: "full" | "crop") =>
  `${API_BASE}/api/snapshot/${hash.slice(0, 16)}/${kind}`;
export const searchViolations = (q: string, limit = 50) =>
  api.get<{ results: Violation[]; count: number }>("/search", { params: { q, limit } }).then(r => r.data);
export const agentQuery = (question: string) =>
  api.post<{ answer: string; question: string; source?: string }>("/agent", { question }).then(r => r.data);
export const reportUrl = (id: number) => `${API_BASE}/api/report/${id}`;
export const saveViolation = (v: DetectionViolation, camera_id: string, plate: string = "UNREADABLE") =>
  api.post("/violations/save", {
    violation_type: v.type,
    confidence:     v.confidence,
    severity:       v.severity,
    camera_id,
    plate_number:   plate,
    vehicle_id:     v.vehicle_id ?? "",
    description:    v.description ?? "",
    bbox:           v.bbox ?? [],
  }).then(r => r.data);
export const uploadVideoForStream = (
  file: File,
  onProgress?: (pct: number) => void
): Promise<string> =>
  new Promise((resolve, reject) => {
    const fd = new FormData();
    fd.append("file", file);
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${API_BASE}/api/detect/video/upload`);
    if (onProgress) {
      xhr.upload.onprogress = (e) => {
        if (e.lengthComputable) onProgress(Math.round((e.loaded / e.total) * 100));
      };
    }
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(JSON.parse(xhr.responseText).session_id);
      } else {
        reject(new Error(`Upload failed: ${xhr.status}`));
      }
    };
    xhr.onerror = () => reject(new Error("Network error during upload"));
    xhr.send(fd);
  });
export const liveStreamUrl = (
  url: string,
  opts: DetectOptions & { frameSkip?: number; maxSeconds?: number; cameraId?: string }
) => {
  const p = new URLSearchParams({
    url,
    stop_line_y:        String(opts.stopLineY ?? 400),
    frame_skip:         String(opts.frameSkip ?? 6),
    max_seconds:        String(opts.maxSeconds ?? 60),
    signal_red:         String(opts.signalRed ?? false),
    stopline_enabled:   String(opts.stoplineEnabled ?? false),
    scene_type:         opts.sceneType ?? "Junction",
    wrong_side_present: String(opts.wrongSidePresent ?? false),
    flow_direction:     opts.flowDirection ?? "Left -> Right",
    camera_id:          opts.cameraId ?? "live_stream",
  });
  return `${API_BASE}/api/detect/stream/live?${p}`;
};

export const videoStreamUrl = (
  sessionId: string,
  opts: DetectOptions & { frameSkip?: number; maxSeconds?: number; cameraId?: string }
) => {
  const p = new URLSearchParams({
    stop_line_y:        String(opts.stopLineY ?? 400),
    frame_skip:         String(opts.frameSkip ?? 6),
    max_seconds:        String(opts.maxSeconds ?? 60),
    signal_red:         String(opts.signalRed ?? false),
    stopline_enabled:   String(opts.stoplineEnabled ?? false),
    scene_type:         opts.sceneType ?? "Junction",
    wrong_side_present: String(opts.wrongSidePresent ?? false),
    flow_direction:     opts.flowDirection ?? "Left -> Right",
    camera_id:          opts.cameraId ?? "live_upload",
  });
  return `${API_BASE}/api/detect/video/stream/${sessionId}?${p}`;
};
