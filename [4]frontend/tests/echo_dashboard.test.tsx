// SUU-237: /echo 페이지가 echo-stats.json 을 읽어 타일·Subpart 표·연도별 차트를 그린다.
// SUU-242: 영어 라벨, 벌금 총액·최대 타일, 10줄 페이지, 정렬 ↓/↑ 토글, 차트 왼쪽에 연도 없음, deviation 설명.
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

const sub = (code: string, over: Partial<Record<string, number | null>> = {}) => ({
  code,
  desc: code,
  facilities: 10,
  mfg_facilities: 1,
  violation_facility_pct: 10,
  penalty_count: 1,
  penalty_median_usd: 1000,
  penalty_total_usd: 1000,
  penalty_max_usd: 1000,
  deviation_y_pct: 10,
  ...over,
});

const STATS = {
  summary: {
    facilities: 49618,
    mfg_facilities: 11884,
    violation_facility_pct: 27.9,
    penalty_count: 9998,
    penalty_median_usd: 9098.5,
    penalty_total_usd: 958783122.68,
    penalty_max_usd: 100000000,
    deviation_y_pct: 18.5,
  },
  subparts: [
    sub("ZZZZ", { facilities: 28174, mfg_facilities: 3335, violation_facility_pct: 26.0, penalty_total_usd: 622077405.61, penalty_max_usd: 47833048.21 }),
    sub("M", { facilities: 8772, mfg_facilities: 0, violation_facility_pct: 7.0, penalty_total_usd: 220790.68, penalty_max_usd: 48254 }),
    sub("A", { facilities: 5074, mfg_facilities: 2684, violation_facility_pct: 49.2, penalty_median_usd: null, penalty_total_usd: 0, penalty_max_usd: null }),
    // 10줄 넘기려고 9개 더 (총 12개)
    ...["B", "C", "D", "E", "F", "G", "H", "I", "J"].map((code, i) => sub(code, { facilities: 100 - i })),
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
const FIRST_PAGE = ["ZZZZ", "M", "A", "B", "C", "D", "E", "F", "G", "H"];

it("타일 5개: 시설·위반%·벌금 총액($958.8M)·최대($100.0M)·deviation%", async () => {
  await openPage();
  expect(screen.getByTestId("tile-facilities").textContent).toContain("49,618");
  expect(screen.getByTestId("tile-violation-pct").textContent).toContain("27.9");
  expect(screen.getByTestId("tile-penalty-total").textContent).toContain("$958.8M");
  expect(screen.getByTestId("tile-penalty-max").textContent).toContain("$100.0M");
  expect(screen.getByTestId("tile-deviation-pct").textContent).toContain("18.5");
  expect(screen.queryByTestId("tile-penalty-median")).toBeNull();
});

it("화면 글자가 전부 영어다 (한글 없음)", async () => {
  const container = await openPage();
  expect(container.textContent).not.toMatch(/[가-힣]/);
  expect(screen.getByRole("heading", { name: "By Subpart" })).toBeTruthy();
  expect(screen.getByRole("heading", { name: "Violations and penalty actions by year" })).toBeTruthy();
});

it("Subpart 표는 10줄씩, Next/Prev 로 넘긴다", async () => {
  await openPage();
  expect(rowCodes()).toEqual(FIRST_PAGE);
  const pager = within(screen.getByTestId("pager"));
  expect(pager.getByText("1 / 2")).toBeTruthy();
  expect((pager.getByRole("button", { name: /Prev/ }) as HTMLButtonElement).disabled).toBe(true);
  fireEvent.click(pager.getByRole("button", { name: /Next/ }));
  expect(rowCodes()).toEqual(["I", "J"]);
  expect((pager.getByRole("button", { name: /Next/ }) as HTMLButtonElement).disabled).toBe(true);
  fireEvent.click(pager.getByRole("button", { name: /Prev/ }));
  expect(rowCodes()).toEqual(FIRST_PAGE);
});

it("Manufacturing only 토글하면 mfg_facilities=0 인 행이 사라지고 1쪽으로 돌아간다", async () => {
  await openPage();
  fireEvent.click(within(screen.getByTestId("pager")).getByRole("button", { name: /Next/ }));
  fireEvent.click(screen.getByRole("checkbox", { name: "Manufacturing only" }));
  expect(rowCodes()).toEqual(["ZZZZ", "A", "B", "C", "D", "E", "F", "G", "H", "I"]);
  fireEvent.click(screen.getByRole("checkbox", { name: "Manufacturing only" }));
  expect(rowCodes()).toEqual(FIRST_PAGE);
});

it("열 헤더 클릭 → 내림차순, 다시 클릭 → 오름차순. null 은 내림차순에서 맨 뒤", async () => {
  await openPage();
  const table = screen.getByRole("table");
  fireEvent.click(within(table).getByRole("button", { name: /Violation %/ }));
  expect(rowCodes().slice(0, 2)).toEqual(["A", "ZZZZ"]); // 49.2, 26.0, 그 뒤 10 짜리 B~J, 마지막 M(7.0)
  fireEvent.click(within(table).getByRole("button", { name: /Violation %/ }));
  expect(rowCodes()[0]).toBe("M");
  expect(within(table).getByRole("button", { name: /Violation %/ }).textContent).toContain("↑");
  fireEvent.click(within(table).getByRole("button", { name: /Max \$/ }));
  expect(rowCodes().slice(0, 2)).toEqual(["ZZZZ", "M"]);
  fireEvent.click(within(screen.getByTestId("pager")).getByRole("button", { name: /Next/ }));
  expect(rowCodes().at(-1)).toBe("A"); // max 가 null → 맨 뒤
});

it("표 셀의 돈은 $622.1M · $48K 처럼 짧게", async () => {
  await openPage();
  const zzzz = screen.getAllByTestId("subpart-row")[0];
  expect(zzzz.textContent).toContain("$622.1M");
  expect(zzzz.textContent).toContain("$47.8M");
  expect(screen.getAllByTestId("subpart-row")[1].textContent).toContain("$48K");
});

it("연도별 차트 SVG 가 그려지고, 왼쪽에 연도 라벨(BarYAxis)이 없다", async () => {
  const container = await openPage();
  await waitFor(() => expect(container.querySelector("[data-chart='yearly'] svg")).not.toBeNull());
  const chart = container.querySelector("[data-chart='yearly']")!;
  // BarYAxis 는 연도를 <span> 으로 찍는다. BarXAxis 도 span 이라 "2023" 이 1번만 나와야 한다
  const yearSpans = Array.from(chart.querySelectorAll("span")).filter((el) => el.textContent === "2023");
  expect(yearSpans.length).toBeLessThanOrEqual(1);
});

it("Title V deviation 설명은 타일 5개 바로 아래, 표보다 위에 있다", async () => {
  await openPage();
  const note = screen.getByTestId("deviation-note");
  expect(note.textContent).toContain("What is a Title V deviation?");
  expect(note.textContent).toMatch(/self-reported/);
  const tiles = screen.getByTestId("tile-deviation-pct").parentElement!;
  expect(tiles.nextElementSibling).toBe(note);
  expect(note.compareDocumentPosition(screen.getByRole("table")) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
});

it("타일 글자는 가운데 정렬, 총액 라벨에 건수 괄호 없음", async () => {
  await openPage();
  const tile = screen.getByTestId("tile-penalty-total");
  expect(tile.className).toContain("text-center");
  expect(tile.textContent).toContain("Total penalties since 2015");
  expect(tile.textContent).not.toMatch(/actions/);
});
