import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import { resolve } from "node:path";

/**
 * Vitest — UI component tests (React Testing Library).
 * Scope: `app/components/__tests__/**` only. Python tests use pytest.
 */
export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    setupFiles: ["./tests/ui-setup.ts"],
    include: ["app/components/__tests__/**/*.{test,spec}.{ts,tsx}"],
    globals: true,
    css: false,
  },
  resolve: {
    alias: {
      "@": resolve(__dirname, "./"),
    },
  },
});
