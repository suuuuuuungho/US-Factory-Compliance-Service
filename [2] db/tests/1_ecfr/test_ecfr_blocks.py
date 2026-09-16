from pathlib import Path

from lxml import etree

from ecfr_blocks import parse_blocks

XML = Path(__file__).parent / "fixtures" / "ecfr_part63_sample.xml"

FIELDS = {"block_no", "kind", "text_content", "markup", "source_locator", "parse_status"}


def load_root():
    parser = etree.XMLParser(
        resolve_entities=False, no_network=True, load_dtd=False, huge_tree=True
    )
    return etree.fromstring(XML.read_bytes(), parser)


def find_node(root, tag, n):
    return root.find(f".//{tag}[@N='{n}']")


def normalize(text):
    return " ".join(text.split())


def test_block_kinds_follow_document_order():
    # 63.110 = 문단 3개, 소제목, 표, 그림, 수식, 인용문, 참고, 각주, 편집자 주, STARS, 출처
    section = find_node(load_root(), "DIV8", "63.110")
    blocks = parse_blocks(section)

    assert [b["kind"] for b in blocks] == [
        "paragraph", "paragraph", "paragraph", "heading", "table", "image", "formula",
        "extract", "note", "footnote", "editorial_note", "other", "citation",
    ]
    assert [b["block_no"] for b in blocks] == list(range(1, 14))
    assert [b["source_locator"] for b in blocks] == [
        f"line:{n}" for n in (255, 256, 257, 258, 260, 285, 286, 288, 290, 293, 296, 298, 299)
    ]
    assert all(set(b) == FIELDS for b in blocks)

    assert blocks[0]["text_content"].startswith("(a) This subpart applies to all process vents")
    assert blocks[3]["text_content"] == "Category I Authorities"
    assert blocks[7]["text_content"] == "Where:"
    assert blocks[8]["text_content"].startswith("Note: This provision applies")
    assert blocks[12]["text_content"].startswith("[59 FR 19468, Apr. 22, 1994")


def test_no_text_is_lost_and_reserved_has_no_blocks():
    root = load_root()
    for tag, n, expected_count in (
        ("DIV8", "63.110", 13),
        ("DIV8", "63.1", 9),
        ("DIV9", "Table 1 to Subpart A of Part 63", 2),
    ):
        node = find_node(root, tag, n)
        # SUU-83: <br/>처럼 텍스트 사이에 공백 없이 끼는 태그도 경계로 친다
        # (안 그러면 "efficiency<br/>requirement"가 "efficiencyrequirement"로 붙어버림).
        body_text = normalize(" ".join(" ".join(c.itertext()) for c in node if c.tag != "HEAD"))
        blocks = parse_blocks(node)

        assert len(blocks) == expected_count
        combined = normalize(" ".join(b["text_content"] for b in blocks).replace("|", " "))
        assert combined == body_text
        assert "§" not in blocks[0]["text_content"][:2]  # HEAD(제목)는 블록이 아님

    assert parse_blocks(find_node(root, "DIV8", "63.569-63.599")) == []


def test_table_markup_kept_and_unknown_tag_marked():
    section = find_node(load_root(), "DIV8", "63.110")
    blocks = parse_blocks(section)
    by_kind = {b["kind"]: b for b in blocks}

    table = by_kind["table"]
    assert table["markup"].startswith('<DIV width="100%">')
    assert "<TABLE" in table["markup"] and "</TABLE>" in table["markup"]
    assert 'class="gpo_table"' in table["markup"]
    assert "Table 5—Three-Stage Arrestor" in table["text_content"]
    assert table["parse_status"] == "ok"

    image = by_kind["image"]
    assert image["markup"].startswith("<img")
    assert 'src="https://www.ecfr.gov/graphics/er04my98.004.gif"' in image["markup"]
    assert image["text_content"] == ""
    assert image["parse_status"] == "ok"

    formula = by_kind["formula"]
    assert formula["markup"].startswith("<MATH")
    assert 'src="https://www.ecfr.gov/graphics/er14my01.003.gif"' in formula["markup"]
    assert formula["parse_status"] == "ok"

    assert not any('src="/graphics/' in b["markup"] for b in blocks)
    # 원본 트리는 바꾸지 않는다 (src 치환은 복사본에서)
    assert section.find("img").get("src") == "/graphics/er04my98.004.gif"

    other = by_kind["other"]
    assert other["markup"] == "<STARS/>"
    assert other["parse_status"] == "unknown_tag"
    assert other["text_content"] == ""

    assert blocks[0]["markup"].startswith("<P>") and blocks[0]["markup"].endswith("</P>")
    assert by_kind["heading"]["markup"].startswith("<HD3>")
    assert by_kind["citation"]["markup"].startswith("<CITA")
    assert all(b["parse_status"] == "ok" for b in blocks if b["kind"] != "other")


def test_table_text_content_keeps_row_and_column_boundaries():
    # SUU-83: 표 셀을 그냥 이어붙이면 ">95"가 어느 열 값인지 알 수 없다.
    # 행은 줄바꿈으로, 셀은 " | "로 구분해서 구조를 살린다.
    section = find_node(load_root(), "DIV8", "63.110")
    blocks = parse_blocks(section)
    table = next(b for b in blocks if b["kind"] == "table")

    lines = [line.strip() for line in table["text_content"].splitlines()]
    assert "Filtration efficiency requirement, % | Aerodynamic particle size range, µm" in lines
    assert ">95 | >2.5" in lines
    assert ">85 | >1.1" in lines
    assert ">75 | >0.70" in lines
