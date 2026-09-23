// SUU-267: About 차트는 bklit 부품(src/components/charts/)으로 그리고, 화면 출처는 about-stats.json의 영어 cite만 보여준다.
// bklit 차트 컴포넌트를 data-bklit 표시가 붙은 상자로 감싸서, 각 차트가 어떤 부품으로 그려졌는지 확인한다.
import { render, waitFor } from "@testing-library/react";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import About from "../src/app/about/page";

const { tag } = vi.hoisted(() => {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const { createElement } = require("react");
  const tag = (kind: string, Comp: (p: object) => unknown) => {
    const Tagged = (p: object) => createElement("div", { "data-bklit": kind }, createElement(Comp, p));
    return Tagged;
  };
  return { tag };
});

// 아직 설치 안 된 부품(line/funnel/ring)은 page가 import할 때만 불린다
vi.mock("@/components/charts/bar-chart", async (orig) => {
  const m = await orig<typeof import("@/components/charts/bar-chart")>();
  const T = tag("bar-chart", m.BarChart as never);
  return { ...m, BarChart: T, default: T };
});
vi.mock("@/components/charts/area-chart", async (orig) => {
  const m = await orig<typeof import("@/components/charts/area-chart")>();
  const T = tag("area-chart", m.AreaChart as never);
  return { ...m, AreaChart: T, default: T };
});
vi.mock("@/components/charts/line-chart", async (orig) => {
  const m = await orig<Record<string, never>>();
  const T = tag("line-chart", m.LineChart);
  return { ...m, LineChart: T, default: T };
});
vi.mock("@/components/charts/funnel-chart", async (orig) => {
  const m = await orig<Record<string, never>>();
  const T = tag("funnel-chart", m.FunnelChart);
  return { ...m, FunnelChart: T, default: T };
});
vi.mock("@/components/charts/ring-chart", async (orig) => {
  const m = await orig<Record<string, never>>();
  const T = tag("ring-chart", m.RingChart);
  return { ...m, RingChart: T, default: T };
});

const { stats, series } = JSON.parse(readFileSync(join(__dirname, "../public/about-stats.json"), "utf8"));

// visx ParentSize 는 ResizeObserver 로 크기를 잰다. 바로 600×300 을 알려주는 가짜 (about_page.test.tsx 와 같음).
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

// 차트별로 허용하는 bklit 부품. 연도 축은 AreaChart·LineChart가 날짜 전용이라 BarChart도 허용 (YearLineChart.tsx 주석 참고)
const ALLOWED: Record<string, string[]> = {
  "corpus-size": ["bar-chart"],
  "rule-changes-by-year": ["bar-chart", "area-chart", "line-chart"],
  "sections-changed": ["bar-chart", "ring-chart"],
  "epa-wait": ["bar-chart"],
  "letters-by-year": ["bar-chart", "area-chart", "line-chart"],
  "violation-share": ["bar-chart", "ring-chart"],
  "penalty-by-subpart": ["bar-chart"],
  "rag-ndcg-steps": ["bar-chart"],
  "rag-funnel": ["funnel-chart"],
  "rag-scores": ["ring-chart"],
};

it("타임라인을 뺀 차트 10개는 bklit 부품으로 그리고, 직접 그린 SVG가 없다", async () => {
  const { container } = render(<About />);
  for (const [name, kinds] of Object.entries(ALLOWED)) {
    const fig = container.querySelector<HTMLElement>(`[data-chart="${name}"]`);
    expect(fig, name).not.toBeNull();
    const used = [...fig!.querySelectorAll<HTMLElement>("[data-bklit]")].map((el) => el.dataset.bklit!);
    expect(used.length, `${name}: bklit 부품이 없다`).toBeGreaterThan(0);
    for (const k of used) expect(kinds, `${name}: ${k}`).toContain(k);
    // 차트 안의 모든 svg는 bklit 부품 안에 있어야 한다 (직접 그린 svg 금지)
    await waitFor(() => expect(fig!.querySelector("svg"), name).not.toBeNull());
    const svgs = [...fig!.querySelectorAll("svg")];
    for (const svg of svgs) expect(svg.closest("[data-bklit]"), `${name}: 직접 그린 svg`).not.toBeNull();
  }
});

// 화면에 보이면 안 되는 내부 이름·한글
const INTERNAL = /[ㄱ-ㆎ가-힣]|\.md\b|\.json\b|\bDB\b|SUU-\d|fr_document|adi_source_entry|평가셋/;

it("화면 출처는 about-stats.json의 cite이고, 내부 이름과 한글이 페이지 어디에도 없다", () => {
  const { container } = render(<About />);
  const text = container.textContent!;
  expect(text).not.toMatch(INTERNAL);
  for (const k of ["part63_pages", "part63_tokens_max", "rule_changes", "sections_changed_pct", "epa_median_days",
    "letters_total", "prison_years", "violation_pct", "rag_citation_grounded_pct"]) {
    expect(text, k).toContain(stats[k].cite);
  }
  for (const k of ["rule_changes_by_year", "letters_by_year", "penalty_by_subpart", "rag_ndcg_steps", "rag_funnel"]) {
    expect(text, k).toContain(series[k].cite);
  }
});
