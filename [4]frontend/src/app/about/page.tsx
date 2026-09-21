// SUU-217: About. 무엇을 하고 / 안 하는지, 어떻게 돌아가는지, 데이터 출처, 면책. 제목·숫자·인용구는 New York(font-serif), 본문은 SF Pro(기본).

const problems = [
  ["Part 63 is vast.", "Hundreds of subparts. Finding the handful that touch your plant is the hard part."],
  ["Rules keep changing.", "Amendments land every year, and nobody on the floor has time to track them."],
  ["The vocabulary is legal, not operational.", "“Affected source” and “major source” don’t sound like anything you run."],
  ["Wrong calls are expensive.", "Misapplying a subpart means penalties, rework, and a certification with your name on it."],
];

const does = [
  "Candidate Part 63 sections that may apply to your plant",
  "The criteria that decide applicability, with the CFR text behind each one",
  "A checklist of what to confirm at your facility",
  "Prior EPA applicability determinations on similar cases",
  "Whether the cited section was recently amended",
];

const doesNot = [
  "A final applicability determination",
  "Legal advice, or anything you should sign without reading the source",
];

const steps = [
  ["Describe your plant", "Processes, materials, emission units — in your own words."],
  ["We search the rule text", "Retrieval over the current 40 CFR Part 63, so answers come from the regulation, not from memory."],
  ["You get candidates, criteria, checklist", "Every item carries its section citation. You verify; you decide."],
];

const sources = [
  ["eCFR", "The current text of 40 CFR Part 63"],
  ["Federal Register", "Amendments and their effective dates"],
  ["ECHO", "EPA enforcement and compliance history by facility"],
  ["ADI", "Applicability Determination Index — past EPA applicability decisions"],
];

function H2({ children }: { children: string }) {
  return <h2 className="font-serif text-3xl leading-tight text-ink">{children}</h2>;
}

export default function AboutPage() {
  return (
    <main className="flex-1 px-6 py-16">
      <div className="mx-auto flex max-w-3xl flex-col gap-20">
        <header className="flex flex-col gap-5">
          <p className="text-xs font-medium uppercase tracking-[0.18em] text-ink-muted">About</p>
          <h1 className="font-serif text-3xl leading-tight tracking-[-0.01em] text-ink sm:text-4xl">
            Questions and evidence, not verdicts.
          </h1>
          <p className="max-w-2xl text-lg leading-relaxed text-ink-muted">
            A service for environmental staff at US manufacturing plants. It finds which 40 CFR Part 63
            sections may apply to your facility, shows the criteria that decide it, and points to the text
            that backs it up.
          </p>
        </header>

        <section className="flex flex-col gap-4">
          <H2>Who it&apos;s for</H2>
          <p className="text-base leading-relaxed text-ink-muted">
            Environmental and regulatory staff preparing a Title V air permit. You know the plant floor; you
            may not know the regulatory vocabulary. Outside counsel for every question is out of reach.
          </p>
        </section>

        <section className="flex flex-col gap-6">
          <H2>Why it&apos;s hard</H2>
          <ol className="grid gap-6 sm:grid-cols-2">
            {problems.map(([title, body], i) => (
              <li key={title} className="flex flex-col gap-2 border-t border-hairline pt-4">
                <span className="font-serif text-2xl text-ink-muted">0{i + 1}</span>
                <p className="font-medium text-ink">{title}</p>
                <p className="text-sm leading-relaxed text-ink-muted">{body}</p>
              </li>
            ))}
          </ol>
        </section>

        <section className="flex flex-col gap-6">
          <H2>What we do — and don&apos;t</H2>
          <div className="grid gap-8 sm:grid-cols-2">
            <div className="flex flex-col gap-3">
              <p id="about-do" className="text-xs font-medium uppercase tracking-[0.18em] text-semantic-success">
                What we do
              </p>
              <ul aria-labelledby="about-do" className="flex flex-col gap-2">
                {does.map((t) => (
                  <li key={t} className="border-l border-semantic-success pl-3 text-sm leading-relaxed text-ink">
                    {t}
                  </li>
                ))}
              </ul>
            </div>
            <div className="flex flex-col gap-3">
              <p id="about-dont" className="text-xs font-medium uppercase tracking-[0.18em] text-ink-muted">
                What we don&apos;t do
              </p>
              <ul aria-labelledby="about-dont" className="flex flex-col gap-2">
                {doesNot.map((t) => (
                  <li key={t} className="border-l border-hairline pl-3 text-sm leading-relaxed text-ink-muted">
                    {t}
                  </li>
                ))}
              </ul>
            </div>
          </div>
          <blockquote className="border-t border-hairline pt-6 font-serif text-lg italic leading-snug text-ink">
            We don&apos;t tell you the answer. We tell you where to look and what to confirm.
          </blockquote>
        </section>

        <section className="flex flex-col gap-6">
          <H2>How it works</H2>
          <ol className="grid gap-4 sm:grid-cols-3">
            {steps.map(([title, body], i) => (
              <li key={title} className="flex flex-col gap-2 rounded-lg bg-surface-1 p-5">
                <span className="font-serif text-3xl text-accent-blue">0{i + 1}</span>
                <p className="font-medium text-ink">{title}</p>
                <p className="text-sm leading-relaxed text-ink-muted">{body}</p>
              </li>
            ))}
          </ol>
        </section>

        <section className="flex flex-col gap-6">
          <H2>Data sources</H2>
          <dl className="grid gap-x-8 gap-y-4 sm:grid-cols-[auto_1fr]">
            {sources.map(([name, desc]) => (
              <div key={name} className="contents">
                <dt className="font-medium text-ink">{name}</dt>
                <dd className="text-sm leading-relaxed text-ink-muted">{desc}</dd>
              </div>
            ))}
          </dl>
        </section>

        <section className="flex flex-col gap-3 border-t border-hairline pt-8">
          <H2>Disclaimer</H2>
          <p className="text-sm leading-relaxed text-ink-muted">
            This service is not legal advice and does not make applicability determinations. Final decisions
            rest with the facility and its qualified advisors. Always read the cited section before relying on
            it.
          </p>
        </section>
      </div>
    </main>
  );
}
