// SUU-243: 목록 영역이 스크롤되고, 10개씩 이전/다음 페이지로 넘긴다.
import { fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import FederalRegisterPage from "../src/app/federal-register/page";

const doc = (n: number) => ({
  document_key: `fr-${n}`,
  document_number: `2025-${n}`,
  title: `Doc ${n}`,
  citation: "90 FR 1",
  canonical_url: "https://www.federalregister.gov/d/x",
  publication_date: "2025-03-10",
  effective_date: "2025-05-09",
  amended_sections: [],
  reason: null,
  summary: { added: 1, removed: 0, changed: 0 },
  sections: [],
});

const DOCS = Array.from({ length: 23 }, (_, i) => doc(i + 1));

async function renderPage() {
  vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({ documents: DOCS }), { status: 200 })));
  const utils = render(<FederalRegisterPage />);
  await screen.findByRole("button", { name: "Doc 1" });
  return utils;
}

afterEach(() => vi.unstubAllGlobals());

const rowNumbers = () =>
  screen.getAllByRole("row").slice(1).map((row) => within(row).getAllByRole("cell")[0].textContent?.trim());

it("목록 영역은 스크롤된다", async () => {
  const { container } = await renderPage();
  const list = container.querySelector("[data-pane='list']")!;
  expect(list.className).toMatch(/overflow-y-auto/);
  expect(list.className).toMatch(/min-h-0/);
});

it("한 페이지 10개, 페이지 표시", async () => {
  await renderPage();
  expect(rowNumbers()).toEqual(["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]);
  expect(screen.getByText("1 / 3")).toBeTruthy();
  expect((screen.getByRole("button", { name: "이전" }) as HTMLButtonElement).disabled).toBe(true);
  expect((screen.getByRole("button", { name: "다음" }) as HTMLButtonElement).disabled).toBe(false);
});

it("다음·이전으로 페이지를 넘긴다", async () => {
  await renderPage();
  fireEvent.click(screen.getByRole("button", { name: "다음" }));
  expect(rowNumbers()[0]).toBe("11");
  expect(rowNumbers()).toHaveLength(10);
  expect(screen.getByText("2 / 3")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "다음" }));
  expect(rowNumbers()).toEqual(["21", "22", "23"]);
  expect((screen.getByRole("button", { name: "다음" }) as HTMLButtonElement).disabled).toBe(true);
  fireEvent.click(screen.getByRole("button", { name: "이전" }));
  expect(rowNumbers()[0]).toBe("11");
});
