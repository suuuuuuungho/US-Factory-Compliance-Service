// SUU-193: 2행은 dockview 작업공간. 기본 칸은 Subparts | Checklist, 조문은 인용마다 칸(§63.4481)으로 열려 여러 개를 나란히 둘 수 있다.
// 끌어서 크기·위치를 바꾸고, 배치는 localStorage에 남는다. SUU-182의 three_columns.test.tsx(고정 3열 grid)를 대체한다.
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import Home from "../src/app/applicability/page";

const ASK = {
  answer: {
    candidates: [{
      subpart: "PPPP", title: "Surface Coating of Plastic Parts",
      criteria: [
        { criterion: "The plant coats plastic parts.", citations: ["40 CFR 63.4481(a)"] },
        { criterion: "Uses a coating line.", citations: ["40 CFR 63.4482"] },
      ],
    }],
    checklist: ["Is the facility a major source of HAP?"],
  },
  sections: [], issues: [], tokens: { prompt: 1, completion: 1 }, cost_usd: 0, ms: 1,
};
const SECTIONS: Record<string, unknown> = {
  "section-63.4481": { section_key: "section-63.4481", subpart: "PPPP", text: "(a) first piece" },
  "section-63.4482": { section_key: "section-63.4482", subpart: "PPPP", text: "(a) second section" },
};

function json(body: unknown) {
  return new Response(JSON.stringify(body), { status: 200, headers: { "content-type": "application/json" } });
}

async function askAndWait() {
  vi.stubGlobal("fetch", vi.fn(async (url: string) =>
    url.endsWith("/ask") ? json(ASK) : json(SECTIONS[url.split("/").pop()!])));
  render(<Home />);
  fireEvent.change(screen.getByRole("textbox"), { target: { value: "solvent welding" } });
  fireEvent.click(screen.getByRole("button", { name: /ask/i }));
  await screen.findByText(/Subpart PPPP/);
}

const tabNames = () => screen.getAllByRole("tab").map((t) => t.getAttribute("aria-label"));

beforeEach(() => localStorage.clear());
afterEach(() => vi.unstubAllGlobals());

it("답이 오면 dockview 안에 끌 수 있는 탭 두 개(Subparts, Checklist)가 있고 조문 칸은 아직 없다", async () => {
  await askAndWait();
  expect(document.querySelector(".dv-dockview")).not.toBeNull();
  expect(tabNames()).toEqual(["Subparts", "Checklist"]);
  for (const tab of screen.getAllByRole("tab")) expect(tab.getAttribute("draggable")).toBe("true");
});

it("Subpart 카드는 Subparts 칸에, Checklist는 Checklist 칸에 있다", async () => {
  await askAndWait();
  within(screen.getByRole("region", { name: "Subparts" })).getByText(/Subpart PPPP/);
  within(screen.getByRole("region", { name: "Checklist" })).getByRole("heading", { name: "Checklist" });
});

it("인용을 클릭하면 조문이 새 칸(§63.4481)으로 열리고, 다른 인용은 또 다른 칸으로 열려 둘 다 남는다", async () => {
  await askAndWait();
  fireEvent.click(screen.getByRole("button", { name: "40 CFR 63.4481(a)" }));
  const first = await screen.findByRole("region", { name: "§63.4481" });
  await within(first).findByText("(a) first piece");

  fireEvent.click(screen.getByRole("button", { name: "40 CFR 63.4482" }));
  await screen.findByText("(a) second section");
  // 둘째 조문은 첫 조문 칸에 탭으로 들어간다 (끌어서 옆으로 빼면 나란히 볼 수 있다)
  expect(tabNames()).toEqual(["Subparts", "Checklist", "§63.4481", "§63.4482"]);
  expect(screen.getByRole("tab", { name: "§63.4482" }).getAttribute("aria-selected")).toBe("true");
});

it("같은 인용을 다시 클릭하면 칸이 하나만 있다", async () => {
  await askAndWait();
  fireEvent.click(screen.getByRole("button", { name: "40 CFR 63.4481(a)" }));
  await screen.findByText("(a) first piece");
  fireEvent.click(screen.getByRole("button", { name: "40 CFR 63.4481(a)" }));
  expect(screen.getAllByRole("tab", { name: "§63.4481" })).toHaveLength(1);
});

it("조문 칸을 ✕로 닫으면 사라지고, 인용을 다시 클릭하면 다시 열린다", async () => {
  await askAndWait();
  fireEvent.click(screen.getByRole("button", { name: "40 CFR 63.4481(a)" }));
  await screen.findByText("(a) first piece");
  fireEvent.click(screen.getByRole("button", { name: "Close §63.4481" }));
  await waitFor(() => expect(screen.queryByRole("tab", { name: "§63.4481" })).toBeNull());
  fireEvent.click(screen.getByRole("button", { name: "40 CFR 63.4481(a)" }));
  await screen.findByRole("tab", { name: "§63.4481" });
});

it("Subparts·Checklist 버튼으로 칸을 껐다 켤 수 있다 (aria-pressed)", async () => {
  await askAndWait();
  const btn = () => screen.getByRole("button", { name: "Checklist", pressed: true });
  fireEvent.click(btn());
  await waitFor(() => expect(screen.queryByRole("tab", { name: "Checklist" })).toBeNull());
  fireEvent.click(screen.getByRole("button", { name: "Checklist", pressed: false }));
  await screen.findByRole("tab", { name: "Checklist" });
  btn();
});

it("칸 배치는 localStorage 'workspace-layout'에 저장되고, 닫은 칸은 다시 열어도 닫혀 있다", async () => {
  await askAndWait();
  const saved = () => JSON.parse(localStorage.getItem("workspace-layout")!);
  expect(Object.keys(saved().panels).sort()).toEqual(["checklist", "subparts"]);

  fireEvent.click(screen.getByRole("button", { name: "Close Checklist" }));
  await waitFor(() => expect(saved().panels.checklist).toBeUndefined());

  cleanup();
  await askAndWait();
  expect(tabNames()).toEqual(["Subparts"]);
});

it("Reset layout을 누르면 닫았던 칸이 돌아오고 기본(Subparts | Checklist)이 된다", async () => {
  await askAndWait();
  fireEvent.click(screen.getByRole("button", { name: "Close Checklist" }));
  await waitFor(() => expect(screen.queryByRole("tab", { name: "Checklist" })).toBeNull());
  fireEvent.click(screen.getByRole("button", { name: "Reset layout" }));
  expect(tabNames()).toEqual(["Subparts", "Checklist"]);
});

// SUU-194: dockview 루트(.dv-shell)는 height:100%인데, flex로 늘어난 칸 안에서는 브라우저가 0px로 계산한다.
// jsdom은 크기를 재지 않으므로, 상자를 relative로 두고 dockview를 absolute inset-0으로 꽉 채우는 클래스를 검사한다.
it("dockview 상자는 relative이고 dockview 루트를 absolute inset-0으로 꽉 채운다 (높이 0 방지)", async () => {
  await askAndWait();
  const root = document.querySelector(".dockview-theme-dark")!;
  const box = root.parentElement!.parentElement!; // DockviewReact가 그리는 div → 우리 상자
  expect(box.className).toContain("relative");
  expect(box.className).toContain("[&>div]:absolute");
  expect(box.className).toContain("[&>div]:inset-0");
});
