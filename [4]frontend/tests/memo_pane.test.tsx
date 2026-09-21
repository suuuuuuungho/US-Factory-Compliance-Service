// SUU-198: Memo 버튼 → 페이지 좌·우 2분할. 왼쪽 = 질문 폼 + Workspace, 오른쪽 = 메모 pane(제목·본문·Save·저장 기록).
// 메모는 localStorage "applicability-memos"에 남고, 기록 항목을 누르면 편집칸에 다시 불려온다.
import { fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import Home from "../src/app/applicability/page";

const ASK = {
  answer: {
    candidates: [{ subpart: "PPPP", title: "Surface Coating of Plastic Parts", criteria: [{ criterion: "The plant coats plastic parts.", citations: ["40 CFR 63.4481(a)"] }] }],
    checklist: ["Is the facility a major source of HAP?"],
  },
  sections: [], issues: [], tokens: { prompt: 1, completion: 1 }, cost_usd: 0, ms: 1,
};

async function askAndWait() {
  vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify(ASK), { status: 200, headers: { "content-type": "application/json" } })));
  render(<Home />);
  fireEvent.change(screen.getByRole("textbox"), { target: { value: "solvent welding" } });
  fireEvent.click(screen.getByRole("button", { name: /ask/i }));
  await screen.findByText(/Subpart PPPP/);
}

const memoButton = () => screen.getByRole("button", { name: "Memo" });
const pane = () => screen.getByRole("complementary", { name: "Memo" });

function saveMemo(title: string, body: string) {
  fireEvent.change(within(pane()).getByPlaceholderText(/title/i), { target: { value: title } });
  fireEvent.change(within(pane()).getByPlaceholderText(/write/i), { target: { value: body } });
  fireEvent.click(within(pane()).getByRole("button", { name: /save/i }));
}

beforeEach(() => localStorage.clear());
afterEach(() => vi.unstubAllGlobals());

it("Memo 버튼은 Checklist 오른쪽에 있고, 누르기 전엔 메모 pane이 없다", async () => {
  await askAndWait();
  const checklist = screen.getByRole("button", { name: "Checklist" });
  const memo = memoButton();
  expect(checklist.compareDocumentPosition(memo) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  expect(memo.getAttribute("aria-pressed")).toBe("false");
  expect(screen.queryByRole("complementary", { name: "Memo" })).toBeNull();
});

it("Memo를 누르면 2분할: 왼쪽 열에 질문 폼, 오른쪽에 메모 pane", async () => {
  await askAndWait();
  fireEvent.click(memoButton());
  expect(memoButton().getAttribute("aria-pressed")).toBe("true");
  const memoPane = pane();
  const form = screen.getByPlaceholderText(/describe the process/i).closest("form")!;
  // 질문 폼과 pane은 같은 부모(2분할 상자)의 서로 다른 열에 있고, 폼이 먼저(왼쪽)다
  const split = memoPane.parentElement!;
  expect(split.contains(form)).toBe(true);
  expect(form.compareDocumentPosition(memoPane) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  expect(split.className).toMatch(/flex-row|grid-cols-2/);
});

it("Save하면 기록 목록에 제목과 시각이 남고 localStorage에도 저장된다", async () => {
  await askAndWait();
  fireEvent.click(memoButton());
  saveMemo("First note", "Check major source status");
  const list = within(pane()).getByRole("list", { name: /saved/i });
  const items = within(list).getAllByRole("listitem");
  expect(items).toHaveLength(1);
  expect(items[0].textContent).toContain("First note");
  expect(items[0].textContent).toMatch(/\d{1,2}:\d{2}/); // 시각
  const stored = JSON.parse(localStorage.getItem("applicability-memos")!);
  expect(stored).toHaveLength(1);
  expect(stored[0]).toMatchObject({ title: "First note", body: "Check major source status" });
  expect(typeof stored[0].savedAt).toBe("string");
});

it("기록 항목을 누르면 그 메모가 편집칸에 불려온다", async () => {
  await askAndWait();
  fireEvent.click(memoButton());
  saveMemo("A", "body a");
  saveMemo("B", "body b");
  const list = within(pane()).getByRole("list", { name: /saved/i });
  expect(within(list).getAllByRole("listitem")).toHaveLength(2);
  fireEvent.click(within(list).getByRole("button", { name: /^A/ }));
  expect((within(pane()).getByPlaceholderText(/title/i) as HTMLInputElement).value).toBe("A");
  expect((within(pane()).getByPlaceholderText(/write/i) as HTMLTextAreaElement).value).toBe("body a");
});

it("Memo를 다시 누르면 pane이 닫힌다", async () => {
  await askAndWait();
  fireEvent.click(memoButton());
  expect(screen.queryByRole("complementary", { name: "Memo" })).not.toBeNull();
  fireEvent.click(memoButton());
  expect(screen.queryByRole("complementary", { name: "Memo" })).toBeNull();
  expect(memoButton().getAttribute("aria-pressed")).toBe("false");
});

// SUU-199: 메모가 열리면 main의 최대 폭을 풀고 좌우 여백을 줄인다. 왼쪽 열과 pane 사이 손잡이를 끌면 pane 폭이 바뀐다.
it("Memo가 열리면 main의 최대 폭이 풀리고 좌우 여백이 줄어든다", async () => {
  await askAndWait();
  const main = screen.getByRole("main");
  expect(main.classList.contains("max-w-7xl")).toBe(true);
  expect(main.classList.contains("p-8")).toBe(true);
  fireEvent.click(memoButton());
  expect(main.classList.contains("max-w-7xl")).toBe(false);
  expect(main.classList.contains("px-4")).toBe(true);
  fireEvent.click(memoButton());
  expect(main.classList.contains("max-w-7xl")).toBe(true);
  expect(main.classList.contains("p-8")).toBe(true);
});

it("손잡이를 끌면 Memo pane 폭이 바뀐다", async () => {
  await askAndWait();
  fireEvent.click(memoButton());
  const handle = screen.getByRole("separator");
  expect(handle.getAttribute("aria-orientation")).toBe("vertical");
  expect(pane().style.width).toBe("480px");
  fireEvent.pointerDown(handle, { clientX: 700, pointerId: 1 });
  fireEvent.pointerMove(handle, { clientX: 600, pointerId: 1 }); // 왼쪽으로 100px → pane이 100px 넓어진다
  fireEvent.pointerUp(handle, { pointerId: 1 });
  expect(pane().style.width).toBe("580px");
  // 손잡이가 pane 바로 앞에 있다
  expect(handle.nextElementSibling).toBe(pane());
});
