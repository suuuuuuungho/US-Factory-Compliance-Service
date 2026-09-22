// SUU-238: 문서를 고르면 목록은 사라지고 diff 만 한 스크롤 영역에 이어진다. 고정 머리글이 지금 보는 조항으로 바뀐다.
import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import FederalRegisterPage from "../src/app/federal-register/page";

const section = (number: string) => ({
  section: number,
  node_key: `40/63/subpart-T/section-${number}`,
  before_date: "2025-05-08",
  after_date: "2025-05-09",
  rows: [{ kind: "changed", before: `(a) ${number} was A.`, after: `(a) ${number} is B.`, is_context: false }],
});

const DOC = {
  document_key: "fr-2025-01234",
  document_number: "2025-01234",
  title: "NESHAP: Halogenated Solvent Cleaning Amendments",
  citation: "90 FR 1000",
  canonical_url: "https://www.federalregister.gov/d/2025-01234",
  publication_date: "2025-03-10",
  effective_date: "2025-05-09",
  amended_sections: ["63.460", "63.463"],
  reason: null,
  summary: { added: 0, removed: 0, changed: 2 },
  sections: [section("63.460"), section("63.463")],
};

const JSON_BODY = { generated_at: "2026-09-22T00:00:00Z", since: "2024-01-01", documents: [DOC] };

async function openDiff() {
  vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify(JSON_BODY), { status: 200 })));
  const { container } = render(<FederalRegisterPage />);
  fireEvent.click(await screen.findByRole("button", { name: /Halogenated Solvent Cleaning/ }));
  await screen.findByText("§ 63.460");
  return container;
}

afterEach(() => vi.unstubAllGlobals());

it("행 클릭하면 목록이 사라지고, 뒤로 버튼으로 돌아온다", async () => {
  const container = await openDiff();
  expect(container.querySelector("[data-pane='list']")).toBeNull();
  expect(container.querySelector("[data-pane='diff']")).not.toBeNull();

  fireEvent.click(screen.getByRole("button", { name: "뒤로" }));
  expect(container.querySelector("[data-pane='list']")).not.toBeNull();
  expect(container.querySelector("[data-pane='diff']")).toBeNull();
  screen.getByRole("button", { name: /Halogenated Solvent Cleaning/ });
});

it("섹션이 카드가 아니라 스크롤 영역 하나에 이어진다", async () => {
  const container = await openDiff();
  const scroll = container.querySelectorAll("[data-diff-scroll]");
  expect(scroll.length).toBe(1);
  expect(scroll[0].className).toMatch(/overflow-y-auto/);
  const sections = scroll[0].querySelectorAll("[data-diff-section]");
  expect(sections.length).toBe(2);
  for (const el of sections) expect(el.className).not.toMatch(/rounded|border/);
});

it("스크롤하면 머리글이 지금 보이는 조항으로 바뀐다", async () => {
  const container = await openDiff();
  const scroll = container.querySelector("[data-diff-scroll]") as HTMLElement;
  const header = container.querySelector("[data-diff-current]") as HTMLElement;
  expect(header.className).toMatch(/sticky/);
  expect(header.textContent).toMatch(/63\.460/);
  expect(header.textContent).not.toMatch(/63\.463/);

  // 둘째 섹션이 머리글 밑까지 올라온 상태를 흉내낸다
  const [first, second] = Array.from(scroll.querySelectorAll("[data-diff-section]")) as HTMLElement[];
  const rect = (top: number) => () => ({ top, bottom: top + 100, left: 0, right: 0, width: 0, height: 100, x: 0, y: top, toJSON: () => ({}) }) as DOMRect;
  scroll.getBoundingClientRect = rect(0);
  header.getBoundingClientRect = rect(0);
  first.getBoundingClientRect = rect(-300);
  second.getBoundingClientRect = rect(10);
  fireEvent.scroll(scroll);

  expect(header.textContent).toMatch(/63\.463/);
  expect(header.textContent).not.toMatch(/63\.460/);
});
