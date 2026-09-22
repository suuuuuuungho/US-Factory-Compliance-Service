// SUU-259: Decision Letter 표에서 Facility 열은 좁게(고정 최대 너비 + ... 자름), Title 열은 남는 폭을 다 쓴다.
import { render, screen, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import DecisionLetterPage from "../src/app/decision-letter/page";

const LONG_FACILITY = "Domtar AW LLC-Ashdown AR Kraft Pulp and Paper Manufacturing Complex";
const LONG_TITLE = "Applicability Determination for Kraft Pulp Mills Regarding Alternative Monitoring Requirements";

const LETTERS = [
  {
    source_key: "ce814c7924dce44b",
    facility_name: LONG_FACILITY,
    title: LONG_TITLE,
    subparts: ["S"],
    date: "2025-03-10",
    pdf_url: null,
  },
];

async function renderPage() {
  vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({ letters: LETTERS }), { status: 200 })));
  render(<DecisionLetterPage />);
  await screen.findByText(LONG_FACILITY);
}

afterEach(() => vi.unstubAllGlobals());

const firstRow = () => within(screen.getAllByRole("row")[1]);

it("Facility 셀은 최대 너비가 있고 글자가 truncate 되며 title 속성에 전체 이름이 있다", async () => {
  await renderPage();
  const text = firstRow().getByText(LONG_FACILITY);
  expect(text.className).toMatch(/\btruncate\b/);
  expect(text.getAttribute("title")).toBe(LONG_FACILITY);
  const cell = text.closest("td") as HTMLTableCellElement;
  expect(cell.className).toMatch(/\bmax-w-\[\d+px\]/);
  expect(cell.className).not.toMatch(/\bwhitespace-nowrap\b/);
});

it("Title 셀은 남는 폭을 쓰고(w-full max-w-0) 넘치면 truncate 된다", async () => {
  await renderPage();
  const text = firstRow().getByText(LONG_TITLE);
  expect(text.className).toMatch(/\btruncate\b/);
  expect(text.getAttribute("title")).toBe(LONG_TITLE);
  const cell = text.closest("td") as HTMLTableCellElement;
  expect(cell.className).toMatch(/\bw-full\b/);
  expect(cell.className).toMatch(/\bmax-w-0\b/);
});
