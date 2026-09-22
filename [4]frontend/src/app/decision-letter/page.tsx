// SUU-218: 빈 페이지. 제목만, 내용은 나중에.
// SUU-253: decision-letters.json(SUU-252) 을 읽어 표로. 행마다 EPA 원본 PDF 링크. 표·페이지 바는 Federal Register 와 같은 모양.
// SUU-258: 위에 공장 설명 글칸 + Search. 결과가 오면 표가 비슷한 서한(score·snippet)으로 바뀌고, Clear 면 원래 목록.
"use client";

import { useEffect, useState } from "react";
import { similarLetters, type SimilarLetter } from "@/lib/api";

type Letter = {
  source_key: string;
  facility_name: string | null;
  title: string;
  subparts: string[];
  date: string | null;
  pdf_url: string | null;
};

type LettersPayload = {
  letters: Letter[];
};

const PAGE_SIZE = 10;

// SUU-260: 열 순서 #, Facility, Title, Subpart, Date, PDF. 초기 너비(px). 손잡이로 끌면 바뀐다.
const HEADERS = ["#", "Facility", "Title", "Subpart", "Date", "PDF"];
const INITIAL_WIDTHS = [48, 180, 360, 110, 100, 80];
const MIN_WIDTH = 60;
// SUU-258: 검색 모드에서만 # 다음에 끼는 Score 열. 너비 고정, 손잡이 없음
const SCORE_WIDTH = 70;

const NO_MATCH_TEXT =
  "No similar cases found. Letters with weak similarity are not recommended, to keep results trustworthy. Try describing your process, fuel, or equipment.";

const BUTTON_CLASS =
  "rounded-full border border-hairline px-3 py-1 text-ink transition-colors hover:bg-surface-1 disabled:cursor-default disabled:opacity-40 disabled:hover:bg-transparent";

export default function DecisionLetterPage() {
  const [letters, setLetters] = useState<Letter[]>([]);
  const [error, setError] = useState(false);
  const [page, setPage] = useState(0);
  const [widths, setWidths] = useState(INITIAL_WIDTHS);
  const [description, setDescription] = useState("");
  const [results, setResults] = useState<SimilarLetter[] | null>(null); // null = 검색 안 한 상태 → 전체 목록
  const [loading, setLoading] = useState(false);

  function startResize(index: number, event: React.MouseEvent) {
    event.preventDefault();
    const startX = event.clientX;
    const startWidth = widths[index];
    const onMove = (e: MouseEvent) =>
      setWidths((prev) => prev.map((w, i) => (i === index ? Math.max(MIN_WIDTH, startWidth + e.clientX - startX) : w)));
    const onUp = () => {
      document.removeEventListener("mousemove", onMove);
      document.removeEventListener("mouseup", onUp);
    };
    document.addEventListener("mousemove", onMove);
    document.addEventListener("mouseup", onUp);
  }

  const pageCount = Math.max(1, Math.ceil(letters.length / PAGE_SIZE));
  const pageLetters = letters.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);
  const searching = results !== null;
  const rows: (Letter | SimilarLetter)[] = results ?? pageLetters;
  const headers = searching ? [HEADERS[0], "Score", ...HEADERS.slice(1)] : HEADERS;
  const colWidths = searching ? [widths[0], SCORE_WIDTH, ...widths.slice(1)] : widths;
  const isScoreColumn = (index: number) => searching && index === 1;
  // 화면 열 번호 → widths 번호. Score 열 뒤는 하나씩 밀린다
  const widthIndex = (index: number) => (searching && index > 1 ? index - 1 : index);

  useEffect(() => {
    let cancelled = false;

    fetch("/decision-letters.json")
      .then((response) => response.json() as Promise<LettersPayload>)
      .then((payload) => {
        if (!cancelled) setLetters(payload.letters);
      })
      .catch(() => {
        if (!cancelled) setError(true);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  async function handleSearch() {
    setLoading(true);
    setError(false);
    try {
      setResults(await similarLetters(description));
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  }

  function handleClear() {
    setResults(null);
    setDescription("");
    setPage(0);
  }

  return (
    <main className="flex min-h-0 flex-auto flex-col px-6 py-6 md:h-[calc(100dvh-60px)] md:overflow-hidden">
      <h1 className="text-center font-serif text-[28px] font-bold text-ink">EPA Decision Letter</h1>
      <div className="mx-auto mt-4 flex w-full max-w-4xl flex-col gap-2">
        <textarea
          aria-label="Factory description"
          value={description}
          onChange={(event) => setDescription(event.target.value)}
          placeholder="Describe your factory: process, fuel, equipment…"
          rows={3}
          className="w-full rounded-md border border-hairline bg-transparent px-3 py-2 text-sm text-ink"
        />
        <div className="flex gap-2 text-sm">
          <button type="button" onClick={handleSearch} disabled={loading || description.trim() === ""} className={BUTTON_CLASS}>
            Search
          </button>
          <button type="button" onClick={handleClear} disabled={loading} className={BUTTON_CLASS}>
            Clear
          </button>
        </div>
      </div>
      {error ? <p className="mt-4 text-sm text-ink-muted">불러오지 못했습니다.</p> : null}
      <div className="mt-6 flex min-h-0 flex-1 flex-col">
        <div data-pane="list" className="scheme-dark mx-auto w-full max-w-4xl min-h-0 overflow-auto">
          {searching && results.length === 0 ? (
            <p className="px-3 py-6 text-center text-sm text-ink-muted">{NO_MATCH_TEXT}</p>
          ) : (
          /* table-fixed: 셀 너비는 colgroup 이 정한다 */
          <table className="w-full table-fixed border-collapse text-left text-sm">
            <colgroup>
              {colWidths.map((width, index) => (
                <col key={index} style={{ width: `${width}px` }} />
              ))}
            </colgroup>
            <thead className="border-b border-hairline text-ink-muted">
              <tr>
                {headers.map((header, index) => (
                  <th key={header} className="relative px-3 py-3 font-medium">
                    {header}
                    {isScoreColumn(index) ? null : (
                      <span
                        data-resize-handle
                        onMouseDown={(event) => startResize(widthIndex(index), event)}
                        className="absolute top-0 right-0 h-full w-1.5 cursor-col-resize select-none hover:bg-hairline"
                      />
                    )}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((letter, index) => (
                <tr key={letter.source_key} className="border-b border-hairline text-ink">
                  <td className="px-3 py-3">{(searching ? 0 : page * PAGE_SIZE) + index + 1}</td>
                  {"score" in letter ? <td className="px-3 py-3 whitespace-nowrap">{letter.score.toFixed(2)}</td> : null}
                  {/* SUU-259: max-w 로 좁히고 넘치면 ... 으로 자른다. 전체 이름은 title 로 */}
                  <td className="max-w-[180px] px-3 py-3">
                    <span title={letter.facility_name ?? undefined} className="block truncate">
                      {letter.facility_name ?? "—"}
                    </span>
                  </td>
                  {/* w-full max-w-0: 남는 폭을 제목이 다 쓰고, 넘치면 한 줄로 자른다 */}
                  <td className="w-full max-w-0 px-3 py-3">
                    <span title={letter.title} className="block w-full truncate font-medium">
                      {letter.title}
                    </span>
                    {"snippet" in letter ? (
                      <span className="mt-1 block text-xs text-ink-muted">{letter.snippet}</span>
                    ) : null}
                  </td>
                  <td className="overflow-hidden px-3 py-3 whitespace-nowrap">{letter.subparts.join(", ") || "—"}</td>
                  <td className="overflow-hidden px-3 py-3 whitespace-nowrap">{letter.date ?? "—"}</td>
                  <td className="overflow-hidden px-3 py-3 whitespace-nowrap">
                    {letter.pdf_url ? (
                      <a
                        href={letter.pdf_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="rounded-full border border-hairline px-3 py-1 text-ink transition-colors hover:bg-surface-1"
                      >
                        PDF
                      </a>
                    ) : (
                      <span className="text-ink-muted">원문 없음</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          )}
        </div>
        {searching ? null : (
        <div data-pager className="mt-3 flex items-center justify-center gap-4 text-sm text-ink-muted">
          <button
            type="button"
            onClick={() => setPage((current) => current - 1)}
            disabled={page === 0}
            className={BUTTON_CLASS}
          >
            Prev
          </button>
          <span>{page + 1} / {pageCount}</span>
          <button
            type="button"
            onClick={() => setPage((current) => current + 1)}
            disabled={page >= pageCount - 1}
            className={BUTTON_CLASS}
          >
            Next
          </button>
        </div>
        )}
      </div>
    </main>
  );
}
