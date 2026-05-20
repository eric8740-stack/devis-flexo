import path from "node:path";
import { defineConfig } from "vitest/config";

// Config vitest minimale pour le frontend Next/React (Sprint 14 Lot 3).
// `happy-dom` est utilisé comme environnement DOM léger (10× plus rapide
// que jsdom au démarrage). Couvre les besoins React/composants.
export default defineConfig({
  test: {
    environment: "happy-dom",
    globals: true,
    include: ["src/**/*.{test,spec}.{ts,tsx}"],
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
});
