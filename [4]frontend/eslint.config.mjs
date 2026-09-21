import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  // Override default ignores of eslint-config-next.
  globalIgnores([
    // Default ignores of eslint-config-next:
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
    // SUU-214: react-bits 에서 받은 그대로 두는 파일. 우리 lint 규칙(react-compiler)에 안 맞아도 손대지 않는다.
    "src/components/PromptBar.tsx",
  ]),
]);

export default eslintConfig;
