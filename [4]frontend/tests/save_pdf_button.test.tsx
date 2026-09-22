// SUU-255: 답이 오면 "Save as PDF" 버튼. 누르면 pdf(<LetterPdf/>).toBlob() → a[download] 로 .pdf 저장.
// 메모칸에 쓴 제목·본문은 편지 끝 Notes 절에 들어가고, 비어 있으면 Notes 절이 없다.
// @react-pdf/renderer 는 jsdom에서 못 그리므로 가짜로 바꾼다: 요소는 data-pdf div, pdf()는 넘겨받은 편지 요소를 잡아둔다.
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import type { ReactElement } from "react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { LetterPdf } from "../src/app/applicability/LetterPdf";
import Home from "../src/app/applicability/page";

const captured: { letter: ReactElement | null } = { letter: null };
const toBlob = vi.fn(async () => new Blob(["pdf"], { type: "application/pdf" }));
const pdfMock = vi.fn((el: ReactElement) => {
  captured.letter = el;
  return { toBlob };
});

vi.mock("@react-pdf/renderer", () => {
  const fake = (kind: string) => {
    const C = ({ children }: { children?: React.ReactNode }) => <div data-pdf={kind}>{children}</div>;
    C.displayName = kind;
    return C;
  };
  return {
    Document: fake("document"),
    Page: fake("page"),
    View: fake("view"),
    Text: fake("text"),
    StyleSheet: { create: (s: unknown) => s },
    pdf: (el: ReactElement) => pdfMock(el),
  };
});

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
  fireEvent.click(screen.getByRole("button", { name: "Send" }));
  await screen.findByText(/Subpart PPPP/);
}

const pane = () => screen.getByRole("region", { name: "Memo pane" });

function typeMemo(title: string, body: string) {
  fireEvent.change(within(pane()).getByPlaceholderText(/title/i), { target: { value: title } });
  fireEvent.change(within(pane()).getByPlaceholderText(/write/i), { target: { value: body } });
}

// 버튼을 누르고 pdf()가 불릴 때까지 기다린 뒤, 편지 요소를 가짜 renderer 로 그려 글자를 돌려준다
async function savePdfAndGetLetterText() {
  fireEvent.click(screen.getByRole("button", { name: "Save as PDF" }));
  await waitFor(() => expect(pdfMock).toHaveBeenCalledTimes(1));
  const { container } = render(captured.letter!);
  return container.textContent ?? "";
}

let clicked: HTMLAnchorElement | null = null;

beforeEach(() => {
  localStorage.clear();
  captured.letter = null;
  clicked = null;
  pdfMock.mockClear();
  toBlob.mockClear();
  // jsdom에는 createObjectURL 이 없다. a.click() 은 실제 이동 대신 잡아둔다.
  URL.createObjectURL = vi.fn(() => "blob:fake");
  URL.revokeObjectURL = vi.fn();
  vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function (this: HTMLAnchorElement) {
    clicked = this;
  });
});
afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

it("답이 없을 때는 Save as PDF 버튼이 없고, 답이 오면 생긴다", async () => {
  vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify(ASK), { status: 200, headers: { "content-type": "application/json" } })));
  render(<Home />);
  expect(screen.queryByRole("button", { name: "Save as PDF" })).toBeNull();
  fireEvent.change(screen.getByRole("textbox"), { target: { value: "solvent welding" } });
  fireEvent.click(screen.getByRole("button", { name: "Send" }));
  await screen.findByText(/Subpart PPPP/);
  expect(screen.getByRole("button", { name: "Save as PDF" })).toBeTruthy();
});

it("Save as PDF 를 누르면 pdf().toBlob 이 1번 불리고 다운로드 파일명이 applicability-letter-YYYY-MM-DD.pdf 다", async () => {
  await askAndWait();
  fireEvent.click(screen.getByRole("button", { name: "Save as PDF" }));
  await waitFor(() => expect(toBlob).toHaveBeenCalledTimes(1));
  await waitFor(() => expect(clicked).not.toBeNull());
  expect(clicked!.download).toMatch(/^applicability-letter-\d{4}-\d{2}-\d{2}\.pdf$/);
  expect(pdfMock).toHaveBeenCalledTimes(1);
});

it("메모칸에 제목·본문을 쓰고 Save as PDF 를 누르면 편지 글자에 Notes 와 그 내용이 있다", async () => {
  await askAndWait();
  typeMemo("Site visit", "Line 3 was idle during the visit.");
  const text = await savePdfAndGetLetterText();
  expect(text).toContain("Notes");
  expect(text).toContain("Site visit");
  expect(text).toContain("Line 3 was idle during the visit.");
});

it("메모칸이 비어 있으면 편지 글자에 Notes 가 없다", async () => {
  await askAndWait();
  const text = await savePdfAndGetLetterText();
  expect(text).not.toContain("Notes");
});

it("LetterPdf 는 memo prop(제목+본문)을 받아 Notes 절을 그리고, memo 가 없으면 Notes 를 그리지 않는다", () => {
  const withMemo = render(
    <LetterPdf question="q" result={ASK} memo={{ title: "Site visit", body: "Line 3 idle" }} />,
  );
  expect(withMemo.container.textContent).toContain("Notes");
  expect(withMemo.container.textContent).toContain("Line 3 idle");
  withMemo.unmount();
  const without = render(<LetterPdf question="q" result={ASK} />);
  expect(without.container.textContent).not.toContain("Notes");
});
