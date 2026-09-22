// SUU-196: (SUU-214 로 Ask → PromptBar Send) Ask 버튼은 처음부터 textarea 오른쪽에 같은 높이로 붙어 있고, Ask를 누르면 h1·설명 p가 사라져 질문 칸이 위로 붙는다.
import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
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

afterEach(() => vi.unstubAllGlobals());

// SUU-214: SUU-196/197 의 textarea·Ask 배치 검사는 PromptBar 로 바뀌면서 뺐다. 아래만 남는다.
it("Send를 누르면 로딩 중에도, 답이 온 뒤에도 h1과 설명 p가 사라진다", async () => {
  let resolve!: (r: Response) => void;
  vi.stubGlobal("fetch", vi.fn(() => new Promise<Response>((r) => (resolve = r))));
  render(<Home />);
  expect(screen.getByRole("heading", { level: 1 }).textContent).toBe("eCFR Applicability");
  expect(screen.getByText(/40 CFR Part 63 applicability criteria/)).toBeTruthy();

  fireEvent.change(screen.getByRole("textbox"), { target: { value: "solvent welding" } });
  fireEvent.click(screen.getByRole("button", { name: "Send" }));
  await screen.findByRole("status");
  expect(screen.queryByRole("heading", { level: 1 })).toBeNull();
  expect(screen.queryByText(/40 CFR Part 63 applicability criteria/)).toBeNull();

  resolve(new Response(JSON.stringify(ASK), { status: 200, headers: { "content-type": "application/json" } }));
  await screen.findByText(/Subpart PPPP/);
  expect(screen.queryByRole("heading", { level: 1 })).toBeNull();
  expect(screen.queryByText(/40 CFR Part 63 applicability criteria/)).toBeNull();
});
