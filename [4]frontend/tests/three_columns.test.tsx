// SUU-182: 1행 = 질문 폼(3열 전부), 2행 = Subparts | Checklist | 조문. 각 칸은 overflow-y-auto로 따로 스크롤.
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

it("결과 영역은 3열 grid이고 질문 폼이 3열을 다 차지한다", async () => {
  await askAndWait();
  const form = screen.getByRole("textbox").closest("form")!;
  expect(form.classList.contains("md:col-span-3")).toBe(true);
  const grid = form.parentElement!.classList;
  expect(grid.contains("grid")).toBe(true);
  expect(grid.contains("md:grid-cols-3")).toBe(true);
});

it("Subpart 카드는 Subparts 칸에, Checklist는 Checklist 칸에 있다", async () => {
  await askAndWait();
  within(screen.getByRole("region", { name: "Subparts" })).getByText(/Subpart PPPP/);
  within(screen.getByRole("region", { name: "Checklist" })).getByRole("heading", { name: "Checklist" });
});

it("3열은 인용 클릭 전엔 안내 문구, 클릭 후엔 조문 패널이다", async () => {
  await askAndWait();
  const col = screen.getByRole("region", { name: "Section text column" });
  within(col).getByText(/Click a citation/);
  expect(within(col).queryByRole("complementary")).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "40 CFR 63.4481(a)" }));
  await within(col).findByRole("complementary");
  within(col).getByText("(a) first piece");
});

it("2행 세 칸 모두 따로 스크롤된다 (overflow-y-auto)", async () => {
  await askAndWait();
  for (const name of ["Subparts", "Checklist", "Section text column"]) {
    expect(screen.getByRole("region", { name }).classList.contains("overflow-y-auto")).toBe(true);
  }
});
