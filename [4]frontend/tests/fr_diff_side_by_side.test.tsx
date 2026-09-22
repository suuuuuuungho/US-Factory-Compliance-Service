// SUU-233: diff 영역이 줄마다 Before(원문) | After(개정문) 두 칸으로 나란히 보인다.
import { fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import FederalRegisterPage from "../src/app/federal-register/page";

const DOC = {
  document_key: "fr-2025-01234",
  document_number: "2025-01234",
  title: "NESHAP: Halogenated Solvent Cleaning Amendments",
  citation: "90 FR 1000",
  canonical_url: "https://www.federalregister.gov/d/2025-01234",
  publication_date: "2025-03-10",
  effective_date: "2025-05-09",
  amended_sections: ["63.460"],
  reason: null,
  summary: { added: 1, removed: 1, changed: 1 },
  sections: [
    {
      section: "63.460",
      node_key: "40/63/subpart-T/section-63.460",
      before_date: "2025-05-08",
      after_date: "2025-05-09",
      rows: [
        { kind: "equal", before: "(a) Context paragraph stays.", after: "(a) Context paragraph stays.", is_context: true },
        { kind: "removed", before: "(b) Old paragraph is gone.", after: null, is_context: false },
        { kind: "added", before: null, after: "(b) New paragraph arrives.", is_context: false },
        { kind: "changed", before: "(c) Owners must do A.", after: "(c) Owners must do B.", is_context: false },
      ],
    },
  ],
};

const JSON_BODY = { generated_at: "2026-09-22T00:00:00Z", since: "2024-01-01", documents: [DOC] };

async function openDiff() {
  vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify(JSON_BODY), { status: 200 })));
  const { container } = render(<FederalRegisterPage />);
  fireEvent.click(await screen.findByRole("button", { name: /Halogenated Solvent Cleaning/ }));
  await screen.findByText(/Old paragraph is gone/);
  return container.querySelector("[data-pane='diff']") as HTMLElement;
}

afterEach(() => vi.unstubAllGlobals());

// 줄 하나 = [data-diff-row] 안에 [data-side='before'] 와 [data-side='after'] 가 하나씩
it("각 줄이 Before/After 두 칸으로 나온다", async () => {
  const diff = await openDiff();
  const rows = Array.from(diff.querySelectorAll("[data-diff-row]"));
  expect(rows.length).toBe(4);
  for (const row of rows) {
    expect(row.querySelectorAll("[data-side='before']").length).toBe(1);
    expect(row.querySelectorAll("[data-side='after']").length).toBe(1);
  }
  // 칸 머리글
  within(diff).getByText(/^Before/);
  within(diff).getByText(/^After/);
});

it("삭제 줄은 왼쪽만, 추가 줄은 오른쪽만 글이 있다", async () => {
  const diff = await openDiff();
  const removed = diff.querySelector("[data-diff-row='removed']")!;
  expect(removed.querySelector("[data-side='before']")!.textContent).toMatch(/Old paragraph is gone/);
  expect(removed.querySelector("[data-side='after']")!.textContent?.trim()).toBe("");

  const added = diff.querySelector("[data-diff-row='added']")!;
  expect(added.querySelector("[data-side='before']")!.textContent?.trim()).toBe("");
  expect(added.querySelector("[data-side='after']")!.textContent).toMatch(/New paragraph arrives/);
});

it("바뀐 줄에서 왼쪽 mark는 빠진 단어, 오른쪽 mark는 새 단어만이다", async () => {
  const diff = await openDiff();
  const changed = diff.querySelector("[data-diff-row='changed']")!;
  const before = changed.querySelector("[data-side='before']")!;
  const after = changed.querySelector("[data-side='after']")!;
  const marksOf = (el: Element) => Array.from(el.querySelectorAll("mark")).map((m) => m.textContent?.trim());
  expect(marksOf(before)).toEqual(["A."]);
  expect(marksOf(after)).toEqual(["B."]);
  // 안 바뀐 단어는 양쪽 다 mark 밖에 그대로
  expect(before.textContent).toMatch(/Owners must do/);
  expect(after.textContent).toMatch(/Owners must do/);
});

it("문맥 줄은 양쪽에 같은 글이 있다", async () => {
  const diff = await openDiff();
  const equal = diff.querySelector("[data-diff-row='equal']")!;
  expect(equal.querySelector("[data-side='before']")!.textContent).toMatch(/Context paragraph stays/);
  expect(equal.querySelector("[data-side='after']")!.textContent).toMatch(/Context paragraph stays/);
});
