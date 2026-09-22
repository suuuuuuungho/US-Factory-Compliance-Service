// SUU-237: /echo 페이지가 echo-stats.json 을 읽어 타일 4개·Subpart 표·연도별 차트를 그린다.
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import EchoPage from "../src/app/echo/page";

// visx ParentSize 는 ResizeObserver 로 크기를 잰다. 바로 600×300 을 알려주는 가짜 (bklit_chart_install.test.tsx 와 같음).
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
  vi.unstubAllGlobals();
});

const STATS = {
  summary: {
    facilities: 49618,
    mfg_facilities: 11884,
    violation_facility_pct: 27.9,
    penalty_count: 9998,
    penalty_median_usd: 9098.5,
    deviation_y_pct: 18.5,
  },
  subparts: [
    { code: "ZZZZ", desc: "RICE", facilities: 28174, mfg_facilities: 3335, violation_facility_pct: 26.0, penalty_count: 5227, penalty_median_usd: 11250, deviation_y_pct: 21.7 },
    { code: "M", desc: "DRY CLEANERS", facilities: 8772, mfg_facilities: 0, violation_facility_pct: 7.0, penalty_count: 29, penalty_median_usd: 5000, deviation_y_pct: 10.0 },
    { code: "A", desc: "GENERAL PROVISIONS", facilities: 5074, mfg_facilities: 2684, violation_facility_pct: 49.2, penalty_count: 2635, penalty_median_usd: null, deviation_y_pct: 20.8 },
  ],
  yearly: [
    { year: 2023, violations: 2000, penalties: 700 },
    { year: 2024, violations: 2100, penalties: 650 },
    { year: 2025, violations: 2279, penalties: 687 },
  ],
};

async function openPage() {
  vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify(STATS), { status: 200 })));
  const { container } = render(<EchoPage />);
  await screen.findAllByTestId("subpart-row");
  return container;
}

const rowCodes = () => screen.getAllByTestId("subpart-row").map((row) => row.getAttribute("data-code"));

it("타일 4개 값과 Subpart 행 수가 JSON과 같다", async () => {
  await openPage();
  expect(screen.getByTestId("tile-facilities").textContent).toContain("49,618");
  expect(screen.getByTestId("tile-violation-pct").textContent).toContain("27.9");
  expect(screen.getByTestId("tile-penalty-median").textContent).toContain("9,098");
  expect(screen.getByTestId("tile-deviation-pct").textContent).toContain("18.5");
  expect(rowCodes()).toEqual(["ZZZZ", "M", "A"]);
});

it("제조업만 토글하면 mfg_facilities=0 인 행이 사라진다", async () => {
  await openPage();
  fireEvent.click(screen.getByRole("checkbox", { name: "제조업만" }));
  expect(rowCodes()).toEqual(["ZZZZ", "A"]);
  fireEvent.click(screen.getByRole("checkbox", { name: "제조업만" }));
  expect(rowCodes()).toEqual(["ZZZZ", "M", "A"]);
});

it("열 헤더를 클릭하면 그 열 기준 내림차순으로 정렬된다", async () => {
  await openPage();
  const table = screen.getByRole("table");
  fireEvent.click(within(table).getByRole("button", { name: /위반 시설/ }));
  expect(rowCodes()).toEqual(["A", "ZZZZ", "M"]);
  // 중앙값이 null 인 행은 맨 뒤
  fireEvent.click(within(table).getByRole("button", { name: /벌금 중앙값/ }));
  expect(rowCodes()).toEqual(["ZZZZ", "M", "A"]);
});

it("연도별 차트 SVG 가 그려진다", async () => {
  const container = await openPage();
  await waitFor(() => expect(container.querySelector("[data-chart='yearly'] svg")).not.toBeNull());
});
