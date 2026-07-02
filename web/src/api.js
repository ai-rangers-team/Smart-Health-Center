import axios from "axios";
import { auth } from "./firebase";

// Same-origin in production (FastAPI serves the built app); proxied in dev.
export const api = axios.create({ baseURL: import.meta.env.VITE_API_BASE || "" });

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
