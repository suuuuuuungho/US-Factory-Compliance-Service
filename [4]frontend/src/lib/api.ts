// SUU-163: POST {NEXT_PUBLIC_API_URL}/ask. 응답 모양은 [3] backend/app/answer.py
export type Criterion = { criterion: string; citations: string[] };
export type Candidate = { subpart: string; title: string; criteria: Criterion[] };
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
