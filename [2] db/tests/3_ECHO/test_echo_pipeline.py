"""SUU-110: PIPELINE_CAA_00_COMPLETE 한 행 → echo_pipeline_link 1행.

행은 실제 CSV (2026-09-17) 첫 행 그대로. 헤더 35열. 식별자가 있어도 실제 사건이 있다고 믿지 않는다 —
`known_activities` 에 (kind, id) 가 있을 때만 `resolved_*` 를 채운다.
"""
import hashlib

from echo_pipeline import pipeline_row

HEADER = [
    "SORT_ORDER", "SORT_DATE", "SOURCE_ID", "REGISTRY_ID", "AIR_NAME", "PIPELINE_FLAG", "OFFICIAL_FLAG", "EVAL_FLAG",
    "EVAL_SORT_ORDER", "EVAL_ACTIVITY_ID", "EVAL_TYPE_DESC", "EVAL_LEAD_AGENCY", "EVAL_DATE", "VIOL_FLAG",
    "VIOL_SORT_ORDER", "FOUND_VIOLATION", "VIOL_ACTIVITY_ID", "VIOL_TYPE", "VIOL_TYPE_SORT", "VIOL_LEAD_AGENCY",
    "VIOL_PROGRAMS", "VIOL_POLLUTANT_CODES", "VIOL_POLLUTANT_DESCS", "VIOL_START_DATE", "VIOL_END_DATE_DATE",
    "VIOL_END_DATE", "EA_FLAG", "EA_SORT_ORDER", "EA_ACTIVITY_ID", "EA_FEA_ACTIVITY_ID", "EA_TYPE", "EA_DATE",
    "FEA_ISSUE_DATE_FLAG", "EA_PENALTY_AMT", "EA_COMP_ACTION_COST",
]
FIRST = dict(zip(HEADER, [
    "55478", "06/26/2018", "PA000515538", "110001083915", "NORTHEAST PAVING/WASHINGTON PLANT", "N", "N", "N",
    "55478", "-9999", "", "", "", "Y", "44050", "Y", "3602684385", "FRV", "1", "PA", "CAASIP", "300000329", "FACIL",
    "06/26/2018", "", "N/A", "N", "55478", "", "", "", "", "", "", "",
]))
KNOWN = {("violation", "3602684385"), ("inspection", "121929"), ("formal", "600031828")}


def test_first_real_row_keeps_flags_and_raw_ids_with_deterministic_link_key():
    link = pipeline_row(FIRST, 1, KNOWN)
    assert link == {
        "link_key": hashlib.sha256("\x1f".join(FIRST.values()).encode("utf-8")).hexdigest(),
        "pgm_sys_id": "PA000515538",
        "eval_activity_id": "-9999",  # 원본 ID 그대로 (가짜라도 증거로 남긴다)
        "violation_activity_id": "3602684385",
        "ea_activity_id": None,  # "" → None
        "ea_fea_activity_id": None,
        "flags": {
            "PIPELINE_FLAG": "N", "OFFICIAL_FLAG": "N", "EVAL_FLAG": "N", "VIOL_FLAG": "Y",
            "FOUND_VIOLATION": "Y", "EA_FLAG": "N", "FEA_ISSUE_DATE_FLAG": None,
        },
        "synthetic_violation": True,  # 점검 없이(-9999) 만들어진 위반 행
        "resolution_status": "resolved",  # 실제 ID는 위반 하나뿐이고 그게 있다
        "resolved_eval_kind": None,
        "resolved_eval_id": None,
        "resolved_violation_id": "3602684385",
        "resolved_ea_kind": None,
        "resolved_ea_id": None,
        "source_row_no": 1,
        "attributes": {
            "SORT_ORDER": "55478", "SORT_DATE": "06/26/2018", "REGISTRY_ID": "110001083915",
            "AIR_NAME": "NORTHEAST PAVING/WASHINGTON PLANT", "EVAL_SORT_ORDER": "55478", "EVAL_TYPE_DESC": None,
            "EVAL_LEAD_AGENCY": None, "EVAL_DATE": None, "VIOL_SORT_ORDER": "44050", "VIOL_TYPE": "FRV",
            "VIOL_TYPE_SORT": "1", "VIOL_LEAD_AGENCY": "PA", "VIOL_PROGRAMS": "CAASIP",
            "VIOL_POLLUTANT_CODES": "300000329", "VIOL_POLLUTANT_DESCS": "FACIL", "VIOL_START_DATE": "06/26/2018",
            "VIOL_END_DATE_DATE": None, "VIOL_END_DATE": "N/A", "EA_SORT_ORDER": "55478", "EA_TYPE": None,
            "EA_DATE": None, "EA_PENALTY_AMT": None, "EA_COMP_ACTION_COST": None,
        },
    }
    assert pipeline_row(FIRST, 2, KNOWN)["link_key"] == link["link_key"]  # 행번호는 키에 안 들어간다
    assert pipeline_row({**FIRST, "SORT_ORDER": "1"}, 1, KNOWN)["link_key"] != link["link_key"]


def test_fake_eval_id_never_resolves_even_when_flag_says_yes():
    # 실제 데이터: EVAL_FLAG=Y 인데 EVAL_ACTIVITY_ID=-9999 인 행이 6,970개 있다
    link = pipeline_row({**FIRST, "EVAL_FLAG": "Y"}, 1, KNOWN | {("inspection", "-9999")})
    assert (link["resolved_eval_kind"], link["resolved_eval_id"]) == (None, None)
    assert link["synthetic_violation"] is True
    assert link["eval_activity_id"] == "-9999"

    real = pipeline_row({**FIRST, "EVAL_FLAG": "Y", "EVAL_ACTIVITY_ID": "121929"}, 1, KNOWN)
    assert (real["resolved_eval_kind"], real["resolved_eval_id"]) == ("inspection", "121929")
    assert real["synthetic_violation"] is False

    missing = pipeline_row({**FIRST, "EVAL_ACTIVITY_ID": ""}, 1, KNOWN)
    assert (missing["eval_activity_id"], missing["synthetic_violation"]) == (None, False)  # 빈값은 가짜가 아니라 없음


def test_resolved_only_when_id_exists_in_known_activities():
    link = pipeline_row(FIRST, 1, KNOWN)
    assert (link["resolved_violation_id"], link["resolution_status"]) == ("3602684385", "resolved")

    unknown = pipeline_row(FIRST, 1, {("inspection", "121929")})
    assert (unknown["resolved_violation_id"], unknown["resolution_status"]) == (None, "unresolved")
    assert unknown["violation_activity_id"] == "3602684385"  # 원본 ID는 그대로

    ea = pipeline_row({**FIRST, "EA_FLAG": "Y", "EA_ACTIVITY_ID": "600031828"}, 1, KNOWN)
    assert (ea["resolved_ea_kind"], ea["resolved_ea_id"], ea["resolution_status"]) == ("formal", "600031828", "resolved")

    half = pipeline_row({**FIRST, "EA_FLAG": "Y", "EA_ACTIVITY_ID": "999"}, 1, KNOWN)
    assert (half["resolved_ea_kind"], half["resolved_ea_id"]) == (None, None)  # 종류·ID는 함께 있거나 함께 None
    assert half["resolution_status"] == "unresolved"  # 하나라도 못 찾으면 unresolved

    nothing = pipeline_row({**FIRST, "VIOL_ACTIVITY_ID": ""}, 1, KNOWN)
    assert nothing["resolution_status"] == "none"  # 찾을 실제 ID가 하나도 없다
