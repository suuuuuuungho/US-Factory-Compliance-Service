"use client";

import aboutStats from "../../../public/about-stats.json";
import { BarChart } from "@/components/charts/bar-chart";
import { Bar } from "@/components/charts/bar";
import { BarXAxis } from "@/components/charts/bar-x-axis";
import { BarYAxis } from "@/components/charts/bar-y-axis";
import { FunnelChart } from "@/components/charts/funnel-chart";
import { RingChart } from "@/components/charts/ring-chart";
import { Ring } from "@/components/charts/ring";

const { stats, series } = aboutStats;
const color = "var(--color-gradient-violet)";

function Bars({ data, keyName = "name", horizontal = false }: {
  data: Record<string, unknown>[];
  keyName?: string;
  horizontal?: boolean;
}) {
  return <BarChart data={data} xDataKey={keyName} orientation={horizontal ? "horizontal" : "vertical"} aspectRatio={horizontal ? "2 / 1" : "2 / 1"} margin={horizontal ? { left: 100, right: 20 } : { bottom: 55 }} animationDuration={0}>
    {horizontal ? <BarYAxis /> : <BarXAxis />}
    <Bar dataKey="value" fill={color} />
  </BarChart>;
}

function Progress({ data }: { data: { label: string; value: number; maxValue: number }[] }) {
  return <RingChart data={data} animationDuration={0} className="mx-auto max-w-sm">
    {data.map((_, index) => <Ring key={index} index={index} animate={false} showGlow={false} />)}
  </RingChart>;
}

export default function AboutCharts({ name }: { name: string }) {
  switch (name) {
    case "corpus-size":
      return <Bars horizontal data={[
        { name: "Part 63", value: stats.part63_tokens_max.value },
        { name: "Model context", value: stats.llm_context_tokens.value },
      ]} />;
    case "rule-changes-by-year":
      return <Bars keyName="year" data={series.rule_changes_by_year.data.map((row) => ({ year: String(row.year), value: row.count }))} />;
    case "sections-changed":
      return <Progress data={[{ label: "Sections changed", value: stats.sections_changed_pct.value, maxValue: 100 }]} />;
    case "epa-wait":
      return <Bars horizontal data={[
        { name: "24h notice", value: 24 },
        { name: "48h notice", value: 48 },
        { name: "EPA median", value: stats.epa_median_days.value * 24 },
      ]} />;
    case "letters-by-year":
      return <Bars keyName="year" data={series.letters_by_year.data.map((row) => ({ year: String(row.year), value: row.count }))} />;
    case "violation-share":
      return <Progress data={[{ label: "Facilities with violations", value: stats.violation_pct.value, maxValue: 100 }]} />;
    case "penalty-by-subpart":
      return <Bars horizontal data={series.penalty_by_subpart.data.map((row) => ({ name: row.code, value: row.penalty_total_usd }))} />;
    case "rag-ndcg-steps":
      return <Bars data={series.rag_ndcg_steps.data.map((row) => ({ name: row.step, value: row.ndcg }))} />;
    case "rag-funnel":
      return <FunnelChart data={series.rag_funnel.data.map((row) => ({ label: row.stage, value: row.count }))} color={color} />;
    case "rag-scores":
      return <Progress data={[
        { label: "Hit@20", value: stats.rag_hit20_pct.value, maxValue: 100 },
        { label: "Grounded citations", value: stats.rag_citation_grounded_pct.value, maxValue: 100 },
      ]} />;
    default:
      return null;
  }
}
