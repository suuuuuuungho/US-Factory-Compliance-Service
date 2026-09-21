"use client";
// SUU-216: Send 뒤 답이 올 때까지 보이는 대기 화면. 서버는 진행 상황을 안 보내주므로 단계는 지난 시간(초)으로 고른다.
import { useEffect, useState } from "react";

export const STEPS = [
  { at: 0, text: "Searching 40 CFR Part 63 for rules that match your process…" },
  { at: 6, text: "Reading the candidate subparts…" },
  { at: 14, text: "Writing the checklist and citations…" },
  { at: 25, text: "Almost there — the server is taking a little longer than usual…" },
] as const;

export default function Waiting() {
  const [seconds, setSeconds] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setSeconds((s) => s + 1), 1000);
    return () => clearInterval(id);
  }, []);
  const step = [...STEPS].reverse().find((s) => seconds >= s.at) ?? STEPS[0];

  return (
    <div role="status" className="flex w-full max-w-[640px] flex-col items-center gap-3 rounded-md border border-hairline bg-surface-1 px-6 py-8">
      <span aria-hidden="true" className="h-6 w-6 animate-spin rounded-full border-2 border-hairline border-t-ink" />
      <p className="text-lg font-medium text-ink">Please wait a moment…</p>
      <p className="text-sm text-ink-muted">{step.text}</p>
    </div>
  );
}
