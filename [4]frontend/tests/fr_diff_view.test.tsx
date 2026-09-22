// SUU-229: /federal-register 가 /fr-diff.json 을 읽어 목록을 그리고, 규칙을 펼치면 바뀐 문단만 빨강·초록으로 보인다.
import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import FederalRegisterPage from "../src/app/federal-register/page";

// SUU-228 fr_diff.py build() 가 쓰는 모양 그대로
const DOC = {
  document_key: "fr-2025-01234",
  document_number: "2025-01234",
  title: "NESHAP: Halogenated Solvent Cleaning Amendments",
  citation: "90 FR 1000",
  canonical_url: "https://www.federalregister.gov/d/2025-01234",
  publication_date: "2025-03-10",
  effective_date: "2025-05-09",
  amended_sections: ["63.460", "63.461"],
  reason: null,
  summary: { added: 1, removed: 1, changed: 1 },
  sections: [
    {
      section: "63.460",
      node_key: "section-63.460",
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

async function renderAndOpen() {
  vi.stubGlobal("fetch", vi.fn(async (url: string) => {
    if (!url.endsWith("/fr-diff.json")) throw new Error(`unexpected fetch ${url}`);
    return new Response(JSON.stringify(JSON_BODY), { status: 200, headers: { "content-type": "application/json" } });
  }));
  const utils = render(<FederalRegisterPage />);
  fireEvent.click(await screen.findByRole("button", { name: /Halogenated Solvent Cleaning/ }));
  await screen.findByText(/Old paragraph is gone/);
  return utils;
}

afterEach(() => vi.unstubAllGlobals());

it("목록: 제목·게재일·시행일·+N −M 요약이 보인다", async () => {
  vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify(JSON_BODY), { status: 200 })));
  render(<FederalRegisterPage />);
  await screen.findByRole("button", { name: /Halogenated Solvent Cleaning/ });
  screen.getByText(/2025-03-10/);
  screen.getByText(/2025-05-09/);
  screen.getByText(/\+1\s*−1/);
});

it("removed 문단에 diff-removed, added 문단에 diff-added 클래스가 붙는다", async () => {
  await renderAndOpen();
  expect(screen.getByText(/Old paragraph is gone/).closest(".diff-removed")).not.toBeNull();
  expect(screen.getByText(/New paragraph arrives/).closest(".diff-added")).not.toBeNull();
  expect(screen.getByText(/Old paragraph is gone/).closest(".diff-added")).toBeNull();
});

it("changed 문단은 바뀐 단어만 <mark>로 감싼다", async () => {
  const { container } = await renderAndOpen();
  const changed = container.querySelector(".diff-changed");
  expect(changed).not.toBeNull();
  const marks = Array.from(changed!.querySelectorAll("mark")).map((m) => m.textContent?.trim());
  expect(marks).toEqual(["A.", "B."]);
  // 안 바뀐 단어는 mark 밖에 있다
  expect(changed!.textContent).toMatch(/Owners must do/);
  for (const m of marks) expect(m).not.toMatch(/Owners/);
});

it("안 바뀐 섹션(63.461)은 DOM에 없고 바뀐 섹션(63.460)만 있다", async () => {
  await renderAndOpen();
  screen.getByText(/63\.460/);
  expect(screen.queryByText(/63\.461/)).toBeNull();
});

it("diff 없는 문서는 '변경 본문 없음' 을 보인다", async () => {
  vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify(JSON_BODY), { status: 200 })));
  render(<FederalRegisterPage />);
  fireEvent.click(await screen.findByRole("button", { name: /Correction Without Effective Date/ }));
  await screen.findByText(/변경 본문 없음/);
});
