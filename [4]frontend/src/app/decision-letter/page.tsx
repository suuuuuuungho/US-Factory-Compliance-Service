// SUU-218: 빈 페이지. 제목만, 내용은 나중에.
// SUU-253: decision-letters.json(SUU-252) 을 읽어 표로. 행마다 EPA 원본 PDF 링크. 표·페이지 바는 Federal Register 와 같은 모양.
"use client";

import { useEffect, useState } from "react";

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

export default function DecisionLetterPage() {
  const [letters, setLetters] = useState<Letter[]>([]);
  const [error, setError] = useState(false);
  const [page, setPage] = useState(0);
  const pageCount = Math.max(1, Math.ceil(letters.length / PAGE_SIZE));
  const pageLetters = letters.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);

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

  return (
    <main className="flex min-h-0 flex-auto flex-col px-6 py-6 md:h-[calc(100dvh-60px)] md:overflow-hidden">
      <h1 className="text-center font-serif text-[28px] font-bold text-ink">EPA Decision Letter</h1>
      {error ? <p className="mt-4 text-sm text-ink-muted">불러오지 못했습니다.</p> : null}
      <div className="mt-6 flex min-h-0 flex-1 flex-col">
        <div data-pane="list" className="scheme-dark mx-auto w-full max-w-4xl min-h-0 overflow-y-auto">
          <table className="w-full border-collapse text-left text-sm">
            <thead className="border-b border-hairline text-ink-muted">
              <tr>
                <th className="px-3 py-3 font-medium">#</th>
                <th className="px-3 py-3 font-medium">Facility</th>
                <th className="px-3 py-3 font-medium">Title</th>
                <th className="px-3 py-3 font-medium">Subpart</th>
                <th className="px-3 py-3 font-medium">Date</th>
                <th className="px-3 py-3 font-medium">PDF</th>
              </tr>
            </thead>
            <tbody>
              {pageLetters.map((letter, index) => (
                <tr key={letter.source_key} className="border-b border-hairline text-ink">
                  <td className="px-3 py-3">{page * PAGE_SIZE + index + 1}</td>
                  <td className="px-3 py-3 whitespace-nowrap">{letter.facility_name ?? "—"}</td>
                  {/* w-full max-w-0: 남는 폭을 제목이 다 쓰고, 넘치면 한 줄로 자른다 */}
                  <td className="w-full max-w-0 px-3 py-3">
                    <span title={letter.title} className="block w-full truncate font-medium">
                      {letter.title}
                    </span>
                  </td>
                  <td className="px-3 py-3 whitespace-nowrap">{letter.subparts.join(", ") || "—"}</td>
                  <td className="px-3 py-3 whitespace-nowrap">{letter.date ?? "—"}</td>
                  <td className="px-3 py-3 whitespace-nowrap">
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
        </div>
        <div data-pager className="mt-3 flex items-center justify-center gap-4 text-sm text-ink-muted">
          <button
            type="button"
            onClick={() => setPage((current) => current - 1)}
            disabled={page === 0}
            className="rounded-full border border-hairline px-3 py-1 text-ink transition-colors hover:bg-surface-1 disabled:cursor-default disabled:opacity-40 disabled:hover:bg-transparent"
          >
            Prev
          </button>
          <span>{page + 1} / {pageCount}</span>
          <button
            type="button"
            onClick={() => setPage((current) => current + 1)}
            disabled={page >= pageCount - 1}
            className="rounded-full border border-hairline px-3 py-1 text-ink transition-colors hover:bg-surface-1 disabled:cursor-default disabled:opacity-40 disabled:hover:bg-transparent"
          >
            Next
          </button>
        </div>
      </div>
    </main>
  );
}
