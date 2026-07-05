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
    if (url.includes("district-briefing")) return { briefing: PREVIEW_API.briefing[lang(url)] };
    if (url.includes("/api/ai/forecast/"))
      return {
        medicines: [],
        narrative: PREVIEW_API.briefing[lang(url)],
        footfall: { projection: 78, trend: "falling" },
      };
    return {};
  };
  api.post = async (url) =>
    url.includes("explain-underperformance")
      ? { explanation: PREVIEW_API.explanation[lang(url)] }
      : { ok: true };
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
