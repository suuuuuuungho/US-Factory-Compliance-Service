// SUU-201: / 히어로 뒤에 에칭 스타일 공장 이미지, 굴뚝 두 곳에 연기 애니메이션.
import { render, screen } from "@testing-library/react";
import { readFileSync, statSync } from "node:fs";
import { join } from "node:path";
import { expect, it } from "vitest";
import Home from "../src/app/page";

it("/ 에 alt가 Factory etching 인 img가 있고 src에 hero-etching 이 들어 있다", () => {
  render(<Home />);
  const img = screen.getByAltText("Factory etching");
  expect(img.getAttribute("src")).toContain("hero-etching");
});

it("hero-smoke 요소가 2개이고 각각 animate-smoke span이 3개 이상이다", () => {
  render(<Home />);
  const smokes = screen.getAllByTestId("hero-smoke");
  expect(smokes).toHaveLength(2);
  for (const s of smokes) {
    expect(s.querySelectorAll("span.animate-smoke").length).toBeGreaterThanOrEqual(3);
  }
});

it("globals.css 에 smoke-rise keyframes 와 prefers-reduced-motion 규칙이 있다", () => {
  const css = readFileSync(join(__dirname, "../src/app/globals.css"), "utf8");
  expect(css).toContain("@keyframes smoke-rise");
  expect(css).toMatch(/prefers-reduced-motion:\s*reduce/);
});

it("public/hero-etching.png 파일이 있고 500KB 이하다", () => {
  const size = statSync(join(__dirname, "../public/hero-etching.png")).size;
  expect(size).toBeLessThanOrEqual(500 * 1024);
});
