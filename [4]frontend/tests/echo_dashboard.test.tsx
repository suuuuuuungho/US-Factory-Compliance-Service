// SUU-237: /echo 페이지가 echo-stats.json 을 읽어 타일·Subpart 표·연도별 차트를 그린다.
// SUU-248: 주별은 지도. 주 path 에 data-state, 값 큰 주가 더 밝다, hover 하면 이름·금액.
// SUU-246: 차트 5개(연도별 $·Subpart Top10·주 Top10·벌금 크기 분포 추가), 가로 막대엔 이름 라벨.
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
    { year: 2023, violations: 2000, penalties: 700, penalty_usd: 136174046.39 },
    { year: 2024, violations: 2100, penalties: 650, penalty_usd: 135917192.26 },
    { year: 2025, violations: 2279, penalties: 687, penalty_usd: 150279934.89 },
  ],
  states: [
    { state: "NM", ...sub("x"), penalty_total_usd: 191816340 },
    { state: "TX", ...sub("x"), penalty_total_usd: 144817823 },
    ...["MI", "IN", "CA", "CO", "PA", "OH", "LA", "IL", "WV", "KY", "AL"].map((state, i) => ({ state, ...sub("x"), penalty_total_usd: 1000 - i })),
  ],
  penalty_buckets: [
    { bucket: "<$1K", count: 585 },
    { bucket: "$1K–10K", count: 4612 },
    { bucket: "$10K–100K", count: 3831 },
    { bucket: "$100K–1M", count: 867 },
    { bucket: "$1M+", count: 103 },
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

it("연도별 두 차트는 꺾은선: 선 path 2개·1개, 연도 눈금, hover 하면 값", async () => {
  const container = await openPage();
  const yearly = container.querySelector("[data-chart='yearly']")!;
  expect(yearly.querySelectorAll("path[data-series]").length).toBe(2);
  expect(container.querySelector("[data-chart='yearly-usd']")!.querySelectorAll("path[data-series]").length).toBe(1);
  expect(yearly.textContent).toContain("2025"); // 5의 배수 연도 눈금
  expect(yearly.querySelectorAll("rect").length).toBe(0); // 막대 없음
  expect(within(yearly as HTMLElement).getByTestId("line-legend").textContent).toBe("ViolationsPenalty actions");
  expect(container.querySelector("[data-chart='yearly-usd'] [data-testid='line-legend']")).toBeNull(); // 선 하나면 범례 없음
  const svg = yearly.querySelector("svg")!;
  svg.getBoundingClientRect = () => ({ left: 0, top: 0, width: 600, height: 300, right: 600, bottom: 300, x: 0, y: 0, toJSON() {} }) as DOMRect;
  fireEvent.mouseMove(svg, { clientX: 590, clientY: 100 }); // 오른쪽 끝 = 마지막 해
  expect(within(yearly as HTMLElement).getByTestId("line-hover").textContent).toBe("2025 · Violations 2,279 · Penalty actions 687");
});

it("차트 5개가 모두 SVG 로 그려지고, 지도는 맨 아래 2열 폭", async () => {
  const container = await openPage();
  for (const id of ["yearly", "yearly-usd", "top-subparts", "buckets", "state-map"]) {
    await waitFor(() => expect(container.querySelector(`[data-chart='${id}'] svg`), id).not.toBeNull());
  }
  const cards = Array.from(container.querySelectorAll("[data-chart]")).map((el) => el.getAttribute("data-chart"));
  expect(cards.at(-1)).toBe("state-map");
  const mapCard = container.querySelector("[data-chart='state-map']")!.closest("section")!;
  expect(mapCard.className).toContain("md:col-span-2");
  expect(mapCard.querySelector("[data-chart='buckets']")).toBeNull(); // 다른 카드 안에 들어가 있지 않다
  expect(container.querySelector("[data-chart='buckets']")!.closest("section")!.contains(mapCard)).toBe(false);
});

it("가로 막대는 벌금 총액 큰 순 10개, 왼쪽에 이름이 보인다", async () => {
  const container = await openPage();
  const labels = (id: string) => Array.from(container.querySelectorAll(`[data-chart='${id}'] span`)).map((el) => el.textContent);
  await waitFor(() => expect(labels("top-subparts")).toContain("ZZZZ"));
  const subparts = labels("top-subparts");
  expect(subparts.indexOf("ZZZZ")).toBeLessThan(subparts.indexOf("M")); // $622M 이 $220K 보다 위
  expect(subparts).not.toContain("A"); // total 0 → 12개 중 10개에 못 듦
  expect(subparts.length).toBe(10);
});

it("주별 지도: 주 path 50개 이상, 금액 클수록 진하게(NM > TX > MI), 데이터 없는 주는 회색, 범례, hover", async () => {
  const container = await openPage();
  const map = container.querySelector("[data-chart='state-map']")!;
  const paths = map.querySelectorAll("path[data-state]");
  expect(paths.length).toBeGreaterThanOrEqual(50);
  const level = (code: string) => Number(map.querySelector(`path[data-state='${code}']`)!.getAttribute("data-level"));
  const fill = (code: string) => map.querySelector(`path[data-state='${code}']`)!.getAttribute("fill")!;
  expect(level("NM")).toBe(1);
  expect(level("NM")).toBeGreaterThan(level("TX"));
  expect(level("TX")).toBeGreaterThan(level("MI"));
  expect(fill("NM")).toContain("#3418b8"); // 1등 = 제일 짙은 보라
  expect(fill("TX")).toContain("color-mix(in oklch"); // 사이 값은 섞은 색
  expect(fill("WY")).toBe("#1c1c1c"); // 데이터 없음 = 회색
  expect(level("WY")).toBe(0);
  expect(screen.getByTestId("map-legend").textContent).toContain("$191.8M");
  fireEvent.mouseEnter(map.querySelector("path[data-state='TX']")!);
  expect(screen.getByTestId("map-hover").textContent).toContain("TX · $144.8M · 10 facilities");
});

it("색 역할: 벌금 $ 타일·선은 보라, 위반은 코랄. 표는 좁은 화면에서 가로 스크롤 상자 안", async () => {
  const container = await openPage();
  expect(screen.getByRole("table").parentElement!.className).toContain("overflow-x-auto");
  expect(screen.getByTestId("tile-penalty-total").querySelector(".text-gradient-violet")).not.toBeNull();
  expect(screen.getByTestId("tile-penalty-max").querySelector(".text-gradient-violet")).not.toBeNull();
  expect(screen.getByTestId("tile-violation-pct").querySelector(".text-gradient-coral")).not.toBeNull();
  expect(screen.getByTestId("tile-facilities").querySelector(".text-ink")).not.toBeNull();
  const yearly = container.querySelector("[data-chart='yearly']")!;
  expect(yearly.querySelector("path[data-series='violations']")!.getAttribute("stroke")).toBe("var(--color-gradient-coral)");
  expect(yearly.querySelector("path[data-series='penalties']")!.getAttribute("stroke")).toBe("var(--color-gradient-violet)");
  expect(yearly.querySelectorAll("linearGradient").length).toBe(2); // 선 아래 그라디언트 면
  const table = screen.getByRole("table");
  fireEvent.click(within(table).getByRole("button", { name: /Total \$/ }));
  expect(within(table).getByRole("button", { name: /Total \$/ }).className).toContain("text-gradient-violet");
});

it("벌금 크기 분포 차트는 구간 5개 라벨을 찍는다", async () => {
  const container = await openPage();
  await waitFor(() => expect(container.textContent).toContain("$1M+"));
  expect(container.querySelector("[data-chart='buckets']")!.textContent).toContain("$10K–100K");
});

it("Title V deviation 설명은 타일 5개 바로 아래, 표보다 위에 있다", async () => {
  await openPage();
  const note = screen.getByTestId("deviation-note");
  expect(note.textContent).toContain("What is a Title V deviation?");
  expect(note.textContent).toMatch(/self-reported/);
  // 설명 안 강조어는 색 없이 굵게만
  expect(note.querySelectorAll(".font-semibold.text-ink").length).toBe(2);
  expect(note.querySelector(".text-gradient-violet")).toBeNull();
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
