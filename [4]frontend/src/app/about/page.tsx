// About: 공장 담당자가 보는 서비스 소개. 문제 → 주는 것/안 주는 것 → 원칙 → 동작 → 검증 → 출처 → 고지.
// 글꼴은 DESIGN.md 그대로: 제목·큰 숫자는 New York(font-serif), 나머지는 SF Pro(body 기본).
// 색: 인용 조문만 accent-blue(eCFR 링크), 색 있는 면은 "What you get" 보라 카드 하나뿐.
import Link from "next/link";

const ECFR = "https://www.ecfr.gov/current/title-40";

const FILINGS = [
  { name: "Semiannual monitoring report", when: "Every 6 months", cite: "40 CFR 70.6(a)(3)(iii)(A)", href: `${ECFR}/section-70.6#p-70.6(a)(3)(iii)(A)` },
  { name: "Annual compliance certification", when: "Every year, signed by a responsible official", cite: "40 CFR 70.6(c)(5), 70.5(d)", href: `${ECFR}/section-70.6#p-70.6(c)(5)` },
  { name: "Deviation report", when: "Promptly after any exceedance; 24 or 48 hours under the federal program", cite: "40 CFR 70.6(a)(3)(iii)(B), 71.6(a)(3)(iii)(B)", href: `${ECFR}/section-70.6#p-70.6(a)(3)(iii)(B)` },
  { name: "Permit renewal", when: "Every 5 years, filed 6 to 18 months before expiry", cite: "40 CFR 70.6(a)(2), 70.5(a)(1)(iii)", href: `${ECFR}/section-70.5#p-70.5(a)(1)(iii)` },
];

const HARD = [
  { value: "957", unit: "pages", label: "40 CFR Part 63 runs 3.3 million words. Too large to read, too large for any AI model's context window." },
  { value: "136", unit: "amendments", label: "Final rules changed Part 63 between 2018 and 2025. More than one a month." },
  { value: "45%", unit: "of sections changed", label: "1,126 sections were rewritten in that period. Last year's answer can be wrong this year." },
  { value: "101", unit: "days", label: "Median wait for an EPA applicability determination. More than 1 in 4 take over 6 months." },
];

const COST = [
  { value: "27.9%", label: "of the 49,618 Part 63 facilities have a violation on record. This is routine, not rare." },
  { value: "$958.8M", label: "in penalties across 9,998 enforcement actions since 2015." },
  { value: "$100M", label: "the largest single penalty. Median is $9,098, but the fine is not the real cost." },
];

const COST_RISKS = [
  { text: "You sign the annual certification personally, stating it is true, accurate, and complete. A wrong basis is your liability.", cite: "40 CFR 70.5(d)", href: `${ECFR}/section-70.5#p-70.5(d)` },
  { text: "A late or incomplete renewal ends your right to operate the day the permit expires.", cite: "40 CFR 70.7(c)(1)(ii)", href: `${ECFR}/section-70.7#p-70.7(c)(1)(ii)` },
];

const WE_GIVE = [
  "Candidate subparts that may apply to your process",
  "The criteria that decide applicability, each with its citation",
  "A checklist of what you must confirm on site",
  "Similar past EPA determinations",
  "Whether the cited sections were recently amended",
];

const WE_NEVER = ["A final applicability determination", "Legal advice", "A sentence without a citation"];

const STEPS = [
  { n: "1", title: "Ask in your own words", body: "“Paint line, 12 tons of solvent a year.” No legal terms needed." },
  { n: "2", title: "Search all 5,625 sections", body: "Every section of Part 63, kept current with the eCFR." },
  { n: "3", title: "Rank with a legal-trained model", body: "The most relevant sections rise to the top." },
  { n: "4", title: "Answer with citations", body: "Criteria, checklist, and the exact section for each one." },
];

const TESTED = [
  { value: "93%", label: "Correct section in the top 5" },
  { value: "99.6%", label: "Citations traceable to the retrieved text" },
  { value: "0.95", label: "Faithfulness score (RAGAS)" },
];

const SOURCES = [
  { name: "eCFR", what: "The current text of 40 CFR Part 63. Every citation links here." },
  { name: "Federal Register", what: "Every rule change, so you know when a cited section was amended." },
  { name: "EPA ECHO", what: "Real inspections, violations, and penalties at facilities like yours." },
  { name: "EPA ADI and CAA Dashboard", what: "Past EPA applicability determinations, used as precedent." },
];

const EYEBROW = "text-[13px] font-medium uppercase tracking-[0.08em] text-ink-muted";
const H2 = "font-serif text-[32px] font-medium leading-[1.13] tracking-[-1px] text-ink";
const BODY = "text-[15px] leading-[1.4] tracking-[-0.15px] text-ink-muted";
const CITE = "text-[13px] font-medium tracking-[-0.13px] text-accent-blue hover:underline";
const SECTION = "mx-auto w-full max-w-[1100px] px-6 py-16 sm:px-10 md:py-24";

export default function AboutPage() {
  return (
    <main className="flex-1">
      {/* 1. Hero */}
      <section className={`${SECTION} pt-20 md:pt-32`}>
        <p className={EYEBROW}>About</p>
        <h1 className="mt-4 max-w-4xl font-serif text-[40px] font-medium leading-[1.0] tracking-[-2px] text-ink text-balance md:text-[62px] md:tracking-[-3.1px]">
          Find the Part 63 rules that may apply to your plant.
        </h1>
        <p className="mt-6 max-w-2xl text-[18px] leading-[1.3] tracking-[-0.18px] text-ink-muted">
          Every criterion comes with its citation. You make the call.
        </p>
      </section>

      {/* 2. Filings */}
      <section className={SECTION}>
        <p className={EYEBROW}>The problem</p>
        <h2 className={`${H2} mt-3`}>You face the same question every filing.</h2>
        <p className={`${BODY} mt-4 max-w-2xl`}>
          After a Title V permit, the law requires these documents for the next 5 years. Each time you must know
          which rules apply to your plant, and what to check.
        </p>
        <ul className="mt-10 divide-y divide-hairline-soft border-y border-hairline-soft">
          {FILINGS.map((f) => (
            <li key={f.name} className="grid gap-2 py-5 md:grid-cols-[1fr_1fr_340px] md:items-baseline md:gap-6">
              <span className="text-[18px] font-medium tracking-[-0.18px] text-ink">{f.name}</span>
              <span className={BODY}>{f.when}</span>
              <a href={f.href} target="_blank" rel="noreferrer" className={CITE}>
                {f.cite}
              </a>
            </li>
          ))}
        </ul>
      </section>

      {/* 3. Why it's hard */}
      <section className={SECTION}>
        <h2 className={H2}>Why it&rsquo;s hard to answer alone.</h2>
        <dl className="mt-10 grid gap-x-8 gap-y-12 sm:grid-cols-2">
          {HARD.map((h) => (
            <div key={h.value + h.unit}>
              <dt className="flex items-baseline gap-3">
                <span className="font-serif text-[56px] font-medium leading-none tracking-[-2.8px] text-ink md:text-[62px] md:tracking-[-3.1px]">
                  {h.value}
                </span>
                <span className="text-[15px] font-medium tracking-[-0.15px] text-ink">{h.unit}</span>
              </dt>
              <dd className={`${BODY} mt-3 max-w-md`}>{h.label}</dd>
            </div>
          ))}
        </dl>
      </section>

      {/* 3b. What a mistake costs */}
      <section className={SECTION}>
        <p className={EYEBROW}>The cost</p>
        <h2 className={`${H2} mt-3`}>What a mistake costs.</h2>
        <dl className="mt-10 grid gap-8 sm:grid-cols-3">
          {COST.map((c) => (
            <div key={c.value}>
              <dt className="font-serif text-[56px] font-medium leading-none tracking-[-2.8px] text-ink md:text-[62px] md:tracking-[-3.1px]">
                {c.value}
              </dt>
              <dd className={`${BODY} mt-3`}>{c.label}</dd>
            </div>
          ))}
        </dl>
        <ul className="mt-12 divide-y divide-hairline-soft border-y border-hairline-soft">
          {COST_RISKS.map((r) => (
            <li key={r.cite} className="grid gap-2 py-5 md:grid-cols-[1fr_220px] md:items-baseline md:gap-6">
              <span className="text-[18px] leading-[1.3] tracking-[-0.18px] text-ink">{r.text}</span>
              <a href={r.href} target="_blank" rel="noreferrer" className={CITE}>
                {r.cite}
              </a>
            </li>
          ))}
        </ul>
        <p className={`${BODY} mt-6 max-w-2xl`}>Source: EPA ECHO enforcement data, 2015 to present.</p>
      </section>

      {/* 4. What you get / What we never do */}
      <section className={SECTION}>
        <div className="grid gap-5 md:grid-cols-2">
          <div className="rounded-xxl bg-gradient-to-br from-gradient-violet to-gradient-magenta p-8">
            <p className="text-[13px] font-medium uppercase tracking-[0.08em] text-ink/70">What you get</p>
            <ul className="mt-5 space-y-3">
              {WE_GIVE.map((t) => (
                <li key={t} className="flex gap-3 text-[18px] leading-[1.3] tracking-[-0.18px] text-ink">
                  <span aria-hidden className="mt-[3px] text-semantic-success">
                    ✓
                  </span>
                  {t}
                </li>
              ))}
            </ul>
          </div>
          <div className="rounded-xxl border border-hairline bg-surface-1 p-8">
            <p className={EYEBROW}>What we never do</p>
            <ul className="mt-5 space-y-3">
              {WE_NEVER.map((t) => (
                <li key={t} className="flex gap-3 text-[18px] leading-[1.3] tracking-[-0.18px] text-ink">
                  <span aria-hidden className="mt-[3px] text-gradient-coral">
                    ✕
                  </span>
                  {t}
                </li>
              ))}
            </ul>
            <p className={`${BODY} mt-8`}>
              We don&rsquo;t give you the answer. We give you the questions and the evidence you need to reach it.
            </p>
          </div>
        </div>
      </section>

      {/* 5. Two rules */}
      <section className={SECTION}>
        <p className={EYEBROW}>Our two rules</p>
        <div className="mt-6 grid gap-10 md:grid-cols-2">
          <div>
            <h2 className={H2}>We don&rsquo;t decide.</h2>
            <p className={`${BODY} mt-4`}>
              A determination is legal advice. If you sign on a wrong one, the liability is yours. So the answer
              format has no &ldquo;applies&rdquo; field at all. The promise is kept by structure, not by a disclaimer.
            </p>
          </div>
          <div>
            <h2 className={H2}>Nothing without a citation.</h2>
            <p className={`${BODY} mt-4`}>
              Every criterion carries a section like{" "}
              <a href={`${ECFR}/part-63`} target="_blank" rel="noreferrer" className={CITE}>
                40 CFR 63.xxxx(a)
              </a>
              . The text is the current eCFR, re-loaded whenever a rule changes. No section is ever made up.
            </p>
          </div>
        </div>
      </section>

      {/* 6. How it works */}
      <section className={SECTION}>
        <h2 className={H2}>How it works</h2>
        <ol className="mt-10 grid gap-8 sm:grid-cols-2 lg:grid-cols-4">
          {STEPS.map((s) => (
            <li key={s.n}>
              <span className="font-serif text-[32px] font-medium leading-none tracking-[-1px] text-ink-muted">{s.n}</span>
              <p className="mt-3 text-[18px] font-medium leading-[1.3] tracking-[-0.18px] text-ink">{s.title}</p>
              <p className={`${BODY} mt-2`}>{s.body}</p>
            </li>
          ))}
        </ol>
      </section>

      {/* 7. Tested */}
      <section className={SECTION}>
        <p className={EYEBROW}>Why you can trust it</p>
        <h2 className={`${H2} mt-3`}>Tested on 102 real EPA questions.</h2>
        <p className={`${BODY} mt-4 max-w-2xl`}>
          The test set is not invented. Each question is one a real plant asked the EPA, and the answer is the
          section the EPA cited in its determination letter. If quality drops below the line, the release is blocked.
        </p>
        <dl className="mt-10 grid gap-8 sm:grid-cols-3">
          {TESTED.map((t) => (
            <div key={t.label}>
              <dt className="font-serif text-[56px] font-medium leading-none tracking-[-2.8px] text-ink md:text-[62px] md:tracking-[-3.1px]">
                {t.value}
              </dt>
              <dd className={`${BODY} mt-3`}>{t.label}</dd>
            </div>
          ))}
        </dl>
      </section>

      {/* 8. Sources */}
      <section className={SECTION}>
        <h2 className={H2}>Where the data comes from</h2>
        <ul className="mt-10 divide-y divide-hairline-soft border-y border-hairline-soft">
          {SOURCES.map((s) => (
            <li key={s.name} className="grid gap-1 py-5 md:grid-cols-[280px_1fr] md:gap-6">
              <span className="text-[18px] font-medium tracking-[-0.18px] text-ink">{s.name}</span>
              <span className={BODY}>{s.what}</span>
            </li>
          ))}
        </ul>
      </section>

      {/* 9. Disclaimer */}
      <footer className={`${SECTION} border-t border-hairline-soft`}>
        <p className="text-[12px] leading-[1.4] tracking-[-0.12px] text-ink-muted">
          Not legal advice. Always verify the cited text before you sign.
        </p>
        <Link href="/applicability" className="mt-6 inline-block rounded-pill bg-primary px-4 py-2.5 text-[14px] font-medium tracking-[-0.14px] text-on-primary">
          Ask about your plant
        </Link>
      </footer>
    </main>
  );
}
