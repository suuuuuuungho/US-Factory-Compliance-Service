# README.md

이 폴더의 문서가 각각 무슨 역할인지 정리한 안내서입니다.
`1) project/0_Project_summary.md` → `1_Project_full.md` 순서로 읽으면 됩니다.

## 1) project — 프로젝트 소개 문서

 1) `0_Project_summary.md`: 면접관용 3분 요약. 문제·해결·성과를 가장 짧게 담은 문서 
 2) `1_Project_full.md`: 프로젝트 전체 설명서(원본). 아래 2~6번 문서는 이 파일을 절 단위로 나눠 놓은 것 
 3) `2_Project_overview.md`: 서비스 소개, 어필 포인트 4가지, 프로젝트 기간·흐름, 기술 스택 
 4) `3_Project_problem_definition.md`: 문제 정의(규제 배경, 반복성, 기존 해법, 경제적 손실)와 활용한 데이터셋 
 5) `4_Project_rag_quality.md`: RAG 검색·답변 품질을 어떻게 실험하고 개선했는지 단계별 기록 
 6) `5_Project_tdd_automation.md`: TDD 개발 자동화 흐름과 사람·Claude·Codex·CI의 역할 분담 
 7) `6_Project_my_decisions.md`: AI에 맡기지 않고 사람이 직접 정한 판단(서비스 원칙, 평가셋, CI 기준, 개발 원칙) 

## 2) Data — 활용한 데이터

1. 데이터 명세서. (양식: Google, The Data Cards Playbook)

Supabase에 실제로 넣어 둔 데이터 명세서(Data Card). 무슨 데이터가 어디에 얼마나 있고, 쓸 때 무엇을 조심해야 하는지 설명. 

`0_Data Specification_v1.md`

2. 데이터 계약서 (양식: ODCS v3.1.0)

Data Specification이 사람용 설명서라면, 계약서는 기계용 약속입니다.
표 이름·컬럼·타입·규칙을 YAML로 적어 두고, CI가 PR마다 실제 Supabase DB와 같은지 자동으로 검사합니다.

   db/contracts

 1) `ecfr.odcs.yaml`: eCFR — 현재 시행 중인 규정집 원문(40 CFR Part 63) 표 
 2) `fr.odcs.yaml`: Federal Register — 규정 변경 소식 표 
 3) `echo.odcs.yaml`: ECHO — 시설·점검·위반·처분 기록 표 
 4) `adi.odcs.yaml`: ADI + CAA Dashboard — EPA 판정 회신 표 
 5) `rag.odcs.yaml`: RAG — 검색 조각과 답변 기록 표 
 6) `common.odcs.yaml`: Common — 적재 운영 기록 표 
 7) `contract_check.py`: 위 계약서 6개와 실제 DB가 같은지 검사하는 스크립트. CI에서 실행됨
