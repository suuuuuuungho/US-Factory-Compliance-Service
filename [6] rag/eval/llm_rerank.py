"""SUU-135: 저장된 hybrid+규칙 상위 20조문을 OpenAI LLM으로 다시 줄 세워 채점한다.

사용법 (레포 루트에서):
  python "[6] rag/eval/llm_rerank.py" --run-id 2026-09-18_hybrid_v2 [--model gpt-4o-mini] [--limit 3] [--workers 8]
  → results/<run-id>_llm_<model>.jsonl + 점수판·토큰·비용 출력

- 입력: results/<run-id>.jsonl 의 ranked_all(Kanon 리랭크 전체 순위) → 규칙(SUU-134) → 상위 TOP_N 조문
- 조문 본문: rag_chunk 첫 body 청크(chunk_key …/<section_key>/0)의 context_text + chunk_text 앞 HEAD_CHARS자.
  cache/section_heads.json 에 캐시(Supabase 읽기만).
- LLM은 상위 TOP_N 안의 순서만 바꾼다. 답에 빠진 조문은 원래 순서로 뒤에 붙인다.
"""
from __future__ import annotations

import argparse
import json
from concurrent.futures import ThreadPoolExecutor
import os
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent.parent / "[2] db/pipeline/5_rag"))
from ecfr_search import RULES, apply_rank_rules  # noqa: E402
from run_eval import load_env  # noqa: E402
from sweep_rules import score  # noqa: E402

RESULTS = HERE / "results"
HEADS_CACHE = HERE / "cache" / "section_heads.json"
TOP_N = 20
HEAD_CHARS = 3000
PRICE_PER_M = {"gpt-4o-mini": (0.15, 0.60), "gpt-5-mini": (0.25, 2.00)}  # (input, output) USD per 1M tokens

SYSTEM = (
    "You are an expert on U.S. EPA air toxics rules (40 CFR Part 63, NESHAP). "
    "A factory describes its situation and asks which rule applies. You get candidate sections, each with a key and the start of its text. "
    "Rank ALL candidates from most to least relevant for answering the question. "
    "Most relevant = the section the EPA would cite to answer (applicability, definitions, or the specific requirement asked about). "
    "Reply with only a JSON array of the candidate numbers, most relevant first, containing every number exactly once."
)


def ruled_sections(line: dict) -> list[dict]:
    """ranked_all → 규칙(SUU-134) 적용한 조문 순위 전체."""
    sections = [{"section_key": k, "subpart": sp, "score": s} for k, sp, s in line["ranked_all"]]
    return apply_rank_rules(sections, **RULES)


def top_sections(line: dict) -> list[dict]:
    return ruled_sections(line)[:TOP_N]


def build_rerank_prompt(question: str, sections: list[dict]) -> str:
    parts = [f"QUESTION:\n{question}\n", f"CANDIDATES ({len(sections)}):"]
    for i, s in enumerate(sections, 1):
        parts.append(f"\n[{i}] key: {s['section_key']} (Subpart {s['subpart']})\n{s.get('text', '')[:HEAD_CHARS]}")
    parts.append("\nReturn a JSON array of all candidate numbers, most relevant first.")
    return "\n".join(parts)


def parse_ranking(text: str, keys: list[str]) -> list[str]:
    """답의 후보 번호(1부터) 순서대로 키를 뽑는다. 번호가 없으면 키 문자열 순서로. 빠진 키는 원래 순서로 뒤에 붙인다."""
    ordered: list[str] = []
    for n in re.findall(r"\d+", text):
        i = int(n) - 1
        if 0 <= i < len(keys) and keys[i] not in ordered:
            ordered.append(keys[i])
    if not ordered:
        found = [(m.start(), key) for key in keys if (m := re.search(re.escape(key) + r"(?![\w.])", text))]
        ordered = [k for _, k in sorted(found)]
    return ordered + [k for k in keys if k not in ordered]


def rerank_line(line: dict, ask, *, heads: dict[str, str]) -> dict:
    """한 케이스: ask(prompt) -> 답 텍스트. 상위 TOP_N만 LLM 순서로 바꾼 ranked_all을 돌려준다."""
    ruled = ruled_sections(line)
    head, tail = ruled[:TOP_N], ruled[TOP_N:]
    for s in head:
        s["text"] = heads.get(s["section_key"], "")
    keys = [s["section_key"] for s in head]
    answer = ask(build_rerank_prompt(line.get("question", ""), head))
    order = parse_ranking(answer, keys)
    subpart = {s["section_key"]: s["subpart"] for s in head}
    ranked = [[k, subpart[k]] for k in order] + [[s["section_key"], s["subpart"]] for s in tail]
    return {"case_id": line["case_id"], "gold_sections": line["gold_sections"], "llm_order": order, "ranked_all": ranked, "answer": answer}


def fetch_heads(section_keys: list[str]) -> dict[str, str]:
    """조문별 첫 body 청크의 context_text + chunk_text 앞부분. 캐시에 없는 것만 Supabase에서 읽는다."""
    heads = json.loads(HEADS_CACHE.read_text(encoding="utf-8")) if HEADS_CACHE.exists() else {}
    missing = [k for k in section_keys if k not in heads]
    if missing:
        from supabase import create_client
        client = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SECRET_KEY"])
        release_id = client.table("common_dataset_current").select("release_id").eq("dataset", "ecfr").execute().data[0]["release_id"]
        for i, key in enumerate(missing, 1):
            rows = (client.table("rag_chunk").select("context_text,chunk_text").eq("release_id", release_id)
                    .like("chunk_key", f"%/{key}/0").limit(1).execute().data)
            text = f"{rows[0].get('context_text') or ''}\n{rows[0]['chunk_text']}" if rows else ""
            heads[key] = text[:HEAD_CHARS]
            if i % 50 == 0:
                print(f"  heads fetched {i}/{len(missing)}", flush=True)
        HEADS_CACHE.parent.mkdir(exist_ok=True)
        HEADS_CACHE.write_text(json.dumps(heads, ensure_ascii=False), encoding="utf-8")
    return heads


def scoreboard(lines: list[dict]) -> dict:
    scores = [score(l["gold_sections"], l["ranked_all"]) for l in lines]
    board = {m: round(sum(s[m] for s in scores) / len(scores), 3) for m in ("hit@5", "hit@20", "ndcg@10", "recall@20")}
    board["miss@20"] = [l["case_id"] for l, s in zip(lines, scores) if not s["hit@20"]]
    return board


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--model", default="gpt-4o-mini")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()
    load_env()
    from openai import OpenAI
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    lines = [json.loads(l) for l in (RESULTS / f"{args.run_id}.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    cases = [json.loads(l) for l in (HERE / "rag_eval_case_v2.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    questions = {c["case_id"]: c["question"] for c in cases}
    for line in lines:
        line["question"] = questions[line["case_id"]]
    lines = lines[: args.limit] if args.limit else lines
    heads = fetch_heads(sorted({s["section_key"] for l in lines for s in top_sections(l)}))

    usage = {"prompt_tokens": 0, "completion_tokens": 0}

    def ask(prompt: str) -> str:
        # gpt-5 계열은 temperature를 못 받고 추론 토큰이 출력에 포함된다
        extra = {"max_completion_tokens": 4000} if args.model.startswith("gpt-5") else {"temperature": 0, "max_tokens": 600}
        r = client.chat.completions.create(model=args.model, messages=[{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}], **extra)
        usage["prompt_tokens"] += r.usage.prompt_tokens
        usage["completion_tokens"] += r.usage.completion_tokens
        return r.choices[0].message.content or ""

    out_path = RESULTS / f"{args.run_id}_llm_{args.model}.jsonl"
    t0 = time.perf_counter()

    def one(line):
        out = rerank_line(line, ask, heads=heads)
        out["run_id"] = f"{args.run_id}_llm_{args.model}"
        out["model"] = args.model
        print(f"  {line['case_id']} ndcg {score(out['gold_sections'], out['ranked_all'])['ndcg@10']:.2f}", flush=True)
        return out

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        outs = list(pool.map(one, lines))
    out_path.write_text("".join(json.dumps(o, ensure_ascii=False) + "\n" for o in outs), encoding="utf-8")
    pin, pout = PRICE_PER_M.get(args.model, (0, 0))
    cost = usage["prompt_tokens"] / 1e6 * pin + usage["completion_tokens"] / 1e6 * pout
    print(f"{out_path.name}: {len(outs)} cases, {time.perf_counter() - t0:.0f}s, tokens {usage}, cost ${cost:.2f} ({args.model})")
    before = [{"case_id": l["case_id"], "gold_sections": l["gold_sections"], "ranked_all": [[s["section_key"], s["subpart"]] for s in ruled_sections(l)]} for l in lines]
    print("before:", scoreboard(before))
    print("after: ", scoreboard(outs))


if __name__ == "__main__":
    main()
