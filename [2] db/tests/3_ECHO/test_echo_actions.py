"""SUU-108: FORMAL_ACTIONS·INFORMAL_ACTIONS 한 행 → echo_activity + echo_activity_facility + echo_penalty(공식만).

행은 실제 CSV (2026-09-17) 첫 행 그대로. 실제 데이터에서 같은 ACTIVITY_ID·PGM_SYS_ID 쌍이 ENF_TYPE_CODE 별로
여러 행 나오고 금액도 행마다 다를 수 있어(425쌍), 벌금은 CSV 행 단위로 남기고 행번호를 키에 넣는다.
"""
from datetime import date
from decimal import Decimal

import pytest

from echo_actions import action_rows

FORMAL = {
    "PGM_SYS_ID": "NE0000003105500410",
    "ACTIVITY_ID": "600031828",
    "ENF_IDENTIFIER": "07-2007-0086",
    "ACTIVITY_TYPE_CODE": "AFR",
    "ACTIVITY_TYPE_DESC": "Administrative - Formal",
    "STATE_EPA_FLAG": "E",
    "ENF_TYPE_CODE": "113A",
    "ENF_TYPE_DESC": "CAA 113A Admin Compliance Order (Non-Penalty)",
    "SETTLEMENT_ENTERED_DATE": "03/08/2007",
    "PENALTY_AMOUNT": "0",
}

INFORMAL = {
    "PGM_SYS_ID": "IL000163121AAP",
    "ACTIVITY_ID": "600027656",
    "ENF_IDENTIFIER": "05-200004899",
    "ACTIVITY_TYPE_CODE": "AIF",
    "ACTIVITY_TYPE_DESC": "Administrative - Informal",
    "STATE_EPA_FLAG": "E",
    "ENF_TYPE_CODE": "NOV",
    "ENF_TYPE_DESC": "Notice of Violation",
    "ACHIEVED_DATE": "09/27/2006",
    "OFFICIAL_FLG": "Y",
}


def test_formal_zero_penalty_is_a_real_zero_dollar_row():
    _, _, penalty = action_rows("formal", FORMAL, 1)
    assert penalty == {
        "penalty_key": "formal:1",
        "activity_kind": "formal",
        "activity_id": "600031828",
        "amount": Decimal("0"),  # 0달러. 빈값이 아니다
        "amount_kind": "penalty",
        "currency": "USD",
        "amount_scope": "row",  # CSV 한 행이 말한 금액. 처분 합계로 확정하지 않는다
        "raw_amount": "0",
        "source_locator": "ICIS-AIR_FORMAL_ACTIONS.csv:1",
    }

    _, _, cents = action_rows("formal", {**FORMAL, "PENALTY_AMOUNT": "103449.5"}, 7)
    assert (cents["amount"], cents["raw_amount"], cents["penalty_key"]) == (Decimal("103449.5"), "103449.5", "formal:7")


def test_blank_penalty_is_none_and_informal_has_no_penalty():
    _, _, blank = action_rows("formal", {**FORMAL, "PENALTY_AMOUNT": ""}, 2)
    assert (blank["amount"], blank["raw_amount"]) == (None, "")  # 신고 없음 ≠ 0달러

    activity, link, penalty = action_rows("informal", INFORMAL, 3)
    assert penalty is None  # 비공식 파일엔 PENALTY_AMOUNT 열이 없다
    assert link == {"activity_kind": "informal", "activity_id": "600027656", "pgm_sys_id": "IL000163121AAP"}
    assert activity["attributes"] == {
        "ENF_IDENTIFIER": "05-200004899",
        "ENF_TYPE_CODE": "NOV",
        "ENF_TYPE_DESC": "Notice of Violation",
        "OFFICIAL_FLG": "Y",
    }


def test_formal_uses_settlement_date_and_informal_uses_achieved_date():
    formal, link, _ = action_rows("formal", FORMAL, 1)
    assert formal == {
        "activity_kind": "formal",
        "activity_id": "600031828",
        "type_code": "AFR",
        "type_desc": "Administrative - Formal",
        "lead_flag": "E",
        "monitor_code": None,  # 처분 파일엔 COMP_MONITOR_TYPE_* 열이 없다
        "monitor_desc": None,
        "activity_date": date(2007, 3, 8),
        "raw_date": "03/08/2007",
        "attributes": {  # PENALTY_AMOUNT 는 penalty 행으로 갔으니 여기 없다
            "ENF_IDENTIFIER": "07-2007-0086",
            "ENF_TYPE_CODE": "113A",
            "ENF_TYPE_DESC": "CAA 113A Admin Compliance Order (Non-Penalty)",
        },
    }
    assert link == {"activity_kind": "formal", "activity_id": "600031828", "pgm_sys_id": "NE0000003105500410"}

    informal, _, _ = action_rows("informal", INFORMAL, 3)
    assert (informal["activity_date"], informal["raw_date"]) == (date(2006, 9, 27), "09/27/2006")

    nodate, _, _ = action_rows("informal", {**INFORMAL, "ACHIEVED_DATE": ""}, 4)
    assert (nodate["activity_date"], nodate["raw_date"]) == (None, "")

    with pytest.raises(ValueError):
        action_rows("inspection", FORMAL, 1)  # 점검은 echo_activities (SUU-107)
