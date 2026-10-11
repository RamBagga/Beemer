import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": "http://127.0.0.1:8080",
      "/actuator": "http://127.0.0.1:8080",
      "/swagger-ui": "http://127.0.0.1:8080",
      "/v3": "http://127.0.0.1:8080",
    },
  },
  preview: {
    port: 4173,
    proxy: {
      "/api": "http://127.0.0.1:8080",
      "/actuator": "http://127.0.0.1:8080",
      "/swagger-ui": "http://127.0.0.1:8080",
      "/v3": "http://127.0.0.1:8080",
    },
  },
  build: { chunkSizeWarningLimit: 4000 },
});
