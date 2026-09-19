// SUU-142: 랜딩 히어로 — 서비스 한 줄 소개 제목 + 판화 그림(hero.png, alt 있음) + CTA 자리표시.
import { cleanup, render, screen } from "@testing-library/react";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { afterEach, describe, expect, it } from "vitest";
import Hero from "./Hero";
import Home from "../app/page";

afterEach(cleanup);

describe("Hero", () => {
  it("서비스 한 줄 소개가 h1으로 렌더된다", () => {
    render(<Hero />);
    const h1 = screen.getByRole("heading", { level: 1 });
    expect(h1.textContent).toContain("규제 조항");
    expect(h1.textContent).toContain("판정 기준");
  });

  it("hero.png가 alt 텍스트와 함께 렌더된다", () => {
    render(<Hero />);
    const img = screen.getByRole("img");
    expect(decodeURIComponent(img.getAttribute("src") ?? "")).toContain("engraving/hero.png");
    expect(img.getAttribute("alt")?.trim().length).toBeGreaterThan(0);
  });

  it("CTA 버튼(링크)이 하나 있다", () => {
    render(<Hero />);
    expect(screen.getAllByRole("link").length).toBeGreaterThanOrEqual(1);
  });

  it("그림 요소에 시차(parallax) 클래스가 붙는다", () => {
    render(<Hero />);
    expect(screen.getByTestId("hero-art").className).toMatch(/parallax/);
  });
});

describe("루트 페이지", () => {
  it("main 안에 Hero의 h1이 있다", () => {
    render(<Home />);
    const main = screen.getByRole("main");
    expect(main.querySelector("h1")).not.toBeNull();
  });
});

describe("폰트 (Source Serif 4)", () => {
  it("globals.css의 serif·sans 둘 다 Source Serif 4 변수를 쓴다", () => {
    const css = readFileSync(resolve(__dirname, "../app/globals.css"), "utf8");
    expect(css).toMatch(/--font-serif:\s*var\(--font-source-serif\)/);
    expect(css).toMatch(/--font-sans:\s*var\(--font-source-serif\)/);
  });
});
