"""SUU-69: raw/ 아래 as_of 폴더 중 가장 최근 것을 고르는 순수 함수만 테스트한다.

실제 Supabase 연동이 들어간 ``if __name__ == "__main__":`` 블록은 자동 테스트 대상이
아니다(티켓의 완료 기준 3번 — 코드 리뷰로만 확인).
"""
import pytest

from ecfr_ingest import _latest_as_of


def test_picks_the_most_recent_as_of_folder(tmp_path):
    raw_root = tmp_path / "raw"
    for as_of in ("2026-08-15", "2026-09-10", "2026-09-01"):
        (raw_root / as_of).mkdir(parents=True)

    assert _latest_as_of(raw_root) == "2026-09-10"


def test_raises_a_clear_error_when_raw_has_no_as_of_folders(tmp_path):
    raw_root = tmp_path / "raw"
    raw_root.mkdir()

    with pytest.raises(FileNotFoundError, match=str(raw_root)):
        _latest_as_of(raw_root)
