# SAP Clean Core Advisor

[![CI](https://github.com/marcellokim/sap-clean-core-advisor/actions/workflows/ci.yml/badge.svg)](https://github.com/marcellokim/sap-clean-core-advisor/actions/workflows/ci.yml)

SAP legacy landscape를 입력하면 **Clean Core Score / TCO / Risk**를 계산하고,
권고안·근거(Evidence Ledger)·PDF 보고서를 생성하는 Streamlit 기반 진단 도구입니다.

---

## 1) Project Overview

이 프로젝트는 SAP 전환 초기 단계에서 자주 발생하는 3가지 문제를 해결하는 데 집중합니다.

1. **현황 진단의 비정형성**
   - 프로젝트/컨설턴트마다 진단 기준이 달라 비교가 어려움
2. **AI 의존 보고서의 불안정성**
   - LLM/RAG 실패 시 결과가 깨지거나 비어버리는 문제
3. **권고안의 설명 가능성 부족**
   - “왜 이 권고가 나왔는가?”를 추적하기 어려움

핵심 원칙:
- **Deterministic-first**: 점수/비용/리스크는 규칙 기반 계산
- **Soft-fail reliability**: LLM/RAG 실패 시에도 fallback 보고서 제공
- **Traceability by design**: 권고안별 근거 체인(Evidence Ledger) 유지

---

## 2) What You Can Do in This App

### A. Clean Core Assessment 탭
- 고객사 입력을 기반으로 아래 결과를 즉시 산출
  - Clean Core Score
  - Current / Projected TCO
  - 3-year savings
  - Risk level / factors
  - Recommendations + Evidence Ledger
  - Executive Summary / Detailed Report / PDF

### B. Joule Readiness Checklist 탭
- 체크리스트 기반으로 Joule 도입 준비도 Gap 분석 결과 생성
- 리스크 레벨(High/Medium/Low) 및 액션 제시

---

## 3) Pipeline (Runtime Architecture)

```text
Input
 -> Ruleset Resolution (generated > industry > base)
 -> Deterministic Calculator (Score/TCO/Risk)
 -> RAG Context (optional)
 -> LLM Report (optional)
 -> Evidence Ledger
 -> PDF Renderer
 -> Streamlit UI
```

### AnalysisPolicy 모드

| mode | deterministic calc | RAG | LLM |
|---|---|---|---|
| `deterministic` | ✅ | ⛔ | ⛔ |
| `hybrid` | ✅ | 선택 | 선택 |
| `llm_only` | ✅(기초 산출) | 선택 | 선택 |

> 포트폴리오 UI(`ui/policy.py`)는 기본적으로 `hybrid` 정책으로 고정되어 실행됩니다.

---

## 4) Input / Output at a Glance

### 주요 입력(`CustomerInput`)
- 회사/업종/ERP 버전/DB 종류·사이즈
- 사용자 수, 커스텀 프로그램 수, 커스텀 비중
- 모듈별 커스텀 심각도
- 연간 IT 예산, Pain Points, 희망 전환 기간

### 주요 출력(`AdvisorOutput`)
- 정량 지표: score, tco, risk
- 리포트: `executive_summary`, `detailed_report`
- 신뢰성 메타:
  - `generation_mode`, `generation_error_code`
  - `rag_status`, `llm_status`, `pdf_status`
  - `stage_metrics_ms`
  - `evidence_ledger`
  - `validation_warnings`

---

## 5) Result Quality Guardrails (현재 구현)

LLM 결과 품질을 안정화하기 위해 아래 보호 장치를 사용합니다.

1. **출력 계약 검증 + 1회 재시도**
   - 빈 섹션/중복 섹션/날짜 불일치/플레이스홀더 등 감지
2. **치명 이슈 시 fallback 전환**
   - `LLM_OUTPUT_QUALITY_FALLBACK` 경고와 함께 규칙 기반 보고서 사용
3. **상세 섹션 구조 보강**
   - LLM 상세 본문 구조가 약하면 deterministic 상세 템플릿 자동 보강
   - `LLM_DETAIL_TEMPLATE_ENFORCED` 경고로 명시
4. **LLM 사용량·비용 추적**
   - provider usage 기반 토큰/비용 집계(`llm_usage_source=provider`)

---

## 6) Key Features (Implementation View)

### 1) Deterministic Assessment Engine
- 입력값 기반으로 일관된 수치 계산
  - score / tco / risk / tech debt breakdown
  - ruleset profile/source/version 추적

### 2) Policy-Driven Analysis Runner
- 실행 정책(`AnalysisPolicy`)으로 단계 제어
  - timeout budget 적용
  - stage별 상태/메트릭 수집

### 3) Evidence Ledger
- 권고안 claim 단위로 근거 등급(A/B/C/D) 기록
- claim ↔ rule_ids ↔ input_facts ↔ rag_sources 연결

### 4) Source Governance
- `docs/sources.yaml` 기반 출처 카탈로그 검증
- 스키마/노후도(staleness) 자동 체크
- 스냅샷 파일 경로/sha256 해시 무결성 자동 체크

### 5) Document Outputs
- Executive Summary / Detailed Report 생성
- PDF 내보내기
- EA/Workshop/Ops/Joule 실무 템플릿 제공(`docs/*`)

---

## 7) Project Structure

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
tools/snapshot_sources.py          # source snapshot/hash refresh
docs/                              # templates, playbooks, appendices
```

---

## 8) Getting Started

### Prerequisites
- Python 3.13+
- [uv](https://docs.astral.sh/uv/)

### Install
```bash
uv sync
cp .env.example .env
# 필요 시 API key 입력
```

`uv`가 없으면:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e .
cp .env.example .env
```

### Run
```bash
make run
# or
uv run streamlit run app.py
```

---

## 9) Configuration

주요 환경 변수(`.env.example` 참고):

- `ANALYSIS_MODE`: `deterministic | hybrid | llm_only`
- `ANALYSIS_TIMEOUT_MS`: 전체 분석 타임아웃(ms)
- `LLM_PROVIDER`: `gemini | glm`
- `LLM_DISABLE`: LLM 단계 비활성화
- `RAG_ENABLE`: RAG 단계 활성화
- `SOURCE_VERIFY_MAX_AGE_DAYS`: 출처 최신성 기준
- `REPORT_PREFLIGHT_ENABLE`: 보고서 사전 검증 활성화
- `REPORT_PREFLIGHT_BLOCK_ON_HIGH`: HIGH 이슈 시 PDF 생성 차단

운영/데모 권장 프로파일:
- **안정성 우선**: `ANALYSIS_MODE=hybrid`, `RAG_ENABLE=true`, `LLM_DISABLE=false`
- **속도 우선**: `ANALYSIS_MODE=deterministic`

---

## 10) Reproducibility & Quality Checks

```bash
make test
make test-compat
make check-import-cycles
make verify-sources
make verify-report-preconfirm
make qa-report
```

- `make test`: 전체 unit test 실행
- `make test-compat`: `analysis_service` / `fpdf_renderer` / `chroma_provider` 호환성 계약 테스트 실행
- `make check-import-cycles`: `services`/`app.py` 내부 import cycle 점검
- `make verify-sources`: 출처 카탈로그 검증
- `make verify-report-preconfirm`: 인용 커버리지 + 수치/날짜 정합성 사전검증
- `make qa-report`: 테스트 + 출처 검증 + pre-confirm 전체 게이트
- CI(`.github/workflows/ci.yml`)에서도 `make qa-report` + `make test-compat`를 필수 게이트로 실행

출처 스냅샷 갱신:
```bash
./.venv/bin/python tools/snapshot_sources.py --offline --update-catalog --json
```

로컬 검증 스냅샷(2026-03-10):
- `make test` → 42 tests, all pass
- `make verify-sources` → `[]`
- `make verify-report-preconfirm` → PASS

예시(결정론 샘플 케이스 기준 기대값):
- Clean Core Score: `42.6`
- Current / Projected TCO: `1.06 / 0.95`
- 3-year savings: `0.33`

---

## 11) Docs & Assets

- Engineering appendix: `docs/engineering/ARCHITECTURE_APPENDIX.md`
- Compatibility contracts: `docs/engineering/COMPATIBILITY_CONTRACTS.md`
- EA cookbook templates: `docs/ea-cookbook/*`
- Workshop kit: `docs/workshop-kit/*`
- Joule playbook: `docs/joule-playbook/*`
- Ops toolkit: `docs/ops-toolkit/*`

---

## 12) Known Limitations

- TCO는 계약/조달 조건을 반영하지 않은 의사결정용 상대 추정치입니다.
- LLM 품질은 모델/키 상태/네트워크에 영향을 받으며, 품질 게이트 실패 시 fallback 보고서가 사용됩니다.
- RAG 품질은 `data/*.md`와 소스 최신성에 직접적으로 영향을 받습니다.

---

## 13) References

- SAP RISE Clean Core:
  https://www.sap.com/products/erp/rise/methodology/clean-core.html
- SAP Strategy / Maintenance:
  https://support.sap.com/en/offerings-programs/strategy.html
- SAP Readiness Check:
  https://help.sap.com/doc/bb0e7ba5158c424ab7ce010228bf1de1
