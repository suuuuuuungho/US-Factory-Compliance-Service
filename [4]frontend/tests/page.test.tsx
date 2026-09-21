// SUU-163: 질문 → POST /ask → 후보 Subpart 카드 + 체크리스트. fetch는 가짜. 항상 "not a final" 문구.
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import Home from "../src/app/applicability/page";

const RESULT = {
  answer: {
    candidates: [
      {
        subpart: "PPPP",
        title: "Surface Coating of Plastic Parts and Products",
        criteria: [{ criterion: "The plant coats plastic parts.", citations: ["40 CFR 63.4481(a)"] }],
      },
      { subpart: "A", title: "General Provisions", criteria: [{ criterion: "Major source of HAP.", citations: ["40 CFR 63.1(a)"] }] },
    ],
    checklist: ["Is the facility a major source of HAP?"],
  },
  sections: [{ section_key: "section-63.4481", subpart: "PPPP" }],
  issues: [],
  tokens: { prompt: 1, completion: 1 },
  cost_usd: 0,
  ms: 1,
};

function fakeFetch(body: unknown, status = 200) {
  const fetch = vi.fn(async () => new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } }));
  vi.stubGlobal("fetch", fetch);
  return fetch;
}

function ask(question: string) {
  fireEvent.change(screen.getByRole("textbox"), { target: { value: question } });
  fireEvent.click(screen.getByRole("button", { name: /ask/i }));
}

afterEach(() => vi.unstubAllGlobals());

it("가짜 응답을 주면 후보 Subpart·기준·인용·체크리스트가 나온다", async () => {
  vi.stubEnv("NEXT_PUBLIC_API_URL", "http://api.test");
  const fetch = fakeFetch(RESULT);
  render(<Home />);
  ask("we solvent weld plastic parts");

  expect(await screen.findByText(/Subpart PPPP/)).toBeTruthy();
  expect(screen.getByText(/Surface Coating of Plastic Parts/)).toBeTruthy();
  expect(screen.getByText(/The plant coats plastic parts\./)).toBeTruthy();
  expect(screen.getByText(/40 CFR 63\.4481\(a\)/)).toBeTruthy();
  expect(screen.getByText(/Subpart A/)).toBeTruthy();
  expect(screen.getByText(/Is the facility a major source of HAP\?/)).toBeTruthy();

  // POST {NEXT_PUBLIC_API_URL}/ask, 몸통은 {question}
  expect(fetch).toHaveBeenCalledTimes(1);
  const [url, init] = fetch.mock.calls[0] as unknown as [string, RequestInit];
  expect(url).toBe("http://api.test/ask");
  expect(init.method).toBe("POST");
  expect(JSON.parse(init.body as string)).toEqual({ question: "we solvent weld plastic parts" });
});

it("기다리는 동안 로딩 표시(role=status)가 보이고 버튼이 잠긴다", async () => {
  vi.stubGlobal("fetch", vi.fn(() => new Promise(() => {})));  // 영원히 안 끝나는 요청
  render(<Home />);
  expect(screen.queryByRole("status")).toBeNull();
  ask("solvent welding");
  expect(await screen.findByRole("status")).toBeTruthy();
  expect((screen.getByRole("button", { name: /ask/i }) as HTMLButtonElement).disabled).toBe(true);
});

it("'not a final applicability determination' 문구는 답 전에도 후에도 있다", async () => {
  fakeFetch(RESULT);
  render(<Home />);
  const notice = /not a final applicability determination/i;
  expect(screen.getByText(notice)).toBeTruthy();
  ask("solvent welding");
  await screen.findByText(/Subpart PPPP/);
  expect(screen.getByText(notice)).toBeTruthy();
});

it("answer가 null이면 issues를 보여준다", async () => {
  fakeFetch({ ...RESULT, answer: null, issues: ["parse error: answer is not JSON"] });
  render(<Home />);
  ask("solvent welding");
  expect(await screen.findByText(/parse error: answer is not JSON/)).toBeTruthy();
  expect(screen.queryByText(/Subpart PPPP/)).toBeNull();
});

it("서버가 200이 아니면(예: 503 색인 준비 중) 상태 코드를 보여준다", async () => {
  fakeFetch({ detail: "index not ready" }, 503);
  render(<Home />);
  ask("solvent welding");
  expect(await screen.findByText(/503/)).toBeTruthy();
});
