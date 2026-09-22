"""SUU-222: 목록의 facility_name + 편지 본문의 주소 줄(주) → adi_facility_candidate 행.

정규화한 이름이 ECHO 시설 이름과 정확히 같고, ECHO 시설의 state 가 편지 본문에서 찾은 주(예: "Logansport, IN 46947",
"Calera, Alabama 35040")에 들어 있을 때만 후보다. 이름만으로 확정하지 않으므로 review_status=검토 전. 퍼지 매칭 없음.
"""
from __future__ import annotations

from adi_facilities import build_facility_index, extract_facility_candidates, normalize_name, states_in_text

DOC = "aaaaaaaa-aaaa-5aaa-8aaa-aaaaaaaaaaaa"
ECHO = [
    {"pgm_sys_id": "IN0001", "name": "ESSROC CEMENT CORP", "state": "IN"},
    {"pgm_sys_id": "PA0001", "name": "ESSROC CEMENT CORP", "state": "PA"},
    {"pgm_sys_id": "AL0001", "name": "LHOIST NORTH AMERICA OF ALABAMA LLC", "state": "AL"},
    {"pgm_sys_id": "IN0002", "name": "ESSROC CEMENT CORP - SPEED PLANT", "state": "IN"},
]


def test_normalize_name_ignores_case_punctuation_and_legal_suffix():
    assert normalize_name("Essroc Cement Corp.") == normalize_name("ESSROC CEMENT CORP") == "ESSROC CEMENT"
    assert normalize_name("Lhoist North America of Alabama, LLC") == normalize_name("LHOIST NORTH AMERICA OF ALABAMA LLC")
    assert normalize_name("Essroc Cement Corp.") != normalize_name("Essroc Cement Corp - Speed Plant")
    assert normalize_name("  A & B   Co.,  Inc. ") == normalize_name("A AND B")


def test_states_in_text_reads_code_and_full_name_from_address_lines():
    assert states_in_text("3084 West C.R. 225 South\nLogansport, IN 46947\nRe: test") == {"IN"}
    assert states_in_text("7444 AL-25\nCalera, Alabama 35040") == {"AL"}
    assert states_in_text("ATLANTA, GEORGIA 30303-8960\nJamestown, North Carolina  27282") == {"GA", "NC"}
    assert states_in_text("No address here. IN this letter we approve.") == set()


def test_exact_name_and_state_match_gives_one_candidate():
    index = build_facility_index(ECHO)
    text = "Mr. Brian Graf\nEssroc Cement Corp.\n3084 West C.R. 225 South\nLogansport, IN 46947\nDear Mr. Graf:"

    candidates = extract_facility_candidates(DOC, ["Essroc Cement Corp."], text, index)

    assert candidates == [{
        "document_id": DOC,
        "echo_pgm_sys_id": "IN0001",
        "match_evidence": "name:ESSROC CEMENT;state:IN",
        "review_status": "검토 전",
    }]


def test_no_exact_match_gives_zero_candidates():
    index = build_facility_index(ECHO)

    assert extract_facility_candidates(DOC, ["Essroc Cement"], "Logansport, IN 46947", index) == []
    assert extract_facility_candidates(DOC, ["Essroc Cement Corp."], "Logansport, OH 46947", index) == []
    assert extract_facility_candidates(DOC, ["Essroc Cement Corp."], "no address at all", index) == []
    assert extract_facility_candidates(DOC, [None, ""], "Logansport, IN 46947", index) == []


def test_two_echo_rows_with_same_name_and_state_both_become_candidates_once():
    echo = ECHO + [{"pgm_sys_id": "IN0009", "name": "Essroc Cement Corp", "state": "IN"}]
    index = build_facility_index(echo)

    candidates = extract_facility_candidates(DOC, ["Essroc Cement Corp.", "ESSROC CEMENT CORP."], "Logansport, IN 46947", index)

    assert [c["echo_pgm_sys_id"] for c in candidates] == ["IN0001", "IN0009"]
