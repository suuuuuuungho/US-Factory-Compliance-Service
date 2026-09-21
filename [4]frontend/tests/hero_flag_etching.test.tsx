// SUU-203: / 히어로에서 h1·설명문·Start 를 없애고, 우측 상단에 판화풍 미국 국기 이미지를 얹는다.
import { render, screen } from "@testing-library/react";
import { statSync } from "node:fs";
import { join } from "node:path";
import { expect, it } from "vitest";
import Home from "../src/app/page";

it("/ 에 h1·설명문·Start 링크가 없다", () => {
  render(<Home />);
  expect(screen.queryByRole("heading", { level: 1 })).toBeNull();
  expect(screen.queryByText(/40 CFR Part 63 applicability criteria/)).toBeNull();
  expect(screen.queryByRole("link", { name: "Start" })).toBeNull();
});

it("/ 에 alt가 Etched American flag 인 img가 있고 src에 flag-etching 이 들어 있다", () => {
  render(<Home />);
  const img = screen.getByAltText("Etched American flag");
  expect(img.getAttribute("src")).toContain("flag-etching");
});

it("국기 img는 우측 상단(absolute top-0 right-0)에 놓이고 어둡기 레이어(z-10)보다 위(z-20)다", () => {
  render(<Home />);
  const cls = screen.getByAltText("Etched American flag").classList;
  for (const c of ["absolute", "top-0", "right-0", "z-20"]) expect(cls.contains(c)).toBe(true);
});

it("public/flag-etching.png 파일이 있고 500KB 이하다", () => {
  const size = statSync(join(__dirname, "../public/flag-etching.png")).size;
  expect(size).toBeLessThanOrEqual(500 * 1024);
});

// 공장 에칭 배경·연기(SUU-201)는 그대로 남는다
it("공장 에칭 img 와 hero-smoke 2개는 그대로 있다", () => {
  render(<Home />);
  expect(screen.getByAltText("Factory etching")).toBeTruthy();
  expect(screen.getAllByTestId("hero-smoke")).toHaveLength(2);
});
