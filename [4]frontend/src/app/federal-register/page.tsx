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
      <div className="mt-6 grid gap-6 lg:grid-cols-[minmax(18rem,24rem)_1fr]">
        <section aria-label="Federal Register documents" className="space-y-2">
          {documents.map((document) => (
            <button
              key={document.document_key}
              type="button"
              onClick={() => setSelectedDocument(document)}
              className="w-full rounded-md border border-hairline bg-surface-1 p-4 text-left hover:border-ink-muted"
            >
              <span className="block font-medium text-ink">{document.title}</span>
              <span className="mt-2 block text-sm text-ink-muted">
                {document.effective_date
                  ? `${document.publication_date} · ${document.effective_date}`
                  : "시행일 없음"}
              </span>
              <span className="mt-2 block text-sm text-ink-muted">
                +{document.summary.added} −{document.summary.removed}
              </span>
            </button>
          ))}
        </section>
        <section aria-live="polite">
          {selectedDocument ? <FrDiff document={selectedDocument} /> : null}
        </section>
      </div>
    </main>
  );
}
