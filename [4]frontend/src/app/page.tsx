"use client";
// SUU-163: 질문 → POST /ask → 후보 Subpart 카드 + 체크리스트. 디자인 없음.
// SUU-172: className만 Framer 토큰(bg-surface-1, rounded-full 등)으로. 기능 동일.
// SUU-171: h1을 히어로(display-lg 근사)로. 상단바는 layout의 TopNav.
// SUU-164: 인용 버튼 → GET /section/{key} → 옆 패널(aside)에 조문 전문. 같은 조문은 캐시.
import { useRef, useState } from "react";
import {
  ask,
  citationToSectionKey,
  getSection,
  type AskResult,
  type Section,
} from "../lib/api";

export default function Home() {
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AskResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [section, setSection] = useState<Section | null>(null);
  const [sectionError, setSectionError] = useState<string | null>(null);
  const sectionCache = useRef<Record<string, Section>>({});

  async function openSection(key: string) {
    setSectionError(null);
    const cached = sectionCache.current[key];
    if (cached) return setSection(cached);
    try {
      const s = await getSection(key);
      sectionCache.current[key] = s;
      setSection(s);
    } catch (err) {
      setSection(null);
      setSectionError(err instanceof Error ? err.message : String(err));
    }
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setResult(null);
    setError(null);
    try {
      setResult(await ask(question));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-1">
      <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-6 p-8">
        <h1 className="text-5xl font-medium leading-none tracking-[-0.05em] text-ink md:text-6xl">
          US FACTORY COMPLIANCE AI SERVICE
        </h1>
        <p className="text-lg text-ink-muted">
          40 CFR Part 63 applicability criteria, with the sections to check.
        </p>
        <form onSubmit={onSubmit} className="flex flex-col gap-2">
          <textarea
            className="rounded-md border border-hairline bg-surface-1 p-3 text-ink placeholder:text-ink-muted focus:border-accent-blue focus:outline-none"
            rows={3}
            placeholder="Describe the process, e.g. we solvent weld plastic parts"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
          />
          <button
            type="submit"
            disabled={loading}
            className="self-start rounded-full bg-primary px-5 py-2.5 text-sm font-medium text-on-primary disabled:opacity-50"
          >
            Ask
          </button>
        </form>

        {loading && <p role="status">Searching the regulations… (10–20 s)</p>}
        {error && <p className="text-red-400">{error}</p>}

        {result && result.answer === null && (
          <ul className="list-disc pl-6">
            {result.issues.map((issue) => (
              <li key={issue}>{issue}</li>
            ))}
          </ul>
        )}

        {result?.answer?.candidates.map((c) => (
          <section
            key={c.subpart}
            className="rounded-lg border border-hairline bg-surface-1 p-5"
          >
            <h2 className="font-semibold">
              Subpart {c.subpart} — {c.title}
            </h2>
            <ul className="list-disc pl-6">
              {c.criteria.map((cr, i) => (
                <li key={i}>
                  {cr.criterion}{" "}
                  {cr.citations.map((cit) => {
                    const key = citationToSectionKey(cit);
                    return key ? (
                      <button
                        key={cit}
                        type="button"
                        onClick={() => openSection(key)}
                        className="mr-2 text-sm text-accent-blue underline"
                      >
                        {cit}
                      </button>
                    ) : (
                      <span key={cit} className="mr-2 text-sm text-ink-muted">
                        {cit}
                      </span>
                    );
                  })}
                </li>
              ))}
            </ul>
          </section>
        ))}

        {result?.answer && (
          <section className="rounded-lg border border-hairline bg-surface-1 p-5">
            <h2 className="font-semibold">Checklist</h2>
            <ul className="list-disc pl-6">
              {result.answer.checklist.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </section>
        )}

        <p className="mt-auto text-sm text-ink-muted">
          This is not a final applicability determination. The plant decides;
          this page gives the criteria and where to look.
        </p>
      </main>
      {(section || sectionError) && (
        <aside
          aria-label="Section text"
          className="w-full max-w-md border-l border-hairline bg-surface-1 p-8"
        >
          {section && (
            <>
              <h2 className="font-semibold">
                {section.section_key} (Subpart {section.subpart})
              </h2>
              <pre className="whitespace-pre-wrap font-sans text-sm">
                {section.text}
              </pre>
            </>
          )}
          {sectionError && <p className="text-red-400">{sectionError}</p>}
        </aside>
      )}
    </div>
  );
}
