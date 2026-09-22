// SUU-186: 빈 페이지. 제목만, 내용은 나중에. SUU-218: Amendment → Federal Register.
// SUU-232: 머리글 영어, 제목은 한 줄(truncate). SUU-234: Section 열은 너무 길어 뺐다.
// SUU-238: 문서를 고르면 목록은 숨기고 diff 만. 뒤로 버튼으로 목록 복귀.
"use client";

import { useEffect, useState } from "react";
import { FrDiff, type FrDiffDocument } from "../../components/FrDiff";

type FrDiffPayload = {
  documents: FrDiffDocument[];
};

export default function FederalRegisterPage() {
  const [documents, setDocuments] = useState<FrDiffDocument[]>([]);
  const [selectedDocument, setSelectedDocument] = useState<FrDiffDocument | null>(null);
  const [error, setError] = useState(false);

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
    <main className="flex-1 px-6 py-10">
      <h1 className="text-[28px] font-bold text-ink">Federal Register</h1>
      {error ? <p className="mt-4 text-sm text-ink-muted">불러오지 못했습니다.</p> : null}
      {selectedDocument ? (
        <section data-pane="diff" aria-live="polite" className="mt-6">
          <button
            type="button"
            aria-label="뒤로"
            onClick={() => setSelectedDocument(null)}
            className="mb-4 flex h-9 w-9 items-center justify-center rounded-full border border-hairline text-ink transition-colors hover:bg-surface-1"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M19 12H5" />
              <path d="M12 19l-7-7 7-7" />
            </svg>
          </button>
          <FrDiff document={selectedDocument} />
        </section>
      ) : (
        <div data-pane="list" className="mx-auto mt-6 w-full max-w-4xl">
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
              {documents.map((document, index) => {
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
                    <td className="px-3 py-3">{index + 1}</td>
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
      )}
    </main>
  );
}
