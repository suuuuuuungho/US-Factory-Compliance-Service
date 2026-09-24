"""SUU-269: 데이터 계약 YAML(`[2] db/contracts/*.odcs.yaml`)과 실제 DB 구조를 비교한다.

모양 (load_contracts / read_db 가 돌려주는 것, compare 가 받는 것):
    {표 이름: {"columns": {칸 이름: {"type": str, "required": bool, "primary_key": bool}},
               "not_empty": bool}}      # load_contracts: YAML quality 의 rowCount > 0 규칙이 있으면 True
    {표 이름: {"columns": {...같은 모양...}, "rows": int}}   # read_db: rows 는 0 또는 1 (비었는지만 본다)

type 은 Postgres format_type() 글자와 같다. 예: "uuid", "text", "timestamp with time zone", "text[]", "vector(1792)".
"""
from pathlib import Path

from contract_check import compare, load_contracts

ROOT = Path(__file__).resolve().parents[3]
CONTRACTS = ROOT / "[2] db" / "contracts"
CI = ROOT / ".github" / "workflows" / "ci.yml"


def _col(type_="text", required=False, primary_key=False):
    return {"type": type_, "required": required, "primary_key": primary_key}


def _expected():
    return {
        "ecfr_node": {"columns": {"release_id": _col("uuid", True, True), "heading": _col()}, "not_empty": True},
        "ecfr_asset": {"columns": {"asset_no": _col("integer", True, True)}, "not_empty": False},
    }


def _actual():
    return {
        "ecfr_node": {"columns": {"release_id": _col("uuid", True, True), "heading": _col()}, "rows": 1},
        "ecfr_asset": {"columns": {"asset_no": _col("integer", True, True)}, "rows": 0},
    }


# ---- load_contracts: 저장소의 진짜 YAML 6개를 읽는다

def test_load_contracts_reads_all_43_tables_and_430_columns():
    tables = load_contracts(CONTRACTS)
    assert len(tables) == 43
    assert sum(len(t["columns"]) for t in tables.values()) == 430


def test_load_contracts_keeps_type_required_and_primary_key():
    col = load_contracts(CONTRACTS)["echo_activity"]["columns"]
    assert col["activity_id"] == {"type": "text", "required": True, "primary_key": True}
    assert col["activity_date"] == {"type": "date", "required": False, "primary_key": False}


def test_contract_matches_real_db_type_with_precision():
    # 실제 DB 는 numeric(10,6). SUU-268 YAML 은 numeric 으로 잘못 적었다
    col = load_contracts(CONTRACTS)["rag_answer_log"]["columns"]["cost_usd"]
    assert col["type"] == "numeric(10,6)"


def test_load_contracts_marks_not_empty_from_row_count_rule():
    tables = load_contracts(CONTRACTS)
    assert tables["ecfr_node"]["not_empty"] is True
    assert tables["ecfr_asset"]["not_empty"] is False


# ---- compare: 같으면 빈 목록, 다르면 사람이 읽는 오류 글자 목록

def test_compare_same_structure_has_no_errors():
    assert compare(_expected(), _actual()) == []


def test_compare_reports_table_missing_in_db():
    actual = _actual()
    del actual["ecfr_asset"]
    errors = compare(_expected(), actual)
    assert len(errors) == 1 and "ecfr_asset" in errors[0]


def test_compare_reports_table_missing_in_contract():
    actual = _actual()
    actual["fr_diff"] = {"columns": {"seq": _col("integer", True, True)}, "rows": 0}
    errors = compare(_expected(), actual)
    assert len(errors) == 1 and "fr_diff" in errors[0]


def test_compare_reports_column_missing_or_extra():
    actual = _actual()
    del actual["ecfr_node"]["columns"]["heading"]
    actual["ecfr_node"]["columns"]["new_col"] = _col()
    errors = compare(_expected(), actual)
    assert len(errors) == 2
    assert any("ecfr_node.heading" in e for e in errors)
    assert any("ecfr_node.new_col" in e for e in errors)


def test_compare_reports_type_difference():
    actual = _actual()
    actual["ecfr_node"]["columns"]["heading"]["type"] = "integer"
    errors = compare(_expected(), actual)
    assert len(errors) == 1 and "ecfr_node.heading" in errors[0]


def test_compare_reports_required_difference():
    actual = _actual()
    actual["ecfr_node"]["columns"]["heading"]["required"] = True
    errors = compare(_expected(), actual)
    assert len(errors) == 1 and "ecfr_node.heading" in errors[0]


def test_compare_reports_primary_key_difference():
    actual = _actual()
    actual["ecfr_node"]["columns"]["release_id"]["primary_key"] = False
    errors = compare(_expected(), actual)
    assert len(errors) == 1 and "ecfr_node.release_id" in errors[0]


def test_compare_reports_empty_table_that_must_not_be_empty():
    actual = _actual()
    actual["ecfr_node"]["rows"] = 0
    errors = compare(_expected(), actual)
    assert len(errors) == 1 and "ecfr_node" in errors[0]


def test_compare_allows_empty_table_without_row_count_rule():
    actual = _actual()
    actual["ecfr_asset"]["rows"] = 0
    assert compare(_expected(), actual) == []


# ---- CI: 모든 PR에서 진짜 DB로 검사한다 (실패하면 기존 Slack 'CI 실패' 알림이 간다)

def test_ci_runs_contract_check_with_db_secret():
    text = CI.read_text(encoding="utf-8")
    assert "contract_check.py" in text
    assert "secrets.SUPABASE_DB_URL" in text
