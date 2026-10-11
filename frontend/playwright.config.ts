import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "e2e",
  timeout: 120_000,
  use: {
    baseURL: process.env.BEEMER_WEB || "http://127.0.0.1:4173",
    viewport: { width: 1440, height: 900 },
  },
  reporter: [["list"]],
});
