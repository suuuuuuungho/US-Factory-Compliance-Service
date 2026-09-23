# SUU-59 feat(db): ADI 회신 PDF에서 페이지별 텍스트 추출

## 목표
저장된 ADI 회신 PDF 하나를 받아 페이지별 텍스트 목록을 뽑는 함수를 만든다.

## 건드릴 파일
- 만들 것: `[2] db/pipeline/4_ADI+CAA/adi_letters_text.py` — `extract_pages(pdf_bytes, *, reader_factory=...) -> list[dict]`
- 이미 있음 (수정 금지): `[2] db/tests/4_ADI+CAA/test_adi_letters_text.py`
- 이미 고침 (그대로 유지): `requirements.txt`에 `pypdf==6.16.1` 추가됨

## 안 하는 것
- OCR (글자가 없는/깨진 페이지를 이미지로 인식) — `status: "empty"`/`"failed"`로만 남긴다
- CFR 인용 파싱, DB 적재
- 저장된 PDF 파일들을 순회해서 전부 실행하는 진입점 (별도 티켓)
- `tests/` 아래 수정, `adi_letters.py`·`adi_letters_collect.py` 등 기존 파일 수정

## 완료 기준 ↔ 테스트
| 완료 기준 | 테스트 함수 |
|---|---|
| 디지털 PDF 한 건에서 페이지별 텍스트를 뽑는다 | `test_extracts_text_per_page_from_a_digital_pdf` |
| 글자를 못 뽑는 페이지는 빈 텍스트+실패 표시로 남기고 멈추지 않는다 | `test_failing_page_is_marked_failed_and_does_not_stop_the_rest` |

테스트 파일: `[2] db/tests/4_ADI+CAA/test_adi_letters_text.py`

## Codex 메모

### `adi_letters_text.py`
```python
from __future__ import annotations

import io
from typing import Any, Callable

from pypdf import PdfReader


def _default_reader(pdf_bytes: bytes) -> PdfReader:
    return PdfReader(io.BytesIO(pdf_bytes))


def extract_pages(
    pdf_bytes: bytes,
    *,
    reader_factory: Callable[[bytes], Any] = _default_reader,
) -> list[dict[str, Any]]:
    reader = reader_factory(pdf_bytes)
    pages: list[dict[str, Any]] = []
    for index, page in enumerate(reader.pages):
        page_no = index + 1
        try:
            text = page.extract_text() or ""
        except Exception as error:
            pages.append({"page_no": page_no, "text": "", "status": "failed", "reason": str(error)})
            continue
        status = "ok" if text.strip() else "empty"
        pages.append({"page_no": page_no, "text": text, "status": status})
    return pages


__all__ = ["extract_pages"]
```
- `page_no`는 1부터 시작한다
- 반환 항목 shape: `{"page_no": int, "text": str, "status": "ok"|"empty"|"failed"}` — `"failed"`일 때만 `"reason"` 키가 추가된다
- `reader_factory`는 테스트에서 가짜 리더를 주입하기 위한 구멍이다. 실제 실행에서는 기본값(`pypdf.PdfReader`)을 그대로 쓴다
- 한 페이지에서 예외가 나도 나머지 페이지는 계속 처리한다 (다른 collect 함수들의 "청크 하나 실패해도 계속" 패턴과 동일한 정신)
- `pypdf`는 이미 `requirements.txt`에 추가됐다 (`pip install -r requirements.txt`)

### 흐름
Codex가 `adi_letters_text.py` 작성 → `python -m pytest` 초록 → commit·push·PR (제목 = 이 파일 첫 줄 + ` (SUU-59)`) → 사용자 merge
