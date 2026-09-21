// SUU-204: 글꼴을 Inter → SF Pro(next/font/local)로 바꾸고, 상단바 제목을 굵게(font-bold).
import { render, screen } from "@testing-library/react";
import { readFileSync, statSync } from "node:fs";
import { join } from "node:path";
import { expect, it } from "vitest";
import TopNav from "../src/app/TopNav";

const app = join(__dirname, "../src/app");

it("layout.tsx 는 next/font/local 로 SF Pro 를 쓰고 Inter(next/font/google) 는 없다", () => {
  const src = readFileSync(join(app, "layout.tsx"), "utf8");
  expect(src).toContain('from "next/font/local"');
  expect(src).toContain("SF-Pro-latin.woff2");
  expect(src).toContain("--font-sf-pro");
  expect(src).not.toContain("next/font/google");
  expect(src).not.toMatch(/\bInter\b/);
});

it("globals.css 의 --font-sans 는 --font-sf-pro 를 가리킨다", () => {
  const css = readFileSync(join(app, "globals.css"), "utf8");
  expect(css).toContain("--font-sans: var(--font-sf-pro)");
  expect(css).not.toContain("--font-inter");
});

it("상단바 제목 링크에 font-bold 가 있다", () => {
  render(<TopNav />);
  const cls = screen.getByRole("link", { name: "US Factory Compliance AI Service" }).classList;
  expect(cls.contains("font-bold")).toBe(true);
  expect(cls.contains("font-medium")).toBe(false);
});

it("fonts/SF-Pro-latin.woff2 가 있고 200KB 이하다", () => {
  const size = statSync(join(app, "fonts/SF-Pro-latin.woff2")).size;
  expect(size).toBeLessThanOrEqual(200 * 1024);
});
