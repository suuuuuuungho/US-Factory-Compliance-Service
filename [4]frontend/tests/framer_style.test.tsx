// SUU-172: 질문창·Ask 버튼·후보 카드·인용 버튼이 DESIGN.md(Framer) 토큰 클래스를 쓴다. 기능은 page/section 테스트가 지킨다.
import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import Home from "../src/app/applicability/page";

const RESULT = {
  answer: {
    candidates: [{
      subpart: "PPPP", title: "Surface Coating of Plastic Parts",
      criteria: [{ criterion: "The plant coats plastic parts.", citations: ["40 CFR 63.4481(a)"] }],
    }],
    checklist: ["Is the facility a major source of HAP?"],
  },
  sections: [], issues: [], tokens: { prompt: 1, completion: 1 }, cost_usd: 0, ms: 1,
};

async function askAndWait() {
  vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify(RESULT), { status: 200, headers: { "content-type": "application/json" } })));
  render(<Home />);
  fireEvent.change(screen.getByRole("textbox"), { target: { value: "solvent welding" } });
  fireEvent.click(screen.getByRole("button", { name: /ask/i }));
  await screen.findByText(/Subpart PPPP/);
}

afterEach(() => vi.unstubAllGlobals());

// SUU-197: 알약(rounded-full)이 아니라 질문 칸과 같은 둥근 네모(rounded-md)
it("Ask 버튼은 흰 둥근 네모다 (rounded-md + bg-primary + text-on-primary)", () => {
  render(<Home />);
  const cls = screen.getByRole("button", { name: /ask/i }).classList;
  expect(cls.contains("rounded-md")).toBe(true);
  expect(cls.contains("rounded-full")).toBe(false);
  expect(cls.contains("bg-primary")).toBe(true);
  expect(cls.contains("text-on-primary")).toBe(true);
});

it("질문 입력칸은 차콜 바탕 + hairline 테두리다 (bg-surface-1 + border-hairline)", () => {
  render(<Home />);
  const cls = screen.getByRole("textbox").classList;
  expect(cls.contains("bg-surface-1")).toBe(true);
  expect(cls.contains("border-hairline")).toBe(true);
});

it("후보 Subpart 카드는 차콜 카드다 (bg-surface-1 + border-hairline + rounded-lg)", async () => {
  await askAndWait();
  const card = screen.getByText(/Subpart PPPP/).closest("section")!;
  expect(card.classList.contains("bg-surface-1")).toBe(true);
  expect(card.classList.contains("border-hairline")).toBe(true);
  expect(card.classList.contains("rounded-lg")).toBe(true);
});

it("인용 버튼은 accent-blue 링크다 (text-accent-blue)", async () => {
  await askAndWait();
  expect(screen.getByRole("button", { name: "40 CFR 63.4481(a)" }).classList.contains("text-accent-blue")).toBe(true);
});
