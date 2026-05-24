import path from "node:path";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

// Config vitest minimale pour le frontend Next/React (Sprint 14 Lot 3).
// `happy-dom` est utilisé comme environnement DOM léger (10× plus rapide
// que jsdom au démarrage). Couvre les besoins React/composants.
//
// `@vitejs/plugin-react` est requis pour le JSX : tsconfig.json a
// `jsx: "preserve"` pour le compilateur Next, mais le bundler vitest doit
// transformer le JSX → JS — le plugin React s'en occupe avec le runtime
// automatic (React 17+).
export default defineConfig({
  plugins: [react()],
  test: {
    environment: "happy-dom",
    globals: true,
    include: ["src/**/*.{test,spec}.{ts,tsx}"],
    setupFiles: ["./vitest.setup.ts"],
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
});
