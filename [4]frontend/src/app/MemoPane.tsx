"use client";
// SUU-198: 메모 pane. (SUU-200: 조문 칸 aside와 구분하려고 section/region) 제목·본문을 쓰고 Save하면 localStorage에 쌓이고, 아래 기록 목록에 제목+시각이 남는다.
// 기록 항목을 누르면 그 메모가 편집칸에 다시 불려온다. 다시 Save하면 새 기록으로 추가된다. SUU-200: 기록 옆 ✕로 지운다.
import { useState } from "react";

type Memo = { title: string; body: string; savedAt: string };

const STORAGE_KEY = "applicability-memos";

function load(): Memo[] {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "[]");
  } catch {
    return [];
  }
}

const INPUT =
  "rounded-md border border-hairline bg-surface-1 p-3 text-ink placeholder:text-ink-muted focus:border-accent-blue focus:outline-none";

// SUU-255: onChange(title, body) — 편집칸이 바뀔 때마다 page에 올려 PDF Notes에 넣는다.
export default function MemoPane({ onChange }: { onChange?: (title: string, body: string) => void } = {}) {
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  function edit(nextTitle: string, nextBody: string) {
    setTitle(nextTitle);
    setBody(nextBody);
    onChange?.(nextTitle, nextBody);
  }
  const [memos, setMemos] = useState<Memo[]>(load);

  function persist(next: Memo[]) {
    setMemos(next);
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    } catch {}
  }
  const save = () => persist([{ title, body, savedAt: new Date().toISOString() }, ...memos]);
  const remove = (i: number) => persist(memos.filter((_, j) => j !== i));

  return (
    <section aria-label="Memo pane" className="flex min-h-0 min-w-0 flex-1 flex-col gap-3 rounded-lg border border-hairline bg-surface-1 p-4">
      <input className={INPUT} placeholder="Title" value={title} onChange={(e) => edit(e.target.value, body)} />
      <textarea
        className={`${INPUT} min-h-40 flex-1 resize-none`}
        placeholder="Write a memo…"
        value={body}
        onChange={(e) => edit(title, e.target.value)}
      />
      <button
        type="button"
        onClick={save}
        className="self-end rounded-md bg-primary px-6 py-2 text-sm font-medium text-on-primary"
      >
        Save
      </button>
      <ul aria-label="Saved memos" className="min-h-0 overflow-y-auto border-t border-hairline pt-3 text-sm">
        {memos.map((m, i) => (
          <li key={i} className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => edit(m.title, m.body)}
              className="flex min-w-0 flex-1 justify-between gap-3 py-1.5 text-left hover:text-accent-blue"
            >
              <span className="truncate text-ink">{m.title || "(untitled)"}</span>
              <span className="shrink-0 text-ink-muted">{new Date(m.savedAt).toLocaleString()}</span>
            </button>
            <button
              type="button"
              aria-label={`Delete ${m.title || "(untitled)"}`}
              onClick={() => remove(i)}
              className="shrink-0 px-1 text-ink-muted hover:text-red-400"
            >
              ✕
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
