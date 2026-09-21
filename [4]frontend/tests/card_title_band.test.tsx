// SUU-180: 카드 제목 줄(h2)만 gradient 색 배경(순환), 카드 본문(section)은 차콜. SUU-174의 color_cards.test.tsx를 대체한다.
import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import Home from "../src/app/page";

const RESULT = {
  answer: {
    candidates: [
      { subpart: "PPPP", title: "Surface Coating of Plastic Parts", criteria: [{ criterion: "The plant coats plastic parts.", citations: ["40 CFR 63.4481(a)"] }] },
      { subpart: "T", title: "Halogenated Solvent Cleaning", criteria: [{ criterion: "The plant uses a solvent cleaning machine.", citations: ["40 CFR 63.461"] }] },
    ],
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

const hasGradient = (el: Element) => Array.from(el.classList).some((c) => c.includes("gradient-"));

afterEach(() => vi.unstubAllGlobals());

it("후보 카드 제목 줄은 순서대로 violet, magenta 배경이다 (h2에 bg-gradient-*)", async () => {
  await askAndWait();
  expect(screen.getByText(/Subpart PPPP/).classList.contains("bg-gradient-violet")).toBe(true);
  expect(screen.getByText(/Subpart T /).classList.contains("bg-gradient-magenta")).toBe(true);
});

it("후보 카드 본문은 차콜이다 (section에 gradient 클래스 없음 + bg-surface-1)", async () => {
  await askAndWait();
  const card = screen.getByText(/Subpart PPPP/).closest("section")!;
  expect(hasGradient(card)).toBe(false);
  expect(card.classList.contains("bg-surface-1")).toBe(true);
});

it("Checklist는 본문 차콜, 제목 줄만 보라다", async () => {
  await askAndWait();
  const h2 = screen.getByText("Checklist");
  const card = h2.closest("section")!;
  expect(h2.classList.contains("bg-gradient-violet")).toBe(true);
  expect(card.classList.contains("bg-surface-1")).toBe(true);
  expect(hasGradient(card)).toBe(false);
});
