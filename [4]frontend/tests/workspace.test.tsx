// SUU-193: 2행 세 칸(Subparts · Checklist · Section text)은 dockview 패널. 끌어서 크기·위치를 바꾸고, 배치는 localStorage에 남는다.
// SUU-182의 three_columns.test.tsx(고정 3열 grid)를 대체한다.
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
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

async function askAndWait() {
  vi.stubGlobal("fetch", vi.fn(async (url: string) => (url.endsWith("/ask") ? json(ASK) : json(SECTION))));
  render(<Home />);
  fireEvent.change(screen.getByRole("textbox"), { target: { value: "solvent welding" } });
  fireEvent.click(screen.getByRole("button", { name: /ask/i }));
  await screen.findByText(/Subpart PPPP/);
}

beforeEach(() => localStorage.clear());
afterEach(() => vi.unstubAllGlobals());

it("답이 오면 dockview 안에 끌 수 있는 탭 세 개(Subparts, Checklist, Section text)가 있다", async () => {
  await askAndWait();
  expect(document.querySelector(".dv-dockview")).not.toBeNull();
  for (const name of ["Subparts", "Checklist", "Section text"]) {
    const tab = screen.getByRole("tab", { name });
    expect(tab.getAttribute("draggable")).toBe("true");
  }
});

it("Subpart 카드는 Subparts 칸에, Checklist는 Checklist 칸에 있다", async () => {
  await askAndWait();
  within(screen.getByRole("region", { name: "Subparts" })).getByText(/Subpart PPPP/);
  within(screen.getByRole("region", { name: "Checklist" })).getByRole("heading", { name: "Checklist" });
});

it("Section text 칸은 인용 클릭 전엔 안내 문구, 클릭 후엔 조문 패널이다", async () => {
  await askAndWait();
  const col = screen.getByRole("region", { name: "Section text" });
  within(col).getByText(/Click a citation/);
  expect(within(col).queryByRole("complementary")).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "40 CFR 63.4481(a)" }));
  await within(col).findByRole("complementary");
  within(col).getByText("(a) first piece");
});

it("칸 배치는 localStorage 'workspace-layout'에 저장되고, 닫은 칸은 다시 열어도 닫혀 있다", async () => {
  await askAndWait();
  const saved = () => JSON.parse(localStorage.getItem("workspace-layout")!);
  expect(Object.keys(saved().panels).sort()).toEqual(["checklist", "section", "subparts"]);

  fireEvent.click(screen.getByRole("button", { name: "Close Checklist" }));
  expect(screen.queryByRole("tab", { name: "Checklist" })).toBeNull();
  await waitFor(() => expect(saved().panels.checklist).toBeUndefined());

  cleanup();
  await askAndWait();
  expect(screen.queryByRole("tab", { name: "Checklist" })).toBeNull();
  screen.getByRole("tab", { name: "Subparts" });
});

it("Reset layout을 누르면 닫았던 칸이 돌아오고 기본 3열이 된다", async () => {
  await askAndWait();
  fireEvent.click(screen.getByRole("button", { name: "Close Checklist" }));
  expect(screen.queryByRole("tab", { name: "Checklist" })).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "Reset layout" }));
  expect(screen.getAllByRole("tab")).toHaveLength(3);
  screen.getByRole("tab", { name: "Checklist" });
});
