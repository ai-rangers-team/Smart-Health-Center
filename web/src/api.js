import axios from "axios";
import { auth } from "./firebase";
import { PREVIEW } from "./dev/preview";
import { PREVIEW_API } from "./dev/fixtures";

// Same-origin in production (FastAPI serves the built app); proxied in dev.
export const api = axios.create({ baseURL: import.meta.env.VITE_API_BASE || "" });

if (PREVIEW) {
  // Dev-only: canned AI responses so screens render without the backend.
  const lang = (url) => new URLSearchParams(url.split("?")[1] || "").get("lang") || "mr";
  api.get = async (url) => {
    if (url.includes("/api/ai/impact/")) return PREVIEW_API.impact;
    if (url.includes("/api/ai/outbreak/")) return { outbreaks: PREVIEW_API.outbreaks };
    if (url.includes("/api/public/centre/")) return PREVIEW_API.publicCentre;
    if (url.includes("district-briefing")) return { briefing: PREVIEW_API.briefing[lang(url)] };
    if (url.includes("/api/ai/forecast/"))
      return {
        medicines: [],
        narrative: PREVIEW_API.briefing[lang(url)],
        footfall: { projection: 78, trend: "falling" },
      };
    return {};
  };
  api.post = async (url, body) => {
    if (url.includes("explain-underperformance"))
      return { explanation: PREVIEW_API.explanation[lang(url)] };
    if (url.includes("/stock/voice")) return PREVIEW_API.voice;
    if (url.includes("/api/sms/report") || url.includes("/api/sms/parse")) {
      // Lightweight offline mirror of the backend alias parser (demo centre only).
      const ALIAS = {
        para: "Paracetamol 500mg", pcm: "Paracetamol 500mg", pc: "Paracetamol 500mg",
        ors: "ORS Sachets", ifa: "Iron + Folic Acid", iron: "Iron + Folic Acid",
        met: "Metformin 500mg", metf: "Metformin 500mg",
      };
      const applied = [], unmatched = [], seen = new Set();
      for (const [, w, n] of (body?.text || "").matchAll(/([A-Za-z]+)\s*[:=]?\s*(\d+)/g)) {
        const name = ALIAS[w.toLowerCase()];
        if (!name) { unmatched.push(w); continue; }
        if (seen.has(name)) continue;
        seen.add(name);
        applied.push({ medicine_name: name, current_stock: Number(n) });
      }
      return { centre_name: "PHC Mulshi", applied, updates: applied, unmatched };
    }
    return { ok: true };
  };
  api.patch = async () => ({ ok: true });
}

api.interceptors.request.use(async (cfg) => {
  const u = auth.currentUser;
  if (u) cfg.headers.Authorization = `Bearer ${await u.getIdToken()}`;
  return cfg;
});

// Unwrap the standard envelope: {success, data, timestamp} -> data
api.interceptors.response.use(
  (r) => (r.data && r.data.success ? r.data.data : Promise.reject(r.data)),
  (e) => Promise.reject(e.response?.data || e)
);
