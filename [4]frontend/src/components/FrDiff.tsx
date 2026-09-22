import { diffWords } from "diff";

type DiffRow = {
  kind: "equal" | "removed" | "added" | "changed";
  before: string | null;
  after: string | null;
  is_context: boolean;
};

type DiffSection = {
  section: string;
  node_key: string;
  before_date: string;
  after_date: string;
  rows: DiffRow[];
};

export type FrDiffDocument = {
  document_key: string;
  document_number: string;
  title: string;
  citation: string;
  canonical_url: string;
  publication_date: string;
  effective_date: string | null;
  amended_sections: string[];
  reason: string | null;
  summary: { added: number; removed: number; changed: number };
  sections: DiffSection[];
};

function ChangedText({ before, after }: Pick<DiffRow, "before" | "after">) {
  const parts = diffWords(before ?? "", after ?? "");

  return (
    <>
      {parts.map((part, index) => {
        const next = parts.slice(index + 1).find((candidate) => !candidate.added && !candidate.removed);
        const includeTrailingPunctuation =
          (part.added || part.removed) && next && !next.added && !next.removed && /^[.,;:!?]+$/.test(next.value);

        if (part.added || part.removed) {
          return <mark key={index}>{part.value}{includeTrailingPunctuation ? next.value : ""}</mark>;
        }
        if (index > 0 && parts.slice(0, index).some((candidate) => candidate.added || candidate.removed) && /^[.,;:!?]+$/.test(part.value)) {
          return null;
        }
        return <span key={index}>{part.value}</span>;
      })}
    </>
  );
}

export function FrDiff({ document }: { document: FrDiffDocument }) {
  if (document.reason || document.sections.length === 0) {
    return <p className="text-sm text-ink-muted">변경 본문 없음</p>;
  }

  return (
    <article className="space-y-6">
      <header>
        <p className="text-sm text-ink-muted">{document.citation}</p>
        <h2 className="mt-1 text-xl font-semibold text-ink">{document.title}</h2>
      </header>
      {document.sections.map((section) => (
        <section key={section.node_key} className="rounded-md border border-hairline bg-surface-1 p-4">
          <h3 className="font-medium text-ink">§ {section.section}</h3>
          <div className="mt-3 space-y-2 text-sm leading-6">
            {section.rows.map((row, index) => {
              if (row.kind === "equal") {
                return row.is_context ? <p key={index} className="text-ink-muted">{row.after}</p> : null;
              }
              if (row.kind === "removed") {
                return <p key={index} className="diff-removed bg-gradient-coral/15 px-2 text-gradient-coral">{row.before}</p>;
              }
              if (row.kind === "added") {
                return <p key={index} className="diff-added bg-semantic-success/15 px-2 text-semantic-success">{row.after}</p>;
              }
              return <p key={index} className="diff-changed px-2 text-ink"><ChangedText before={row.before} after={row.after} /></p>;
            })}
          </div>
        </section>
      ))}
    </article>
  );
}
