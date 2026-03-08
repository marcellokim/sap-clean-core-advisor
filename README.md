# SAP Clean Core Advisor

[![CI](https://github.com/marcellokim/sap-clean-core-advisor/actions/workflows/ci.yml/badge.svg)](https://github.com/marcellokim/sap-clean-core-advisor/actions/workflows/ci.yml)

SAP legacy landscape를 입력하면 **Clean Core Score / TCO / Risk**를 계산하고,
권고안·근거(Evidence Ledger)·PDF 보고서를 생성하는 Streamlit 기반 진단 도구입니다.

---

## Overview

이 프로젝트는 다음 문제를 해결하는 데 초점을 둡니다.

- 복잡한 SAP 현황을 빠르게 정량화하고 비교 가능한 KPI로 표현
- AI 단계 실패 시에도 분석 결과를 안정적으로 제공(soft-fail)
- 권고안별 근거를 남겨 설명 가능성(traceability) 확보

---

## Key Features

### 1) Deterministic Assessment Engine
- 입력값 기반으로 일관된 수치 계산
  - Clean Core Score
  - Current / Projected TCO
  - 3-year savings
  - Risk level / factors

### 2) Policy-Driven Analysis Runner
- 실행 정책(`AnalysisPolicy`)으로 단계 제어
  - `deterministic`
  - `hybrid`
  - `llm_only`
- RAG/LLM/PDF 단계별 상태 및 에러코드 추적

### 3) Evidence Ledger
- 권고안 claim 단위로 근거 등급(A/B/C/D) 기록
- 보고서 신뢰성과 설명 가능성 강화

### 4) Source Governance
- `docs/sources.yaml` 기반 출처 카탈로그 검증
- 스키마/노후도(staleness) 자동 체크

### 5) Document Outputs
- Executive Summary / Detailed Report 생성
- PDF 내보내기
- 실무 문서 템플릿 제공(`docs/*`)

---

## Architecture (High-Level)

```text
Input Form
 -> Ruleset Resolution (generated > industry > base)
 -> Deterministic Calculator (Score/TCO/Risk)
 -> RAG Context (optional)
 -> LLM Report (optional)
 -> Evidence Ledger
 -> PDF Renderer
 -> Streamlit UI
```

핵심 원칙:
- Deterministic-first
- Soft-fail reliability
- Traceability by design

---

## Project Structure

```text
app.py                             # Streamlit entrypoint
config/                            # settings, rulesets
models/                            # pydantic schemas
services/
  application/analysis_runner.py   # orchestration policy
  cost_calculator.py               # KPI calculations
  domain/                          # recommendation/evidence/validation
  infrastructure/                  # llm/rag/pdf adapters
tests/                             # unit tests
tools/verify_sources.py            # source catalog validator
docs/                              # templates, playbooks, appendices
```

---

## Getting Started

### Prerequisites
- Python 3.13+
- [uv](https://docs.astral.sh/uv/)

### Install
```bash
uv sync
cp .env.example .env
# 필요 시 API key 입력
```

### Run
```bash
make run
# or
uv run streamlit run app.py
```

---

## Configuration

주요 환경 변수(`.env`):

- `ANALYSIS_MODE`: `deterministic | hybrid | llm_only`
- `ANALYSIS_TIMEOUT_MS`: 전체 분석 타임아웃(ms)
- `LLM_PROVIDER`: `gemini | glm`
- `LLM_DISABLE`: LLM 단계 비활성화
- `RAG_ENABLE`: RAG 단계 활성화
- `SOURCE_VERIFY_MAX_AGE_DAYS`: 출처 최신성 기준

전체 목록은 `.env.example` 참고.

---

## Quality Checks

```bash
make test
make verify-sources
```

- `make test`: unit test 실행
- `make verify-sources`: 출처 카탈로그 검증

---

## Docs & Assets

- Engineering appendix: `docs/engineering/ARCHITECTURE_APPENDIX.md`
- EA cookbook templates: `docs/ea-cookbook/*`
- Workshop kit: `docs/workshop-kit/*`
- Joule playbook: `docs/joule-playbook/*`
- Ops toolkit: `docs/ops-toolkit/*`

---

## References

- SAP RISE Clean Core:
  https://www.sap.com/products/erp/rise/methodology/clean-core.html
- SAP Strategy / Maintenance:
  https://support.sap.com/en/offerings-programs/strategy.html
- SAP Readiness Check:
  https://help.sap.com/doc/bb0e7ba5158c424ab7ce010228bf1de1
