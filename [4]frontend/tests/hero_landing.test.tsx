// SUU-191: / 는 히어로 랜딩. SUU-203: h1·부제·Start 는 없앴다 (hero_flag_etching.test.tsx).
import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";
import Home from "../src/app/page";

// SUU-192: 보라 gradient 배경은 뺀다. 다른 페이지처럼 canvas 배경.
it("히어로 섹션(region=Hero)에 gradient 배경 클래스가 없다", () => {
  render(<Home />);
  const hero = screen.getByRole("region", { name: "Hero" });
  expect(hero.classList.contains("bg-gradient-violet")).toBe(false);
});
