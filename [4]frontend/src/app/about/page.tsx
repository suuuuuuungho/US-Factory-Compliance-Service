import aboutStats from "../../../public/about-stats.json";
import AboutCharts from "./AboutCharts";

const { stats, series } = aboutStats;
type StatKey = keyof typeof stats;

function Stat({ name, label }: { name: StatKey; label?: string }) {
  const item = stats[name];
  return <div className="min-w-0"><span data-stat={name} data-value={String(item.value)} className="block font-serif text-4xl text-ink sm:text-5xl">{label ?? item.value.toLocaleString("en-US")}</span><small className="block text-xs leading-relaxed text-ink-muted">{item.cite}</small></div>;
}
function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return <section className="space-y-8 border-t border-hairline pt-10 sm:pt-14"><h2 className="font-serif text-3xl text-ink sm:text-5xl">{title}</h2>{children}</section>;
}
function Chart({ name, title, cite, children }: { name: string; title: string; cite?: string; children?: React.ReactNode }) {
  return <figure data-chart={name} className="min-w-0 space-y-3 border-t border-hairline-soft pt-5"><figcaption className="text-sm text-ink">{title}</figcaption>{name === "obligation-timeline" ? <svg viewBox="0 0 600 220" role="img" aria-label={title} className="h-auto w-full">{children}</svg> : <AboutCharts name={name} />}{cite && <p className="text-xs text-ink-muted">Source: {cite}</p>}</figure>;
}

export default function AboutPage() {
  const letters = series.letters_by_year;
  return <main className="flex-1 px-6 py-16 sm:px-10"><div className="mx-auto max-w-5xl space-y-24 sm:space-y-32">
    <header className="space-y-8"><p className="text-xs uppercase tracking-widest text-ink-muted">About / the signature</p>
      <h1 className="max-w-4xl font-serif text-4xl leading-tight text-ink sm:text-6xl">Every year, someone at your plant signs a legal statement that the plant followed {stats.part63_pages.value} pages of rules no one there has read in full.</h1>
      <p className="max-w-2xl text-lg leading-relaxed text-ink-muted">The rules changed {stats.rule_changes.value} times since 2018. A false certification can mean up to {stats.prison_years.value} years in prison.</p>
      <div className="grid gap-8 border-t border-hairline pt-8 sm:grid-cols-3"><Stat name="part63_pages" /><Stat name="rule_changes" /><Stat name="prison_years" /></div>
    </header>
    <Section title="The signature"><p className="text-ink-muted">Across a five-year Title V permit term, reporting continues between signatures. Deviations can require notice within hours.</p>
      <Chart name="obligation-timeline" title="A five-year permit term" cite="40 CFR 70.6(a)(3)(iii)(A), 70.6(c)(5), 70.5(d), 71.6(a)(3)(iii)(B), 70.5(a)(1)(iii); CAA §113(c)(2)"><line x1="50" x2="560" y1="95" y2="95" stroke="#777" />{Array.from({ length: 11 }, (_, i) => <g key={i}><circle cx={50 + i * 51} cy="95" r="4" fill="#eee" />{i % 2 === 0 && <text x={45 + i * 51} y="125" fill="#aaa" fontSize="11">{i / 2}</text>}</g>)}<text x="50" y="30" fill="#aaa" fontSize="12">10 semiannual reports · 5 annual certifications</text><text x="250" y="155" fill="#aaa" fontSize="12">1 renewal, 6–18 months before expiry</text><text x="50" y="195" fill="#aaa" fontSize="12">Unscheduled: 24h / 48h notices</text></Chart>
    </Section>
    <Section title="Why no one can answer it"><div className="space-y-14">
      <div className="space-y-4"><h3 className="font-serif text-2xl text-ink">Too big to hold in context</h3><div className="grid gap-6 sm:grid-cols-2"><Stat name="part63_tokens_max" /><Stat name="llm_context_tokens" /></div><Chart name="corpus-size" title="Part 63 tokens versus model context" cite={stats.part63_tokens_max.cite}></Chart></div>
      <div className="space-y-4"><h3 className="font-serif text-2xl text-ink">It keeps changing</h3><div className="grid gap-6 sm:grid-cols-2"><Stat name="rule_changes" /><Stat name="sections_changed_pct" label={`${stats.sections_changed_pct.value}%`} /></div><Chart name="rule-changes-by-year" title="Part 63 rules published by year" cite={series.rule_changes_by_year.cite}></Chart><Chart name="sections-changed" title="Share of sections changed" cite={stats.sections_changed_pct.cite}></Chart></div>
      <div className="space-y-4"><h3 className="font-serif text-2xl text-ink">Help arrives too slowly</h3><p className="text-ink-muted">In a sample of {stats.epa_letters_sample.value} letters, the median EPA response took:</p><Stat name="epa_median_days" /><Chart name="epa-wait" title="Notice windows versus median response" cite={stats.epa_median_days.cite}></Chart></div>
    </div></Section>
    <Section title={`The same question, ${stats.letters_total.value.toLocaleString("en-US")} times`}><p className="text-ink-muted">EPA determination letters show how often a facility asked whether a rule applied. This series groups letters by date.</p><Stat name="letters_total" /><Chart name="letters-by-year" title="Part 63 determination letters, 1993–2025" cite={letters.cite}></Chart><p className="text-xs text-ink-muted">{letters.before_1993} letters before 1993; {letters.unknown} without a usable date.</p></Section>
    <Section title="The cost of a wrong answer"><p className="text-ink-muted">Among {stats.facilities.value.toLocaleString("en-US")} ECHO facilities, violation records carry real costs. Penalties can accrue per day, per violation (CAA §113(b)).</p><div className="grid gap-6 sm:grid-cols-3"><Stat name="violation_pct" label={`${stats.violation_pct.value}%`} /><Stat name="penalty_total_usd" label={`$${(stats.penalty_total_usd.value / 1000000).toFixed(1)}M`} /><Stat name="penalty_max_usd" label={`$${stats.penalty_max_usd.value / 1000000}M`} /></div><Chart name="violation-share" title="Facilities with a violation record" cite={stats.violation_pct.cite}></Chart><Chart name="penalty-by-subpart" title="Recorded penalties by subpart" cite={series.penalty_by_subpart.cite}></Chart></Section>
    <Section title="How we solved it: RAG"><p className="text-ink-muted">Retrieval augmented generation narrows the rule text first, then builds an answer with citations. Measured on {stats.rag_eval_cases.value} real EPA questions.</p><div className="grid gap-6 sm:grid-cols-3"><Stat name="rag_chunks" /><Stat name="rag_eval_cases" /><Stat name="rag_hit20_pct" label={`${stats.rag_hit20_pct.value}%`} /></div>
      <div className="grid border-y border-hairline sm:grid-cols-2">{[["Too big", `${stats.rag_chunks.value.toLocaleString("en-US")} searchable chunks and Hit@20 retrieval.`], ["Too slow", `nDCG rose from ${series.rag_ndcg_steps.data[0].ndcg} to ${series.rag_ndcg_steps.data.at(-1)?.ndcg} with reranking.`], ["A signature needs evidence", "Cited rule text and measured citation grounding."], ["Rules change", "Source date, eCFR link, and connected Federal Register amendment."]].map(([problem, solution]) => <div key={problem} className="border-b border-hairline-soft p-5 sm:odd:border-r"><p className="text-xs uppercase tracking-widest text-ink-muted">{problem}</p><p className="mt-3 text-ink">{solution}</p></div>)}</div>
      <Chart name="rag-ndcg-steps" title="Retrieval quality by iteration" cite={series.rag_ndcg_steps.cite}></Chart>
      <Chart name="rag-funnel" title="From chunks to answer context" cite={series.rag_funnel.cite}></Chart>
      <Chart name="rag-scores" title="Hit@20 and citation grounding" cite={stats.rag_citation_grounded_pct.cite}></Chart>
      <div className="grid gap-6 sm:grid-cols-2"><Stat name="rag_subpart_pct" label={`${stats.rag_subpart_pct.value}%`} /><Stat name="rag_citation_grounded_pct" label={`${stats.rag_citation_grounded_pct.value}%`} /></div>
      <blockquote className="border-l border-ink pl-6 font-serif text-2xl leading-snug text-ink">A general AI answers from memory. We answer from the current rule text, and show you the line.</blockquote>
    </Section>
    <Section title="What you get"><ul className="grid gap-4 sm:grid-cols-2">{["Candidate sections that may apply", "The criteria and cited rule text", "A checklist to confirm at your facility", "Similar EPA precedents", "Recent amendment indicators"].map((x) => <li key={x} className="border-t border-hairline-soft pt-3 text-ink-muted">{x}</li>)}</ul></Section>
    <Section title="What we don't do"><p className="text-ink-muted">We do not make a final applicability determination or give legal advice. Verify the cited text with qualified advisors before signing.</p></Section>
    <Section title="Also for regulators"><p className="text-ink-muted">The cited trail helps reviewers see which rule and precedent informed a facility&apos;s question.</p></Section>
    <Section title="Sources"><dl className="grid gap-5 sm:grid-cols-2">{[["eCFR", "40 CFR Part 63 text"], ["Federal Register", "Amendments and effective dates"], ["ECHO", "Facility compliance records"], ["ADI", "EPA applicability decisions"]].map(([name, desc]) => <div key={name} className="border-t border-hairline-soft pt-3"><dt className="text-ink">{name}</dt><dd className="text-sm text-ink-muted">{desc}</dd></div>)}</dl></Section>
    <Section title="Disclaimer"><p className="text-sm text-ink-muted">This service is not legal advice and does not make final applicability determinations. Check every citation against the governing text before relying on it.</p></Section>
  </div></main>;
}
