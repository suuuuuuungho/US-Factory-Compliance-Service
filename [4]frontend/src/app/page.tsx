"use client";
// SUU-163: 질문 → POST /ask → 후보 Subpart 카드 + 체크리스트. 디자인 없음.
import { useState } from "react";
import { ask, type AskResult } from "../lib/api";

export default function Home() {
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AskResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setResult(null);
    setError(null);
    try {
      setResult(await ask(question));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-6 p-8">
      <h1 className="text-2xl font-semibold">US Factory Compliance — 40 CFR Part 63</h1>
      <form onSubmit={onSubmit} className="flex flex-col gap-2">
        <textarea
          className="rounded border p-2"
          rows={3}
          placeholder="Describe the process, e.g. we solvent weld plastic parts"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
        />
        <button type="submit" disabled={loading} className="self-start rounded border px-4 py-2 disabled:opacity-50">
          Ask
        </button>
      </form>

      {loading && <p role="status">Searching the regulations… (10–20 s)</p>}
      {error && <p className="text-red-700">{error}</p>}

      {result && result.answer === null && (
        <ul className="list-disc pl-6">
          {result.issues.map((issue) => <li key={issue}>{issue}</li>)}
        </ul>
      )}

      {result?.answer?.candidates.map((c) => (
        <section key={c.subpart} className="rounded border p-4">
          <h2 className="font-semibold">Subpart {c.subpart} — {c.title}</h2>
          <ul className="list-disc pl-6">
            {c.criteria.map((cr, i) => (
              <li key={i}>
                {cr.criterion} <span className="text-sm text-zinc-500">{cr.citations.join(", ")}</span>
              </li>
            ))}
          </ul>
        </section>
      ))}

      {result?.answer && (
        <section>
          <h2 className="font-semibold">Checklist</h2>
          <ul className="list-disc pl-6">
            {result.answer.checklist.map((item) => <li key={item}>{item}</li>)}
          </ul>
        </section>
      )}

      <p className="mt-auto text-sm text-zinc-500">
        This is not a final applicability determination. The plant decides; this page gives the criteria and where to look.
      </p>
    </main>
  );
}
