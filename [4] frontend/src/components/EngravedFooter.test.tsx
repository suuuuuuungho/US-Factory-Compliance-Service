// SUU-141: 판화 푸터 — 공장·기차·연기 그림이 렌더되고, 기차/연기가 무한 반복 애니메이션을 갖는다.
import { cleanup, render, screen } from "@testing-library/react";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { afterEach, describe, expect, it } from "vitest";
import EngravedFooter from "./EngravedFooter";

afterEach(cleanup);

// 장식 이미지(alt="")는 role이 img가 아니므로 태그로 찾는다
const imgSrcs = (root: HTMLElement) =>
  Array.from(root.querySelectorAll("img")).map((el) => decodeURIComponent(el.getAttribute("src") ?? ""));

describe("EngravedFooter", () => {
  it("공장·기차·연기 그림을 렌더한다", () => {
    const { container } = render(<EngravedFooter />);
    const srcs = imgSrcs(container);
    expect(srcs.some((s) => s.includes("engraving/factory.png"))).toBe(true);
    expect(srcs.some((s) => s.includes("engraving/train.png"))).toBe(true);
    expect(srcs.filter((s) => /engraving\/smoke-[123]\.png/.test(s)).length).toBeGreaterThanOrEqual(3);
  });

  it("기차 요소에 무한 반복 애니메이션 클래스가 붙는다", () => {
    render(<EngravedFooter />);
    expect(screen.getByTestId("footer-train").className).toMatch(/animate-train/);
    for (const smoke of screen.getAllByTestId("footer-smoke")) {
      expect(smoke.className).toMatch(/animate-smoke/);
    }
  });

  it("푸터 링크 3열이 있다", () => {
    render(<EngravedFooter />);
    expect(screen.getByRole("contentinfo")).toBeTruthy();
    expect(screen.getAllByRole("list").length).toBeGreaterThanOrEqual(3);
  });
});

describe("globals.css 애니메이션", () => {
  const css = readFileSync(resolve(__dirname, "../app/globals.css"), "utf8");

  it("train·smoke 애니메이션이 infinite로 정의된다", () => {
    expect(css).toMatch(/--animate-train:[^;]*infinite/);
    expect(css).toMatch(/--animate-smoke:[^;]*infinite/);
  });

  it("prefers-reduced-motion: reduce 이면 animation: none", () => {
    const m = css.match(/@media\s*\(prefers-reduced-motion:\s*reduce\)\s*\{([\s\S]*?)\n\}/);
    expect(m, "reduced-motion 블록 없음").toBeTruthy();
    expect(m![1]).toMatch(/animation:\s*none/);
  });
});
