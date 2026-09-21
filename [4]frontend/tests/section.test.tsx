// SUU-164: 인용 버튼 클릭 → GET /section/{key} → 옆 패널(aside)에 조문 전문. fetch는 가짜. 같은 조문은 한 번만 부른다.
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import Home from "../src/app/applicability/page";
import { citationToSectionKey } from "../src/lib/api";

const ASK = {
  answer: {
    candidates: [{
      subpart: "PPPP", title: "Surface Coating of Plastic Parts",
      criteria: [
        { criterion: "The plant coats plastic parts.", citations: ["40 CFR 63.4481(a)(1)"] },
        { criterion: "It uses solvent welding.", citations: ["40 CFR 63.4481(b)"] },
      ],
    }],
    checklist: ["Is the facility a major source of HAP?"],
  },
  sections: [{ section_key: "section-63.4481", subpart: "PPPP" }],
  issues: [], tokens: { prompt: 1, completion: 1 }, cost_usd: 0, ms: 1,
};
const SECTION = { section_key: "section-63.4481", subpart: "PPPP", text: "(a) first piece\n\n(b) second piece" };

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } });
}

/** /ask → ASK, /section/* → sectionStatus에 따라. 부른 URL을 calls에 남긴다 */
function fakeApi(sectionStatus = 200) {
  const calls: string[] = [];
  vi.stubGlobal("fetch", vi.fn(async (url: string, init?: RequestInit) => {
    calls.push(`${init?.method ?? "GET"} ${url}`);
    if (url.endsWith("/ask")) return json(ASK);
    return sectionStatus === 200 ? json(SECTION) : json({ detail: "section not found" }, sectionStatus);
  }));
  return calls;
}

async function askAndWait() {
  render(<Home />);
  fireEvent.change(screen.getByRole("textbox"), { target: { value: "solvent welding" } });
  fireEvent.click(screen.getByRole("button", { name: /ask/i }));
  await screen.findByText(/Subpart PPPP/);
}

afterEach(() => vi.unstubAllGlobals());

it("인용 문자열 → section_key", () => {
  expect(citationToSectionKey("40 CFR 63.4481(a)(1)")).toBe("section-63.4481");
  expect(citationToSectionKey("40 CFR 63.1(a)")).toBe("section-63.1");
  expect(citationToSectionKey("40 CFR 63.4481")).toBe("section-63.4481");
  expect(citationToSectionKey("Table 1 to Subpart PPPP")).toBeNull();
});

it("인용을 누르면 /section/section-63.4481을 부르고 패널에 본문이 나온다", async () => {
  vi.stubEnv("NEXT_PUBLIC_API_URL", "http://api.test");
  const calls = fakeApi();
  await askAndWait();
  expect(screen.queryByRole("complementary")).toBeNull(); // 누르기 전엔 패널 없음

  fireEvent.click(screen.getByRole("button", { name: "40 CFR 63.4481(a)(1)" }));
  const panel = await screen.findByRole("complementary");
  expect(within(panel).getByText(/section-63\.4481/)).toBeTruthy();
  expect(within(panel).getByText(/\(a\) first piece/)).toBeTruthy();
  expect(within(panel).queryByText(/\(b\) second piece/)).toBeNull(); // SUU-189: (a)만. 전체는 Show all
  expect(calls).toContain("GET http://api.test/section/section-63.4481");
});

it("같은 조문을 두 번 눌러도 /section은 한 번만 부른다", async () => {
  const calls = fakeApi();
  await askAndWait();
  fireEvent.click(screen.getByRole("button", { name: "40 CFR 63.4481(a)(1)" }));
  await screen.findByRole("complementary");
  fireEvent.click(screen.getByRole("button", { name: "40 CFR 63.4481(b)" })); // 같은 63.4481, 문단은 (b)
  await waitFor(() => expect(within(screen.getByRole("complementary")).getByText(/\(b\) second piece/)).toBeTruthy());
  expect(calls.filter((c) => c.includes("/section/")).length).toBe(1);
});

it("조문이 없으면(404) 패널에 상태 코드가 나온다", async () => {
  fakeApi(404);
  await askAndWait();
  fireEvent.click(screen.getByRole("button", { name: "40 CFR 63.4481(b)" }));
  const panel = await screen.findByRole("complementary");
  expect(await within(panel).findByText(/404/)).toBeTruthy();
});
