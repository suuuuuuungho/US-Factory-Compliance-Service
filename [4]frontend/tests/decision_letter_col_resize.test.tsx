// SUU-260: Decision Letter 표 머리글 오른쪽 손잡이를 끌면 그 열의 <col> 너비가 바뀐다. 최소 60px.
import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import DecisionLetterPage from "../src/app/decision-letter/page";

const LETTERS = [
  {
    source_key: "ce814c7924dce44b",
    facility_name: "Domtar AW LLC-Ashdown AR",
    title: "Applicability Determination for Kraft Pulp Mills",
    subparts: ["S"],
    date: "2025-03-10",
    pdf_url: null,
  },
];

const HEADERS = ["#", "Facility", "Title", "Subpart", "Date", "PDF"];
const FACILITY = 1;

async function renderPage() {
  vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({ letters: LETTERS }), { status: 200 })));
  const utils = render(<DecisionLetterPage />);
  await screen.findByText(LETTERS[0].facility_name);
  return utils;
}

afterEach(() => vi.unstubAllGlobals());

const handles = (container: HTMLElement) => Array.from(container.querySelectorAll<HTMLElement>("th [data-resize-handle]"));
const cols = (container: HTMLElement) => Array.from(container.querySelectorAll<HTMLTableColElement>("colgroup col"));
const colWidth = (col: HTMLTableColElement) => parseFloat(col.style.width);

function drag(handle: HTMLElement, from: number, to: number) {
  fireEvent.mouseDown(handle, { clientX: from });
  fireEvent.mouseMove(document, { clientX: to });
  fireEvent.mouseUp(document, { clientX: to });
}

it("머리글마다 data-resize-handle 손잡이가 있고 열마다 <col> 이 있다", async () => {
  const { container } = await renderPage();
  expect(handles(container)).toHaveLength(HEADERS.length);
  expect(cols(container)).toHaveLength(HEADERS.length);
});

it("Facility 손잡이를 +80px 끌면 Facility <col> 너비가 80px 늘어난다", async () => {
  const { container } = await renderPage();
  const before = colWidth(cols(container)[FACILITY]);
  expect(before).toBeGreaterThan(0);
  drag(handles(container)[FACILITY], 100, 180);
  expect(colWidth(cols(container)[FACILITY])).toBe(before + 80);
});

it("아무리 왼쪽으로 끌어도 60px 아래로는 줄지 않는다", async () => {
  const { container } = await renderPage();
  drag(handles(container)[FACILITY], 500, -500);
  expect(colWidth(cols(container)[FACILITY])).toBe(60);
});

it("mouseup 뒤에 mousemove 해도 너비가 더 안 바뀐다", async () => {
  const { container } = await renderPage();
  drag(handles(container)[FACILITY], 100, 150);
  const after = colWidth(cols(container)[FACILITY]);
  fireEvent.mouseMove(document, { clientX: 400 });
  expect(colWidth(cols(container)[FACILITY])).toBe(after);
});
