import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // dev convenience: frontend on 5173, FastAPI on 8000
      "/api": "http://localhost:8000",
    },
  },
});
