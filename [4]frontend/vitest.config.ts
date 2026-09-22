import { fileURLToPath } from "node:url";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  // SUU-235: 설치된 Bklit 차트가 "@/lib/utils" 를 import 한다. tsconfig paths 와 같게.
  resolve: { alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) } },
  test: { globals: true, environment: "jsdom", include: ["tests/**/*.test.tsx"], setupFiles: ["tests/setup.ts"] },
});
