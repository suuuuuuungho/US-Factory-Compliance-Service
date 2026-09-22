// SUU-258: /decision-letter 위에 공장 설명 글칸 + Search. 결과가 오면 표가 비슷한 서한(최대 5건)으로 바뀌고
// 행마다 score·snippet 이 보인다. 빈 배열이면 표 대신 안내 문구. Clear 면 원래 목록으로 복귀.
import { fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import DecisionLetterPage from "../src/app/decision-letter/page";
import { similarLetters } from "../src/lib/api";

const NO_MATCH_TEXT =
  "No similar cases found. Letters with weak similarity are not recommended, to keep results trustworthy. Try describing your process, fuel, or equipment.";

const base = {
  title: "Applicability Determination",
  subparts: ["S"],
  date: "2025-03-10",
  pdf_url: "https://www.epa.gov/x.pdf",
};

// 132건 목록 (SUU-253 표). 10개씩 → 14쪽
const ALL = Array.from({ length: 132 }, (_, i) => ({ ...base, source_key: `k${i + 1}`, facility_name: `Facility ${i + 1}` }));

// 백엔드(SUU-257)가 주는 모양: 메타 + score + snippet, 점수 내림차순
const SIMILAR = [
  { ...base, source_key: "s1", facility_name: "Domtar Ashdown", score: 0.91, snippet: "kraft pulp mill lime kiln" },
  { ...base, source_key: "s2", facility_name: "Shuqualak Lumber", score: 0.42, snippet: "wood-fired boiler alternative monitoring" },
  { ...base, source_key: "s3", facility_name: "Foley Cellulose", score: 0.07, snippet: "recovery furnace" },
];

/** fetch 를 가짜로: decision-letters.json 은 132건, /letters/similar 는 similar 를 준다 */
function stubFetch(similar: object[] | (() => Promise<Response>)) {
  const fetch = vi.fn(async (url: string) => {
    if (String(url).endsWith("/letters/similar")) {
      if (typeof similar === "function") return similar();
      return new Response(JSON.stringify({ letters: similar }), { status: 200, headers: { "content-type": "application/json" } });
    }
    return new Response(JSON.stringify({ letters: ALL }), { status: 200 });
  });
  vi.stubGlobal("fetch", fetch);
  return fetch;
}

async function renderPage() {
  render(<DecisionLetterPage />);
  await screen.findByText("Facility 1");
}

function search(description: string) {
  fireEvent.change(screen.getByRole("textbox", { name: "Factory description" }), { target: { value: description } });
  fireEvent.click(screen.getByRole("button", { name: "Search" }));
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
});

const bodyRows = () => screen.getAllByRole("row").slice(1);

it("similarLetters(description) 은 POST {API}/letters/similar 로 {description} 을 보내고 letters 를 돌려준다", async () => {
  vi.stubEnv("NEXT_PUBLIC_API_URL", "http://api.test");
  const fetch = stubFetch(SIMILAR);
  const result = await similarLetters("we make kraft pulp");
  expect(result).toEqual(SIMILAR);
  const [url, init] = fetch.mock.calls[0] as unknown as [string, RequestInit];
  expect(url).toBe("http://api.test/letters/similar");
  expect(init.method).toBe("POST");
  expect(JSON.parse(init.body as string)).toEqual({ description: "we make kraft pulp" });
});

it("검색 API 가 3건을 주면 표에 그 3건만, 첫 행이 가장 높은 score, 행마다 score·snippet 이 보인다", async () => {
  stubFetch(SIMILAR);
  await renderPage();
  search("we make kraft pulp");

  await screen.findByText("Domtar Ashdown");
  const rows = bodyRows();
  expect(rows).toHaveLength(3);
  expect(screen.queryByText("Facility 1")).toBeNull();
  const first = within(rows[0]);
  expect(first.getByText("Domtar Ashdown")).toBeTruthy();
  expect(first.getByText("0.91")).toBeTruthy();
  expect(first.getByText("kraft pulp mill lime kiln")).toBeTruthy();
  expect(within(rows[2]).getByText("0.07")).toBeTruthy();
});

it("API 가 빈 배열을 주면 표 대신 안내 문구가 보인다", async () => {
  stubFetch([]);
  await renderPage();
  search("we sell shoes");

  expect(await screen.findByText(NO_MATCH_TEXT)).toBeTruthy();
  expect(screen.queryByRole("table")).toBeNull();
  expect(screen.queryByText("Facility 1")).toBeNull();
});

it("Clear 를 누르면 원래 132건 표(10개씩, 1 / 14)로 돌아온다", async () => {
  stubFetch(SIMILAR);
  await renderPage();
  search("we make kraft pulp");
  await screen.findByText("Domtar Ashdown");

  fireEvent.click(screen.getByRole("button", { name: "Clear" }));

  expect(await screen.findByText("Facility 1")).toBeTruthy();
  expect(bodyRows()).toHaveLength(10);
  expect(screen.getByText("1 / 14")).toBeTruthy();
  expect(screen.queryByText("Domtar Ashdown")).toBeNull();
  expect((screen.getByRole("textbox", { name: "Factory description" }) as HTMLTextAreaElement).value).toBe("");
});

it("로딩 중엔 Search 버튼이 비활성화되고, 답이 오면 다시 활성화된다", async () => {
  let resolve!: (r: Response) => void;
  stubFetch(() => new Promise<Response>((r) => { resolve = r; }));
  await renderPage();
  search("we make kraft pulp");

  const button = () => screen.getByRole("button", { name: "Search" }) as HTMLButtonElement;
  expect(button().disabled).toBe(true);

  resolve(new Response(JSON.stringify({ letters: SIMILAR }), { status: 200, headers: { "content-type": "application/json" } }));
  await screen.findByText("Domtar Ashdown");
  expect(button().disabled).toBe(false);
});
