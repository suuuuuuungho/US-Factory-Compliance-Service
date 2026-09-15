from pathlib import Path

from lxml import etree

from ecfr_blocks import parse_blocks
from ecfr_labels import assign_label_paths

XML = Path(__file__).parent / "fixtures" / "ecfr_part63_sample.xml"

BLOCK_FIELDS = {"block_no", "kind", "text_content", "markup", "source_locator", "parse_status"}
NEW_FIELDS = {"label_path", "label_status"}


def load_root():
    parser = etree.XMLParser(
        resolve_entities=False, no_network=True, load_dtd=False, huge_tree=True
    )
    return etree.fromstring(XML.read_bytes(), parser)


def find_node(root, tag, n):
    return root.find(f".//{tag}[@N='{n}']")


def para(markup):
    # parse_blocks 가 만드는 paragraph 블록과 같은 모양 (필요한 칸만)
    text = " ".join("".join(etree.fromstring(markup).itertext()).split())
    return {"kind": "paragraph", "text_content": text, "markup": markup}


def paths(blocks):
    return [b["label_path"] for b in blocks]


def statuses(blocks):
    return [b["label_status"] for b in blocks]


def test_label_paths_follow_sequence():
    # (a)(1)(2)(i)(ii)(b) → 앞 문단 맥락으로 형제/자식을 판단해 경로를 붙인다
    blocks = [
        para("<P>(a) First.</P>"),
        para("<P>(1) Under a.</P>"),
        para("<P>(2) Also under a.</P>"),
        para("<P>(i) Under a-2.</P>"),
        para("<P>(ii) Also under a-2.</P>"),
        para("<P>(b) Second.</P>"),
    ]
    out = assign_label_paths(blocks)

    assert paths(out) == [["a"], ["a", "1"], ["a", "2"], ["a", "2", "i"], ["a", "2", "ii"], ["b"]]
    assert statuses(out) == ["ok"] * 6
    # 원래 칸은 그대로, label_path·label_status 두 칸만 늘어난다
    assert all(set(b) == {"kind", "text_content", "markup"} | NEW_FIELDS for b in out)
    assert len(out) == 6


def test_roman_vs_letter_uses_context():
    a_to_h = [para(f"<P>({c}) Letter {c}.</P>") for c in "abcdefgh"]
    a_to_h_paths = [[c] for c in "abcdefgh"]

    # (h) 다음 (i) 는 형제 = 알파벳 i
    out = assign_label_paths(a_to_h + [para("<P>(i) I.</P>"), para("<P>(j) J.</P>")])
    assert paths(out) == a_to_h_paths + [["i"], ["j"]]

    # (1) 다음 (i) 는 자식 = 로마자 i
    out = assign_label_paths([
        para("<P>(a) A.</P>"), para("<P>(1) One.</P>"), para("<P>(i) Roman.</P>"), para("<P>(ii) Roman two.</P>"),
    ])
    assert paths(out) == [["a"], ["a", "1"], ["a", "1", "i"], ["a", "1", "ii"]]

    # (h)(1) 다음 (i) 는 둘 다 가능 → 다음 문단을 보고 정한다
    #   다음이 (ii) 면 로마자 자식, 다음이 (1) 이면 알파벳 형제
    out = assign_label_paths(a_to_h + [
        para("<P>(1) One.</P>"), para("<P>(i) Roman.</P>"), para("<P>(ii) Roman two.</P>"),
    ])
    assert paths(out) == a_to_h_paths + [["h", "1"], ["h", "1", "i"], ["h", "1", "ii"]]

    out = assign_label_paths(a_to_h + [
        para("<P>(1) One.</P>"), para("<P>(i) Letter.</P>"), para("<P>(1) One.</P>"), para("<P>(2) Two.</P>"),
    ])
    assert paths(out) == a_to_h_paths + [["h", "1"], ["i"], ["i", "1"], ["i", "2"]]
    assert statuses(out) == ["ok"] * 12


def test_multi_label_and_unnumbered_blocks_inherit():
    root = load_root()

    # 63.1: "(a) <I>General.</I> (1) …" 은 소제목을 건너뛰고 두 단계, "(4)(i)" 도 두 단계
    out = assign_label_paths(parse_blocks(find_node(root, "DIV8", "63.1")))
    assert [b["kind"] for b in out] == ["paragraph"] * 8 + ["citation"]
    assert paths(out) == [
        ["a", "1"], ["a", "2"], ["a", "3"], ["a", "4", "i"], ["a", "4", "ii"], ["a", "4", "iii"],
        ["a", "5"], ["a", "6"], ["a", "6"],
    ]
    assert statuses(out) == ["ok"] * 8 + ["inherited"]

    # 63.3: 번호 없는 첫 문단은 빈 경로, 문단 아닌 블록(EXTRACT)은 직전 경로 + inherited
    #   "(a) <I>System International (SI) units of measure:</I>" 의 (SI) 는 번호가 아니다
    out = assign_label_paths(parse_blocks(find_node(root, "DIV8", "63.3")))
    assert [b["kind"] for b in out] == [
        "paragraph", "paragraph", "extract", "paragraph", "extract", "paragraph", "extract", "citation",
    ]
    assert paths(out) == [[], ["a"], ["a"], ["b"], ["b"], ["c"], ["c"], ["c"]]
    assert statuses(out) == ["inherited", "ok", "inherited", "ok", "inherited", "ok", "inherited", "inherited"]

    # 번호 없는 문단은 직전 경로를 물려받고, 같은 번호가 또 나오면 uncertain (경로는 최선의 추측)
    out = assign_label_paths([
        para("<P>(a) A.</P>"), para("<P>(1) One.</P>"), para("<P>No number here.</P>"),
        para("<P>(2) Two.</P>"), para("<P>(2) Two again.</P>"), para("<P>(3) Three.</P>"),
    ])
    assert paths(out) == [["a"], ["a", "1"], ["a", "1"], ["a", "2"], ["a", "2"], ["a", "3"]]
    assert statuses(out) == ["ok", "ok", "inherited", "ok", "uncertain", "ok"]
    assert all(set(b) >= NEW_FIELDS for b in out)


def test_definition_terms_become_labels():
    # 63.2: "<P><I>Act</I> means …" 처럼 이탤릭으로 시작하는 정의 문단은 용어 이름이 번호 역할
    out = assign_label_paths(parse_blocks(find_node(load_root(), "DIV8", "63.2")))
    assert [b["kind"] for b in out] == ["paragraph"] * 4 + ["citation"]
    assert paths(out) == [[], ["Act"], ["Actual emissions"], ["Administrator"], ["Administrator"]]
    assert statuses(out) == ["inherited", "ok", "ok", "ok", "inherited"]

    # (b) 밑의 용어는 바깥 번호도 붙는다. 용어 뒤 (i)(ii) 는 용어의 자식. 다음 용어가 앞 용어를 대신한다.
    # 용어 끝의 쉼표·마침표는 뗀다. "(CEMS)" 같은 약어는 번호가 아니다. (c) 가 오면 용어 맥락이 끝난다.
    out = assign_label_paths([
        para("<P>(a) <I>Applicability.</I> This subpart applies.</P>"),
        para("<P>(b) <I>Definitions.</I> The following apply.</P>"),
        para("<P><I>Wastewater</I> means water that:</P>"),
        para("<P>(i) Contains either:</P>"),
        para("<P>(ii) Is discarded.</P>"),
        para("<P><I>Affected source,</I> for this subpart, means the unit.</P>"),
        para("<P><I>Continuous emission monitoring system</I> (CEMS) means the equipment.</P>"),
        para("<P>(c) Next paragraph.</P>"),
    ])
    assert paths(out) == [
        ["a"], ["b"], ["b", "Wastewater"], ["b", "Wastewater", "i"], ["b", "Wastewater", "ii"],
        ["b", "Affected source"], ["b", "Continuous emission monitoring system"], ["c"],
    ]
    assert statuses(out) == ["ok"] * 8
