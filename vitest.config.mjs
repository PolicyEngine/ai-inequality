import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

// Run the suite west of UTC. There, UTC midnight on the 1st falls on the last
// day of the prior month in local time, so a date label that forgets to name
// its time zone fails here as it would for readers in the Americas.
process.env.TZ = "America/Los_Angeles";

export default defineConfig({
  plugins: [react({ include: /\.(js|jsx|ts|tsx)$/ })],
  esbuild: {
    loader: "jsx",
    include: /src\/.*\.[jt]sx?$/,
  },
  test: {
    environment: "jsdom",
    exclude: ["tests/e2e/**", "node_modules/**", ".next/**", "out/**"],
    globals: true,
    setupFiles: "./src/setupTests.js",
  },
});
