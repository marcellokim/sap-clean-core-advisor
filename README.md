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
5. **타임아웃 비활성 경로 최적화**
   - `ANALYSIS_TIMEOUT_MS=0`일 때 LLM 호출을 직접 실행해 불필요한 thread 생성 오버헤드 제거

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
  application/analysis_runner.py   # orchestration policy (slim)
  application/llm_costs.py         # provider usage token/cost helpers
  application/llm_runtime.py       # optional-timeout LLM execution helper
  application/report_content.py    # report payload/fallback/quality helpers
  application/report_preflight.py  # pre-confirm + PDF gate helpers
  cost_calculator.py               # KPI calculations
  domain/                          # recommendation/evidence/validation
  infrastructure/                  # llm/rag/pdf adapters + compat telemetry
ui/sidebar.py                      # sidebar/support-pack rendering
tests/                             # unit tests
tools/verify_sources.py            # source catalog validator
tools/snapshot_sources.py          # source snapshot/hash refresh
scripts/check_import_cycles.py     # internal import cycle checker
scripts/verify_prune_hygiene.py    # fast-lane prune hygiene gate
scripts/compat_telemetry_report.py # safe-lane telemetry summary/promotion checker
scripts/verify_release_readiness.py # final readiness gate (qa-report x3 + promotion checks)
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
- `COMPAT_TELEMETRY_ENABLE`: safe-lane 호환 래퍼 사용 telemetry 로깅
- `COMPAT_TELEMETRY_LOG_PATH`: compatibility telemetry JSONL 경로
- `COMPAT_TELEMETRY_INCLUDE_TESTS`: 테스트 실행 시 telemetry 파일 기록 포함 여부(기본 false)
- `COMPAT_DEPRECATION_WARN`: safe-lane 호환 래퍼 호출 시 deprecation warning
- `COMPAT_DEPRECATION_REMOVE_AFTER`: 제거 목표 시점(기본 `2026-06-30`)

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
make verify-prune-hygiene
make report-compat-telemetry
make verify-safe-lane-promotion
make verify-safe-lane-promotion-strict
make verify-release-readiness
make qa-report
```

- `make test`: 전체 unit test 실행
- `make test-compat`: `analysis_service` / `fpdf_renderer` / `chroma_provider` 호환성 계약 테스트 실행
- `make check-import-cycles`: `services`/`app.py` 내부 import cycle 점검
- `make verify-sources`: 출처 카탈로그 검증
- `make verify-report-preconfirm`: 인용 커버리지 + 수치/날짜 정합성 사전검증
- `make verify-prune-hygiene`: fast-lane 삭제 대상/deprecated target(backtest/calibrate) 재유입 방지
- `make report-compat-telemetry`: 최근 7일 safe-lane 호환 래퍼 호출량 JSON 요약
- `make verify-safe-lane-promotion`: 7일 호출량 0건 + prune hygiene + compat contract 통합 검증 (PR/CI 기본 게이트)
- `make verify-safe-lane-promotion-strict`: `verify-safe-lane-promotion` + telemetry 로그 실재 여부(`--require-log`) + 로그 유효성(`--fail-on-invalid-rows`)까지 검증하는 릴리즈 전 필수 게이트
- `make verify-release-readiness`: 최종 릴리즈 체크리스트(`make qa-report` 3회 연속 + `test-compat` + import cycle + safe-lane **strict** 게이트) 실행 및 리포트 저장(`artifacts/qa/release_readiness.json`)
- `make qa-report`: 테스트 + 출처 검증 + pre-confirm + prune hygiene 전체 게이트
- CI(`.github/workflows/ci.yml`)에서는 `make qa-report` + `make verify-safe-lane-promotion`를 기본 게이트로 실행하며, telemetry 로그 artifact가 있을 때만 strict 게이트를 추가 실행합니다. 릴리즈 직전에는 `make verify-safe-lane-promotion-strict`를 필수 실행하세요.

릴리즈 전 권장 순서(필수):
```bash
make verify-release-readiness
make verify-safe-lane-promotion-strict
```

테스트/검증 커맨드는 synthetic 호출로 telemetry가 오염되지 않도록 기본적으로
`COMPAT_TELEMETRY_ENABLE=false` 및 `COMPAT_DEPRECATION_WARN=false`로 실행됩니다.

출처 스냅샷 갱신:
```bash
./.venv/bin/python tools/snapshot_sources.py --offline --update-catalog --json
```

로컬 검증 스냅샷(2026-03-10):
- `make test` → 59 tests, all pass
- `make test-compat` → 10 tests, all pass
- `make check-import-cycles` → No internal import cycles detected
- `make verify-sources` → `[]`
- `make verify-report-preconfirm` → PASS
- `make verify-prune-hygiene` → `[]`
- `make report-compat-telemetry` → `{ total_events_in_window: 0, promotion_ready: true }`
- `make verify-safe-lane-promotion` → PASS (nonstrict mode)
- `make verify-safe-lane-promotion-strict` → telemetry log가 없거나 비어있거나 invalid row가 있으면 **의도적으로 FAIL**
- `make verify-release-readiness` → strict safe-lane 조건 충족 시 PASS (`artifacts/qa/release_readiness.json` 생성)
- Refactor KPI snapshot: `analysis_runner.py` 439 lines / `app.py` 196 lines
- Microbench(모킹 LLM, 150회): timeout=0 경로 p95 `0.139ms`, timeout=1000 경로 p95 `0.198ms`

예시(결정론 샘플 케이스 기준 기대값):
- Clean Core Score: `42.6`
- Current / Projected TCO: `1.06 / 0.95`
- 3-year savings: `0.33`

---

## 11) Docs & Assets

- Engineering appendix: `docs/engineering/ARCHITECTURE_APPENDIX.md`
- Compatibility contracts: `docs/engineering/COMPATIBILITY_CONTRACTS.md`
  - safe-lane deprecate/telemetry 정책 및 제거 목표일(`2026-06-30`) 포함
- Release notes (2026-03-10): `docs/engineering/RELEASE_NOTES_2026-03-10.md`
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
