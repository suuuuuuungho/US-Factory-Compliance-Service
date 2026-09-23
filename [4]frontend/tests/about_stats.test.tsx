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
  expect(sum(letters.data) + letters.unknown).toBe(1127);
  expect(stats.letters_total.value).toBe(1127);
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
