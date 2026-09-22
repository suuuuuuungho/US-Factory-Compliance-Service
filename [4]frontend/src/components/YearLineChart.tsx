// SUU-249: 연도별 꺾은선. Bklit AreaChart 는 날짜(월/일) 전용이라 연도 라벨이 안 나와서 @visx/shape·scale 로 직접 그린다.
"use client";

import { useState } from "react";
import { LinePath } from "@visx/shape";
import { curveMonotoneX } from "@visx/curve";
import { scaleLinear } from "@visx/scale";

export type YearSeries = { key: string; label: string; color: string };

type Props = {
  data: Record<string, number>[];
  series: YearSeries[];
  format?: (v: number) => string;
};

const W = 600;
const H = 300;
const M = { top: 16, right: 16, bottom: 28, left: 56 };

export function YearLineChart({ data, series, format = (v) => v.toLocaleString("en-US") }: Props) {
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);
  if (data.length === 0) return null;

  const years = data.map((d) => d.year);
  const maxY = Math.max(1, ...data.flatMap((d) => series.map((s) => d[s.key] ?? 0)));
  const x = scaleLinear({ domain: [years[0], years[years.length - 1]], range: [M.left, W - M.right] });
  const y = scaleLinear({ domain: [0, maxY], range: [H - M.bottom, M.top], nice: true });
  const yTicks = y.ticks(4);
  const xTicks = years.filter((yr) => yr % 5 === 0);

  const onMove = (e: React.MouseEvent<SVGSVGElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const px = ((e.clientX - rect.left) / rect.width) * W;
    const year = Math.round(x.invert(px));
    const i = years.indexOf(Math.min(years[years.length - 1], Math.max(years[0], year)));
    setHoverIndex(i < 0 ? null : i);
  };

  const hover = hoverIndex === null ? null : data[hoverIndex];

  return (
    <div>
      {series.length > 1 ? (
        <div data-testid="line-legend" className="mb-1 flex justify-end gap-4 text-xs text-ink-muted">
          {series.map((s) => (
            <span key={s.key} className="flex items-center gap-1.5">
              <span className="inline-block h-0.5 w-4" style={{ backgroundColor: s.color }} />
              {s.label}
            </span>
          ))}
        </div>
      ) : null}
      <svg viewBox={`0 0 ${W} ${H}`} className="block h-auto w-full" onMouseMove={onMove} onMouseLeave={() => setHoverIndex(null)}>
        {yTicks.map((t) => (
          <g key={t}>
            <line x1={M.left} x2={W - M.right} y1={y(t)} y2={y(t)} stroke="currentColor" strokeOpacity={0.12} strokeDasharray="3 3" />
            <text x={M.left - 8} y={y(t)} dy="0.32em" textAnchor="end" fontSize={11} fill="currentColor" fillOpacity={0.6}>
              {format(t)}
            </text>
          </g>
        ))}
        {xTicks.map((yr) => (
          <text key={yr} x={x(yr)} y={H - 8} textAnchor="middle" fontSize={11} fill="currentColor" fillOpacity={0.6}>
            {yr}
          </text>
        ))}
        {series.map((s) => (
          <LinePath<Record<string, number>>
            key={s.key}
            data={data}
            x={(d) => x(d.year)}
            y={(d) => y(d[s.key] ?? 0)}
            curve={curveMonotoneX}
            stroke={s.color}
            strokeWidth={2}
            data-series={s.key}
          />
        ))}
        {hover ? (
          <g>
            <line x1={x(hover.year)} x2={x(hover.year)} y1={M.top} y2={H - M.bottom} stroke="currentColor" strokeOpacity={0.3} />
            {series.map((s) => (
              <circle key={s.key} cx={x(hover.year)} cy={y(hover[s.key] ?? 0)} r={4} fill={s.color} />
            ))}
          </g>
        ) : null}
      </svg>
      <p data-testid="line-hover" className="mt-1 h-5 text-center text-sm text-ink tabular-nums">
        {hover ? `${hover.year} · ${series.map((s) => `${s.label} ${format(hover[s.key] ?? 0)}`).join(" · ")}` : " "}
      </p>
    </div>
  );
}
