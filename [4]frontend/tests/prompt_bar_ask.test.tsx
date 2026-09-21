// SUU-214: /applicability 질문 칸은 react-bits PromptBar. 옛 Ask 버튼은 없고, 글을 쓰고 Send 를 누르면 POST /ask.
import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import Home from "../src/app/applicability/page";

const RESULT = {
  answer: {
    candidates: [{ subpart: "PPPP", title: "Surface Coating", criteria: [{ criterion: "Coats plastic.", citations: [] }] }],
    checklist: ["Major source?"],
  },
  sections: [], issues: [], tokens: { prompt: 1, completion: 1 }, cost_usd: 0, ms: 1,
};

afterEach(() => vi.unstubAllGlobals());

it("/applicability 에 PromptBar(.prompt-bar)가 있고 Ask 버튼은 없다", () => {
  const { container } = render(<Home />);
  expect(container.querySelector(".prompt-bar")).toBeTruthy();
  expect(screen.getByRole("textbox", { name: "Prompt" })).toBeTruthy();
  expect(screen.queryByRole("button", { name: "Ask" })).toBeNull();
});

it("글을 쓰고 Send 를 누르면 그 글로 POST /ask 하고 답이 보인다", async () => {
  vi.stubEnv("NEXT_PUBLIC_API_URL", "http://api.test");
  const fetch = vi.fn(async () => new Response(JSON.stringify(RESULT), { status: 200, headers: { "content-type": "application/json" } }));
  vi.stubGlobal("fetch", fetch);
  render(<Home />);
  fireEvent.change(screen.getByRole("textbox", { name: "Prompt" }), { target: { value: "we weld plastic" } });
  fireEvent.click(screen.getByRole("button", { name: "Send" }));

  expect(await screen.findByText(/Subpart PPPP/)).toBeTruthy();
  const [url, init] = fetch.mock.calls[0] as unknown as [string, RequestInit];
  expect(url).toBe("http://api.test/ask");
  expect(JSON.parse(init.body as string)).toEqual({ question: "we weld plastic" });
});
