"""SUU-145: 답 모양 JSON과 채점표가 문서에 고정되어 있는지 검사한다."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).parents[2]
DOC = ROOT / "[1] docs" / "3) rag" / "4_rag 답변 품질 개선 과정.md"
PLAN = ROOT / "[6] rag" / "eval" / "rag_eval_plan.md"

REQUIRED_HEADINGS = ["## 1. 답 모양", "## 2. 채점표", "## 3. 동점 폭", "## 4. 실험 순서"]
METRICS = ["Subpart 적중", "인용 Recall", "인용 근거율", "판정 기준 점수"]


def doc_text() -> str:
    return DOC.read_text(encoding="utf-8")


def test_doc_has_four_required_headings():
    text = doc_text()
    for heading in REQUIRED_HEADINGS:
        assert heading in text, f"제목 없음: {heading}"


def test_answer_schema_example_is_valid_json_without_final_verdict():
    blocks = re.findall(r"```json\n(.*?)```", doc_text(), re.S)
    assert blocks, "```json 예시 블록이 없다"
    example = json.loads(blocks[0])
    assert isinstance(example["candidates"], list) and example["candidates"]
    first = example["candidates"][0]
    assert first["subpart"]
    assert first["criteria"] and all(c["citations"] for c in first["criteria"])
    assert isinstance(example["checklist"], list) and example["checklist"]
    assert "applies" not in json.dumps(example), "최종 판정(applies)은 답에 없어야 한다"


def test_scoring_table_names_four_metrics_and_judge_scale():
    text = doc_text()
    for metric in METRICS:
        assert metric in text, f"채점표에 없음: {metric}"
    assert "0·1·2" in text or "0/1/2" in text, "심판 점수 0·1·2 척도가 없다"
    assert "notes" in text, "심판 기준(EPA notes)이 없다"


def test_eval_plan_has_answer_stage_rows():
    text = PLAN.read_text(encoding="utf-8")
    for row in ["A-1", "A-2", "A-3", "A-4", "A-5"]:
        assert f"| {row} |" in text, f"rag_eval_plan.md에 {row} 행이 없다"
