// SUU-217: About 페이지. 서비스가 무엇을 하고/안 하는지, 데이터 출처, 면책. 제목은 New York(font-serif).
import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";
import About from "../src/app/about/page";

it("h1이 있고 New York(font-serif)을 쓴다", () => {
  render(<About />);
  const h1 = screen.getByRole("heading", { level: 1 });
  expect(h1.textContent).toMatch(/verdict/i);
  expect(h1.className).toContain("font-serif");
});

it("섹션 6개가 순서대로 있다", () => {
  render(<About />);
  const h2s = screen.getAllByRole("heading", { level: 2 }).map((h) => h.textContent);
  expect(h2s).toEqual([
    "Who it's for",
    "Why it's hard",
    "What we do — and don't",
    "How it works",
    "Data sources",
    "Disclaimer",
  ]);
});

it("하는 것 5개 / 안 하는 것 2개 목록이 있다", () => {
  render(<About />);
  expect(screen.getByRole("list", { name: "What we do" }).children).toHaveLength(5);
  expect(screen.getByRole("list", { name: "What we don't do" }).children).toHaveLength(2);
});

it("데이터 출처 4개(eCFR, Federal Register, ECHO, ADI)가 보인다", () => {
  const { container } = render(<About />);
  const terms = [...container.querySelectorAll("dt")].map((d) => d.textContent);
  expect(terms).toEqual(["eCFR", "Federal Register", "ECHO", "ADI"]);
});

it("법률 자문이 아니라는 면책 문구가 있다", () => {
  render(<About />);
  expect(screen.getByText(/not legal advice/i)).toBeTruthy();
});
