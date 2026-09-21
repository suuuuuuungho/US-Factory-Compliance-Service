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

// SUU-175: 카드 제목 headline(22px/700), 목록 줄 간격, 옆 패널 조문 body 크기.
// SUU-180: 카드 제목 줄만 gradient 배경, 본문은 차콜. SUU-183: 세 칸 제목 띠 전부 같은 보라.
// SUU-184: main을 화면 높이(100dvh-상단바 60px)로 고정, 2행이 남은 높이를 다 쓰고 카드 안에서 스크롤.
// SUU-188: 카드가 flex-1로 칸을 꽉 채워 세 카드 높이가 같다. 칸은 overflow-hidden, 스크롤은 카드가 한다.
const CARD = "flex-1 min-h-0 overflow-y-auto rounded-lg border border-hairline bg-surface-1";
const CARD_TITLE = "bg-gradient-violet px-5 py-3 text-[22px] font-bold leading-tight tracking-[-0.8px] text-ink";
const CARD_LIST = "list-disc space-y-3 p-5 pl-10 leading-relaxed";
const COLUMN = "flex min-h-0 flex-col gap-6 overflow-hidden";

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
    <main className="mx-auto flex w-full max-w-7xl flex-1 flex-col gap-6 p-8 md:h-[calc(100dvh-60px)] md:overflow-hidden">
      <h1 className="whitespace-nowrap text-2xl font-medium leading-none tracking-[-0.04em] text-ink sm:text-4xl md:text-[2.75rem]">
        US Factory Compliance AI Service
      </h1>
      <p className="text-lg text-accent-blue">
        40 CFR Part 63 applicability criteria, with the sections to check.
      </p>

      {/* SUU-182: 1행 = 질문 폼(3열 전부), 2행 = Subparts | Checklist | 조문. 칸마다 스크롤. */}
      <div className="grid grid-cols-1 gap-6 md:min-h-0 md:flex-1 md:grid-cols-3 md:grid-rows-[auto_minmax(0,1fr)]">
        <form onSubmit={onSubmit} className="flex flex-col gap-2 md:col-span-3">
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

        {loading && <p role="status" className="md:col-span-3">Searching the regulations… (10–20 s)</p>}
        {error && <p className="text-red-400 md:col-span-3">{error}</p>}

        {result && result.answer === null && (
          <ul className="list-disc pl-6 md:col-span-3">
            {result.issues.map((issue) => (
              <li key={issue}>{issue}</li>
            ))}
          </ul>
        )}

        {result?.answer && (
          <>
            <section aria-label="Subparts" className={COLUMN}>
              <section className={CARD}>
                {result.answer.candidates.map((c) => (
                  <div key={c.subpart}>
                    <h2 className={CARD_TITLE}>
                      Subpart {c.subpart} — {c.title}
                    </h2>
                    <ul className={CARD_LIST}>
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
                                className="mt-1 mr-2 block text-sm text-accent-blue underline"
                              >
                                {cit}
                              </button>
                            ) : (
                              <span key={cit} className="mt-1 mr-2 block text-sm text-ink-muted">
                                {cit}
                              </span>
                            );
                          })}
                        </li>
                      ))}
                    </ul>
                  </div>
                ))}
              </section>
            </section>

            <section aria-label="Checklist" className={COLUMN}>
              <section className={CARD}>
                <h2 className={CARD_TITLE}>Checklist</h2>
                <ul className={CARD_LIST}>
                  {result.answer.checklist.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </section>
            </section>

            <section aria-label="Section text column" className={COLUMN}>
              {!section && !sectionError && (
                <p className="text-sm text-ink-muted">Click a citation to read the section.</p>
              )}
              {(section || sectionError) && (
                <aside aria-label="Section text" className={CARD}>
                  {section && (
                    <>
                      <h2 className={CARD_TITLE}>
                        {section.section_key} (Subpart {section.subpart})
                      </h2>
                      <pre className="whitespace-pre-wrap p-5 font-sans text-base leading-relaxed text-ink">
                        {section.text}
                      </pre>
                    </>
                  )}
                  {sectionError && <p className="p-5 text-red-400">{sectionError}</p>}
                </aside>
              )}
            </section>
          </>
        )}
      </div>

      <p className="mt-auto text-sm text-ink-muted">
        This is not a final applicability determination. The plant decides;
        this page gives the criteria and where to look.
      </p>
    </main>
  );
}
