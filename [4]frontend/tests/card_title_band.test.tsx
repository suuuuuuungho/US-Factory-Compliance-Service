// SUU-180: 카드 제목 줄(h2)만 gradient 배경, 본문(section)은 차콜. SUU-183: 띠는 전부 같은 보라, 조문 칸도 같은 띠. SUU-174의 color_cards.test.tsx를 대체한다.
import { fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import Home from "../src/app/applicability/page";

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
  const SECTION = { section_key: "section-63.4481", subpart: "PPPP", text: "(a) first piece" };
  vi.stubGlobal("fetch", vi.fn(async (url: string) => new Response(JSON.stringify(url.endsWith("/ask") ? RESULT : SECTION), { status: 200, headers: { "content-type": "application/json" } })));
  render(<Home />);
  fireEvent.change(screen.getByRole("textbox"), { target: { value: "solvent welding" } });
  fireEvent.click(screen.getByRole("button", { name: /ask/i }));
  await screen.findByText(/Subpart PPPP/);
}

const hasGradient = (el: Element) => Array.from(el.classList).some((c) => c.includes("gradient-"));

afterEach(() => vi.unstubAllGlobals());

it("모든 카드 제목 줄은 같은 보라색이다 (bg-gradient-violet, magenta 없음)", async () => {
  await askAndWait();
  const h1 = screen.getByText(/Subpart PPPP/);
  const h2 = screen.getByText(/Subpart T /);
  expect(h1.classList.contains("bg-gradient-violet")).toBe(true);
  expect(h2.classList.contains("bg-gradient-violet")).toBe(true);
  expect(document.querySelector(".bg-gradient-magenta")).toBeNull();
});

it("조문 칸 제목 줄은 Subpart 제목 줄과 className이 같다", async () => {
  await askAndWait();
  fireEvent.click(screen.getByRole("button", { name: "40 CFR 63.4481(a)" }));
  const panel = await screen.findByRole("complementary");
  const sectionH2 = within(panel).getByRole("heading", { level: 2 });
  expect(sectionH2.className).toBe(screen.getByText(/^Subpart PPPP —/).className);
  expect(sectionH2.classList.contains("bg-gradient-violet")).toBe(true);
});

it("후보 카드 본문은 차콜이다 (section에 gradient 클래스 없음 + bg-surface-1)", async () => {
  await askAndWait();
  const card = screen.getByText(/Subpart PPPP/).closest("section")!;
  expect(hasGradient(card)).toBe(false);
  expect(card.classList.contains("bg-surface-1")).toBe(true);
});

it("Checklist는 본문 차콜, 제목 줄만 보라다", async () => {
  await askAndWait();
  const h2 = screen.getByRole("heading", { name: "Checklist" });
  const card = h2.closest("section")!;
  expect(h2.classList.contains("bg-gradient-violet")).toBe(true);
  expect(card.classList.contains("bg-surface-1")).toBe(true);
  expect(hasGradient(card)).toBe(false);
});
