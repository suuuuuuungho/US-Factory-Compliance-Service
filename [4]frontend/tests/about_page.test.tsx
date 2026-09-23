// SUU-266: About을 "서명의 아픔 → 원인 3개 → 대가 → RAG로 푼 방법" 흐름으로. 숫자는 전부 public/about-stats.json(SUU-265)에서.
// 제목·숫자·인용구는 New York(font-serif), 본문은 SF Pro(기본).
import { render, screen, within } from "@testing-library/react";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { afterEach, beforeEach, expect, it } from "vitest";
import About from "../src/app/about/page";

const { stats } = JSON.parse(readFileSync(join(__dirname, "../public/about-stats.json"), "utf8"));

// visx ParentSize 는 ResizeObserver 로 크기를 잰다. 바로 600×300 을 알려주는 가짜 (echo_dashboard.test.tsx 와 같음).
const realRO = globalThis.ResizeObserver;
class SizedResizeObserver {
  private cb: ResizeObserverCallback;
  constructor(cb: ResizeObserverCallback) {
    this.cb = cb;
  }
  observe(target: Element) {
    const contentRect = { left: 0, top: 0, width: 600, height: 300 } as DOMRectReadOnly;
    this.cb([{ target, contentRect } as ResizeObserverEntry], this as unknown as ResizeObserver);
  }
  unobserve() {}
  disconnect() {}
}
beforeEach(() => {
  globalThis.ResizeObserver = SizedResizeObserver as unknown as typeof ResizeObserver;
});
afterEach(() => {
  globalThis.ResizeObserver = realRO;
});

it("h1은 서명 문장(957쪽)이고 font-serif, 부제에 136번 개정과 징역 2년이 있다", () => {
  const { container } = render(<About />);
  const h1 = screen.getByRole("heading", { level: 1 });
  expect(h1.textContent).toBe(
    `Every year, someone at your plant signs a legal statement that the plant followed ${stats.part63_pages.value} pages of rules no one there has read in full.`,
  );
  expect(h1.className).toContain("font-serif");
  const header = container.querySelector("header")!;
  expect(header.textContent).toContain(`The rules changed ${stats.rule_changes.value} times since 2018.`);
  expect(header.textContent).toContain(`up to ${stats.prison_years.value} years in prison`);
});

it("h2 섹션이 문제 → 대가 → RAG → 범위 → 출처 순서로 있다", () => {
  render(<About />);
  const h2s = screen.getAllByRole("heading", { level: 2 }).map((h) => h.textContent);
  expect(h2s).toEqual([
    "The signature",
    "Why no one can answer it",
    `The same question, ${stats.letters_total.value.toLocaleString("en-US")} times`,
    "The cost of a wrong answer",
    "How we solved it: RAG",
    "What you get",
    "What we don't do",
    "Also for regulators",
    "Sources",
    "Disclaimer",
  ]);
});

// 큰 숫자는 <… data-stat="키" data-value="JSON 값"> 로 표시한다. 화면 표기($958.8M 등)는 자유, data-value는 JSON 원값
it("화면의 큰 숫자는 모두 about-stats.json 값이고, 핵심 숫자가 빠짐없이 있다", () => {
  const { container } = render(<About />);
  const shown = [...container.querySelectorAll<HTMLElement>("[data-stat]")];
  for (const el of shown) {
    const key = el.dataset.stat!;
    expect(stats[key], key).toBeDefined();
    expect(el.dataset.value, key).toBe(String(stats[key].value));
  }
  const keys = new Set(shown.map((el) => el.dataset.stat));
  for (const k of [
    "part63_pages", "rule_changes", "prison_years",
    "part63_tokens_max", "llm_context_tokens", "sections_changed_pct", "epa_median_days",
    "letters_total", "violation_pct", "penalty_total_usd", "penalty_max_usd",
    "rag_chunks", "rag_eval_cases", "rag_hit20_pct", "rag_subpart_pct", "rag_citation_grounded_pct",
  ]) {
    expect(keys.has(k), k).toBe(true);
  }
});

it("RAG 섹션에 평가 기준 102건이 보이고, 인용구가 있다", () => {
  render(<About />);
  const rag = screen.getByRole("heading", { level: 2, name: "How we solved it: RAG" }).closest("section")!;
  expect(rag.textContent).toContain(String(stats.rag_eval_cases.value));
  expect(within(rag).getByText(/We answer from the current rule text, and show you the line\./)).toBeTruthy();
});

it("차트 11개가 모두 SVG로 그려진다", () => {
  const { container } = render(<About />);
  const charts = [...container.querySelectorAll<HTMLElement>("[data-chart]")].map((el) => el.dataset.chart);
  expect(charts).toEqual([
    "obligation-timeline",
    "corpus-size",
    "rule-changes-by-year",
    "sections-changed",
    "epa-wait",
    "letters-by-year",
    "violation-share",
    "penalty-by-subpart",
    "rag-ndcg-steps",
    "rag-funnel",
    "rag-scores",
  ]);
  for (const el of container.querySelectorAll("[data-chart]")) {
    expect(el.querySelector("svg"), (el as HTMLElement).dataset.chart).not.toBeNull();
  }
});

it("확인 안 된 표현(매일 갱신·실시간)이 없고, 법률 자문이 아니라는 면책이 있다", () => {
  const { container } = render(<About />);
  expect(container.textContent).not.toMatch(/updated daily|daily updates|real[- ]time/i);
  expect(screen.getByText(/not legal advice/i)).toBeTruthy();
});
