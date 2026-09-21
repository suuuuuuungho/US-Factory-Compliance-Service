// SUU-163: POST {NEXT_PUBLIC_API_URL}/ask. 응답 모양은 [3] backend/app/answer.py
export type Criterion = { criterion: string; citations: string[] };
export type Candidate = {
  subpart: string;
  title: string;
  criteria: Criterion[];
};
export type AskResult = {
  answer: { candidates: Candidate[]; checklist: string[] } | null;
  sections: { section_key: string; subpart: string }[];
  issues: string[];
  tokens: { prompt: number; completion: number };
  cost_usd: number;
  ms: number;
};

export async function ask(question: string): Promise<AskResult> {
  const base = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"; // 호출 시점에 읽는다(테스트가 vi.stubEnv 한다)
  const r = await fetch(`${base}/ask`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ question }),
  });
  if (!r.ok) throw new Error(`Server error (${r.status})`); // Render가 잠들었다 깨면 색인 전까지 503(SUU-167)
  return r.json();
}

// SUU-164: 인용 → GET /section/{key}
export type Section = { section_key: string; subpart: string; text: string };

/** "40 CFR 63.4481(a)(1)" → "section-63.4481". 63.숫자 가 없으면 null (표 인용 등) */
export function citationToSectionKey(citation: string): string | null {
  const m = citation.match(/63\.(\d+)/);
  return m ? `section-63.${m[1]}` : null;
}

// SUU-189: "40 CFR 63.460(a)(1)" → "a". 문단 표시가 없으면 null
export function citationToParagraph(citation: string): string | null {
  const m = citation.match(/63\.\d+\(([a-z]+)\)/);
  return m ? m[1] : null;
}

/** 조문 본문("(a) …\n\n(1) …\n\n(b) …")에서 문단 letter 부터 다음 상위 문단 앞까지. 못 찾으면 null */
export function paragraphText(text: string, letter: string): string | null {
  const pieces = text.split("\n\n");
  const start = pieces.findIndex((p) => p.startsWith(`(${letter})`));
  if (start < 0) return null;
  const next = `(${String.fromCharCode(letter.charCodeAt(0) + 1)})`;
  let end = pieces.findIndex((p, i) => i > start && p.startsWith(next));
  if (end < 0) end = pieces.length;
  return pieces.slice(start, end).join("\n\n");
}

export async function getSection(key: string): Promise<Section> {
  const base = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  const r = await fetch(`${base}/section/${key}`);
  if (!r.ok) throw new Error(`Section not found (${r.status})`);
  return r.json();
}
