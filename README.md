# SAP Advisor: Clean Core Assessment & Migration Decision Support

Deterministic SAP 진단 엔진 + LLM 보조 리포트 계층으로 구성된 포트폴리오 프로젝트입니다.

## Executive Summary (KOR)
이 프로젝트는 SAP ECC 기반 고객의 전환 의사결정을 위해 다음을 보장합니다.

1. **같은 입력 = 같은 수치/근거**
2. **LLM 실패 ≠ 제품 실패** (규칙 기반 fallback)
3. **권고사항별 근거 추적 가능** (Evidence Ledger)
4. **규칙 버전/프로파일/품질 메타 추적 가능**

핵심 구조는 `결정론적 계산 코어` + `RAG/LLM 보조 계층`입니다. 계산 수치(Clean Core/TCO/Risk)는 규칙 엔진이 책임지고, LLM은 요약/문서화 역할만 수행합니다.

## Executive Summary (ENG)
This project is a deterministic SAP migration advisor that separates:

- **Deterministic core** for KPI calculation (score, TCO, risk)
- **LLM assist layer** for narrative report generation

Design principles:

1. Same input always returns same numbers and rule traces.
2. LLM failure never breaks product output.
3. Every recommendation has traceable evidence.
4. Ruleset version/profile/quality are fully observable.

---

## Why This Project
SAP EA 지원 직무 맥락에서 중요한 것은 “모델이 멋진 문장을 쓰는 능력”보다,

- 비즈니스 입력을 구조화하고,
- 규칙 기반으로 재현 가능한 의사결정을 만들고,
- 결과 근거를 문서/출처로 설명하는 능력

입니다.

이 프로젝트는 이 3가지를 검증 가능하게 보여주도록 설계했습니다.

---

## System Architecture

```text
Input Form
  -> Analysis Service (orchestrator)
    -> Ruleset Resolution (generated > industry > base)
    -> Deterministic Calculator (Score/TCO/Risk)
    -> RAG Context (soft-fail)
    -> LLM report attempt (single-pass by default)
    -> Fallback report (deterministic)
    -> Evidence Ledger (rule/input/source trace)
    -> PDF generation (soft-fail)
  -> Dashboard + Download
```

### Runtime Flow
1. 입력 수집 (`CustomerInput`)
2. 산업 정규화 + 룰셋 선택
3. 규칙 계산 + rule IDs + ruleset 메타
4. RAG 컨텍스트 수집 (실패해도 계속)
5. LLM 시도 (실패 시 fallback)
6. Evidence Ledger 생성 (A/B/C/D)
7. PDF 생성 시도 (실패 코드 분리)
8. UI/로그 출력

---

## Deterministic Core

### Ruleset Resolution
우선순위:
1. `config/rulesets/generated/{industry}.yaml`
2. `config/rulesets/industries/{industry}.yaml`
3. `config/rulesets/base.yaml`

산업 문자열은 `config/industry_aliases.yaml`로 정규화합니다.
정규화 실패 시 `base` 폴백 + `INDUSTRY_MAPPING_FALLBACK_TO_BASE` 경고를 남깁니다.

### Clean Core Score
구성 항목:
- `custom_code`
- `erp_version`
- `database`
- `module_complexity`

가중합 방식으로 0~100 점수를 계산합니다.
세부 계수는 ruleset 파일에서 로드됩니다.

### TCO
연간 현재/전환 후 TCO 계산:
- 인프라 비용
- DB 규모 비용
- 커스텀 유지보수 비용
- 라이선스 비용

3년 누적 변화:
- `savings_3yr = (current - projected) * 3`

### Risk
임계값 기반 규칙으로 리스크 요인과 레벨(High/Medium/Low)을 산정합니다.

---

## Evidence Ledger
각 권고사항(claim)에 대해 아래를 저장합니다.

- `claim_id`
- `claim_text`
- `input_facts`
- `rule_ids`
- `rag_sources`
- `reference_source_ids`
- `evidence_grade`

### Evidence Grade
- `A`: 입력 사실 + 규칙 ID 모두 존재
- `B`: 규칙 ID만 존재
- `C`: 규칙 ID는 없고 RAG 출처만 존재
- `D`: 위 조건 미충족

즉, 권고가 단순 생성 텍스트가 아니라 어떤 규칙/입력/출처를 통해 나왔는지 추적할 수 있습니다.

---

## Error Taxonomy
표준 오류코드는 `services/error_codes.py`에서 중앙 관리합니다.

- LLM: `ERR_LLM_DISABLED`, `ERR_LLM_RATE_LIMIT`, `ERR_LLM_AUTH`, `ERR_LLM_PROVIDER`
- Provider: `ERR_PROVIDER_NOT_SUPPORTED`
- RAG: `ERR_RAG_UNAVAILABLE`
- PDF: `ERR_PDF_LAYOUT_OVERFLOW`, `ERR_PDF_FONT`, `ERR_PDF_UNKNOWN`

정책:
- LLM/RAG/PDF 실패는 가능한 한 soft-fail 처리
- 치명 오류가 아니면 결과 반환 유지

---

## Industry-specific Ruleset & Calibration

### Ruleset Files
- `config/rulesets/base.yaml`
- `config/rulesets/industries/manufacturing.yaml`
- `config/rulesets/industries/retail.yaml`
- `config/rulesets/industries/finance.yaml`
- `config/rulesets/generated/*.yaml`

### Calibration Quality Gate
`services/data_quality.py`에서 아래를 검증합니다.
- 필수 컬럼 존재
- 숫자형/범위 검사
- 최소 샘플 수 (`CALIBRATION_MIN_SAMPLES`)

조건 미충족 시:
- 보정 중단
- generated 룰셋 갱신 금지
- 에러/경고 리포트 출력

### Calibration Objective
`services/calibration_engine.py`

고정 목적함수:
- `loss = w_tco * MAPE + w_risk * risk_mismatch_rate`

고정 탐색 범위:
- multiplier `0.60 ~ 1.60`, step `0.05`

홀드아웃 평가를 포함하며, 품질 임계치 미달 시 결과를 배포하지 않습니다.

---

## Backtest Methodology
백테스트 스크립트:
- `tools/backtest_ruleset.py`

리포트 출력:
- `calibration/reports/backtest_YYYYMMDD.md`

지표:
- Train/Holdout TCO MAPE
- Train/Holdout Risk Agreement

---

## Source Governance

출처 카탈로그:
- `docs/sources.yaml`

검증 스크립트:
- `tools/verify_sources.py`

검증 규칙:
1. 스키마 유효성 (`source_id`, `tier`, `access`, `last_verified_date` 등)
2. staleness 검사 (`SOURCE_VERIFY_MAX_AGE_DAYS`)
3. URL 검사 (선택)

티어 정책:
- `official`: 2xx/3xx 기대
- `benchmark`: 접근 제한(401/403) 허용 가능, 상태 기록
- `academic`: open 접근 우선

---

## Reproducibility

### Install
```bash
uv sync
```

### Run App
```bash
uv run streamlit run app.py
```

### Run Tests
```bash
./.venv/bin/python -m unittest discover -s tests -v
```

### Verify Source Catalog (offline-safe)
```bash
./.venv/bin/python tools/verify_sources.py --skip-http --json
```

### Backtest
```bash
./.venv/bin/python tools/backtest_ruleset.py --industry manufacturing
```

### Calibrate
```bash
./.venv/bin/python tools/calibrate_ruleset.py --industry manufacturing
```

---

## Failure Modes & Mitigations

### 1) 데이터 품질 부족
- 원인: 표본 수 부족, 결측, 이상치
- 대응: 품질 게이트로 보정 차단 + base/industry ruleset 유지

### 2) 산업 매핑 실패
- 원인: 비정형 industry 입력
- 대응: alias 정규화 + base 폴백 + warning 노출

### 3) 과적합 보정
- 원인: 제한 없는 탐색/목적함수 편향
- 대응: 고정 범위 탐색 + holdout + 품질 임계치

### 4) 외부 소스 드리프트
- 원인: 링크 변경/만료
- 대응: sources catalog + staleness/URL 검증

### 5) LLM 쿼터/장애
- 원인: 429/인증/네트워크
- 대응: fallback report 자동 전환

### 6) PDF 렌더 실패
- 원인: 폰트/레이아웃 오버플로
- 대응: 화면 결과 유지 + PDF 오류코드 분리 표시

---

## Public Interfaces

### `AdvisorOutput` (추가 메타)
- `ruleset_version`
- `ruleset_profile_id`
- `ruleset_profile_source`
- `calibration_quality`
- `validation_warnings`
- `stage_metrics_ms`
- `evidence_ledger`

### `EvidenceItem` (확장)
- `reference_source_ids`

### `CalculationResult` (확장)
- `ruleset_profile_id`
- `ruleset_profile_source`
- `calibration_quality`

---

## Environment Variables
`.env.example` 기준

```bash
# LLM
LLM_PROVIDER=gemini
LLM_PIPELINE_MODE=single
LLM_MAX_RETRIES=2
LLM_BASE_DELAY_SEC=5
LLM_DISABLE=false

# RAG
RAG_MAX_CONTEXT_CHARS=6000

# Ruleset/Calibration
RULESET_DIR=config/rulesets
RULESET_GENERATED_DIR=config/rulesets/generated
CALIBRATION_MIN_SAMPLES=20
CALIBRATION_WEIGHT_TCO=0.7
CALIBRATION_WEIGHT_RISK=0.3

# Source Governance
SOURCE_VERIFY_MAX_AGE_DAYS=90
```

---

## CSV Data Contract (Calibration/Backtest)
필수 컬럼:

- `company_id`
- `industry`
- `erp_version`
- `db_type`
- `num_users`
- `num_custom_programs`
- `custom_code_ratio`
- `actual_current_tco`
- `actual_projected_tco`
- `actual_risk_level`
- `migration_duration_months`

정책:
- 샘플 데이터는 저장소에 포함하지 않음 (실데이터 전용)
- 품질 게이트 통과 시에만 보정 허용

---

## Rule IDs (대표)
추천 규칙:
- `REC_SCORE_LT_30`
- `REC_SCORE_LT_60`
- `REC_ECC_VERSION_TRANSITION`
- `REC_DB_TO_HANA`
- `REC_CUSTOM_RATIO_OVER_40`
- `REC_TCO_SAVINGS_POSITIVE`

리스크 규칙:
- `RISK_CUSTOM_RATIO_HIGH`
- `RISK_CUSTOM_RATIO_MEDIUM`
- `RISK_ECC6_EOS_2027`
- `RISK_DB_NOT_HANA`
- `RISK_LEVEL_HIGH_RULE`
- `RISK_LEVEL_MEDIUM_RULE`
- `RISK_LEVEL_LOW_RULE`

전체 매핑은 `config/rule_reference_map.yaml` 참고.

---

## Source IDs (대표)
- `SRC_SAP_CLEAN_CORE`
- `SRC_SAP_MAINTENANCE_STRATEGY`
- `SRC_SAP_READINESS_CHECK`
- `SRC_SAP_CUSTOM_CODE_MIGRATION`
- `SRC_GOOGLE_GEMINI_RATE_LIMITS`
- `SRC_ASUG_S4_ADOPTION`
- `SRC_SAPINSIDER_MIGRATION_2025`

전체 목록은 `docs/sources.yaml` 참고.

---

## Project Structure

```text
sap-clean-core-advisor/
├── app.py
├── models/
│   └── schemas.py
├── services/
│   ├── analysis_service.py
│   ├── cost_calculator.py
│   ├── ruleset_loader.py
│   ├── industry_mapper.py
│   ├── data_quality.py
│   ├── calibration_engine.py
│   ├── reference_mapper.py
│   ├── error_codes.py
│   ├── rag_pipeline.py
│   ├── llm_engine.py
│   └── pdf_generator.py
├── config/
│   ├── industry_aliases.yaml
│   ├── rule_reference_map.yaml
│   └── rulesets/
│       ├── base.yaml
│       ├── industries/
│       └── generated/
├── docs/
│   └── sources.yaml
├── tools/
│   ├── verify_sources.py
│   ├── backtest_ruleset.py
│   └── calibrate_ruleset.py
├── calibration/
│   ├── data/
│   └── reports/
└── tests/
```

---

## Limitations & Next Steps

현재 한계:
1. calibration은 실데이터가 있어야 의미 있는 성능을 보장
2. RAG-claim 매칭은 키워드 기반(고급 semantic 매칭 아님)
3. ruleset은 수동 버전 관리

다음 단계:
1. 규칙별 민감도 분석 자동 리포트
2. golden dataset 기반 릴리즈 게이트 강화
3. source verification 결과를 CI에 상시 통합

---

## References (as of 2026-02-16)

Official:
- https://ai.google.dev/gemini-api/docs/rate-limits
- https://support.sap.com/en/offerings-programs/strategy.html
- https://www.sap.com/products/erp/rise/methodology/clean-core.html
- https://help.sap.com/doc/bb0e7ba5158c424ab7ce010228bf1de1
- https://help.sap.com/doc/saphelp_nw75/7.5.5/en-US/11/84265accb6415b925bf6ee60a30362/content.htm

Benchmark/Community:
- https://www.asug.com/insights/the-state-of-sap-s-4hana-adoption-trends-successes-and-challenges
- https://sapinsider.org/webinars/sap-s4hana-migration-2025/

Academic/Methodology:
- https://robjhyndman.com/publications/another-look-at-measures-of-forecast-accuracy/
