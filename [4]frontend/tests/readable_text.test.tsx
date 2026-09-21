// SUU-175: 카드 제목은 headline(22px/700), 기준 목록은 줄 간격 넓게, 옆 패널 조문은 body 크기. 클래스 이름만 본다.
import { fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import Home from "../src/app/page";

const ASK = {
  answer: {
    candidates: [{
      subpart: "PPPP", title: "Surface Coating of Plastic Parts",
      criteria: [{ criterion: "The plant coats plastic parts.", citations: ["40 CFR 63.4481(a)"] }],
    }],
    checklist: ["Is the facility a major source of HAP?"],
  },
  sections: [], issues: [], tokens: { prompt: 1, completion: 1 }, cost_usd: 0, ms: 1,
};
const SECTION = { section_key: "section-63.4481", subpart: "PPPP", text: "(a) first piece" };

function json(body: unknown) {
  return new Response(JSON.stringify(body), { status: 200, headers: { "content-type": "application/json" } });
}

async function askAndWait() {
  vi.stubGlobal("fetch", vi.fn(async (url: string) => (url.endsWith("/ask") ? json(ASK) : json(SECTION))));
  render(<Home />);
  fireEvent.change(screen.getByRole("textbox"), { target: { value: "solvent welding" } });
  fireEvent.click(screen.getByRole("button", { name: /ask/i }));
  await screen.findByText(/Subpart PPPP/);
}

afterEach(() => vi.unstubAllGlobals());

it("후보 카드 제목은 headline 크기다 (text-[22px] + font-bold)", async () => {
  await askAndWait();
  const cls = screen.getByText(/Subpart PPPP/).classList;
  expect(cls.contains("text-[22px]")).toBe(true);
  expect(cls.contains("font-bold")).toBe(true);
});

it("기준 목록은 줄 간격이 넓다 (leading-relaxed + space-y-3)", async () => {
  await askAndWait();
  const card = screen.getByText(/Subpart PPPP/).closest("section")!;
  const cls = within(card).getByRole("list").classList;
  expect(cls.contains("leading-relaxed")).toBe(true);
  expect(cls.contains("space-y-3")).toBe(true);
});

it("옆 패널 조문은 body 크기다 (text-base + leading-relaxed)", async () => {
  await askAndWait();
  fireEvent.click(screen.getByRole("button", { name: "40 CFR 63.4481(a)" }));
  const pre = (await screen.findByText("(a) first piece")).closest("pre")!;
  expect(pre.classList.contains("text-base")).toBe(true);
  expect(pre.classList.contains("leading-relaxed")).toBe(true);
});
