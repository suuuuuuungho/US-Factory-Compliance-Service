// SUU-254: AskResult → 편지 한 장짜리 PDF(<Document>). 첫 Text는 "법적 판정이 아니다" 면책 박스(굵고 큼), 전체 폰트 Times-Roman.
// @react-pdf/renderer 는 jsdom에서 그리지 못하므로 가짜로 바꾼다: 각 요소를 data-pdf 속성과 style JSON을 가진 div로 렌더한다.
import { render } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import type { AskResult } from "../src/lib/api";
import { LetterPdf } from "../src/app/applicability/LetterPdf";

vi.mock("@react-pdf/renderer", () => {
  const flat = (s: unknown) => Object.assign({}, ...(Array.isArray(s) ? s : [s]).filter(Boolean));
  const fake = (kind: string) => {
    const C = ({ style, children }: { style?: unknown; children?: React.ReactNode }) => (
      <div data-pdf={kind} data-style={JSON.stringify(flat(style))}>{children}</div>
    );
    C.displayName = kind;
    return C;
  };
  return {
    Document: fake("document"),
    Page: fake("page"),
    View: fake("view"),
    Text: fake("text"),
    StyleSheet: { create: (s: unknown) => s },
  };
});

const FAKE: AskResult = {
  answer: {
    candidates: [{
      subpart: "PPPP", title: "Surface Coating of Plastic Parts",
      criteria: [{ criterion: "The plant coats plastic parts.", citations: ["40 CFR 63.4481(a)"] }],
    }],
    checklist: ["Is the facility a major source of HAP?"],
  },
  sections: [{ section_key: "section-63.4481", subpart: "PPPP" }],
  issues: [], tokens: { prompt: 1, completion: 1 }, cost_usd: 0, ms: 1,
};
const QUESTION = "Does solvent welding of plastic parts trigger Part 63?";

const styleOf = (el: Element) => JSON.parse(el.getAttribute("data-style") ?? "{}");

it("가짜 AskResult로 렌더하면 질문·subpart·criteria·citation·checklist·section key가 모두 텍스트로 있다", () => {
  const { container } = render(<LetterPdf question={QUESTION} result={FAKE} />);
  const text = container.textContent ?? "";
  for (const s of [QUESTION, "PPPP", "The plant coats plastic parts.", "40 CFR 63.4481(a)",
    "Is the facility a major source of HAP?", "section-63.4481"]) {
    expect(text, s).toContain(s);
  }
});

it("면책 문구가 첫 번째 Text이고, 본문(Page)보다 큰 fontSize와 bold(Times-Bold)가 붙어 있다", () => {
  const { container } = render(<LetterPdf question={QUESTION} result={FAKE} />);
  const first = container.querySelector('[data-pdf="text"]')!;
  expect(first.textContent).toMatch(/not a legal determination/i);
  const page = styleOf(container.querySelector('[data-pdf="page"]')!);
  const box = styleOf(first);
  expect(box.fontSize).toBeGreaterThan(page.fontSize);
  expect(box.fontFamily === "Times-Bold" || box.fontWeight === "bold").toBe(true);
});

it("Page 스타일의 fontFamily가 Times-Roman이다", () => {
  const { container } = render(<LetterPdf question={QUESTION} result={FAKE} />);
  expect(styleOf(container.querySelector('[data-pdf="page"]')!).fontFamily).toBe("Times-Roman");
});
