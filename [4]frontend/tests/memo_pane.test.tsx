// SUU-198: Memo 버튼 → 메모 pane(제목·본문·Save·저장 기록). 메모는 localStorage "applicability-memos"에 남고, 기록 항목을 누르면 편집칸에 다시 불려온다.
// SUU-199: Memo는 dockview 칸이다. Checklist 왼쪽에 놓여 네 칸(질문·Subparts·Memo·Checklist)을 전부 끌 수 있다.
// SUU-200: Memo 칸은 처음부터 열려 있다. Memo 버튼은 닫기/다시 열기.
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
const pane = () => screen.getByRole("region", { name: "Memo pane" });

function saveMemo(title: string, body: string) {
  fireEvent.change(within(pane()).getByPlaceholderText(/title/i), { target: { value: title } });
  fireEvent.change(within(pane()).getByPlaceholderText(/write/i), { target: { value: body } });
  fireEvent.click(within(pane()).getByRole("button", { name: /save/i }));
}

beforeEach(() => localStorage.clear());
afterEach(() => vi.unstubAllGlobals());

it("Memo 칸은 처음부터 열려 있고 Checklist 왼쪽에 있다", async () => {
  await askAndWait();
  const checklist = screen.getByRole("button", { name: "Checklist" });
  const memo = memoButton();
  expect(checklist.compareDocumentPosition(memo) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  expect(memo.getAttribute("aria-pressed")).toBe("true");
  const tabs = screen.getAllByRole("tab").map((t) => t.getAttribute("aria-label"));
  expect(tabs).toEqual(["Question", "Subparts", "Memo", "Checklist"]);
  expect(pane().closest('[data-panel="memo"]')).not.toBeNull();
  // Memo 칸은 Question/Subparts 열 밖에 있다 (세로 전체를 쓴다)
  const column = (id: string) => document.querySelector(`[data-panel="${id}"]`)!.closest(".dv-branch-node")!;
  expect(column("memo")).not.toBe(column("question"));
});

it("Ask 뒤에는 main의 최대 폭이 풀리고 좌우 여백이 줄어든다", async () => {
  vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify(ASK), { status: 200, headers: { "content-type": "application/json" } })));
  render(<Home />);
  const main = screen.getByRole("main");
  expect(main.classList.contains("max-w-7xl")).toBe(true);
  fireEvent.change(screen.getByRole("textbox"), { target: { value: "solvent welding" } });
  fireEvent.click(screen.getByRole("button", { name: /ask/i }));
  await screen.findByText(/Subpart PPPP/);
  expect(main.classList.contains("max-w-7xl")).toBe(false);
  expect(main.classList.contains("px-4")).toBe(true);
});

it("Save하면 기록 목록에 제목과 시각이 남고 localStorage에도 저장된다", async () => {
  await askAndWait();
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
  saveMemo("A", "body a");
  saveMemo("B", "body b");
  const list = within(pane()).getByRole("list", { name: /saved/i });
  expect(within(list).getAllByRole("listitem")).toHaveLength(2);
  fireEvent.click(within(list).getByRole("button", { name: /^A/ }));
  expect((within(pane()).getByPlaceholderText(/title/i) as HTMLInputElement).value).toBe("A");
  expect((within(pane()).getByPlaceholderText(/write/i) as HTMLTextAreaElement).value).toBe("body a");
});

it("Memo 버튼을 누르면 닫히고 다시 누르면 열린다", async () => {
  await askAndWait();
  fireEvent.click(memoButton());
  await screen.findByRole("button", { name: "Memo", pressed: false });
  expect(screen.queryByRole("region", { name: "Memo pane" })).toBeNull();
  fireEvent.click(memoButton());
  await screen.findByRole("button", { name: "Memo", pressed: true });
  expect(screen.queryByRole("region", { name: "Memo pane" })).not.toBeNull();
});
