// SUU-188: 2행 세 카드가 칸 높이를 꽉 채워 같은 높이가 되고, 스크롤은 칸이 아니라 카드 안에서 된다.
import { fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import Home from "../src/app/applicability/page";

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

async function askAndOpen() {
  vi.stubGlobal("fetch", vi.fn(async (url: string) => (url.endsWith("/ask") ? json(ASK) : json(SECTION))));
  render(<Home />);
  fireEvent.change(screen.getByRole("textbox"), { target: { value: "solvent welding" } });
  fireEvent.click(screen.getByRole("button", { name: /ask/i }));
  await screen.findByText(/Subpart PPPP/);
  fireEvent.click(screen.getByRole("button", { name: "40 CFR 63.4481(a)" }));
  await screen.findByRole("complementary");
}

afterEach(() => vi.unstubAllGlobals());

it("세 카드 모두 칸을 꽉 채우고(flex-1 min-h-0) 카드 안에서 스크롤된다", async () => {
  await askAndOpen();
  const cards = [
    within(screen.getByRole("region", { name: "Subparts" })).getByText(/Subpart PPPP/).closest("section")!,
    within(screen.getByRole("region", { name: "Checklist" })).getByRole("heading", { name: "Checklist" }).closest("section")!,
    screen.getByRole("complementary"),
  ];
  for (const card of cards) {
    for (const cls of ["flex-1", "min-h-0", "overflow-y-auto"]) {
      expect(card.classList.contains(cls), cls).toBe(true);
    }
  }
});

// SUU-193: 칸은 Workspace의 Panel(div[data-panel])이다.
it("세 칸(열) 자체는 스크롤하지 않는다 (overflow-hidden)", async () => {
  await askAndOpen();
  for (const name of ["subparts", "checklist", "section"]) {
    const col = document.querySelector(`[data-panel="${name}"]`)!.classList;
    expect(col.contains("overflow-hidden"), name).toBe(true);
    expect(col.contains("overflow-y-auto"), name).toBe(false);
  }
});
