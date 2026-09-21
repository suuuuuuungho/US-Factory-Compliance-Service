// SUU-193: 2행은 dockview 작업공간. 기본 칸은 Subparts | Checklist, 조문은 인용마다 칸(§63.4481)으로 열려 여러 개를 나란히 둘 수 있다.
// 끌어서 크기·위치를 바꾸고, 배치는 localStorage에 남는다. SUU-182의 three_columns.test.tsx(고정 3열 grid)를 대체한다.
// SUU-199: 질문 폼도 Question 칸이 된다. 저장 키는 workspace-layout-v2.
// SUU-200: 기본 배치 = 왼쪽 열 Question(위)/Subparts(아래) | Memo | Checklist. Memo는 처음부터 열려 있고, 조문은 Subparts 옆에 열린다.
// 위쪽 버튼 줄(Question~Memo, Reset layout)은 없다. 각 칸 머리의 + 메뉴로 칸을 넣고, ✕로 지운다. 저장 키는 workspace-layout-v3.
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
  fireEvent.click(screen.getByRole("button", { name: "Send" }));
  await screen.findByText(/Subpart PPPP/);
}

const tabNames = () => screen.getAllByRole("tab").map((t) => t.getAttribute("aria-label"));
// 탭 이름으로 그 칸(dockview group)을 찾고, 그 칸의 + 메뉴에서 항목을 고른다
const groupOf = (tab: string) => screen.getByRole("tab", { name: tab }).closest(".dv-groupview") as HTMLElement;
function pickFromMenu(tab: string, item: string) {
  fireEvent.click(within(groupOf(tab)).getByRole("button", { name: "Add panel" }));
  fireEvent.click(within(groupOf(tab)).getByRole("menuitem", { name: item }));
}

beforeEach(() => localStorage.clear());
afterEach(() => vi.unstubAllGlobals());

it("답이 오면 dockview 안에 끌 수 있는 탭 네 개(Question, Subparts, Memo, Checklist)가 있고 조문 칸은 아직 없다", async () => {
  await askAndWait();
  expect(document.querySelector(".dv-dockview")).not.toBeNull();
  expect(tabNames()).toEqual(["Question", "Subparts", "Memo", "Checklist"]);
  for (const tab of screen.getAllByRole("tab")) expect(tab.getAttribute("draggable")).toBe("true");
});

// SUU-199: 질문 폼은 Question 칸 안. Question과 Subparts는 같은 세로 열(같은 branch)에, Checklist는 그 옆.
it("질문 폼은 Question 칸 안에 있고, Question·Subparts는 한 열에 세로로 쌓인다", async () => {
  await askAndWait();
  const question = screen.getByRole("region", { name: "Question" });
  within(question).getByPlaceholderText(/describe the process/i);
  within(question).getByRole("button", { name: "Send" });
  const column = (id: string) => document.querySelector(`[data-panel="${id}"]`)!.closest(".dv-branch-node")!;
  expect(column("question")).toBe(column("subparts"));
  expect(column("question")).not.toBe(column("checklist"));
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
  // SUU-200: 조문 칸은 Subparts 옆(같은 열)에 열린다
  expect(tabNames()).toEqual(["Question", "Subparts", "§63.4481", "§63.4482", "Memo", "Checklist"]);
  const column = (id: string) => document.querySelector(`[data-panel="${id}"]`)!.closest(".dv-branch-node")!;
  expect(column("section:section-63.4482")).toBe(column("subparts")); // 활성 탭(둘째 조문)만 그려진다
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

// SUU-200: 위쪽 버튼 줄이 없다. 칸마다 + 버튼이 있고, 메뉴에는 네 칸 + 인용된 조문이 있다 (Reset layout 없음)
it("위쪽에 Question~Memo·Reset layout 버튼이 없고, 각 칸 머리에 + 버튼이 있다", async () => {
  await askAndWait();
  for (const name of ["Question", "Subparts", "Checklist", "Memo", "Reset layout"])
    expect(screen.queryByRole("button", { name })).toBeNull();
  expect(screen.getAllByRole("button", { name: "Add panel" })).toHaveLength(4);
  fireEvent.click(within(groupOf("Checklist")).getByRole("button", { name: "Add panel" }));
  const items = within(groupOf("Checklist")).getAllByRole("menuitem").map((m) => m.textContent);
  expect(items).toEqual(["Question", "Subparts", "Checklist", "Memo", "§63.4481", "§63.4482"]);
});

it("✕로 닫은 칸을 다른 칸의 + 메뉴로 고르면 그 칸에 탭으로 들어온다", async () => {
  await askAndWait();
  fireEvent.click(screen.getByRole("button", { name: "Close Checklist" }));
  await waitFor(() => expect(screen.queryByRole("tab", { name: "Checklist" })).toBeNull());
  pickFromMenu("Subparts", "Checklist");
  await screen.findByRole("tab", { name: "Checklist" });
  expect(groupOf("Checklist")).toBe(groupOf("Subparts"));
});

it("이미 열린 칸을 + 메뉴로 고르면 그 칸으로 옮겨 온다", async () => {
  await askAndWait();
  expect(groupOf("Memo")).not.toBe(groupOf("Checklist"));
  pickFromMenu("Checklist", "Memo");
  await waitFor(() => expect(groupOf("Memo")).toBe(groupOf("Checklist")));
  expect(screen.getAllByRole("tab", { name: "Memo" })).toHaveLength(1);
});

it("+ 메뉴의 조문을 고르면 그 칸에 조문이 열린다", async () => {
  await askAndWait();
  pickFromMenu("Memo", "§63.4482");
  const tab = await screen.findByRole("tab", { name: "§63.4482" });
  await screen.findByText("(a) second section");
  expect(tab.closest(".dv-groupview")).toBe(groupOf("Memo"));
});

it("칸을 전부 닫으면 기본 배치로 돌아온다", async () => {
  await askAndWait();
  for (const name of ["Question", "Subparts", "Memo"]) fireEvent.click(screen.getByRole("button", { name: `Close ${name}` }));
  fireEvent.click(screen.getByRole("button", { name: "Close Checklist" }));
  await waitFor(() => expect(tabNames()).toEqual(["Question", "Subparts", "Memo", "Checklist"]));
});

it("칸 배치는 localStorage 'workspace-layout-v3'에 저장되고, 닫은 칸은 다시 열어도 닫혀 있다", async () => {
  await askAndWait();
  const saved = () => JSON.parse(localStorage.getItem("workspace-layout-v3")!);
  expect(Object.keys(saved().panels).sort()).toEqual(["checklist", "memo", "question", "subparts"]);

  fireEvent.click(screen.getByRole("button", { name: "Close Checklist" }));
  await waitFor(() => expect(saved().panels.checklist).toBeUndefined());

  cleanup();
  await askAndWait();
  expect(tabNames()).toEqual(["Question", "Subparts", "Memo"]);
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
