"""CAA Dashboard 판정서한에서 EPA 회신 기간(요청일 → 회신일)을 잰다.

실행: python "[2] db/4) ADI+CAA/analysis/epa_response_days.py"
입력: dashboard_letters/raw/<날짜>/**/*.pdf (SUU-225 수집본) + caa_dashboard/raw/<날짜>/**/caa-dashboard.html
출력: analysis/epa_response_days.jsonl (서한별) + 화면 요약

회신일 = 서한 머리(인사말 "Dear ..." 앞)의 첫 날짜(Month D, YYYY). 머리에 날짜가 없으면(레터헤드가 그림인 경우)
        EPA 파일 이름 끝의 날짜(예 `..._6-16-20.pdf`)를 쓴다. 둘 다 없으면 못 읽은 것으로 뺀다.
요청일 = ① "in response to your letter dated ..."처럼 요청을 가리키는 문장 주변 400자 안의 첫 날짜(cue),
        ② 없으면 인사말 뒤 첫 600자(보통 첫 문단) 안의 첫 날짜(first). 회신일보다 뒤거나 3년 넘게 앞인 날짜는 건너뛴다.
스캔본이라 글자를 못 읽는 PDF(no_text)는 뺀다. OCR은 안 한다.
검산 = EPA 파일 이름 끝의 날짜(예 `..._6-16-20.pdf`)와 읽은 회신일이 같은지 비교해 일치율을 찍는다.
"""
from __future__ import annotations

import json
import re
import statistics
import sys
from datetime import date
from pathlib import Path

import pypdf

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parents[0] / "pipeline" / "4_ADI+CAA"))
from adi_dashboard import parse_dashboard  # noqa: E402

LETTERS = ROOT / "dashboard_letters" / "raw"
DASHBOARD = ROOT / "caa_dashboard" / "raw"
OUT = Path(__file__).with_suffix(".jsonl")

MONTHS = "January|February|March|April|May|June|July|August|September|October|November|December"
DATE = re.compile(rf"({MONTHS})\s+(\d{{1,2}}),?\s+(\d{{4}})")
REQUEST_CUE = re.compile(
    r"(in response to|in reference to|respon(?:ds?|ding) to|regarding|received|acknowledg\w*)[^.]{0,120}?"
    r"(letter|request|e-?mail|petition|submittal|submission|correspondence|application|notification|inquiry)",
    re.IGNORECASE,
)
SALUTATION = re.compile(r"\bDear\b[^:,\n]{0,80}[:,]")
FILENAME_DATE = re.compile(r"[_-](\d{1,2})-(\d{1,2})-(\d{2,4})\.pdf$")
MAX_DAYS = 3 * 365


def _date(m: re.Match) -> date:
    return date(int(m.group(3)), MONTHS.split("|").index(m.group(1)) + 1, int(m.group(2)))


def first_pages(pdf: Path, n: int = 2) -> str:
    reader = pypdf.PdfReader(str(pdf))
    text = "\n".join((page.extract_text() or "") for page in reader.pages[:n])
    return re.sub(r"\s+", " ", text)


def parse_letter(text: str, fallback_response: str | None = None) -> dict:
    if not DATE.search(text):
        return {"response_on": None, "request_on": None, "days": None, "why": "no_text"}
    salutation = SALUTATION.search(text)
    header_end = salutation.start() if salutation else len(text)
    head = DATE.search(text[:header_end])
    if head is not None:
        response_on, source = _date(head), "header"
    elif fallback_response:
        response_on, source = date.fromisoformat(fallback_response), "filename"
    else:
        return {"response_on": None, "request_on": None, "days": None, "why": "no_response_date"}
    body_start = salutation.end() if salutation else (head.end() if head else 0)

    def usable(d: date) -> bool:
        return 0 < (response_on - d).days <= MAX_DAYS

    request_on, how = None, None
    for cue in REQUEST_CUE.finditer(text, body_start):
        window = text[cue.start(): cue.end() + 400]
        cands = [d for d in (_date(m) for m in DATE.finditer(window)) if usable(d)]
        if cands:
            request_on, how = cands[0], "cue"
            break
    if request_on is None:
        cands = [d for d in (_date(m) for m in DATE.finditer(text[body_start: body_start + 600])) if usable(d)]
        if cands:
            request_on, how = cands[0], "first"
    if request_on is None:
        return {"response_on": response_on.isoformat(), "response_source": source, "request_on": None, "days": None, "why": "no_request_date"}
    return {"response_on": response_on.isoformat(), "response_source": source, "request_on": request_on.isoformat(),
            "days": (response_on - request_on).days, "why": how}


def filename_date(url: str | None) -> str | None:
    m = FILENAME_DATE.search(url or "")
    if not m:
        return None
    year = int(m.group(3))
    year = year + 2000 if year < 100 else year
    try:
        return date(year, int(m.group(1)), int(m.group(2))).isoformat()
    except ValueError:
        return None


def main() -> None:
    manifest = json.loads(next(LETTERS.rglob("manifest.json")).read_text(encoding="utf-8"))
    by_url = {}
    for row in parse_dashboard(next(DASHBOARD.rglob("caa-dashboard.html")).read_bytes()):
        for key in (row["canonical_url"], row["source_url"]):
            if key:
                by_url[key] = row
    rows = []
    for item in manifest:
        pdf = LETTERS.parent / item["path"]
        if not pdf.exists():
            continue
        dash = by_url.get(item["source_url"]) or by_url.get(item["final_url"]) or {}
        parts = {p["part"] for p in dash.get("affected_subparts", [])}
        fn_date = filename_date(item["final_url"])
        rows.append({"file": item["name"], "facility": dash.get("facility_name"), "part63": "63" in parts,
                     "filename_date": fn_date, **parse_letter(first_pages(pdf), fn_date)})
    OUT.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")

    def summary(label: str, subset: list[dict]) -> None:
        days = sorted(r["days"] for r in subset if r["days"] is not None)
        if not days:
            print(f"{label}: 0건")
            return
        q = statistics.quantiles(days, n=4)
        cue = sum(r["why"] == "cue" for r in subset)
        print(f"{label}: PDF {len(subset)}건 → 요청일·회신일 둘 다 읽힌 {len(days)}건(cue {cue} · first {len(days) - cue}) | "
              f"중앙값 {statistics.median(days):.0f}일 · 평균 {statistics.fmean(days):.0f}일 · "
              f"Q1 {q[0]:.0f} · Q3 {q[2]:.0f} · 6개월(180일) 이상 {sum(d >= 180 for d in days) / len(days):.0%} · "
              f"1년 이상 {sum(d >= 365 for d in days) / len(days):.0%}")

    summary("전체", rows)
    summary("Part 63 표기", [r for r in rows if r["part63"]])
    both = [r for r in rows if r["filename_date"] and r["response_on"] and r.get("response_source") == "header"]
    same = sum(r["filename_date"] == r["response_on"] for r in both)
    print(f"검산: 머리 날짜와 파일 이름 날짜가 둘 다 있는 {len(both)}건 중 같은 것 {same}건 ({same / len(both):.0%})")
    print("회신일 출처:", {k: sum(r.get("response_source") == k for r in rows) for k in ("header", "filename")})
    print("못 읽은 이유:", {k: sum(r["why"] == k for r in rows) for k in ("no_text", "no_response_date", "no_request_date")})
    print("결과 파일:", OUT)


if __name__ == "__main__":
    main()
