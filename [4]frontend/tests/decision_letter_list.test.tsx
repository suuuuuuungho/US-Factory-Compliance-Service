// SUU-253: /decision-letter 가 decision-letters.json 을 읽어 표로 보여주고, 행마다 EPA 원본 PDF 링크를 단다.
// 표·페이지 바는 Federal Register 페이지(SUU-243/244)와 같은 모양.
import { fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import DecisionLetterPage from "../src/app/decision-letter/page";

const PDF_URL = "https://www.epa.gov/system/files/documents/2025-06/domtar-response_3-10-25.pdf";

const LETTERS = [
  {
    source_key: "ce814c7924dce44b",
    facility_name: "Domtar AW LLC-Ashdown AR",
    title: "Applicability Determination for Kraft Pulp Mills",
    subparts: ["S"],
    date: "2025-03-10",
    pdf_url: PDF_URL,
  },
  {
    source_key: "d06f168138377095",
    facility_name: "Missing PDF Co",
    title: "Alternative Monitoring for Boilers",
    subparts: ["DDDDD", "ZZZZ"],
    date: "2021-03-19",
    pdf_url: null,
  },
];

const letter = (n: number) => ({ ...LETTERS[0], source_key: `k${n}`, facility_name: `Facility ${n}` });

async function renderPage(letters: object[] = LETTERS) {
  vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({ letters }), { status: 200 })));
  const utils = render(<DecisionLetterPage />);
  await screen.findByText((letters[0] as { facility_name: string }).facility_name);
  return utils;
}

afterEach(() => vi.unstubAllGlobals());

const bodyRows = () => screen.getAllByRole("row").slice(1);

it("letters 2개면 행 2개, Facility·Title·Subpart·Date 가 보인다", async () => {
  await renderPage();
  const rows = bodyRows();
  expect(rows).toHaveLength(2);
  const first = within(rows[0]);
  expect(first.getByText("Domtar AW LLC-Ashdown AR")).toBeTruthy();
  expect(first.getByText("Applicability Determination for Kraft Pulp Mills")).toBeTruthy();
  expect(first.getByText("S")).toBeTruthy();
  expect(first.getByText("2025-03-10")).toBeTruthy();
  expect(within(rows[1]).getByText("DDDDD, ZZZZ")).toBeTruthy();
});

it("pdf_url 있는 행은 새 탭으로 여는 PDF 링크가 있다", async () => {
  await renderPage();
  const link = within(bodyRows()[0]).getByRole("link", { name: "PDF" }) as HTMLAnchorElement;
  expect(link.getAttribute("href")).toBe(PDF_URL);
  expect(link.getAttribute("target")).toBe("_blank");
  expect(link.getAttribute("rel")).toMatch(/noopener/);
});

it("pdf_url null 인 행은 링크 없이 '원문 없음' 이 보인다", async () => {
  await renderPage();
  const row = within(bodyRows()[1]);
  expect(row.queryByRole("link")).toBeNull();
  expect(row.getByText("원문 없음")).toBeTruthy();
});

it("fetch 실패 시 '불러오지 못했습니다.' 가 보인다", async () => {
  vi.stubGlobal("fetch", vi.fn(async () => { throw new Error("network"); }));
  render(<DecisionLetterPage />);
  expect(await screen.findByText("불러오지 못했습니다.")).toBeTruthy();
});

it("10개씩 Prev/Next 로 넘긴다 (FR 과 같은 모양)", async () => {
  await renderPage(Array.from({ length: 23 }, (_, i) => letter(i + 1)));
  const numbers = () => bodyRows().map((row) => within(row).getAllByRole("cell")[0].textContent?.trim());
  expect(numbers()).toHaveLength(10);
  expect(screen.getByText("1 / 3")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Next" }));
  expect(numbers()[0]).toBe("11");
  fireEvent.click(screen.getByRole("button", { name: "Next" }));
  expect(numbers()).toEqual(["21", "22", "23"]);
  expect((screen.getByRole("button", { name: "Next" }) as HTMLButtonElement).disabled).toBe(true);
});
