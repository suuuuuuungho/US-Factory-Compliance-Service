// SUU-174: 후보 카드마다 gradient 색 띠(border-l-4)가 순환하고, 체크리스트는 보라(bg-gradient-violet) 카드다.
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

afterEach(() => vi.unstubAllGlobals());

it("후보 카드는 순서대로 violet, magenta 색 띠가 붙는다 (border-l-4 + border-gradient-*)", async () => {
  await askAndWait();
  const first = screen.getByText(/Subpart PPPP/).closest("section")!;
  const second = screen.getByText(/Subpart T /).closest("section")!;
  expect(first.classList.contains("border-l-4")).toBe(true);
  expect(first.classList.contains("border-gradient-violet")).toBe(true);
  expect(second.classList.contains("border-l-4")).toBe(true);
  expect(second.classList.contains("border-gradient-magenta")).toBe(true);
});

it("체크리스트는 보라 카드다 (bg-gradient-violet)", async () => {
  await askAndWait();
  const card = screen.getByText("Checklist").closest("section")!;
  expect(card.classList.contains("bg-gradient-violet")).toBe(true);
});
