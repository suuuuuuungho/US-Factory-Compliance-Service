// SUU-233: 줄마다 Before(원문) | After(개정문) 두 칸으로 나란히. 바뀐 줄은 왼쪽에 빠진 단어, 오른쪽에 새 단어만 mark.
// SUU-238: 섹션 카드 대신 스크롤 영역 하나. 고정 머리글이 지금 보는 조항(§)으로 바뀐다.
// SUU-239: Applicability 카드(CARD/CARD_TITLE)와 같은 모양. 문서 제목·인용도 머리글 안에.
// SUU-240: 머리글 배경색 없이, 제목은 § 바로 옆. scheme-dark 로 스크롤바도 어둡게.
"use client";

import { useRef, useState } from "react";
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

const PUNCT = /^[.,;:!?]+$/;

// 한쪽 칸만 그린다. side="before"면 removed 조각을, "after"면 added 조각을 mark 로 감싼다.
function ChangedText({ before, after, side }: Pick<DiffRow, "before" | "after"> & { side: "before" | "after" }) {
  const parts = diffWords(before ?? "", after ?? "");
  const isMine = (part: { added?: boolean; removed?: boolean }) => (side === "before" ? part.removed : part.added);
  const isOther = (part: { added?: boolean; removed?: boolean }) => (side === "before" ? part.added : part.removed);

  return (
    <>
      {parts.map((part, index) => {
        if (isOther(part)) return null;
        if (isMine(part)) {
          // 바로 뒤 구두점은 mark 안으로 (예: "A" + "." → "A.")
          const next = parts.slice(index + 1).find((candidate) => !isOther(candidate));
          const swallow = next && !next.added && !next.removed && PUNCT.test(next.value);
          return <mark key={index}>{part.value}{swallow ? next.value : ""}</mark>;
        }
        // 앞에서 mark 가 삼킨 구두점은 건너뛴다
        const prev = parts.slice(0, index).filter((candidate) => !isOther(candidate)).at(-1);
        if (prev && isMine(prev) && PUNCT.test(part.value)) return null;
        return <span key={index}>{part.value}</span>;
      })}
    </>
  );
}

const CELL = "min-w-0 px-2 py-1 whitespace-pre-wrap";
const REMOVED = "diff-removed bg-gradient-coral/15 text-gradient-coral";
const ADDED = "diff-added bg-semantic-success/15 text-semantic-success";

function Row({ row }: { row: DiffRow }) {
  if (row.kind === "equal") {
    if (!row.is_context) return null;
    return (
      <div data-diff-row="equal" className="grid grid-cols-2 gap-px text-ink-muted">
        <div data-side="before" className={CELL}>{row.before}</div>
        <div data-side="after" className={CELL}>{row.after}</div>
      </div>
    );
  }
  if (row.kind === "removed") {
    return (
      <div data-diff-row="removed" className="grid grid-cols-2 gap-px">
        <div data-side="before" className={`${CELL} ${REMOVED}`}>{row.before}</div>
        <div data-side="after" className={CELL} />
      </div>
    );
  }
  if (row.kind === "added") {
    return (
      <div data-diff-row="added" className="grid grid-cols-2 gap-px">
        <div data-side="before" className={CELL} />
        <div data-side="after" className={`${CELL} ${ADDED}`}>{row.after}</div>
      </div>
    );
  }
  return (
    <div data-diff-row="changed" className="diff-changed grid grid-cols-2 gap-px text-ink">
      <div data-side="before" className={`${CELL} [&>mark]:bg-gradient-coral/25 [&>mark]:text-gradient-coral`}>
        <ChangedText before={row.before} after={row.after} side="before" />
      </div>
      <div data-side="after" className={`${CELL} [&>mark]:bg-semantic-success/25 [&>mark]:text-semantic-success`}>
        <ChangedText before={row.before} after={row.after} side="after" />
      </div>
    </div>
  );
}

export function FrDiff({ document }: { document: FrDiffDocument }) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const headerRef = useRef<HTMLDivElement>(null);
  const [currentIndex, setCurrentIndex] = useState(0);

  if (document.reason || document.sections.length === 0) {
    return <p className="text-sm text-ink-muted">변경 본문 없음</p>;
  }

  // 머리글 아래를 지난 마지막 섹션이 "지금 보는 조항"
  const handleScroll = () => {
    const scroll = scrollRef.current;
    const header = headerRef.current;
    if (!scroll || !header) return;
    const limit = header.getBoundingClientRect().bottom + 1;
    const sections = Array.from(scroll.querySelectorAll<HTMLElement>("[data-diff-section]"));
    let index = 0;
    sections.forEach((section, i) => {
      if (section.getBoundingClientRect().top <= limit) index = i;
    });
    setCurrentIndex(index);
  };

  const current = document.sections[Math.min(currentIndex, document.sections.length - 1)];

  return (
    <div
      ref={scrollRef}
      data-diff-scroll
      onScroll={handleScroll}
      className="scheme-dark max-h-[calc(100dvh-10rem)] min-h-0 flex-1 overflow-y-auto rounded-lg border border-hairline bg-surface-1 md:max-h-none"
    >
      <div ref={headerRef} data-diff-current className="sticky top-0 z-10 border-b border-hairline bg-surface-1 px-5 py-3 text-ink">
        <div className="flex items-baseline gap-4">
          <h3 className="text-[22px] font-bold leading-tight tracking-[-0.8px]">§ {current.section}</h3>
          <p className="min-w-0 truncate text-sm text-ink-muted" title={document.title}>
            {document.citation} · {document.title}
          </p>
        </div>
        <div className="mt-2 grid grid-cols-2 gap-px text-xs text-ink-muted">
          <div className="px-2">Before ({current.before_date})</div>
          <div className="px-2">After ({current.after_date})</div>
        </div>
      </div>
      <div className="px-5 pb-5 text-sm leading-6">
        {document.sections.map((section) => (
          <div key={section.node_key} data-diff-section className="space-y-1 pt-3">
            {section.rows.map((row, index) => (
              <Row key={index} row={row} />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}
