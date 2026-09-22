// SUU-186: 빈 페이지. 제목만, 내용은 나중에. SUU-218: Amendment → Federal Register.
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
      <div className={`mt-6 ${selectedDocument ? "grid gap-6 lg:grid-cols-[minmax(20rem,28rem)_1fr]" : ""}`}>
        <div
          data-pane="list"
          className={`${selectedDocument ? "" : "mx-auto "}w-full max-w-4xl transition-all duration-300`}
        >
          <table className="w-full border-collapse text-left text-sm">
            <thead className="border-b border-hairline text-ink-muted">
              <tr>
                <th className="px-3 py-3 font-medium">연번</th>
                <th className="px-3 py-3 font-medium">Subpart</th>
                <th className="px-3 py-3 font-medium">제목</th>
                <th className="px-3 py-3 font-medium">개정일</th>
                <th className="px-3 py-3 font-medium">변경</th>
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
                    } ${selectedDocument?.document_key === document.document_key ? "bg-surface-1" : ""}`}
                  >
                    <td className="px-3 py-3">{index + 1}</td>
                    <td className="px-3 py-3">{subparts}</td>
                    <td className="px-3 py-3">
                      <button type="button" className="text-left font-medium">
                        {document.title}
                      </button>
                    </td>
                    <td className="px-3 py-3">{document.effective_date ?? "—"}</td>
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
        {selectedDocument ? (
          <section data-pane="diff" aria-live="polite">
            <FrDiff document={selectedDocument} />
          </section>
        ) : null}
      </div>
    </main>
  );
}
