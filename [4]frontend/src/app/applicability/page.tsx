"use client";
// SUU-190: 질문 화면을 / 에서 여기로 옮김. h1만 Applicability.
// SUU-163: 질문 → POST /ask → 후보 Subpart 카드 + 체크리스트. 디자인 없음.
// SUU-172: className만 Framer 토큰(bg-surface-1, rounded-full 등)으로. 기능 동일.
// SUU-171: h1을 히어로(display-lg 근사)로. 상단바는 layout의 TopNav.
// SUU-164: 인용 버튼 → GET /section/{key} → 옆 패널(aside)에 조문 전문. 같은 조문은 캐시.
import { useRef, useState } from "react";
import {
  ask,
  citationToParagraph,
  citationToSectionKey,
  getSection,
  paragraphText,
  type AskResult,
  type Section,
} from "../../lib/api";

// SUU-175: 카드 제목 headline(22px/700), 목록 줄 간격, 옆 패널 조문 body 크기.
// SUU-180: 카드 제목 줄만 gradient 배경, 본문은 차콜. SUU-183: 세 칸 제목 띠 전부 같은 보라.
// SUU-184: main을 화면 높이(100dvh-상단바 60px)로 고정, 2행이 남은 높이를 다 쓰고 카드 안에서 스크롤.
// SUU-188: 카드가 flex-1로 칸을 꽉 채워 세 카드 높이가 같다. 칸은 overflow-hidden, 스크롤은 카드가 한다.
// SUU-193: 2행 세 칸은 Workspace(dockview) 안의 패널. 끌어서 크기·위치를 바꾼다. 칸(COLUMN) 역할은 Workspace의 Panel이 한다.
// SUU-196: Ask 버튼은 textarea 오른쪽에 같은 높이. 한 번 Ask를 누르면 h1·설명 p를 숨겨 Workspace가 더 길어진다.
import Workspace from "../Workspace";

const CARD = "flex-1 min-h-0 overflow-y-auto rounded-lg border border-hairline bg-surface-1";
const CARD_TITLE = "sticky top-0 z-10 bg-gradient-violet px-5 py-3 text-[22px] font-bold leading-tight tracking-[-0.8px] text-ink";
const CARD_LIST = "list-disc space-y-3 p-5 pl-10 leading-relaxed";

type OpenedSection = { section: Section | null; error: string | null; paragraph: string | null };

export default function ApplicabilityPage() {
  const [question, setQuestion] = useState("");
  const [asked, setAsked] = useState(false);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AskResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  // SUU-193: 열린 조문 칸들. key = section_key. paragraph는 SUU-189의 문단 글자("a"), null이면 전체 보기.
  const [opened, setOpened] = useState<Record<string, OpenedSection>>({});
  const [activeKey, setActiveKey] = useState<string | null>(null);
  const sectionCache = useRef<Record<string, Section>>({});

  function patchOpened(key: string, patch: Partial<OpenedSection>) {
    setOpened((o) => (o[key] ? { ...o, [key]: { ...o[key], ...patch } } : o));
  }

  async function openSection(key: string, para: string | null) {
    setActiveKey(key);
    setOpened((o) => ({
      ...o,
      [key]: { section: o[key]?.section ?? null, error: null, paragraph: para },
    }));
    const cached = sectionCache.current[key];
    if (cached) return patchOpened(key, { section: cached });
    try {
      const s = await getSection(key);
      sectionCache.current[key] = s;
      patchOpened(key, { section: s });
    } catch (err) {
      patchOpened(key, { section: null, error: err instanceof Error ? err.message : String(err) });
    }
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setAsked(true);
    setLoading(true);
    setResult(null);
    setError(null);
    setOpened({});
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
      {!asked && (
        <>
          <h1 className="whitespace-nowrap text-2xl font-medium leading-none tracking-[-0.04em] text-ink sm:text-4xl md:text-[2.75rem]">
            Applicability
          </h1>
          <p className="text-lg text-accent-blue">
            40 CFR Part 63 applicability criteria, with the sections to check.
          </p>
        </>
      )}

      {/* SUU-182: 1행 = 질문 폼, 2행 = Subparts | Checklist | 조문. SUU-193: 2행은 Workspace 패널. */}
      <div className="flex flex-col gap-6 md:min-h-0 md:flex-1">
        <form onSubmit={onSubmit} className="flex flex-row gap-2">
          <textarea
            className="flex-1 rounded-md border border-hairline bg-surface-1 p-3 text-ink placeholder:text-ink-muted focus:border-accent-blue focus:outline-none"
            rows={3}
            placeholder="Describe the process, e.g. we solvent weld plastic parts"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
          />
          <button
            type="submit"
            disabled={loading}
            className="shrink-0 self-stretch rounded-full bg-primary px-6 text-sm font-medium text-on-primary disabled:opacity-50"
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

        {result?.answer && (
          <Workspace
            className="h-[70vh] md:h-auto md:min-h-0 md:flex-1"
            active={activeKey ? `section:${activeKey}` : undefined}
            onClose={(id) =>
              setOpened((o) => Object.fromEntries(Object.entries(o).filter(([k]) => `section:${k}` !== id)))
            }
            panels={{
              subparts: {
                title: "Subparts",
                node: (
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
                                    onClick={() => openSection(key, citationToParagraph(cit))}
                                    className="mt-1 mr-2 block text-sm text-accent-blue underline"
                                  >
                                    {cit}
                                  </button>
                                ) : (
                                  <span
                                    key={cit}
                                    className="mt-1 mr-2 block text-sm text-ink-muted"
                                  >
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
                ),
              },
              checklist: {
                title: "Checklist",
                node: (
                  <section className={CARD}>
                    <h2 className={CARD_TITLE}>Checklist</h2>
                    <ul className={CARD_LIST}>
                      {result.answer.checklist.map((item) => (
                        <li key={item}>{item}</li>
                      ))}
                    </ul>
                  </section>
                ),
              },
              ...Object.fromEntries(
                Object.entries(opened).map(([key, { section, error, paragraph }]) => {
                  // SUU-189: 문단이 있으면 그 문단만. 본문에서 못 찾으면 전체로 떨어진다
                  const shown =
                    section && paragraph ? paragraphText(section.text, paragraph) : null;
                  return [
                    `section:${key}`,
                    {
                      title: `§${key.replace("section-", "")}`,
                      node: (
                        <aside aria-label="Section text" className={CARD}>
                          {section && (
                            <>
                              <h2 className={CARD_TITLE}>
                                {section.section_key}
                                {shown && `(${paragraph})`} (Subpart {section.subpart})
                              </h2>
                              {shown && (
                                <button
                                  type="button"
                                  onClick={() => patchOpened(key, { paragraph: null })}
                                  className="mx-5 mt-4 text-sm text-accent-blue underline"
                                >
                                  Show all of {section.section_key.replace("section-", "")}
                                </button>
                              )}
                              <pre className="whitespace-pre-wrap p-5 font-sans text-base leading-relaxed text-ink">
                                {shown ?? section.text}
                              </pre>
                            </>
                          )}
                          {error && <p className="p-5 text-red-400">{error}</p>}
                        </aside>
                      ),
                    },
                  ];
                }),
              ),
            }}
          />
        )}
      </div>

      <p className="mt-auto text-sm text-ink-muted">
        This is not a final applicability determination. The plant decides; this page gives the
        criteria and where to look.
      </p>
    </main>
  );
}
