// SUU-231: /federal-register 목록이 표(연번·Subpart·제목·개정일·+/−)로 가운데 보이고,
// 한 줄을 누르면 표가 왼쪽 열로 가고 오른쪽에 diff가 붙는다.
import { fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import FederalRegisterPage from "../src/app/federal-register/page";

const ROW = (kind: "removed" | "added", text: string) =>
  kind === "removed"
    ? { kind, before: text, after: null, is_context: false }
    : { kind, before: null, after: text, is_context: false };

// subpart 는 node_key "40/63/subpart-X/section-…" 에서 뽑는다. A 와 T 두 개.
const DOC = {
  document_key: "fr-2025-01234",
  document_number: "2025-01234",
  title: "NESHAP: Halogenated Solvent Cleaning Amendments",
  citation: "90 FR 1000",
  canonical_url: "https://www.federalregister.gov/d/2025-01234",
  publication_date: "2025-03-10",
  effective_date: "2025-05-09",
  amended_sections: ["63.14", "63.460"],
  reason: null,
  summary: { added: 3, removed: 1, changed: 0 },
  sections: [
    { section: "63.14", node_key: "40/63/subpart-A/section-63.14", before_date: "2025-05-08", after_date: "2025-05-09",
      rows: [ROW("added", "(a) IBR line one."), ROW("added", "(b) IBR line two.")] },
    { section: "63.460", node_key: "40/63/subpart-T/section-63.460", before_date: "2025-05-08", after_date: "2025-05-09",
      rows: [ROW("removed", "(b) Old paragraph is gone."), ROW("added", "(b) New paragraph arrives.")] },
  ],
};

const NO_DIFF = {
  ...DOC,
  document_key: "fr-2025-09999",
  document_number: "2025-09999",
  title: "Correction Without Effective Date",
  effective_date: null,
  amended_sections: [],
  sections: [],
  reason: "no_effective_date",
  summary: { added: 0, removed: 0, changed: 0 },
};

const JSON_BODY = { generated_at: "2026-09-22T00:00:00Z", since: "2024-01-01", documents: [DOC, NO_DIFF] };

async function renderPage() {
  vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify(JSON_BODY), { status: 200 })));
  const utils = render(<FederalRegisterPage />);
  await screen.findByRole("button", { name: /Halogenated Solvent Cleaning/ });
  return utils;
}

afterEach(() => vi.unstubAllGlobals());

it("표 머리글: 연번·Subpart·제목·개정일·변경", async () => {
  await renderPage();
  const headers = screen.getAllByRole("columnheader").map((h) => h.textContent?.trim());
  expect(headers).toEqual(["연번", "Subpart", "제목", "개정일", "변경"]);
});

it("첫 행: 연번 1, subpart 'A, T', 개정일은 시행일", async () => {
  await renderPage();
  const row = screen.getByRole("button", { name: /Halogenated Solvent Cleaning/ }).closest("tr")!;
  const cells = within(row).getAllByRole("cell").map((c) => c.textContent?.trim());
  expect(cells[0]).toBe("1");
  expect(cells[1]).toBe("A, T");
  expect(cells[3]).toBe("2025-05-09");
  // 게재일은 표에 없다
  expect(screen.queryByText(/2025-03-10/)).toBeNull();
});

it("+N 은 초록(semantic-success), −M 은 빨강(gradient-coral) 으로 따로 색이 있다", async () => {
  await renderPage();
  const plus = screen.getByText("+3");
  const minus = screen.getByText("−1");
  expect(plus.className).toMatch(/semantic-success/);
  expect(minus.className).toMatch(/gradient-coral/);
});

it("diff 없는 문서는 연번 2, subpart '—', 개정일 '—', 행이 회색(text-ink-muted)", async () => {
  await renderPage();
  const row = screen.getByRole("button", { name: /Correction Without Effective Date/ }).closest("tr")!;
  const cells = within(row).getAllByRole("cell").map((c) => c.textContent?.trim());
  expect(cells[0]).toBe("2");
  expect(cells[1]).toBe("—");
  expect(cells[3]).toBe("—");
  expect(row.className).toMatch(/text-ink-muted/);
});

it("선택 전: diff 영역이 없고 목록이 가운데(mx-auto)", async () => {
  const { container } = await renderPage();
  expect(container.querySelector("[data-pane='diff']")).toBeNull();
  expect(container.querySelector("[data-pane='list']")!.className).toMatch(/mx-auto/);
});

it("행 클릭: 목록이 왼쪽으로 가고(mx-auto 제거) 오른쪽 diff 영역에 본문이 붙는다", async () => {
  const { container } = await renderPage();
  fireEvent.click(screen.getByRole("button", { name: /Halogenated Solvent Cleaning/ }));
  const diff = container.querySelector("[data-pane='diff']");
  expect(diff).not.toBeNull();
  await within(diff as HTMLElement).findByText(/Old paragraph is gone/);
  expect(container.querySelector("[data-pane='list']")!.className).not.toMatch(/mx-auto/);
});
