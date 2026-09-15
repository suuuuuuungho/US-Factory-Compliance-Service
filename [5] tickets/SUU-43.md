# SUU-43 feat(db): 문단 번호 (a)(1)(i)를 label_path로 채움

## 목표
조문 하나의 블록 목록(SUU-42 `parse_blocks` 결과)을 받아, 블록마다 "어느 문단 밑인가" 경로 `label_path`(예: `["a","2","ii"]`)와 `label_status`(`ok`/`inherited`/`uncertain`)를 붙인다. 정의 조문은 용어 이름이 번호 역할을 한다(예: `["b","Wastewater","i"]`).

## 건드릴 파일
- 만들 것: `[2] db/pipeline/1_eCFR/ecfr_labels.py`
  - `assign_label_paths(blocks) -> list[dict]` — `blocks`는 조문(DIV8/DIV9) 하나의 `parse_blocks` 결과. 각 dict에 `label_path`(list[str])와 `label_status`(str) 두 칸을 더해 같은 순서로 돌려준다. 다른 칸은 손대지 않는다
- 이미 있음: `ecfr_blocks.py`(`kind`, `markup`, `text_content`), fixture `ecfr_part63_sample.xml`

## 안 하는 것
- 번호 고쳐 쓰기, 법적 판단, 조문 인용 추출, 파일 저장(SUU-44)
- `tests/` 아래 파일 수정. `ecfr_blocks.py` 등 기존 `ecfr_*.py` 수정. 새 의존성(표준 `re`만 쓰면 됨)
- 문단 중간에 숨은 번호(`… means: (1) …`) 찾기 — 첫머리와 이탤릭 소제목 뒤만 본다

## 완료 기준 ↔ 테스트
| 완료 기준 | 테스트 함수 |
|---|---|
| `(a)(1)(2)(i)(ii)(b)` 순서가 맞는 경로로 나옴. 두 칸만 추가되고 나머지는 그대로 | `test_label_paths_follow_sequence` |
| `(h)` 다음 `(i)`는 형제 `["i"]`, `(1)` 다음 `(i)`는 자식 `["a","1","i"]`. 둘 다 되면 다음 문단 첫 번호로 정함 | `test_roman_vs_letter_uses_context` |
| `(4)(i)` 한 문단은 두 단계 다, `(a) <I>General.</I> (1)`은 소제목 건너뛰고 두 단계. 번호 없는 문단·문단 아닌 블록은 직전 경로 + `inherited`. 같은 번호 반복은 `uncertain` | `test_multi_label_and_unnumbered_blocks_inherit` |
| `<P><I>용어</I> means …` 정의 문단은 용어 이름이 경로에 들어가고, 바깥 `(b)`가 있으면 `["b","용어"]`, 그 밑 `(i)`는 `["b","용어","i"]` | `test_definition_terms_become_labels` |

테스트 파일: `[2] db/tests/test_ecfr_labels.py`

## Codex 메모

### 규칙 한 줄
**문단 첫머리의 `(x)` 번호를 읽고, 스택(현재 경로)에서 "형제 → 자식 → 조상 → 건너뛴 자식" 순서로 들어갈 자리를 찾는다.** 번호 없는 블록은 직전 경로를 그대로 물려받는다.

### 1. 번호 읽기 — `markup`에서 읽는다 (`text_content` 아님)
이탤릭 소제목 `<I>…</I>`를 구분해야 해서 `markup`을 본다. 진짜 파일에서 나오는 모양:
```
<P>(2) 본문…                              → ["2"]
<P>(4)(i) 본문…                           → ["4","i"]
<P>(a) <I>General.</I> (1) 본문…          → ["a","1"]      소제목 뒤 번호도 읽는다
<P>(b) <I>Tomahawk Mill</I>—(1) <I>Applicability.</I> (i) 본문…  → ["b","1","i"]
<P>(6) <I>Cl<E T="52">2</E>HCl ratios</I>—(i) …   → ["6","i"]   <I> 안에 태그가 있어도 됨
<P>(a) <I>Compliance dates</I>. (1) …      → ["a","1"]      </I> 뒤 마침표·콜론·— 허용
<P>(a) <I>Units (SI) of measure:</I></P>  → ["a"]          <I> 안의 (SI)는 번호 아님
<P>(a) Except as provided in paragraph (b) … → ["a"]       본문 속 (b)는 안 읽음
```
정규식 (앞에서부터 "번호 묶음 + (이탤릭 소제목 + 구두점)?" 반복):
```python
_LABEL  = r"\([^()\s<>]{1,4}\)"
_ITALIC = r"<I>[\s\S]*?</I>"
_LEAD   = re.compile(rf"^<[^>]+>\s*(?:(?:{_LABEL}\s*)+(?:{_ITALIC}[\s.:—-]*)?)+")
_TOKEN  = re.compile(r"\(([^()\s<>]{1,4})\)")
# 토큰 = _LEAD 매치 부분에서 <I>…</I>를 지운 뒤 _TOKEN.findall
```
읽은 토큰 중 **모양(아래 2번)에 안 맞는 첫 토큰부터는 버린다** (`(a)(MW)` → `["a"]`, `(CEMS)` → 없음).

**정의 용어**: `_LEAD`에 안 걸리고 markup이 `^<[^>]+>\s*<I>(…)</I>` 로 시작하면 용어 문단. 용어 이름 = `<I>` 안 글에서 태그 지우고 공백 정리 후 끝의 `,.:;` 뗀 것 (`<I>Affected source,</I>` → `Affected source`). `</I>` 바로 뒤 `[\s.:—-]*` 다음에 오는 번호(`<I>Deviation.</I> (1)`)는 용어의 자식으로 읽는다 (`["Deviation","1"]`). 약어 `(CEMS)`는 모양이 안 맞으니 무시.

### 2. 번호 모양 4가지와 단계 6개
| 모양 | 정규식(fullmatch) | 순서값 |
|---|---|---|
| `alpha` | `[a-z]` | a=1 … z=26 |
| `num` | `[0-9]{1,3}` | int |
| `roman` | `x{0,3}(ix\|iv\|v?i{0,3})` | 로마 숫자 값 (i=1, iv=4, xx=20) |
| `upper` | `[A-Z]` | A=1 … |

한 토큰이 여러 모양일 수 있다: `i`,`v`,`x` = alpha+roman. `ii`,`xx` = roman만 (진짜 파일에 `(aa)` 같은 겹글자 alpha는 없음).

단계(`LEVELS`, 인덱스가 깊이): `["alpha","num","roman","upper","num","roman"]` = `(a)(1)(i)(A)(1)(i)`.

### 3. 스택
스택 = `[(pos, tok, cls)]`. `pos`는 LEVELS 인덱스, `cls`는 모양 이름 또는 `"term"`. `label_path = [tok for _, tok, _ in stack]`.

`_after(entry, tok)`: 같은 모양이고 순서값이 더 크면 True ("뒤에 오는 번호"). **크기만 비교**(`(7)-(9) [Reserved]` 다음 `(10)`처럼 건너뛰어도 형제). `cls == "term"`이면 항상 False.

`_first_at(pos, tok)`: `LEVELS[pos]` 모양이고 순서값이 1이면 True (`a`,`1`,`i`,`A`).

### 4. 토큰 하나의 후보 자리 — `_candidates(stack, tok)` 순서대로
`d` = 스택 맨 위 `pos` (비었으면 −1)
1. **sibling**: 맨 위와 `_after` → 맨 위를 바꿈
2. **child**: `_first_at(d+1, tok)` → 밑에 붙임
3. **ancestor**: 맨 위 바로 아래부터 바닥까지 내려가며 `_after` 되는 항목 → 그 항목까지 자르고 바꿈 (깊은 쪽 우선)
4. **child_skip**: `d+2` 이상에서 `_first_at` 되는 가장 가까운 단계 → 밑에 붙임 (`(a)(5)` 다음 `(A)`, 용어 다음 `(i)`)

후보가 하나도 없으면 **fallback**: `top+1`부터 0까지 내려가며 토큰 모양과 같은 `LEVELS[pos]`를 찾아, 현재 체인(마지막 용어 항목 뒤)에서 `pos` 미만 항목만 남기고 붙인다. 그것도 없으면 스택 그대로. 둘 다 `uncertain`.

### 5. 문단 하나 넣기 — `_place_paragraph(stack, toks, next_toks)`
1. 첫 토큰의 후보를 전부 구한다
2. 후보마다 나머지 토큰이 **바로 아래 단계 첫 번호로 연달아** 붙는지 본다 (`(4)(i)`: 4 다음 i가 `_first_at(d+1)`). 붙는 후보만 남긴다 → `(i)(1)`은 alpha i로만 이어지므로 자동으로 알파벳
3. 남은 후보가 2개 이상이고 다음 번호 문단(`next_toks`)이 있으면: 후보를 적용한 스택에 다음 문단 첫 토큰을 넣었을 때 첫 후보가 sibling/child/ancestor인 후보를 고른다 (**한 문단 미리 보기**). `(h)(1)` 다음 `(i)`: 다음이 `(ii)`면 roman 자식, `(1)`이면 alpha 형제
4. 남은 첫 후보 채택, `ok`
5. 아무 후보도 안 이어지면: 첫 토큰은 후보 1번(없으면 fallback, `uncertain`), 나머지는 `d+1`부터 `_first_at` 되는 단계에 붙이고 안 되면 fallback + `uncertain`

### 6. 블록 순회 — `assign_label_paths`
```
toks_of = [번호 읽기(markup) if kind=="paragraph" else None  for 블록]
stack = []
for i, b in enumerate(blocks):
    kind != "paragraph"  → label_path = 현재 경로, label_status = "inherited"
    토큰 없음:
        용어 문단        → 스택에 용어 넣기(아래), 뒤따르는 번호는 자식으로, "ok"
        아니면          → 현재 경로, "inherited"
    토큰 있음            → next_toks = 뒤에 오는 첫 번호 문단의 토큰
                           _place_paragraph → label_path, label_status
```
**용어 넣기**: 스택에 `cls=="term"` 항목이 있으면 그 자리부터 잘라 새 용어로 바꾸고, 없으면 맨 위에 `(0, 이름, "term")`을 얹는다 (바깥 `(b)` 맥락은 유지 → `["b","Wastewater"]`). 용어의 `pos`는 0이라 그 자식은 `(1)`/`(i)`(child_skip)/`(A)`가 된다. `(c)`가 오면 ancestor 규칙으로 `(b)`를 찾아 용어가 빠진다.

### 7. 결과 칸
| 칸 | 값 |
|---|---|
| `label_path` | `list[str]`. 새 list (스택 복사) |
| `label_status` | `ok` 번호를 읽어 자리 찾음(용어 포함) / `inherited` 번호 없어 직전 경로 / `uncertain` fallback이 한 번이라도 쓰임 |

### 8. 진짜 파일(26 MB, 조문·부록 3,120개) 기대치 — merge 후 Claude가 확인
- 문단 블록 65,188개 = `ok` 55,330 (번호 50,051 + 용어 5,279) · `inherited` 9,818 · `uncertain` **40**
- 자리 찾은 방법: sibling 30,158 · child 11,778 · ancestor 8,077 · child_skip 48 · fallback 37 · none 3
- 경로 깊이(ok): 1단계 13,888 · 2단계 21,055 · 3단계 15,036 · 4단계 5,349 · 5단계 2
- 남은 `uncertain` 40개는 원문 자체 문제(같은 번호 두 번 `(vi)(vi)`, 중간 단계 없이 `(B)`, 부록 수식 `(V) = …`)
- 전체 1.7초. 같은 입력 → 같은 출력(랜덤·시간 없음)

### 9. 주의
- `markup`만 읽고 원본 트리·다른 칸은 건드리지 않는다
- 부록(DIV9)은 `(a)(1)` 체계가 아니라 `<I>` 수식 이름이 용어로 잡힐 수 있다. 정상이며 SUU-44 품질 보고에서 본다
- `(h)` 뒤 `(i)`처럼 스택만으로 못 정하는 건 다음 문단으로 정한다. 그래도 안 되면 첫 후보(형제 > 자식)
