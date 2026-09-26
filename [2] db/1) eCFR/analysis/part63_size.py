"""40 CFR Part 63 원문(eCFR XML)의 크기를 잰다: 글자 수, 단어 수, 토큰 수.

실행: python "[2] db/1) eCFR/analysis/part63_size.py"
입력: raw/<날짜>/<해시>/title-40-part-63.xml (SUU-35 수집본, 가장 최근 것)
토큰: tiktoken o200k_base(gpt-4o·gpt-5 계열), cl100k_base(gpt-4 계열). XML 태그는 빼고 글자만 센다.
"""
from __future__ import annotations

import re
from pathlib import Path

import tiktoken
from lxml import etree

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    xml = sorted(ROOT.glob("raw/*/*/title-40-part-63.xml"))[-1]
    raw = xml.read_text(encoding="utf-8")
    text = re.sub(r"\s+", " ", " ".join(etree.fromstring(raw.encode("utf-8")).itertext())).strip()
    print("파일:", xml.relative_to(ROOT.parent))
    print(f"XML 글자 수(태그 포함): {len(raw):,}")
    print(f"본문 글자 수(태그 제외): {len(text):,}")
    print(f"단어 수: {len(text.split()):,}")
    for name in ("o200k_base", "cl100k_base"):
        print(f"토큰 수 {name}: {len(tiktoken.get_encoding(name).encode(text, disallowed_special=())):,}")


if __name__ == "__main__":
    main()
