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
// SUU-197: 버튼 모서리는 textarea와 같은 rounded-md (알약 아님).
import Workspace from "../Workspace";
// SUU-198: Memo 버튼 → MemoPane. SUU-199: Ask 뒤에는 질문 폼(question)과 메모(memo)도 Workspace 칸이라
// 네 칸(질문·Subparts·Memo·Checklist)을 전부 끌어서 크기·위치를 바꾼다. 기본 배치는 Workspace.tsx.
// SUU-200: 각 칸의 + 메뉴에 답변에 인용된 조문(sections)을 넘겨 그 칸에 열 수 있게 한다.
import MemoPane from "../MemoPane";
// SUU-214: 질문 칸은 react-bits PromptBar (npx shadcn add @react-bits/PromptBar-TS-CSS). 메뉴는 전부 비우고 Send 만 쓴다.
import PromptBar from "../../components/PromptBar";

// SUU-215: 제목은 다른 페이지와 같은 28px. PromptBar 는 640px. 아래 예시 질문 3개(manual_test_questions.md A-1~A-3)를 누르면 PromptBar 에 올라간다.
const EXAMPLES = [
  "Our medical device plant in Indiana is a major source of HAP. On the breathing-circuit assembly lines we bond polymer sub-assemblies by applying methylene chloride so the plastic softens and fuses as the solvent evaporates; nothing with solids is applied and no dry film is left behind. We are adding six more of these lines. Does the NESHAP for surface coating of plastic parts cover this solvent welding step?",
  "We run a small perchloroethylene dry cleaning shop in Michigan. There is an apartment above the shop that is currently unoccupied, and the machine is often idle because the location is mainly a pick-up and drop-off store. Does the requirement to eliminate perc emissions from dry cleaning systems located in a building with a residence after December 21, 2020 apply to us?",
  "At our gas plant in Utah, an area source of HAP, we operate three existing 800 hp four-stroke lean-burn natural gas engines that have met the geographic criteria for a remote location since October 2013. We never sent the state a notification of remote status. Can we meet the work practice standards for remote engines instead of doing performance tests?",
];

const CARD = "flex-1 min-h-0 overflow-y-auto rounded-lg border border-hairline bg-surface-1";
const CARD_TITLE = "sticky top-0 z-10 bg-gradient-violet px-5 py-3 text-[22px] font-bold leading-tight tracking-[-0.8px] text-ink";
const CARD_LIST = "list-disc space-y-3 p-5 pl-10 leading-relaxed";

type OpenedSection = { section: Section | null; error: string | null; paragraph: string | null };

export default function ApplicabilityPage() {
  const [asked, setAsked] = useState(false);
  const [preset, setPreset] = useState<string | undefined>(undefined);
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

  async function submit(question: string) {
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

  const answer = result?.answer;
  // + 메뉴에 보일 조문: 후보들의 인용에서 section_key를 모아 중복 없이
  const sections = Array.from(
    new Set(answer?.candidates.flatMap((c) => c.criteria.flatMap((cr) => cr.citations.map(citationToSectionKey))) ?? []),
  )
    .filter((k): k is string => !!k)
    .map((key) => ({ key, title: `§${key.replace("section-", "")}` }));

  // SUU-199: 폼과 상태 표시는 답이 오기 전엔 제목 아래에, 답이 온 뒤엔 Question 칸 안에 들어간다.
  const form = (
    <PromptBar
      width={640}
      value={preset}
      placeholder="Describe the process, e.g. we solvent weld plastic parts"
      sources={[]}
      commands={[]}
      models={[]}
      efforts={[]}
      busy={loading}
      onSend={submit}
    />
  );
  const status = (
    <>
      {loading && <p role="status">Searching the regulations… (10–20 s)</p>}
      {error && <p className="text-red-400">{error}</p>}
      {result && result.answer === null && (
        <ul className="list-disc pl-6">
          {result.issues.map((issue) => (
            <li key={issue}>{issue}</li>
          ))}
        </ul>
      )}
    </>
  );

  return (
    // SUU-199: Ask 뒤에는 최대 폭을 풀고 좌우 여백을 줄여 네 칸이 화면을 넉넉히 쓴다.
    <main
      className={`mx-auto flex w-full flex-1 flex-col gap-6 md:h-[calc(100dvh-60px)] md:overflow-hidden ${asked ? "px-4 py-6" : "max-w-7xl p-8"}`}
    >
      {!asked && (
        <>
          <h1 className="text-[28px] font-bold text-ink">Applicability</h1>
          <p className="text-lg text-accent-blue">
            40 CFR Part 63 applicability criteria, with the sections to check.
          </p>
        </>
      )}

      {/* SUU-182: 1행 = 질문 폼, 2행 = Subparts | Checklist | 조문. SUU-193: Workspace 패널. SUU-199: 폼도 Question 칸. */}
      <div className="flex flex-col gap-6 md:min-h-0 md:flex-1">
        {!answer && form}
        {!answer && (
          <ul aria-label="Example questions" className="flex max-w-[640px] flex-col gap-2">
            {EXAMPLES.map((q) => (
              <li key={q}>
                <button
                  type="button"
                  onClick={() => setPreset(q)}
                  className="w-full rounded-md border border-hairline bg-surface-1 px-4 py-3 text-left text-sm text-ink-muted hover:text-ink"
                >
                  {q}
                </button>
              </li>
            ))}
          </ul>
        )}
        {!answer && status}

        {answer && (
          <Workspace
            className="h-[70vh] md:h-auto md:min-h-0 md:flex-1"
            active={activeKey ? `section:${activeKey}` : undefined}
            sections={sections}
            onOpenSection={(key) => openSection(key, null)}
            onClose={(id) =>
              setOpened((o) => Object.fromEntries(Object.entries(o).filter(([k]) => `section:${k}` !== id)))
            }
            panels={{
              question: {
                title: "Question",
                node: (
                  <section className={`${CARD} flex flex-col gap-3 p-3`}>
                    {form}
                    {status}
                  </section>
                ),
              },
              subparts: {
                title: "Subparts",
                node: answer && (
                  <section className={CARD}>
                    {answer.candidates.map((c) => (
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
                node: answer && (
                  <section className={CARD}>
                    <h2 className={CARD_TITLE}>Checklist</h2>
                    <ul className={CARD_LIST}>
                      {answer.checklist.map((item) => (
                        <li key={item}>{item}</li>
                      ))}
                    </ul>
                  </section>
                ),
              },
              memo: { title: "Memo", node: <MemoPane /> },
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
