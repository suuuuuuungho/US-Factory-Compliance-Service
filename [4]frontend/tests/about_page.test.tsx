// About 페이지: 담당자용 소개. h1·h2 New York, 인용 조문은 eCFR 링크(accent-blue), 한글·개발자 이야기 없음.
import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";
import About from "../src/app/about/page";

const H2 = [
  "You face the same question every filing.",
  "Why it’s hard to answer alone.",
  "What a mistake costs.",
  "We don’t decide.",
  "Nothing without a citation.",
  "How it works",
  "Tested on 102 real EPA questions.",
  "Where the data comes from",
];

it("/about h1은 New York(font-serif)이고 서비스가 무엇인지 말한다", () => {
  render(<About />);
  const h1 = screen.getByRole("heading", { level: 1 });
  expect(h1.textContent).toBe("Find the Part 63 rules that may apply to your plant.");
  expect(h1.classList.contains("font-serif")).toBe(true);
});

it("/about h2 8개가 순서대로 있고 전부 font-serif다", () => {
  render(<About />);
  const h2s = screen.getAllByRole("heading", { level: 2 });
  expect(h2s.map((h) => h.textContent)).toEqual(H2);
  for (const h of h2s) expect(h.classList.contains("font-serif")).toBe(true);
});

it("/about 반복 서류 4개 + 책임 2개는 각각 40 CFR 조문을 eCFR 새 창 링크(accent-blue)로 단다", () => {
  render(<About />);
  const cites = screen.getAllByRole("link", { name: /^40 CFR 7[01]\./ });
  expect(cites).toHaveLength(6);
  for (const a of cites) {
    expect(a.getAttribute("href")).toMatch(/^https:\/\/www\.ecfr\.gov\/current\/title-40\//);
    expect(a.getAttribute("target")).toBe("_blank");
    expect(a.classList.contains("text-accent-blue")).toBe(true);
  }
});

it("/about 과징금 숫자 3개와 서명자 책임·가동 중단 근거가 있다", () => {
  render(<About />);
  expect(screen.getByText("27.9%")).toBeTruthy();
  expect(screen.getByText("$958.8M")).toBeTruthy();
  expect(screen.getByText("$100M")).toBeTruthy();
  expect(screen.getByRole("link", { name: "40 CFR 70.5(d)" })).toBeTruthy();
  expect(screen.getByRole("link", { name: "40 CFR 70.7(c)(1)(ii)" })).toBeTruthy();
});

it("/about 주는 것 5개·안 주는 것 3개가 있고, 최종 판정과 법률 자문은 안 준다", () => {
  render(<About />);
  expect(screen.getByText("What you get")).toBeTruthy();
  expect(screen.getByText("What we never do")).toBeTruthy();
  expect(screen.getByText("A final applicability determination")).toBeTruthy();
  expect(screen.getByText("Legal advice")).toBeTruthy();
  expect(screen.getByText("A checklist of what you must confirm on site")).toBeTruthy();
});

it("/about How it works는 4단계다", () => {
  render(<About />);
  const list = screen.getByRole("heading", { level: 2, name: "How it works" }).nextElementSibling!;
  expect(list.tagName).toBe("OL");
  expect(list.querySelectorAll("li")).toHaveLength(4);
});

it("/about 검증 숫자 3개와 법률 자문 아님 고지, Ask 버튼이 있다", () => {
  render(<About />);
  expect(screen.getByText("93%")).toBeTruthy();
  expect(screen.getByText("99.6%")).toBeTruthy();
  expect(screen.getByText("0.95")).toBeTruthy();
  expect(screen.getByText("Not legal advice. Always verify the cited text before you sign.")).toBeTruthy();
  expect(screen.getByRole("link", { name: "Ask about your plant" }).getAttribute("href")).toBe("/applicability");
});

it("/about 글자에 한글·개발자 이야기(Claude, Codex, Linear, TDD)가 없다", () => {
  const { container } = render(<About />);
  const text = container.textContent ?? "";
  expect(text).not.toMatch(/[가-힣]/);
  expect(text).not.toMatch(/Claude|Codex|Linear|TDD|SUU-\d+/);
});
