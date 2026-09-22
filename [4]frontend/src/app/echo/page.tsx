// SUU-218: 빈 페이지. 제목만, 내용은 나중에.
// SUU-237: public/echo-stats.json 을 읽어 타일 4개 · Subpart 표(정렬·제조업 필터) · 연도별 차트.
// SUU-245: deviation 설명은 타일 바로 아래, 타일 글자 가운데.
// SUU-242: 글자 전부 영어. 벌금은 중앙값 대신 총액·최대(크게). 표는 10줄씩, 정렬은 ↓/↑ 토글. BarYAxis 는 가로 막대용이라 연도가 왼쪽에 또 찍혀서 뺐다.
"use client";

import { useEffect, useState } from "react";
import { Bar } from "@/components/charts/bar";
import { BarChart } from "@/components/charts/bar-chart";
import { BarXAxis } from "@/components/charts/bar-x-axis";
import { Grid } from "@/components/charts/grid";
import { ChartTooltip } from "@/components/charts/tooltip";

type Subpart = {
  code: string;
  desc: string;
  facilities: number;
  mfg_facilities: number;
  violation_facility_pct: number;
  penalty_count: number;
  penalty_median_usd: number | null;
  penalty_total_usd: number;
  penalty_max_usd: number | null;
  deviation_y_pct: number;
};

type EchoStats = {
  summary: {
    facilities: number;
    mfg_facilities: number;
    violation_facility_pct: number;
    penalty_count: number;
    penalty_median_usd: number | null;
    penalty_total_usd: number;
    penalty_max_usd: number | null;
    deviation_y_pct: number;
  };
  subparts: Subpart[];
  yearly: { year: number; violations: number; penalties: number }[];
};

type NumericKey = Exclude<keyof Subpart, "code" | "desc">;

const COLUMNS: { key: NumericKey; label: string }[] = [
  { key: "facilities", label: "Facilities" },
  { key: "mfg_facilities", label: "Mfg" },
  { key: "violation_facility_pct", label: "Violation %" },
  { key: "penalty_count", label: "Penalties" },
  { key: "penalty_total_usd", label: "Total $" },
  { key: "penalty_max_usd", label: "Max $" },
  { key: "deviation_y_pct", label: "Deviation %" },
];
const PAGE_SIZE = 10;

const num = (v: number) => v.toLocaleString("en-US");
const usd = (v: number | null) => (v === null ? "—" : `$${num(Math.floor(v))}`);
// 큰 돈은 $958.8M 처럼 짧게
const usdShort = (v: number | null) => {
  if (v === null) return "—";
  if (v >= 1e9) return `$${(v / 1e9).toFixed(2)}B`;
  if (v >= 1e6) return `$${(v / 1e6).toFixed(1)}M`;
  if (v >= 1e3) return `$${(v / 1e3).toFixed(0)}K`;
  return usd(v);
};
const pct = (v: number) => `${v.toFixed(1)}%`;
// "MACT Part 63 - Subpart ZZZZ - STATIONARY ..." → "STATIONARY ..."
const shortDesc = (desc: string) => desc.replace(/^MACT Part 63 - Subpart \S+ - /, "");

function cell(key: NumericKey, value: number | null) {
  if (key === "penalty_total_usd" || key === "penalty_max_usd") return usdShort(value);
  if (value === null) return "—";
  return key.endsWith("_pct") ? pct(value) : num(value);
}

export default function EchoPage() {
  const [stats, setStats] = useState<EchoStats | null>(null);
  const [error, setError] = useState(false);
  const [mfgOnly, setMfgOnly] = useState(false);
  const [sortKey, setSortKey] = useState<NumericKey | null>(null);
  const [sortAsc, setSortAsc] = useState(false);
  const [page, setPage] = useState(0);

  useEffect(() => {
    let cancelled = false;

    fetch("/echo-stats.json")
      .then((response) => response.json() as Promise<EchoStats>)
      .then((payload) => {
        if (!cancelled) setStats(payload);
      })
      .catch(() => {
        if (!cancelled) setError(true);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const rows = (stats?.subparts ?? []).filter((s) => !mfgOnly || s.mfg_facilities > 0);
  if (sortKey) {
    // 내림차순. null 은 맨 뒤.
    rows.sort((a, b) => {
      const av = a[sortKey];
      const bv = b[sortKey];
      if (av === null) return bv === null ? 0 : 1;
      if (bv === null) return -1;
      return sortAsc ? av - bv : bv - av;
    });
  }
  const pageCount = Math.max(1, Math.ceil(rows.length / PAGE_SIZE));
  const pageRows = rows.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);

  // 같은 열 다시 누르면 ↓ ↔ ↑. 정렬·필터가 바뀌면 1쪽으로
  const toggleSort = (key: NumericKey) => {
    setSortAsc(sortKey === key ? !sortAsc : false);
    setSortKey(key);
    setPage(0);
  };

  return (
    <main className="flex flex-1 flex-col px-6 py-6">
      <h1 className="text-center text-[28px] font-bold text-ink">EPA ECHO</h1>
      <p className="mt-1 text-center text-sm text-ink-muted">Violations and penalties at facilities subject to Part 63 (NESHAP)</p>
      {error ? <p className="mt-4 text-center text-sm text-ink-muted">Failed to load.</p> : null}
      {stats ? (
        <div className="mx-auto mt-6 w-full max-w-5xl">
          <div className="grid grid-cols-2 gap-4 md:grid-cols-5">
            <Tile id="facilities" label="Part 63 facilities" value={num(stats.summary.facilities)} />
            <Tile id="violation-pct" label="Facilities with violations" value={pct(stats.summary.violation_facility_pct)} />
            <Tile id="penalty-total" label="Total penalties since 2015" value={usdShort(stats.summary.penalty_total_usd)} />
            <Tile id="penalty-max" label="Largest single penalty" value={usdShort(stats.summary.penalty_max_usd)} />
            <Tile id="deviation-pct" label="Title V deviation %" value={pct(stats.summary.deviation_y_pct)} />
          </div>

          <section data-testid="deviation-note" className="mt-4 rounded-xl border border-hairline p-5 text-sm leading-6 text-ink-muted">
            <h2 className="text-base font-semibold text-ink">What is a Title V deviation?</h2>
            <p className="mt-2">
              A Title V (major source) operating permit lists every Clean Air Act requirement a facility must follow. At least once a
              year the facility must certify, signed by a responsible official, whether it complied with each permit condition.
              Any period when a condition was not met — a missed monitoring run, an emission limit exceeded, a late report — is
              a <span className="text-ink">deviation</span> and must be disclosed in that certification.
            </p>
            <p className="mt-2">
              <span className="text-ink">Title V deviation %</span> above is the share of annual compliance certifications in ECHO
              where the facility reported at least one deviation. A deviation is self-reported and is not automatically a violation,
              but it is the first thing regulators look at when deciding whom to inspect.
            </p>
          </section>

          <section className="mt-10">
            <h2 className="text-lg font-semibold text-ink">Violations and penalty actions by year</h2>
            <div data-chart="yearly" className="mt-3">
              <BarChart data={stats.yearly} xDataKey="year" aspectRatio="3 / 1">
                <Grid horizontal vertical={false} />
                <BarXAxis />
                <Bar dataKey="violations" fill="var(--chart-1)" />
                <Bar dataKey="penalties" fill="var(--chart-3)" />
                <ChartTooltip />
              </BarChart>
            </div>
            <p className="mt-1 text-xs text-ink-muted">Dark: violations (by first FRV date) · Light: penalty actions</p>
          </section>

          <section className="mt-10">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-ink">By Subpart</h2>
              <label className="flex items-center gap-2 text-sm text-ink">
                <input
                  type="checkbox"
                  checked={mfgOnly}
                  onChange={(e) => {
                    setMfgOnly(e.target.checked);
                    setPage(0);
                  }}
                />
                Manufacturing only
              </label>
            </div>
            <table className="mt-3 w-full border-collapse text-left text-sm">
              <thead className="border-b border-hairline text-ink-muted">
                <tr>
                  <th className="px-3 py-3 font-medium">Subpart</th>
                  <th className="px-3 py-3 font-medium">Description</th>
                  {COLUMNS.map((c) => (
                    <th key={c.key} className="px-3 py-3 text-right font-medium whitespace-nowrap">
                      <button
                        type="button"
                        onClick={() => toggleSort(c.key)}
                        className={sortKey === c.key ? "font-semibold text-ink" : "hover:text-ink"}
                      >
                        {c.label}
                        {sortKey === c.key ? (sortAsc ? " ↑" : " ↓") : ""}
                      </button>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-hairline">
                {pageRows.map((s) => (
                  <tr key={s.code} data-testid="subpart-row" data-code={s.code}>
                    <td className="px-3 py-3 font-medium whitespace-nowrap">{s.code}</td>
                    <td className="w-full max-w-0 truncate px-3 py-3" title={s.desc}>
                      {shortDesc(s.desc)}
                    </td>
                    {COLUMNS.map((c) => (
                      <td key={c.key} className="px-3 py-3 text-right tabular-nums whitespace-nowrap">
                        {cell(c.key, s[c.key])}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
            <div data-testid="pager" className="mt-3 flex items-center justify-end gap-3 text-sm text-ink-muted">
              <button type="button" onClick={() => setPage(page - 1)} disabled={page === 0} className="hover:text-ink disabled:opacity-40">
                ← Prev
              </button>
              <span>
                {page + 1} / {pageCount}
              </span>
              <button type="button" onClick={() => setPage(page + 1)} disabled={page + 1 >= pageCount} className="hover:text-ink disabled:opacity-40">
                Next →
              </button>
            </div>
          </section>

        </div>
      ) : null}
    </main>
  );
}

function Tile({ id, label, value }: { id: string; label: string; value: string }) {
  return (
    <div data-testid={`tile-${id}`} className="rounded-xl border border-hairline p-4 text-center">
      <div className="text-sm text-ink-muted">{label}</div>
      <div className="mt-1 text-2xl font-bold text-ink tabular-nums">{value}</div>
    </div>
  );
}
