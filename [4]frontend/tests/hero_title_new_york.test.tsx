// SUU-211: / 히어로 가운데에 제목 h1 + 카피 한 줄을 New York(세리프) 글꼴로. 제목은 굵게, 카피는 보통. Start 는 없다.
import { render, screen } from "@testing-library/react";
import { readFileSync, statSync } from "node:fs";
import { join } from "node:path";
import { expect, it } from "vitest";
import Home from "../src/app/page";

const app = join(__dirname, "../src/app");
const COPY = "Know which 40 CFR Part 63 rules apply to your plant — and why.";

it("/ 에 h1 제목이 있고 font-serif·font-semibold 다", () => {
  render(<Home />);
  const h1 = screen.getByRole("heading", { level: 1, name: "US Factory Compliance AI Service" });
  expect(h1.classList.contains("font-serif")).toBe(true);
  expect(h1.classList.contains("font-semibold")).toBe(true);
});

it("/ 에 카피 한 줄이 있고 font-serif·font-normal 다", () => {
  render(<Home />);
  const p = screen.getByText(COPY);
  expect(p.classList.contains("font-serif")).toBe(true);
  expect(p.classList.contains("font-normal")).toBe(true);
});

it("/ 에 Start 링크는 없다", () => {
  render(<Home />);
  expect(screen.queryByRole("link", { name: "Start" })).toBeNull();
});

it("fonts/NewYork-latin.woff2 가 있고(200KB 이하) layout·globals.css 가 --font-new-york 을 잇는다", () => {
  expect(statSync(join(app, "fonts/NewYork-latin.woff2")).size).toBeLessThanOrEqual(200 * 1024);
  const layout = readFileSync(join(app, "layout.tsx"), "utf8");
  expect(layout).toContain("NewYork-latin.woff2");
  expect(layout).toContain("--font-new-york");
  expect(readFileSync(join(app, "globals.css"), "utf8")).toContain("--font-serif: var(--font-new-york)");
});
