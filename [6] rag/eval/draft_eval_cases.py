"""SUU-115: ADI·Dashboard 회신 PDF에서 평가셋 v2 초안을 만든다.

후보 고르기(텍스트·인용·v1 제외) → gpt-4o-mini 초안 → 자동 검사 → `rag_eval_case_v2.draft.jsonl`.
사람이 확인한 뒤 `rag_eval_case_v2.jsonl`로 옮긴다. 이 파일은 v1 파일을 건드리지 않는다.

    python draft_eval_cases.py --limit 10          # 표본
    python draft_eval_cases.py                     # 전부
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import warnings
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(REPO / "[2] db/pipeline/4_ADI+CAA")]

from adi_dashboard import parse_dashboard  # noqa: E402
from adi_letters_text import extract_pages  # noqa: E402

HERE = Path(__file__).parent
ADI_ROOT = REPO / "[2] db/4) ADI+CAA"
V1 = HERE / "rag_eval_case.jsonl"
DRAFT = HERE / "rag_eval_case_v2.draft.jsonl"
FIXTURE = json.loads((HERE.parent / "tests/fixtures/ecfr_part63_index_2026-09-11.json").read_text(encoding="utf-8"))
SECTIONS, SUBPARTS = set(FIXTURE["sections"]), set(FIXTURE["subparts"])
CITE = re.compile(r"\b63\.(\d{1,5})\b")
MAX_CHARS = 16_000  # 회신 본문 앞 12k + 뒤 4k (인용은 대개 앞이나 끝에 있다)
PRICE = {"gpt-4o-mini": (0.15, 0.60), "gpt-4o": (2.50, 10.00)}  # $/M input, output

SYSTEM = """You turn one EPA applicability determination letter (Clean Air Act, 40 CFR Part 63 NESHAP) into one retrieval-evaluation case. Return JSON only.

Fields:
- "question": 2-4 English sentences, first person plural ("We operate ..."), as the facility would ask BEFORE knowing EPA's answer. Include only the request side: facility type, process/equipment, materials/solvents/pollutants, size or throughput, state. Use ONLY facts written in the letter; never add, guess, or generalize anything, and name a rule in words only if the letter itself names it that way. Do NOT name the company, facility, city, or people, and do not open with "As the compliance manager". NEVER include any Part 63 subpart code (like PPPP, ZZZZ, HHHHHH), the word "subpart" followed by a code, or any section number (63.xxxx). Do not reveal or hint at EPA's answer.
- "evidence": 2-5 strings copied VERBATIM from the letter text (exact characters, 5-30 words each) that state the facts used in the question. Every fact in the question must be covered by one of them.
- "kind": "applicability" (whether/which rule or requirement applies to a process or source), "monitoring" (alternative monitoring/test method approval), "extension" (compliance or test deadline extension), or "other".
- "gold_subparts": Part 63 subpart codes EPA used as the basis of its decision, the subpart the question is about FIRST. Include "A" only if a General Provisions section (63.1-63.16) was part of the basis.
- "gold_citations": Part 63 sections EPA relied on for the decision, formatted "40 CFR 63.xxxx" (add a paragraph like "40 CFR 63.4481(a)" only when the letter pins that paragraph). Exclude sections that are merely mentioned in passing ("see also"). At least one.
- "verdict": one English sentence: applies / does not apply / partially applies, plus the reason. May contain codes and section numbers.
- "letter_date": "YYYY-MM-DD" of EPA's signed response, or null.
- "skip_reason": null normally. A short string if this letter should NOT become a case: it is not about Part 63 (e.g. only Part 60/61/70), is a withdrawal/cover letter without a determination, or the text is unreadable.
"""


def load_v1_refs() -> set[str]:
    return {json.loads(l)["source_ref"] for l in V1.read_text(encoding="utf-8").splitlines() if l.strip()}


def pdf_text(path: Path) -> str | None:
    """PDF 본문. 글자가 안 나오면(스캔본·깨짐) None."""
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            pages = extract_pages(path.read_bytes())
    except Exception:
        return None
    ok = sum(1 for p in pages if p["status"] == "ok")
    text = "\n".join(p["text"] for p in pages)
    if ok < max(1, len(pages) * 0.5) or len(text) < 800:
        return None
    return text


def cited_sections(text: str) -> list[str]:
    return sorted({f"63.{n}" for n in CITE.findall(text) if f"63.{n}" in SECTIONS})


def candidates() -> list[dict]:
    """텍스트가 나오고 Part 63 조문 인용이 있으며 v1에 없는 회신."""
    v1 = load_v1_refs()
    out = []

    details = {r["control_number"]: r for r in json.loads(
        next(ADI_ROOT.glob("adi_details/raw/*/details.json")).read_text(encoding="utf-8"))}
    for path in sorted(ADI_ROOT.glob("adi_letters/*/raw/*/*/*.pdf")):
        cn = path.stem
        if cn in v1 or cn not in details:
            continue
        text = pdf_text(path)
        if text and (cites := cited_sections(text)):
            meta = details[cn]
            out.append({
                "source": "adi", "source_ref": cn, "case_id": f"adi-{cn}",
                "title": meta["title"], "letter_date_raw": meta["letter_date_raw"],
                "abstract": meta["abstract"], "affected": "", "text": text, "cites": cites,
            })

    dashboard_html = next(ADI_ROOT.glob("caa_dashboard/raw/*/*/*.html")).read_bytes()
    by_url = {}
    for m in ADI_ROOT.glob("dashboard_letters/raw/*/manifest.json"):
        for e in json.loads(m.read_text(encoding="utf-8")):
            by_url[e["source_url"]] = m.parent / Path(e["path"]).relative_to("raw/" + m.parent.name)
    for row in parse_dashboard(dashboard_html):
        url = row["canonical_url"]
        if url in v1 or url not in by_url or not any(s["part"] == "63" for s in row["affected_subparts"]):
            continue
        text = pdf_text(by_url[url])
        if text and (cites := cited_sections(text)):
            slug = re.sub(r"[^a-z0-9]+", "-", row["facility_name"].lower()).strip("-")[:40]
            out.append({
                "source": "dashboard", "source_ref": url, "case_id": f"dashboard-{slug}",
                "title": row["title"], "letter_date_raw": row["link_text"],
                "abstract": "", "affected": row["affected_subpart_raw"], "text": text, "cites": cites,
            })
    return out


def build_request(cand: dict) -> list[dict]:
    text = cand["text"]
    if len(text) > MAX_CHARS:
        text = text[:12_000] + "\n[...]\n" + text[-4_000:]
    user = (
        f"Source: {cand['source']} / {cand['source_ref']}\nTitle: {cand['title']}\n"
        f"Letter date (from listing): {cand['letter_date_raw']}\n"
        + (f"Affected subparts (from listing): {cand['affected']}\n" if cand["affected"] else "")
        + (f"Abstract (from listing):\n{cand['abstract']}\n" if cand["abstract"] else "")
        + f"Part 63 sections found in the text: {', '.join(cand['cites'])}\n\n--- LETTER TEXT ---\n{text}"
    )
    return [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]


def squash(t: str) -> str:
    """소문자·영숫자만(띄어쓰기도 제거). PDF가 단어를 끊어 놓아도('gran ulated') 맞춰 보려고."""
    return re.sub(r"[^a-z0-9]+", "", t.lower())


RULE_NAMES = (
    re.compile(r"\b(?:NESHAP|MACT)\s+for\s+([A-Za-z ,&/-]{3,60}?)(?=[.,;?]|\s(?:apply|applies|applicable|to|and|or)\b)"),
    re.compile(r"\b((?:[A-Za-z&/-]+\s){1,4}?)(?:NESHAP|MACT)\b"),
)
GENERIC = {"national", "emission", "emissions", "standards", "standard", "hazardous", "pollutants", "pollutant", "source", "sources", "major",
           "under", "these", "those", "which", "would", "should", "could", "about", "there", "their", "requirements", "applicable"}


def grounding_problems(question: str, evidence: list[str], text: str) -> list[str]:
    """지어낸 말 검사: 근거 문장이 회신에 그대로 있어야 하고, 질문에 쓴 규정 이름의 단어가 회신에 있어야 한다."""
    out = []
    body = squash(text)
    if not evidence:
        out.append("no evidence")
    for e in evidence:
        if squash(e) not in body:
            out.append(f"evidence not in letter: {e[:40]}")
    for rx in RULE_NAMES:
        for name in rx.findall(question):
            for w in re.findall(r"[A-Za-z]{5,}", name):
                if w.lower() not in GENERIC and w.lower() not in body:
                    out.append(f"rule name word not in letter: {w}")
    return out


def problems(case: dict) -> list[str]:
    """SUU-46 테스트 규칙과 같은 자동 검사. 빈 목록이면 통과."""
    out = []
    q = case["question"]
    if re.search(r"\b63\.\d", q):
        out.append("question cites 63.x")
    for code in case["gold_subparts"]:
        if code not in SUBPARTS:
            out.append(f"unknown subpart {code}")
        if re.search(rf"\bsubpart\s+{code}\b", q, re.IGNORECASE) or (len(code) >= 2 and re.search(rf"\b{code}\b", q)):
            out.append(f"question leaks {code}")
    if not case["gold_subparts"]:
        out.append("no subpart")
    if not case["gold_citations"]:
        out.append("no citation")
    for c in case["gold_citations"]:
        m = re.match(r"^40 CFR (63\.\d+)(\([A-Za-z0-9]+\))*$", c)
        if not m:
            out.append(f"bad citation {c}")
        elif m.group(1) not in SECTIONS:
            out.append(f"unknown section {c}")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int)
    ap.add_argument("--model", default="gpt-4o-mini", choices=list(PRICE))
    args = ap.parse_args()
    for line in (REPO / ".env").read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())
    from openai import OpenAI
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    cands = candidates()
    print(f"candidates {len(cands)} (adi {sum(c['source'] == 'adi' for c in cands)}, dashboard {sum(c['source'] == 'dashboard' for c in cands)})")
    if args.limit:
        cands = cands[:args.limit // 2] + [c for c in cands if c["source"] == "dashboard"][:args.limit - args.limit // 2]

    tokens_in = tokens_out = 0
    lines, stats = [], {"drafted": 0, "skipped": 0, "passed": 0, "error": 0}
    for i, cand in enumerate(cands, 1):
        try:
            resp = client.chat.completions.create(
                model=args.model, max_tokens=900, temperature=0,
                response_format={"type": "json_object"}, messages=build_request(cand),
            )
            tokens_in += resp.usage.prompt_tokens
            tokens_out += resp.usage.completion_tokens
            draft = json.loads(resp.choices[0].message.content)
        except Exception as e:
            stats["error"] += 1
            print(f"  [{i}] {cand['case_id']} error: {e}")
            continue
        if draft.get("skip_reason"):
            stats["skipped"] += 1
            print(f"  [{i}] {cand['case_id']} skip: {draft['skip_reason']}")
            continue
        stats["drafted"] += 1
        date = draft.get("letter_date") or ""
        case = {
            "case_id": cand["case_id"] + (f"-{date}" if cand["source"] == "dashboard" and date else ""),
            "question": (draft.get("question") or "").strip(),
            "gold_subparts": [s.strip().upper() for s in draft.get("gold_subparts") or []],
            "gold_citations": [c.strip() for c in draft.get("gold_citations") or []],
            "source": cand["source"],
            "source_ref": cand["source_ref"],
            "notes": f"{(draft.get('verdict') or '').strip()} Letter {date or cand['letter_date_raw']}.".replace("�", "'"),
        }
        evidence = [str(e) for e in draft.get("evidence") or []]
        probs = problems(case) + grounding_problems(case["question"], evidence, cand["text"])
        stats["passed"] += not probs
        lines.append({**case, "_kind": draft.get("kind"), "_problems": probs, "_evidence": evidence, "_cites_in_text": cand["cites"], "_title": cand["title"]})
        if i % 20 == 0:
            print(f"  {i}/{len(cands)} in={tokens_in} out={tokens_out}", flush=True)

    DRAFT.write_text("".join(json.dumps(l, ensure_ascii=False) + "\n" for l in lines), encoding="utf-8")
    pi, po = PRICE[args.model]
    cost = (tokens_in * pi + tokens_out * po) / 1e6
    print(json.dumps({**stats, "tokens_in": tokens_in, "tokens_out": tokens_out, "cost_usd": round(cost, 3), "model": args.model}, indent=1))


if __name__ == "__main__":
    main()
