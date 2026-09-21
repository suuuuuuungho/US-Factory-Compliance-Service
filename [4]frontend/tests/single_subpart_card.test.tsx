// SUU-184: Subpart는 카드 하나 안에 보라 제목 띠 여러 개. 2행은 화면 남은 높이를 다 쓰고 카드 안에서 스크롤.
import { fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import Home from "../src/app/applicability/page";

const ASK = {
  answer: {
    candidates: [
      { subpart: "PPPP", title: "Surface Coating of Plastic Parts", criteria: [{ criterion: "The plant coats plastic parts.", citations: ["40 CFR 63.4481(a)"] }] },
      { subpart: "T", title: "Halogenated Solvent Cleaning", criteria: [{ criterion: "The plant uses a solvent cleaning machine.", citations: ["40 CFR 63.461"] }] },
    ],
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

const scrolls = (el: Element) =>
  el.classList.contains("overflow-y-auto") && el.classList.contains("min-h-0");

afterEach(() => vi.unstubAllGlobals());

it("Subpart는 카드 하나 안에 보라 제목 띠가 여러 개다", async () => {
  await askAndWait();
  const region = screen.getByRole("region", { name: "Subparts" });
  const cards = region.querySelectorAll(".bg-surface-1");
  expect(cards).toHaveLength(1);
  const h2s = within(cards[0] as HTMLElement).getAllByRole("heading", { level: 2 });
  expect(h2s).toHaveLength(2);
  for (const h2 of h2s) expect(h2.classList.contains("bg-gradient-violet")).toBe(true);
});

it("세 카드 모두 카드 안에서 스크롤된다 (overflow-y-auto + min-h-0)", async () => {
  await askAndWait();
  const subpartCard = screen.getByText(/Subpart PPPP/).closest("section")!;
  const checklistCard = screen.getByRole("heading", { name: "Checklist" }).closest("section")!;
  expect(scrolls(subpartCard)).toBe(true);
  expect(scrolls(checklistCard)).toBe(true);
  fireEvent.click(screen.getByRole("button", { name: "40 CFR 63.4481(a)" }));
  expect(scrolls(await screen.findByRole("complementary"))).toBe(true);
});

// SUU-193: 2행은 Workspace. 그 바깥 상자가 flex-1 + min-h-0로 남은 높이를 다 쓴다.
it("2행이 화면 남은 높이를 다 쓴다 (main 고정 높이, Workspace flex-1 min-h-0)", async () => {
  await askAndWait();
  expect(screen.getByRole("main").classList.contains("md:h-[calc(100dvh-60px)]")).toBe(true);
  const workspace = screen.getByRole("button", { name: "Reset layout" }).parentElement!.parentElement!;
  expect(workspace.classList.contains("md:flex-1")).toBe(true);
  expect(workspace.classList.contains("md:min-h-0")).toBe(true);
});
