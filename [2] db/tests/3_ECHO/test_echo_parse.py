"""SUU-111: raw ZIP 2개 → parsed/{확인일}/{테이블}.jsonl 13개 + report.json.

가짜 ZIP 2개(실제 헤더, 몇 행)로 돌린다. SUU-102~110 함수를 순서대로 부르고, 원본 행은 echo_source_row 에 남긴다.
"""
import csv
import hashlib
import io
import json
import zipfile
from datetime import date

import pytest

from echo_parse import ParseError, parse_release

AS_OF = date(2026, 9, 17)
CODE_MAP_VERSION = "2026-09-17"

HEADERS = {
    "ICIS-AIR_FACILITIES.csv": [
        "PGM_SYS_ID", "REGISTRY_ID", "FACILITY_NAME", "STREET_ADDRESS", "CITY", "COUNTY_NAME", "STATE", "ZIP_CODE",
        "EPA_REGION", "SIC_CODES", "NAICS_CODES", "FACILITY_TYPE_CODE", "AIR_POLLUTANT_CLASS_CODE",
        "AIR_POLLUTANT_CLASS_DESC", "AIR_OPERATING_STATUS_CODE", "AIR_OPERATING_STATUS_DESC", "CURRENT_HPV",
        "LOCAL_CONTROL_REGION_CODE", "LOCAL_CONTROL_REGION_NAME",
    ],
    "ICIS-AIR_PROGRAMS.csv": [
        "PGM_SYS_ID", "PROGRAM_CODE", "PROGRAM_DESC", "AIR_OPERATING_STATUS_CODE", "AIR_OPERATING_STATUS_DESC",
        "BEGIN_DATE", "UPDATED_DATE",
    ],
    "ICIS-AIR_PROGRAM_SUBPARTS.csv": [
        "PGM_SYS_ID", "PROGRAM_CODE", "PROGRAM_DESC", "AIR_PROGRAM_SUBPART_CODE", "AIR_PROGRAM_SUBPART_DESC",
    ],
    "ICIS-AIR_POLLUTANTS.csv": [
        "PGM_SYS_ID", "POLLUTANT_CODE", "POLLUTANT_DESC", "SRS_ID", "CHEMICAL_ABSTRACT_SERVICE_NMBR",
        "AIR_POLLUTANT_CLASS_CODE", "AIR_POLLUTANT_CLASS_DESC",
    ],
    "ICIS-AIR_FCES_PCES.csv": [
        "PGM_SYS_ID", "ACTIVITY_ID", "STATE_EPA_FLAG", "ACTIVITY_TYPE_CODE", "ACTIVITY_TYPE_DESC",
        "COMP_MONITOR_TYPE_CODE", "COMP_MONITOR_TYPE_DESC", "ACTUAL_END_DATE", "PROGRAM_CODES", "ACTIVITY_PURPOSE_DESC",
    ],
    "ICIS-AIR_STACK_TESTS.csv": [
        "PGM_SYS_ID", "ACTIVITY_ID", "COMP_MONITOR_TYPE_CODE", "COMP_MONITOR_TYPE_DESC", "STATE_EPA_FLAG",
        "ACTUAL_END_DATE", "POLLUTANT_CODES", "POLLUTANT_DESCS", "AIR_STACK_TEST_STATUS_CODE", "AIR_STACK_TEST_STATUS_DESC",
    ],
    "ICIS-AIR_TITLEV_CERTS.csv": [
        "PGM_SYS_ID", "ACTIVITY_ID", "COMP_MONITOR_TYPE_CODE", "COMP_MONITOR_TYPE_DESC", "STATE_EPA_FLAG",
        "ACTUAL_END_DATE", "FACILITY_RPT_DEVIATION_FLAG",
    ],
    "ICIS-AIR_FORMAL_ACTIONS.csv": [
        "PGM_SYS_ID", "ACTIVITY_ID", "ENF_IDENTIFIER", "ACTIVITY_TYPE_CODE", "ACTIVITY_TYPE_DESC", "STATE_EPA_FLAG",
        "ENF_TYPE_CODE", "ENF_TYPE_DESC", "SETTLEMENT_ENTERED_DATE", "PENALTY_AMOUNT",
    ],
    "ICIS-AIR_INFORMAL_ACTIONS.csv": [
        "PGM_SYS_ID", "ACTIVITY_ID", "ENF_IDENTIFIER", "ACTIVITY_TYPE_CODE", "ACTIVITY_TYPE_DESC", "STATE_EPA_FLAG",
        "ENF_TYPE_CODE", "ENF_TYPE_DESC", "ACHIEVED_DATE", "OFFICIAL_FLG",
    ],
    "ICIS-AIR_VIOLATION_HISTORY.csv": [
        "PGM_SYS_ID", "ACTIVITY_ID", "AGENCY_TYPE_DESC", "STATE_CODE", "AIR_LCON_CODE", "COMP_DETERMINATION_UID",
        "ENF_RESPONSE_POLICY_CODE", "PROGRAM_CODES", "PROGRAM_DESCS", "POLLUTANT_CODES", "POLLUTANT_DESCS",
        "EARLIEST_FRV_DETERM_DATE", "HPV_DAYZERO_DATE", "HPV_RESOLVED_DATE", "DSCV_PATHWAY_DATE", "NFTC_PATHWAY_DATE",
    ],
    "PIPELINE_CAA_00_COMPLETE.csv": [
        "SORT_ORDER", "SORT_DATE", "SOURCE_ID", "REGISTRY_ID", "AIR_NAME", "PIPELINE_FLAG", "OFFICIAL_FLAG", "EVAL_FLAG",
        "EVAL_SORT_ORDER", "EVAL_ACTIVITY_ID", "EVAL_TYPE_DESC", "EVAL_LEAD_AGENCY", "EVAL_DATE", "VIOL_FLAG",
        "VIOL_SORT_ORDER", "FOUND_VIOLATION", "VIOL_ACTIVITY_ID", "VIOL_TYPE", "VIOL_TYPE_SORT", "VIOL_LEAD_AGENCY",
        "VIOL_PROGRAMS", "VIOL_POLLUTANT_CODES", "VIOL_POLLUTANT_DESCS", "VIOL_START_DATE", "VIOL_END_DATE_DATE",
        "VIOL_END_DATE", "EA_FLAG", "EA_SORT_ORDER", "EA_ACTIVITY_ID", "EA_FEA_ACTIVITY_ID", "EA_TYPE", "EA_DATE",
        "FEA_ISSUE_DATE_FLAG", "EA_PENALTY_AMT", "EA_COMP_ACTION_COST",
    ],
}

# 시설 F1·F2. F1 은 이름만 다른 두 번째 행이 있다(충돌). 프로그램 F9 는 시설이 없다(고아).
ROWS = {
    "ICIS-AIR_FACILITIES.csv": [
        ["F1", "110000000001", "PLANT ONE", "1 A ST", "SUFFIELD", "Hartford", "CT", "06078", "01", "", "445110",
         "", "", "", "OPR", "Operating", "No Violation Identified", "", ""],
        ["F2", "", "PLANT TWO", "2 B ST", "NORTH ARLINGTON", "Bergen", "NJ", "07032", "02", "3541 3545", "335311",
         "POF", "MIN", "Minor Emissions", "OPR", "Operating", "No Violation Identified", "", ""],
        ["F1", "110000000001", "PLANT ONE RENAMED", "1 A ST", "SUFFIELD", "Hartford", "CT", "06078", "01", "", "445110",
         "", "", "", "OPR", "Operating", "No Violation Identified", "", ""],
    ],
    "ICIS-AIR_PROGRAMS.csv": [
        ["F1", "CAASIP", "State Implementation Plan", "OPR", "Operating", "02/22/2017", "02/21/2020"],
        ["F1", "CAANESH", "NESHAP", "OPR", "Operating", "02/22/2017", "02/21/2020"],
        ["F1", "CAAGACT", "GACT", "OPR", "Operating", "02/22/2017", "02/21/2020"],
        ["F9", "CAASIP", "State Implementation Plan", "", "", "", ""],
    ],
    "ICIS-AIR_PROGRAM_SUBPARTS.csv": [
        ["F1", "CAANESH", "NESHAP", "CAANESHFF", "NESHAP Part 61 - Subpart FF - BENZENE WASTE OPERATIONS"],
        ["F1", "CAAGACT", "GACT", "CAAGACTZZZZZZ", "unknown"],
    ],
    "ICIS-AIR_POLLUTANTS.csv": [
        ["F1", "300000322", "TOTAL PARTICULATE MATTER", "1647643", "", "MIN", "Minor Emissions"],
    ],
    "ICIS-AIR_FCES_PCES.csv": [  # 점검 A1 이 시설 둘에 붙는다 → 활동 1행, 연결 2행
        ["F1", "A1", "E", "INS", "Inspection/Evaluation", "PCE", "PCE On-Site", "05-04-2004", "", "Agency Priority"],
        ["F2", "A1", "E", "INS", "Inspection/Evaluation", "PCE", "PCE On-Site", "05-04-2004", "", "Agency Priority"],
    ],
    "ICIS-AIR_STACK_TESTS.csv": [
        ["F1", "A2", "CST", "Stack Test", "E", "06/24/2004", "HAPS [HAZARDOUS AIR POLLUTANTS/AIR TOXICS]", "", "", ""],
    ],
    "ICIS-AIR_TITLEV_CERTS.csv": [
        ["F1", "A3", "TVA", "TV ACC Receipt/Review", "S", "04/30/2015", "Y"],
    ],
    "ICIS-AIR_FORMAL_ACTIONS.csv": [  # E1 이 시설 둘 → 활동 1행, 벌금은 행마다. 셋째 행은 금액이 깨져 보류
        ["F1", "E1", "07-2007-0086", "AFR", "Administrative - Formal", "E", "113A", "Order", "03/08/2007", "0"],
        ["F2", "E1", "07-2007-0086", "AFR", "Administrative - Formal", "E", "113A", "Order", "03/08/2007", "500"],
        ["F1", "E2", "07-2007-0099", "AFR", "Administrative - Formal", "E", "113A", "Order", "03/08/2007", "abc"],
    ],
    "ICIS-AIR_INFORMAL_ACTIONS.csv": [
        ["F1", "N1", "05-200004899", "AIF", "Administrative - Informal", "E", "NOV", "Notice of Violation",
         "09/27/2006", "Y"],
    ],
    "ICIS-AIR_VIOLATION_HISTORY.csv": [
        ["F1", "V1", "State", "CT", "", "CT000A1", "HPV", "CAASIP", "SIP", "300000243", "VOC", "", "02-28-1997",
         "02-19-1998", "", ""],
    ],
    "PIPELINE_CAA_00_COMPLETE.csv": [  # 첫 행은 전부 실제 ID, 둘째 행은 -9999 점검 + 없는 위반 V9
        ["1", "06/26/2018", "F1", "110000000001", "PLANT ONE", "Y", "N", "Y", "1", "A1", "", "", "", "Y", "1", "Y",
         "V1", "HPV", "1", "CT", "CAASIP", "300000243", "VOC", "06/26/2018", "", "N/A", "Y", "1", "E1", "", "", "", "",
         "0", ""],
        ["2", "06/26/2018", "F2", "", "PLANT TWO", "N", "N", "N", "2", "-9999", "", "", "", "Y", "2", "Y", "V9", "FRV",
         "1", "NJ", "CAASIP", "300000329", "FACIL", "06/26/2018", "", "N/A", "N", "2", "", "", "", "", "", "", ""],
    ],
}

TABLES = [
    "echo_source_row", "echo_facility", "echo_facility_identifier", "echo_industry", "echo_program",
    "echo_program_subpart", "echo_pollutant", "echo_activity", "echo_activity_facility", "echo_violation",
    "echo_violation_facility", "echo_penalty", "echo_pipeline_link",
]


def _csv_bytes(header, rows):
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(header)
    writer.writerows(rows)
    return buf.getvalue().encode("utf-8")


def _write_zip(root, as_of, name, members, drop_column=None):
    body = io.BytesIO()
    with zipfile.ZipFile(body, "w") as zf:
        for member in members:
            header, rows = HEADERS[member], ROWS[member]
            if drop_column and drop_column[0] == member:
                idx = header.index(drop_column[1])
                header = header[:idx] + header[idx + 1:]
                rows = [r[:idx] + r[idx + 1:] for r in rows]
            zf.writestr(member, _csv_bytes(header, rows))
    data = body.getvalue()
    sha = hashlib.sha256(data).hexdigest()
    path = root / "raw" / as_of.isoformat() / sha / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return {"name": name, "path": path.relative_to(root).as_posix(), "sha256": sha}


def _make_release(root, drop_column=None):
    icis = [m for m in HEADERS if m.startswith("ICIS-AIR_")]
    manifest = [
        _write_zip(root, AS_OF, "ICIS-AIR_downloads.zip", icis, drop_column),
        _write_zip(root, AS_OF, "pipeline_caa_downloads.zip", ["PIPELINE_CAA_00_COMPLETE.csv"], drop_column),
    ]
    (root / "raw" / AS_OF.isoformat() / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    code_map = root / "code_map" / CODE_MAP_VERSION / "echo_code_map.jsonl"
    code_map.parent.mkdir(parents=True, exist_ok=True)
    code_map.write_text(json.dumps({
        "program_code": "CAANESH", "raw_subpart_code": "CAANESHFF", "raw_description": "x", "cfr_title": "40",
        "cfr_part": "61", "cfr_subpart": "FF", "review_status": "ok", "dictionary_version": CODE_MAP_VERSION,
        "source_url": "u",
    }) + "\n", encoding="utf-8")
    return root


def _jsonl(root, table):
    path = root / "parsed" / AS_OF.isoformat() / f"{table}.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_fake_release_writes_13_jsonl_and_read_equals_ok_plus_held(tmp_path):
    root = _make_release(tmp_path / "echo")

    report = parse_release(root, AS_OF, CODE_MAP_VERSION)

    out = root / "parsed" / AS_OF.isoformat()
    assert sorted(p.name for p in out.glob("*.jsonl")) == sorted(f"{t}.jsonl" for t in TABLES)
    assert json.loads((out / "report.json").read_text(encoding="utf-8")) == report

    assert report["as_of"] == "2026-09-17"
    assert report["code_map_version"] == CODE_MAP_VERSION
    assert set(report["files"]) == set(HEADERS)  # 11개 파일 전부
    for name, counts in report["files"].items():
        assert counts["read"] == counts["ok"] + counts["held"], name
        assert counts["read"] == len(ROWS[name]), name
    assert report["files"]["ICIS-AIR_FORMAL_ACTIONS.csv"] == {"read": 3, "ok": 2, "held": 1}

    # 원본 행은 전부 echo_source_row 에 남는다 (보류 행 포함, 이유와 함께)
    source_rows = _jsonl(root, "echo_source_row")
    assert len(source_rows) == sum(len(rows) for rows in ROWS.values())
    held = [r for r in source_rows if r["parse_status"] == "held"]
    assert len(held) == 1
    assert (held[0]["source_file"], held[0]["source_row_no"]) == ("ICIS-AIR_FORMAL_ACTIONS.csv", 3)
    assert "abc" in held[0]["error"]
    assert held[0]["raw_payload"]["PENALTY_AMOUNT"] == "abc"
    first = source_rows[0]
    assert first["source_file"] == "ICIS-AIR_FACILITIES.csv" and first["source_row_no"] == 1
    assert first["row_hash"] == hashlib.sha256("\x1f".join(ROWS["ICIS-AIR_FACILITIES.csv"][0]).encode("utf-8")).hexdigest()
    assert first["source_object_sha256"] == json.loads(
        (root / "raw" / AS_OF.isoformat() / "manifest.json").read_text(encoding="utf-8"))[0]["sha256"]
    assert first["parse_status"] == "ok" and first["error"] is None

    # 표 몇 개는 행 수를 직접 확인한다. 날짜·금액은 문자열로 적힌다
    assert [f["pgm_sys_id"] for f in _jsonl(root, "echo_facility")] == ["F1", "F2"]  # 충돌 행은 첫 행만
    assert _jsonl(root, "echo_facility_identifier") == [{
        "program_system": "ICIS-AIR", "pgm_sys_id": "F1", "registry_id": "110000000001",
        "mapping_source": "ICIS-AIR_FACILITIES.csv", "review_status": "source_stated",
    }]  # registry_id 가 빈 F2 는 안 만든다
    assert len(_jsonl(root, "echo_industry")) == 4  # F1 445110 + F2 3541·3545·335311. F1 충돌 행의 445110 은 같은 키라 한 번만
    activities = _jsonl(root, "echo_activity")
    assert sorted((a["activity_kind"], a["activity_id"]) for a in activities) == [
        ("formal", "E1"), ("informal", "N1"), ("inspection", "A1"), ("stack_test", "A2"), ("titlev", "A3"),
    ]
    assert next(a for a in activities if a["activity_id"] == "A1")["activity_date"] == "2004-05-04"
    assert len(_jsonl(root, "echo_activity_facility")) == 7  # A1×2, A2, A3, E1×2, N1
    penalties = _jsonl(root, "echo_penalty")
    assert [(p["penalty_key"], p["amount"], p["raw_amount"]) for p in penalties] == [("formal:1", "0", "0"), ("formal:2", "500", "500")]
    subparts = _jsonl(root, "echo_program_subpart")
    assert [(s["subpart_code"], s["cfr_part"], s["mapping_status"]) for s in subparts] == [
        ("CAANESHFF", "61", "mapped"), ("CAAGACTZZZZZZ", None, "unresolved"),
    ]
    assert _jsonl(root, "echo_pollutant")[0]["source_locator"] == "ICIS-AIR_POLLUTANTS.csv:1"


def test_report_counts_orphans_duplicates_missing_and_penalties(tmp_path):
    root = _make_release(tmp_path / "echo")

    report = parse_release(root, AS_OF, CODE_MAP_VERSION)

    assert report["orphans"] == {
        "echo_industry.pgm_sys_id": 0,
        "echo_program.pgm_sys_id": 1,  # F9
        "echo_program_subpart.program": 0,
        "echo_pollutant.pgm_sys_id": 0,
        "echo_activity_facility.pgm_sys_id": 0,
        "echo_activity_facility.activity": 0,
        "echo_violation_facility.pgm_sys_id": 0,
        "echo_violation_facility.violation": 0,
        "echo_penalty.activity": 0,
        "echo_pipeline_link.resolved": 0,  # 확정 연결은 만들 때부터 실제 집합만 본다
    }
    assert report["duplicates"] == {  # 같은 키·같은 내용 → 첫 행만 쓰고 센다
        "echo_facility": 0, "echo_facility_identifier": 1, "echo_industry": 1, "echo_program": 0,
        "echo_program_subpart": 0, "echo_pollutant": 0, "echo_activity": 2, "echo_activity_facility": 0,
        "echo_violation": 0, "echo_violation_facility": 0, "echo_pipeline_link": 0,
    }
    assert report["conflicts"] == {  # 같은 키·다른 내용 → 첫 행만 쓰고 센다
        "echo_facility": 1, "echo_program": 0, "echo_program_subpart": 0, "echo_pollutant": 0,
        "echo_activity": 0, "echo_violation": 0,
    }
    assert report["conflict_examples"]["echo_facility"] == [{"key": ["F1"], "source_file": "ICIS-AIR_FACILITIES.csv", "source_row_no": 3}]

    ids = report["identifiers"]
    assert ids["ICIS-AIR_FACILITIES.csv"]["PGM_SYS_ID"] == {"missing": 0, "missing_rate": 0.0, "duplicate": 1, "duplicate_rate": 0.3333}
    assert ids["ICIS-AIR_FCES_PCES.csv"]["ACTIVITY_ID"] == {"missing": 0, "missing_rate": 0.0, "duplicate": 1, "duplicate_rate": 0.5}
    assert ids["ICIS-AIR_FCES_PCES.csv"]["PGM_SYS_ID"]["duplicate"] == 0
    assert "ACTIVITY_ID" not in ids["ICIS-AIR_FACILITIES.csv"]  # 그 파일에 없는 열은 안 센다
    assert ids["PIPELINE_CAA_00_COMPLETE.csv"]["SOURCE_ID"]["duplicate"] == 0

    assert report["penalties"] == {"rows": 2, "formal_rows_ok": 2}  # 벌금 행 수 = 정상 공식처분 행 수 (합산 없음)
    assert report["subpart_mapping"] == {"mapped": 1, "unresolved": 1, "conflict": 0}
    assert report["pipeline"] == {"resolved": 1, "unresolved": 1, "none": 0, "synthetic_violation": 1}

    links = _jsonl(root, "echo_pipeline_link")
    assert (links[0]["resolved_eval_kind"], links[0]["resolved_eval_id"], links[0]["resolved_ea_kind"], links[0]["resolved_violation_id"]) == ("inspection", "A1", "formal", "V1")
    assert (links[1]["resolved_eval_id"], links[1]["resolved_violation_id"], links[1]["resolution_status"]) == (None, None, "unresolved")


def test_missing_required_column_raises_and_leaves_no_parsed_dir(tmp_path):
    root = _make_release(tmp_path / "echo", drop_column=("ICIS-AIR_STACK_TESTS.csv", "ACTIVITY_ID"))

    with pytest.raises(ParseError, match="ICIS-AIR_STACK_TESTS.csv.*ACTIVITY_ID"):
        parse_release(root, AS_OF, CODE_MAP_VERSION)

    assert not (root / "parsed" / AS_OF.isoformat()).exists()  # 반쪽짜리 결과를 남기지 않는다


def test_pipeline_rows_share_one_known_set_built_once(tmp_path, monkeypatch):
    # SUU-118: 실제 데이터에서 행마다 activities | violations(550만 개)를 새로 합치면 Pipeline 6.7만 행에 1시간 반이 걸린다
    import echo_parse

    real = echo_parse.pipeline_row
    calls = []

    def spy(row, source_row_no, known_activities):
        calls.append(known_activities)  # 객체 자체를 붙잡아 둔다 (id()만 저장하면 주소가 재사용돼 못 잡는다)
        return real(row, source_row_no, known_activities)

    monkeypatch.setattr(echo_parse, "pipeline_row", spy)
    root = _make_release(tmp_path / "echo")

    parse_release(root, AS_OF, CODE_MAP_VERSION)

    assert len(calls) == 2  # Pipeline 행 2개
    assert all(known is calls[0] for known in calls)  # 같은 객체를 다시 쓴다
    expected = {(a["activity_kind"], a["activity_id"]) for a in _jsonl(root, "echo_activity")} | {("violation", v["violation_id"]) for v in _jsonl(root, "echo_violation")}
    assert set(calls[0]) == expected
