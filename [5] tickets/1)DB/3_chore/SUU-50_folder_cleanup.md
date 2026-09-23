# SUU-50 chore(db): 데이터셋별 폴더 구조와 경로 정리

## 목표
DB 데이터 저장소와 테스트를 데이터셋별 폴더로 구분하고, 실행 코드와 문서의 경로를 새 구조에 맞춘다.

## 건드릴 파일
- 이동: `[2] db/1_eCFR` 등 데이터 저장 폴더 4개 → `[2] db/1) eCFR` 등 번호·이름 표기 폴더
- 이동: `[2] db/tests/test_*.py`, `[2] db/tests/fixtures/*` → 데이터셋별 테스트·fixture 폴더
- 수정: `[2] db/pipeline/1_eCFR/ecfr_collect.py`, `ecfr_parse.py`
- 수정: DB 구축 계획 4개, 워크플로 규칙, 기존 티켓의 경로 참조
- 추가: 빈 Federal Register·ECHO 테스트 폴더의 `.gitkeep`

## 완료 기준
- eCFR 실행 진입점이 `[2] db/1) eCFR`을 raw·parsed 저장 루트로 사용한다.
- eCFR와 ADI+CAA 테스트 및 fixture가 각각 같은 데이터셋 폴더에 있다.
- 저장소 문서에 옛 데이터 루트와 옛 공용 테스트 경로가 남지 않는다.
- `python -m pytest`가 전부 통과한다.
