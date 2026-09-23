# SUU-60 feat(db): Dashboard 회신 PDF에서 페이지별 텍스트 추출

## 목표
저장된 Dashboard 회신 PDF 하나를 받아 페이지별 텍스트 목록을 뽑는 함수를 만든다. SUU-59(ADI 쪽)와 대칭.

## 건드릴 파일
- 만들 것: `[2] db/pipeline/4_ADI+CAA/dashboard_letters_text.py` — `extract_pages(pdf_bytes, *, reader_factory=...) -> list[dict]`
- 이미 있음 (수정 금지): `[2] db/tests/4_ADI+CAA/test_dashboard_letters_text.py`
- 이미 고침 (그대로 유지): `requirements.txt`에 `pypdf==6.16.1` 추가됨 (SUU-59 브랜치에도 같은 줄이 추가돼 있다. merge 순서와 상관없이 내용이 같으므로 충돌 나면 그대로 유지)

## 안 하는 것
- OCR, CFR 인용 파싱, DB 적재
- 저장된 PDF 파일들을 순회해서 전부 실행하는 진입점 (별도 티켓)
- `tests/` 아래 수정, `adi_letters_text.py`·`dashboard_letters.py`·`dashboard_letters_collect.py` 등 기존 파일 수정

## 완료 기준 ↔ 테스트
| 완료 기준 | 테스트 함수 |
|---|---|
| 디지털 PDF 한 건에서 페이지별 텍스트를 뽑는다 | `test_extracts_text_per_page_from_a_digital_pdf` |
| 글자를 못 뽑는 페이지는 빈 텍스트+실패 표시로 남기고 멈추지 않는다 | `test_failing_page_is_marked_failed_and_does_not_stop_the_rest` |

테스트 파일: `[2] db/tests/4_ADI+CAA/test_dashboard_letters_text.py`

## Codex 메모

### `dashboard_letters_text.py`
PDF 파일 형식은 ADI든 Dashboard든 같다(둘 다 `%PDF` 매직바이트를 확인해 저장한 원문). SUU-59의 `adi_letters_text.extract_pages`와 완전히 같은 로직이므로, 로직을 복붙하지 말고 import해서 그대로 다시 내보낸다. SUU-59가 먼저 merge되지 않았어도(브랜치가 독립적이므로) `adi_letters_text.py`를 그대로 작성해서 두면 된다.

```python
from __future__ import annotations

from adi_letters_text import extract_pages

__all__ = ["extract_pages"]
```

- `adi_letters_text.py`가 이 브랜치에 없다면(SUU-59가 아직 merge 전이라면), 먼저 SUU-59의 `[5] tickets/SUU-59.md` Codex 메모에 있는 `extract_pages` 구현을 `adi_letters_text.py`에 그대로 작성한 뒤 위처럼 재사용한다
- `pypdf`는 이미 `requirements.txt`에 추가됐다

### 흐름
Codex가 `dashboard_letters_text.py` 작성 → `python -m pytest` 초록 → commit·push·PR (제목 = 이 파일 첫 줄 + ` (SUU-60)`) → 사용자 merge
