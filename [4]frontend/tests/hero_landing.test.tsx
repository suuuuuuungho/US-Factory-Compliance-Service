// SUU-191: / 는 히어로 랜딩. 섹션 + h1 + 부제 + Start 링크(/applicability).
import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";
import Home from "../src/app/page";

it("/ 의 h1이 US Factory Compliance AI Service 다", () => {
  render(<Home />);
  expect(screen.getByRole("heading", { level: 1 }).textContent).toBe("US Factory Compliance AI Service");
});

it("Start 링크의 href가 /applicability 다", () => {
  render(<Home />);
  expect(screen.getByRole("link", { name: "Start" }).getAttribute("href")).toBe("/applicability");
});

// SUU-192: 보라 gradient 배경은 뺀다. 다른 페이지처럼 canvas 배경.
it("히어로 섹션(region=Hero)에 gradient 배경 클래스가 없다", () => {
  render(<Home />);
  const hero = screen.getByRole("region", { name: "Hero" });
  expect(hero.classList.contains("bg-gradient-violet")).toBe(false);
});
