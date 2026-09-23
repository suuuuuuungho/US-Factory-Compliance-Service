// SUU-265: About 페이지 숫자를 public/about-stats.json 한 곳에 모으고, 숫자마다 출처(source)를 붙인다.
import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { expect, it } from "vitest";

const PUBLIC = join(__dirname, "../public");
const load = (name: string) => JSON.parse(readFileSync(join(PUBLIC, name), "utf8"));

// SUU-266이 읽을 키. 값·출처는 설계 파일 [5] tickets/4)Frontend/1_feat/SUU-265.md 표를 따른다
const STAT_KEYS = [
  "part63_pages", "part63_words", "part63_tokens_min", "part63_tokens_max", "llm_context_tokens",
  "rule_changes", "sections_changed", "sections_changed_pct",
  "epa_median_days", "epa_over_6mo_pct", "epa_letters_sample", "letters_total",
  "prison_years", "violation_pct", "facilities", "penalty_total_usd", "penalty_max_usd",
  "rag_chunks", "rag_eval_cases", "rag_hit20_pct", "rag_subpart_pct", "rag_citation_grounded_pct",
];
const SERIES_KEYS = ["rule_changes_by_year", "letters_by_year", "penalty_by_subpart", "rag_ndcg_steps", "rag_funnel"];

it("about-stats.json의 모든 숫자에 비어 있지 않은 source가 있다", () => {
  expect(existsSync(join(PUBLIC, "about-stats.json"))).toBe(true);
  const { stats, series } = load("about-stats.json");
  for (const k of STAT_KEYS) {
    expect(typeof stats[k]?.value, k).toBe("number");
    expect(stats[k].source?.trim(), k).toBeTruthy();
  }
  for (const k of SERIES_KEYS) {
    expect(series[k]?.data?.length, k).toBeGreaterThan(0);
    expect(series[k].source?.trim(), k).toBeTruthy();
  }
});

it("연도별 규칙 개정을 더하면 136, 연도별 판정서한 + 날짜 모름을 더하면 1,127이다", () => {
  const { stats, series } = load("about-stats.json");
  const sum = (rows: { count: number }[]) => rows.reduce((a, r) => a + r.count, 0);

  const rules = series.rule_changes_by_year.data;
  expect(rules.map((r: { year: number }) => r.year)).toEqual([2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025]);
  expect(sum(rules)).toBe(136);
  expect(stats.rule_changes.value).toBe(136);

  const letters = series.letters_by_year;
  expect(sum(letters.data) + letters.before_1993 + letters.unknown).toBe(1127);
  expect(stats.letters_total.value).toBe(1127);
});

// SUU-266: CAA Dashboard 132건 날짜를 채워 "날짜 모름"은 엑셀 빈 날짜(12/30/1899) 6건만 남는다. 차트는 1993년부터
it("판정서한 연도별은 1993~2025, 날짜 모름 6건, 1993년 전은 before_1993으로 따로 센다", () => {
  const { letters_by_year: letters } = load("about-stats.json").series;
  const years = letters.data.map((r: { year: number }) => r.year);
  expect(years[0]).toBe(1993);
  expect(years.at(-1)).toBe(2025);
  expect(letters.unknown).toBe(6);
  expect(letters.before_1993).toBeGreaterThan(0);
  for (const y of [2021, 2022, 2023, 2024, 2025]) {
    expect(letters.data.find((r: { year: number }) => r.year === y)?.count, String(y)).toBeGreaterThan(0);
  }
});

// SUU-267: 화면용 출처 cite. 사용자가 직접 찾아볼 수 있는 영어 공개 출처. source(내부 추적용)는 그대로 둔다
const CITE = {
  PART63: "40 CFR Part 63 (eCFR / govinfo PDF)",
  COUNT: "Our count of the 40 CFR Part 63 text",
  LLM: "Published context limits of leading AI models",
  FR: "Federal Register, final rules amending 40 CFR Part 63, 2018–2025",
  SECTIONS: "Sections of 40 CFR Part 63 amended by those rules, 2018–2025",
  ADI_SAMPLE: "EPA Applicability Determination Index, 235 Part 63 letters",
  LETTERS: "EPA Applicability Determination Index + CAA Applicability Determinations Dashboard",
  CAA: "Clean Air Act §113(c)(2), 42 U.S.C. 7413(c)(2)",
  ECHO: "EPA ECHO enforcement data, 2015–",
  RAG: "Our evaluation on 102 real EPA applicability questions",
};
const STAT_CITE: Record<string, string> = {
  part63_pages: CITE.PART63, part63_words: CITE.COUNT, part63_tokens_min: CITE.COUNT, part63_tokens_max: CITE.COUNT,
  llm_context_tokens: CITE.LLM, rule_changes: CITE.FR, sections_changed: CITE.SECTIONS, sections_changed_pct: CITE.SECTIONS,
  epa_median_days: CITE.ADI_SAMPLE, epa_over_6mo_pct: CITE.ADI_SAMPLE, epa_letters_sample: CITE.ADI_SAMPLE,
  letters_total: CITE.LETTERS, prison_years: CITE.CAA,
  violation_pct: CITE.ECHO, facilities: CITE.ECHO, penalty_total_usd: CITE.ECHO, penalty_max_usd: CITE.ECHO,
  rag_chunks: CITE.RAG, rag_eval_cases: CITE.RAG, rag_hit20_pct: CITE.RAG, rag_subpart_pct: CITE.RAG, rag_citation_grounded_pct: CITE.RAG,
};
const SERIES_CITE: Record<string, string> = {
  rule_changes_by_year: CITE.FR, letters_by_year: CITE.LETTERS, penalty_by_subpart: CITE.ECHO,
  rag_ndcg_steps: CITE.RAG, rag_funnel: CITE.RAG,
};

it("모든 숫자에 화면용 영어 cite가 있고, 내부 추적용 source는 남아 있다", () => {
  const { stats, series } = load("about-stats.json");
  for (const [k, cite] of Object.entries(STAT_CITE)) {
    expect(stats[k].cite, k).toBe(cite);
    expect(stats[k].source?.trim(), k).toBeTruthy();
  }
  for (const [k, cite] of Object.entries(SERIES_CITE)) {
    expect(series[k].cite, k).toBe(cite);
    expect(series[k].source?.trim(), k).toBeTruthy();
  }
});

it("과징금·위반 숫자가 echo-stats.json summary와 같다", () => {
  const { stats, series } = load("about-stats.json");
  const { summary, subparts } = load("echo-stats.json");
  expect(stats.violation_pct.value).toBe(summary.violation_facility_pct);
  expect(stats.facilities.value).toBe(summary.facilities);
  expect(stats.penalty_total_usd.value).toBe(summary.penalty_total_usd);
  expect(stats.penalty_max_usd.value).toBe(summary.penalty_max_usd);

  const byCode = Object.fromEntries(subparts.map((s: { code: string; penalty_total_usd: number }) => [s.code, s.penalty_total_usd]));
  for (const row of series.penalty_by_subpart.data) {
    expect(row.penalty_total_usd, row.code).toBe(byCode[row.code]);
  }
});
