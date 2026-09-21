// SUU-205: / 히어로에서 판화풍 미국 국기(SUU-203)를 뺀다. 공장 배경·연기(SUU-201)는 그대로.
import { render, screen } from "@testing-library/react";
import { existsSync } from "node:fs";
import { join } from "node:path";
import { expect, it } from "vitest";
import Home from "../src/app/page";

it("/ 에 alt가 Etched American flag 인 img가 없다", () => {
  render(<Home />);
  expect(screen.queryByAltText("Etched American flag")).toBeNull();
});

it("public/flag-etching.png 파일이 없다", () => {
  expect(existsSync(join(__dirname, "../public/flag-etching.png"))).toBe(false);
});

it("공장 에칭 img 와 hero-smoke 2개는 그대로 있다", () => {
  render(<Home />);
  expect(screen.getByAltText("Factory etching")).toBeTruthy();
  expect(screen.getAllByTestId("hero-smoke")).toHaveLength(2);
});

// SUU-211: h1·카피는 다시 넣었다 (hero_title_new_york.test.tsx). 옛 설명문·Start 만 없는지 본다.
it("/ 에 옛 설명문·Start 링크는 여전히 없다", () => {
  render(<Home />);
  expect(screen.queryByText(/40 CFR Part 63 applicability criteria/)).toBeNull();
  expect(screen.queryByRole("link", { name: "Start" })).toBeNull();
});
