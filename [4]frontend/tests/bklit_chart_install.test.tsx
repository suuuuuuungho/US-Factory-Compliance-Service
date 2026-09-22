// SUU-235: Bklit UI 차트가 설치돼 있고, 샘플 데이터 3개로 BarChart를 그리면 SVG가 나온다.
import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { render, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it } from "vitest";

const ROOT = join(__dirname, "..");
const CHARTS = join(ROOT, "src", "components", "charts");

it("components.json에 @bklit 레지스트리가 있다", () => {
  const json = JSON.parse(readFileSync(join(ROOT, "components.json"), "utf8"));
  expect(json.registries?.["@bklit"]).toBe("https://ui.bklit.com/r/{name}.json");
});

it("bar-chart·area-chart 파일이 src/components/charts/에 있다", () => {
  expect(existsSync(join(CHARTS, "bar-chart.tsx"))).toBe(true);
  expect(existsSync(join(CHARTS, "bar.tsx"))).toBe(true);
  expect(existsSync(join(CHARTS, "area-chart.tsx"))).toBe(true);
});

// visx ParentSize는 ResizeObserver로 크기를 잰다. jsdom엔 없으니 바로 600×300을 알려주는 가짜를 쓴다.
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

it("샘플 데이터 3개로 BarChart를 렌더하면 SVG가 그려진다", async () => {
  // 파일이 아직 없을 때 앞의 두 테스트까지 못 돌게 되지 않도록 동적 import
  const dir = "../src/components/charts/";
  const { BarChart } = await import(/* @vite-ignore */ `${dir}bar-chart`);
  const { Bar } = await import(/* @vite-ignore */ `${dir}bar`);
  const data = [
    { year: "2023", violations: 10 },
    { year: "2024", violations: 25 },
    { year: "2025", violations: 18 },
  ];
  const { container } = render(
    <BarChart data={data} xDataKey="year">
      <Bar dataKey="violations" animate={false} />
    </BarChart>,
  );
  await waitFor(() => expect(container.querySelector("svg")).not.toBeNull());
});
