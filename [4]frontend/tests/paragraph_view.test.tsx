// SUU-189: 인용 "63.460(a)" 클릭 → 조문 카드에 (a) 문단만. "Show all of 63.460" 누르면 전체. 문단 없는 인용은 처음부터 전체.
import { fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import Home from "../src/app/applicability/page";
import { citationToParagraph, paragraphText } from "../src/lib/api";

const TEXT = [
  "(a) Owners must do A.",
  "(1) Sub-item of a.",
  "(i) Deeper sub-item of a.",
  "(b) Owners must do B.",
  "(c) Owners must do C.",
].join("\n\n");

const ASK = {
  answer: {
    candidates: [{
      subpart: "T", title: "Halogenated Solvent Cleaning",
      criteria: [{ criterion: "Uses a halogenated solvent.", citations: ["40 CFR 63.460(a)(1)", "40 CFR 63.460"] }],
    }],
    checklist: ["Is the facility a major source of HAP?"],
  },
  sections: [], issues: [], tokens: { prompt: 1, completion: 1 }, cost_usd: 0, ms: 1,
};
const SECTION = { section_key: "section-63.460", subpart: "T", text: TEXT };

function json(body: unknown) {
  return new Response(JSON.stringify(body), { status: 200, headers: { "content-type": "application/json" } });
}

async function askAndWait() {
  vi.stubGlobal("fetch", vi.fn(async (url: string) => (url.endsWith("/ask") ? json(ASK) : json(SECTION))));
  render(<Home />);
  fireEvent.change(screen.getByRole("textbox"), { target: { value: "solvent cleaning" } });
  fireEvent.click(screen.getByRole("button", { name: /ask/i }));
  await screen.findByText(/Subpart T/);
}

afterEach(() => vi.unstubAllGlobals());

it("citationToParagraph: 인용에서 첫 문단 글자만 꺼낸다", () => {
  expect(citationToParagraph("40 CFR 63.460(a)(1)")).toBe("a");
  expect(citationToParagraph("40 CFR 63.460(b)")).toBe("b");
  expect(citationToParagraph("40 CFR 63.460")).toBeNull();
});

it("paragraphText: 그 문단부터 다음 문단 앞까지 (하위 항목 포함). 없으면 null", () => {
  expect(paragraphText(TEXT, "a")).toBe("(a) Owners must do A.\n\n(1) Sub-item of a.\n\n(i) Deeper sub-item of a.");
  expect(paragraphText(TEXT, "b")).toBe("(b) Owners must do B.");
  expect(paragraphText(TEXT, "c")).toBe("(c) Owners must do C.");
  expect(paragraphText(TEXT, "z")).toBeNull();
});

it("63.460(a)(1) 클릭 → (a) 문단만 보이고 제목에 (a)가 붙는다", async () => {
  await askAndWait();
  fireEvent.click(screen.getByRole("button", { name: "40 CFR 63.460(a)(1)" }));
  const panel = await screen.findByRole("complementary");
  within(panel).getByText(/Owners must do A/);
  within(panel).getByText(/Deeper sub-item of a/);
  expect(within(panel).queryByText(/Owners must do B/)).toBeNull();
  within(panel).getByRole("heading", { name: /section-63\.460\(a\)/ });
});

it("Show all of 63.460 누르면 전체가 보인다", async () => {
  await askAndWait();
  fireEvent.click(screen.getByRole("button", { name: "40 CFR 63.460(a)(1)" }));
  const panel = await screen.findByRole("complementary");
  fireEvent.click(within(panel).getByRole("button", { name: "Show all of 63.460" }));
  within(panel).getByText(/Owners must do B/);
  within(panel).getByText(/Owners must do C/);
  expect(within(panel).queryByRole("button", { name: "Show all of 63.460" })).toBeNull();
});

it("문단 없는 인용(63.460)은 처음부터 전체, 버튼 없음", async () => {
  await askAndWait();
  fireEvent.click(screen.getByRole("button", { name: "40 CFR 63.460" }));
  const panel = await screen.findByRole("complementary");
  within(panel).getByText(/Owners must do C/);
  expect(within(panel).queryByRole("button", { name: /Show all/ })).toBeNull();
});
