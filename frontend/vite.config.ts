import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // Proxy API calls to the FastAPI backend during development
    // so we avoid CORS issues when running without Docker
    proxy: {
      "/auth": "http://localhost:8000",
      "/agent": "http://localhost:8000",
      "/flights": "http://localhost:8000",
      "/health": "http://localhost:8000",
    },
  },
});
