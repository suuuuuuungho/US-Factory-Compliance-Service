// SUU-218: 빈 페이지. 제목만, 내용은 나중에.
// SUU-237: public/echo-stats.json 을 읽어 타일 4개 · Subpart 표(정렬·제조업 필터) · 연도별 차트.
"use client";

import { useEffect, useState } from "react";
import { Bar } from "@/components/charts/bar";
import { BarChart } from "@/components/charts/bar-chart";
import { BarXAxis } from "@/components/charts/bar-x-axis";
import { BarYAxis } from "@/components/charts/bar-y-axis";
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
  deviation_y_pct: number;
};

type EchoStats = {
  summary: {
    facilities: number;
    mfg_facilities: number;
    violation_facility_pct: number;
    penalty_count: number;
    penalty_median_usd: number | null;
    deviation_y_pct: number;
  };
  subparts: Subpart[];
  yearly: { year: number; violations: number; penalties: number }[];
};

type NumericKey = Exclude<keyof Subpart, "code" | "desc">;

const COLUMNS: { key: NumericKey; label: string }[] = [
  { key: "facilities", label: "시설 수" },
  { key: "mfg_facilities", label: "제조업" },
  { key: "violation_facility_pct", label: "위반 시설 %" },
  { key: "penalty_count", label: "벌금 건수" },
  { key: "penalty_median_usd", label: "벌금 중앙값" },
  { key: "deviation_y_pct", label: "deviation %" },
];

const num = (v: number) => v.toLocaleString("en-US");
const usd = (v: number | null) => (v === null ? "—" : `$${num(Math.floor(v))}`);
const pct = (v: number) => `${v.toFixed(1)}%`;
// "MACT Part 63 - Subpart ZZZZ - STATIONARY ..." → "STATIONARY ..."
const shortDesc = (desc: string) => desc.replace(/^MACT Part 63 - Subpart \S+ - /, "");

function cell(key: NumericKey, value: number | null) {
  if (key === "penalty_median_usd") return usd(value);
  if (value === null) return "—";
  return key.endsWith("_pct") ? pct(value) : num(value);
}

export default function EchoPage() {
  const [stats, setStats] = useState<EchoStats | null>(null);
  const [error, setError] = useState(false);
  const [mfgOnly, setMfgOnly] = useState(false);
  const [sortKey, setSortKey] = useState<NumericKey | null>(null);

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
      return bv - av;
    });
  }

  return (
    <main className="flex flex-1 flex-col px-6 py-6">
      <h1 className="text-center text-[28px] font-bold text-ink">EPA ECHO</h1>
      <p className="mt-1 text-center text-sm text-ink-muted">Part 63 (NESHAP) 적용 시설의 위반 · 벌금 통계</p>
      {error ? <p className="mt-4 text-center text-sm text-ink-muted">불러오지 못했습니다.</p> : null}
      {stats ? (
        <div className="mx-auto mt-6 w-full max-w-5xl">
          <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
            <Tile id="facilities" label="Part 63 시설" value={num(stats.summary.facilities)} />
            <Tile id="violation-pct" label="위반 이력 시설 %" value={pct(stats.summary.violation_facility_pct)} />
            <Tile id="penalty-median" label="벌금 중앙값 (2015~)" value={usd(stats.summary.penalty_median_usd)} />
            <Tile id="deviation-pct" label="Title V deviation %" value={pct(stats.summary.deviation_y_pct)} />
          </div>

          <section className="mt-10">
            <h2 className="text-lg font-semibold text-ink">연도별 위반 · 벌금 건수</h2>
            <div data-chart="yearly" className="mt-3">
              <BarChart data={stats.yearly} xDataKey="year" aspectRatio="3 / 1">
                <Grid horizontal vertical={false} />
                <BarXAxis />
                <BarYAxis />
                <Bar dataKey="violations" fill="var(--chart-1)" />
                <Bar dataKey="penalties" fill="var(--chart-3)" />
                <ChartTooltip />
              </BarChart>
            </div>
            <p className="mt-1 text-xs text-ink-muted">진한 색: 위반 (FRV 시작일 기준) · 연한 색: 벌금 처분</p>
          </section>

          <section className="mt-10">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-ink">Subpart 별</h2>
              <label className="flex items-center gap-2 text-sm text-ink">
                <input type="checkbox" checked={mfgOnly} onChange={(e) => setMfgOnly(e.target.checked)} />
                제조업만
              </label>
            </div>
            <table className="mt-3 w-full border-collapse text-left text-sm">
              <thead className="border-b border-hairline text-ink-muted">
                <tr>
                  <th className="px-3 py-3 font-medium">Subpart</th>
                  <th className="px-3 py-3 font-medium">설명</th>
                  {COLUMNS.map((c) => (
                    <th key={c.key} className="px-3 py-3 text-right font-medium whitespace-nowrap">
                      <button
                        type="button"
                        onClick={() => setSortKey(c.key)}
                        className={sortKey === c.key ? "font-semibold text-ink" : "hover:text-ink"}
                      >
                        {c.label}
                        {sortKey === c.key ? " ↓" : ""}
                      </button>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-hairline">
                {rows.map((s) => (
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
          </section>
        </div>
      ) : null}
    </main>
  );
}

function Tile({ id, label, value }: { id: string; label: string; value: string }) {
  return (
    <div data-testid={`tile-${id}`} className="rounded-xl border border-hairline p-4">
      <div className="text-sm text-ink-muted">{label}</div>
      <div className="mt-1 text-2xl font-bold text-ink tabular-nums">{value}</div>
    </div>
  );
}
