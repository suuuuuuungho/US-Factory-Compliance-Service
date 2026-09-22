// SUU-186: 빈 페이지. 제목만, 내용은 나중에. SUU-218: Amendment → Federal Register.
// SUU-232: 머리글 영어, 제목은 한 줄(truncate). SUU-234: Section 열은 너무 길어 뺐다.
// SUU-238: 문서를 고르면 목록은 숨기고 diff 만. 뒤로 버튼으로 목록 복귀.
// SUU-239: 제목 가운데, 뒤로 버튼은 제목과 같은 줄. diff 는 Applicability 처럼 화면 남는 높이를 다 쓴다.
// SUU-243: 목록은 남는 높이 안에서 스크롤, 10개씩 이전/다음 페이지.
// SUU-241: flex-1 이면 basis 0% 라 내용 크기만큼 main 이 커져 h-[calc] 가 무시됐다 → min-h-0 flex-auto.
"use client";

import { useEffect, useState } from "react";
import { FrDiff, type FrDiffDocument } from "../../components/FrDiff";

type FrDiffPayload = {
  documents: FrDiffDocument[];
};

const PAGE_SIZE = 10;

export default function FederalRegisterPage() {
  const [documents, setDocuments] = useState<FrDiffDocument[]>([]);
  const [selectedDocument, setSelectedDocument] = useState<FrDiffDocument | null>(null);
  const [error, setError] = useState(false);
  const [page, setPage] = useState(0);
  const pageCount = Math.max(1, Math.ceil(documents.length / PAGE_SIZE));
  const pageDocuments = documents.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);

  useEffect(() => {
    let cancelled = false;

    fetch("/fr-diff.json")
      .then((response) => response.json() as Promise<FrDiffPayload>)
      .then((payload) => {
        if (!cancelled) setDocuments(payload.documents);
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
      <div className="relative flex items-center justify-center">
        {selectedDocument ? (
          <button
            type="button"
            aria-label="뒤로"
            onClick={() => setSelectedDocument(null)}
            className="absolute left-0 flex h-9 w-9 items-center justify-center rounded-full border border-hairline text-ink transition-colors hover:bg-surface-1"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M19 12H5" />
              <path d="M12 19l-7-7 7-7" />
            </svg>
          </button>
        ) : null}
        <h1 className="text-center text-[28px] font-bold text-ink">Federal Register</h1>
      </div>
      {error ? <p className="mt-4 text-sm text-ink-muted">불러오지 못했습니다.</p> : null}
      {selectedDocument ? (
        <section data-pane="diff" aria-live="polite" className="mx-auto mt-4 flex w-full max-w-6xl min-h-0 flex-1 flex-col">
          <FrDiff document={selectedDocument} />
        </section>
      ) : (
        <div className="mt-6 flex min-h-0 flex-1 flex-col">
          <div data-pane="list" className="scheme-dark mx-auto w-full max-w-4xl min-h-0 flex-1 overflow-y-auto">
          <table className="w-full border-collapse text-left text-sm">
            <thead className="border-b border-hairline text-ink-muted">
              <tr>
                <th className="px-3 py-3 font-medium">#</th>
                <th className="px-3 py-3 font-medium">Subpart</th>
                <th className="px-3 py-3 font-medium">Title</th>
                <th className="px-3 py-3 font-medium">Effective</th>
                <th className="px-3 py-3 font-medium">Changes</th>
              </tr>
            </thead>
            <tbody>
              {pageDocuments.map((document, index) => {
                const subparts = [...new Set(
                  document.sections
                    .map((section) => section.node_key?.split("/")[2]?.replace("subpart-", ""))
                    .filter(Boolean),
                )].join(", ") || "—";

                return (
                  <tr
                    key={document.document_key}
                    onClick={() => setSelectedDocument(document)}
                    className={`cursor-pointer border-b border-hairline transition-colors hover:bg-surface-1 ${
                      document.reason ? "text-ink-muted" : "text-ink"
                    }`}
                  >
                    <td className="px-3 py-3">{page * PAGE_SIZE + index + 1}</td>
                    <td className="px-3 py-3 whitespace-nowrap">{subparts}</td>
                    {/* w-full max-w-0: 남는 폭을 제목이 다 쓰고, 넘치면 한 줄로 자른다 */}
                    <td className="w-full max-w-0 px-3 py-3">
                      <button type="button" title={document.title} className="block w-full truncate text-left font-medium">
                        {document.title}
                      </button>
                    </td>
                    <td className="px-3 py-3 whitespace-nowrap">{document.effective_date ?? "—"}</td>
                    <td className="px-3 py-3 whitespace-nowrap">
                      <span className="text-semantic-success">+{document.summary.added}</span>
                      <span className="ml-2 text-gradient-coral">−{document.summary.removed}</span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          </div>
          <div className="flex items-center justify-center gap-4 py-3 text-sm text-ink-muted">
            <button
              type="button"
              onClick={() => setPage((current) => current - 1)}
              disabled={page === 0}
              className="rounded-full border border-hairline px-3 py-1 text-ink transition-colors hover:bg-surface-1 disabled:cursor-default disabled:opacity-40 disabled:hover:bg-transparent"
            >
              이전
            </button>
            <span>{page + 1} / {pageCount}</span>
            <button
              type="button"
              onClick={() => setPage((current) => current + 1)}
              disabled={page >= pageCount - 1}
              className="rounded-full border border-hairline px-3 py-1 text-ink transition-colors hover:bg-surface-1 disabled:cursor-default disabled:opacity-40 disabled:hover:bg-transparent"
            >
              다음
            </button>
          </div>
        </div>
      )}
    </main>
  );
}
