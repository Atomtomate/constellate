import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": {
        // 127.0.0.1, never localhost: on Windows the latter resolves to ::1 first and
        // stalls for uvicorn's whole connect timeout (root CLAUDE.md). Overridable via
        // API_PROXY_TARGET to point the dev proxy at an API on another port -- a branch's
        // own uvicorn running beside the rig's, say -- without editing this file.
        target: process.env.API_PROXY_TARGET ?? "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
});
