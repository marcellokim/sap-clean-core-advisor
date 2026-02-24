# SAP EA Support Portfolio: Deterministic Clean Core Advisor

## 0. Role Fit (Enterprise Architect Support)
이 프로젝트는 단순 앱 데모가 아니라, **SAP Enterprise Architect Support 업무를 바로 수행 가능한 산출물 패키지**를 목표로 설계했습니다.

### English Snapshot
This repository is positioned as an **EA Support Pack**, not just a SaaS demo.
It provides deterministic migration assessment, traceable evidence, and customer-facing artifacts (cookbook/workshop/Joule/ops kits) aligned with SAP Enterprise Architect Support responsibilities.

### JD 업무 1~4 매핑
1. EA cookbook 및 고객 문서 작성
- `docs/ea-cookbook/*` 템플릿 + 케이스 PDF 생성 흐름 제공

2. 고객 미팅/워크샵 번역·운영 지원
- `docs/workshop-kit/*` (Agenda/Script/Minutes/Decision Log/Action Items)
- EN/KO 용어집 `docs/workshop-kit/Glossary_EN_KO.md`

3. AI adoption 지원 (Joule activation support)
- `docs/joule-playbook/*` 체크리스트/트러블슈팅

4. 팀 운영 ad hoc 지원
- `docs/ops-toolkit/*` (Weekly status, meeting precheck, document QA)

---

## 1. Deliverables (실물 파일)

### EA Cookbook
- `/Users/ydmac/Documents/sap-clean-core-advisor/docs/ea-cookbook/EA_Cookbook_Template_KO.md`
- `/Users/ydmac/Documents/sap-clean-core-advisor/docs/ea-cookbook/EA_Cookbook_Template_EN.md`
- `/Users/ydmac/Documents/sap-clean-core-advisor/docs/ea-cookbook/CaseStudy_Manufacturing_v1.pdf`
- `/Users/ydmac/Documents/sap-clean-core-advisor/docs/ea-cookbook/CaseStudy_Retail_v1.pdf`

### Workshop Kit
- `/Users/ydmac/Documents/sap-clean-core-advisor/docs/workshop-kit/Workshop_Agenda_KO.md`
- `/Users/ydmac/Documents/sap-clean-core-advisor/docs/workshop-kit/Workshop_Agenda_EN.md`
- `/Users/ydmac/Documents/sap-clean-core-advisor/docs/workshop-kit/Workshop_Script_KO.md`
- `/Users/ydmac/Documents/sap-clean-core-advisor/docs/workshop-kit/Workshop_Script_EN.md`
- `/Users/ydmac/Documents/sap-clean-core-advisor/docs/workshop-kit/Minutes_Template.md`
- `/Users/ydmac/Documents/sap-clean-core-advisor/docs/workshop-kit/Decision_Log.csv`
- `/Users/ydmac/Documents/sap-clean-core-advisor/docs/workshop-kit/Action_Items.csv`

### Joule Playbook
- `/Users/ydmac/Documents/sap-clean-core-advisor/docs/joule-playbook/Joule_Activation_Checklist_KO.md`
- `/Users/ydmac/Documents/sap-clean-core-advisor/docs/joule-playbook/Joule_Activation_Checklist_EN.md`
- `/Users/ydmac/Documents/sap-clean-core-advisor/docs/joule-playbook/Joule_Troubleshooting_KO.md`
- `/Users/ydmac/Documents/sap-clean-core-advisor/docs/joule-playbook/Joule_Troubleshooting_EN.md`

### Ops Toolkit
- `/Users/ydmac/Documents/sap-clean-core-advisor/docs/ops-toolkit/Weekly_Status_Template.md`
- `/Users/ydmac/Documents/sap-clean-core-advisor/docs/ops-toolkit/Customer_Meeting_Precheck.md`
- `/Users/ydmac/Documents/sap-clean-core-advisor/docs/ops-toolkit/Document_QA_Checklist.md`

### Demo dataset (synthetic)
- `/Users/ydmac/Documents/sap-clean-core-advisor/calibration/data/demo_synthetic.csv`

---

## 2. Demo (3분 설명용)

- Demo Video (3~5 min): `docs/demo/`에 녹화본 추가 권장 (면접 Phone/Functional Interview에서 사용)

### Run App
```bash
cd /Users/ydmac/Documents/sap-clean-core-advisor
uv run streamlit run app.py
```

### Run App with GLM-5
```bash
cd /Users/ydmac/Documents/sap-clean-core-advisor
LLM_PROVIDER=glm GLM_API_KEY=your_key ANALYSIS_MODE=hybrid uv run streamlit run app.py
```

### Sidebar Export
- `EA Support Pack Language` 선택
- `Download EA Support Pack` 클릭

### Test Suite
```bash
./.venv/bin/python -m unittest discover -s tests -v
```

### Make Commands
```bash
make run
make test
make verify-sources
make backtest INDUSTRY=manufacturing
make calibrate INDUSTRY=manufacturing
```

---

## 3. Core Design Principles

1. **같은 입력 = 같은 수치/근거**
- 결정론적 규칙 코어
- `ruleset_version`, `ruleset_profile_id`, `ruleset_profile_source` 기록

2. **LLM 실패 ≠ 제품 실패**
- LLM rate limit/auth/provider 실패 시 fallback 리포트 자동 생성

3. **근거 추적 가능성**
- Evidence Ledger에 `input_facts`, `rule_ids`, `rag_sources`, `reference_source_ids`

4. **출처 거버넌스**
- `docs/sources.yaml` + `tools/verify_sources.py`

---

## 4. Architecture

```text
Input Form
 -> Analysis Policy Resolver (deterministic | hybrid | llm_only)
 -> Industry Mapper (alias normalization)
 -> Ruleset Loader (generated opt-in > industry > base)
 -> Deterministic Calculator (Score/TCO/Risk)
 -> RAG (policy + circuit breaker + soft-fail)
 -> LLM (policy + circuit breaker + soft-fail)
 -> Fallback report (always available)
 -> Evidence Ledger (Rule ↔ Source link)
 -> PDF generation (soft-fail)
 -> Dashboard / Download / Artifact(JSON optional)
```

### Key Files
- `/Users/ydmac/Documents/sap-clean-core-advisor/services/analysis_service.py`
- `/Users/ydmac/Documents/sap-clean-core-advisor/services/application/analysis_runner.py`
- `/Users/ydmac/Documents/sap-clean-core-advisor/services/domain/recommendation_engine.py`
- `/Users/ydmac/Documents/sap-clean-core-advisor/services/domain/evidence_engine.py`
- `/Users/ydmac/Documents/sap-clean-core-advisor/services/domain/validation_engine.py`
- `/Users/ydmac/Documents/sap-clean-core-advisor/services/infrastructure/policy/circuit_breaker.py`
- `/Users/ydmac/Documents/sap-clean-core-advisor/services/infrastructure/llm/gemini_provider.py`
- `/Users/ydmac/Documents/sap-clean-core-advisor/services/infrastructure/llm/glm_provider.py`
- `/Users/ydmac/Documents/sap-clean-core-advisor/services/infrastructure/rag/chroma_provider.py`
- `/Users/ydmac/Documents/sap-clean-core-advisor/services/infrastructure/pdf/fpdf_renderer.py`
- `/Users/ydmac/Documents/sap-clean-core-advisor/services/cost_calculator.py`
- `/Users/ydmac/Documents/sap-clean-core-advisor/services/llm_cost.py`
- `/Users/ydmac/Documents/sap-clean-core-advisor/services/ruleset_loader.py`
- `/Users/ydmac/Documents/sap-clean-core-advisor/services/industry_mapper.py`
- `/Users/ydmac/Documents/sap-clean-core-advisor/services/reference_mapper.py`

### Public Python API
- `analyze_customer_input(customer_input)` (기존 호환)
- `run_analysis(customer_input, policy: AnalysisPolicy)`
- `AnalysisPolicy(analysis_mode, rag_enabled, llm_enabled, timeout_ms, use_circuit_breaker)`

---

## 5. Execution Policy & Circuit Breaker

### Analysis Mode
- `deterministic` (default): calc/evidence/pdf만 수행, RAG/LLM 스킵
- `hybrid`: calc + RAG + LLM 시도, 실패 시 자동 fallback
- `llm_only`: 데모/실험용, LLM 실패 시 fallback 허용

### Stage Status
- `rag_status`: `ok | failed | skipped`
- `llm_status`: `ok | fallback | skipped`
- `pdf_status`: `ok | failed`

### Circuit Breaker
- LLM/RAG 각각 독립 breaker 사용
- 연속 실패 임계치 도달 시 Open
- Open 기간 동안 즉시 스킵하여 재시도 지연 제거

---

## 6. Deterministic Calculation Policy

### Score/TCO/Risk
- Ruleset 설정 기반 계산
- 산업별 프로파일 자동 적용
- 미매핑 산업은 `base` fallback + warning

### Maintenance Timeline Rule (정확 문구 적용)
- 리스크 규칙 ID: `RISK_BS7_MAINSTREAM_END_2027`
- 정보 규칙 ID: `INFO_BS7_EXTENDED_MAINT_AVAILABLE_2030`
- 메시지 기준:
  - Business Suite 7 mainstream maintenance 종료: **2027-12-31**
  - Extended maintenance 옵션: **2030-12-31**

### TCO 해석 정책
- TCO는 계약 정산값이 아니라 **Decision Proxy Estimate**
- 즉, 절대정답이 아닌 상대비교/우선순위 결정을 위한 추정치

---

## 7. Evidence Ledger

각 권고사항에 대해 아래 필드를 제공합니다.
- `claim_id`
- `claim_text`
- `evidence_grade` (A/B/C/D)
- `input_facts`
- `rule_ids`
- `rag_sources`
- `reference_source_ids`

### Grade 정의
- A: 입력 사실 + 규칙 ID
- B: 규칙 ID
- C: RAG 출처만 있음
- D: 근거 약함

---

## 8. Industry Ruleset & Calibration

### Ruleset Files
- `/Users/ydmac/Documents/sap-clean-core-advisor/config/rulesets/base.yaml`
- `/Users/ydmac/Documents/sap-clean-core-advisor/config/rulesets/industries/manufacturing.yaml`
- `/Users/ydmac/Documents/sap-clean-core-advisor/config/rulesets/industries/retail.yaml`
- `/Users/ydmac/Documents/sap-clean-core-advisor/config/rulesets/industries/finance.yaml`
- `/Users/ydmac/Documents/sap-clean-core-advisor/config/rulesets/generated/`

### Generated Ruleset Activation Policy
- 기본값: `RULESET_ALLOW_GENERATED=false`
- 명시적으로 활성화할 때만 generated ruleset 우선 적용

### Data Quality Gate
- `/Users/ydmac/Documents/sap-clean-core-advisor/services/data_quality.py`
- 필수 컬럼/범위/최소 샘플 수 검증
- 실패 시 calibration 수행 금지

### Backtest / Calibration CLI
```bash
./.venv/bin/python tools/backtest_ruleset.py --industry manufacturing
./.venv/bin/python tools/calibrate_ruleset.py --industry manufacturing
```

출력:
- `/Users/ydmac/Documents/sap-clean-core-advisor/calibration/reports/`
- `/Users/ydmac/Documents/sap-clean-core-advisor/config/rulesets/generated/{industry}.yaml`
- `backtest_YYYYMMDD.md + backtest_YYYYMMDD.json`
- `calibration_YYYYMMDD.md + calibration_YYYYMMDD.json`

주의:
- 입력 CSV는 `industry_mapper` 기준 canonical profile로 필터링 후 평가됩니다.
- mismatch row 개수(`excluded_rows`)가 리포트에 기록됩니다.

---

## 9. Source Governance

### Source Catalog
- `/Users/ydmac/Documents/sap-clean-core-advisor/docs/sources.yaml`

### Verification
```bash
# offline-safe mode
./.venv/bin/python tools/verify_sources.py --skip-http --json

# full mode (network)
./.venv/bin/python tools/verify_sources.py
```

정책:
- `official`은 유효성 엄격 검증
- `benchmark`는 접근 제한(401/403) 상태 기록 허용
- `SOURCE_VERIFY_MAX_AGE_DAYS` 기준 stale 관리

---

## 10. Failure Modes & Mitigation

1. LLM quota/rate limit
- `ERR_LLM_RATE_LIMIT`로 분류
- fallback report 제공

2. 산업 매핑 실패
- `INDUSTRY_MAPPING_FALLBACK_TO_BASE` 경고
- base ruleset 적용

3. calibration 데이터 품질 미달
- 수행 차단, generated 룰셋 미갱신

4. RAG 실패
- `ERR_RAG_UNAVAILABLE`, 분석 지속
- `RAG_OFFLINE_ALLOW=true`일 때 soft-fail

5. PDF 실패
- `ERR_PDF_*`, 화면 결과 유지

---

## 11. LLM Usage & Cost Estimator

- 출력 메타에 `llm_usage_source`, `llm_usage_tokens`, `llm_cost_estimate_usd`, `llm_monthly_projection_usd`를 기록합니다.
- Provider usage 메타가 있으면 실제 토큰(`provider`)을 사용합니다.
- usage 메타가 없거나 폴백이면 입력/출력 길이 기반 추정(`estimated`)으로 계산합니다.
- 비용은 모델별 토큰 단가(기본: `LLM_MODEL` 또는 provider별 기본 모델)를 사용해 1회/월간 시나리오 비용을 계산합니다.

---

## 12. Environment Variables

```bash
# Analysis runtime policy
ANALYSIS_MODE=deterministic
ANALYSIS_TIMEOUT_MS=0
ANALYSIS_USE_CIRCUIT_BREAKER=true
ANALYSIS_ARTIFACTS_ENABLE=false

# LLM
LLM_PROVIDER=gemini
LLM_MODEL=
LLM_PIPELINE_MODE=single
LLM_MAX_RETRIES=2
LLM_BASE_DELAY_SEC=5
LLM_HTTP_TIMEOUT_SEC=45
LLM_DISABLE=false
LLM_CB_FAILURE_THRESHOLD=3
LLM_CB_OPEN_SEC=120
LLM_PRICE_INPUT_PER_1M=0.075
LLM_PRICE_OUTPUT_PER_1M=0.30
LLM_MONTHLY_REQUESTS=1000
LLM_TOKEN_ESTIMATE_CHAR_DIVISOR=4

# Gemini
GOOGLE_API_KEY=
GEMINI_MODEL=gemini-2.0-flash-lite

# GLM
GLM_API_KEY=
GLM_MODEL=glm-5
GLM_API_BASE_URL=https://open.bigmodel.cn/api/paas/v4

# RAG
RAG_ENABLE=true
RAG_OFFLINE_ALLOW=true
RAG_WARMUP_ON_START=false
RAG_MAX_CONTEXT_CHARS=6000
RAG_CB_FAILURE_THRESHOLD=3
RAG_CB_OPEN_SEC=120

# Ruleset/Calibration
RULESET_DIR=config/rulesets
RULESET_GENERATED_DIR=config/rulesets/generated
RULESET_ALLOW_GENERATED=false
CALIBRATION_MIN_SAMPLES=20
CALIBRATION_WEIGHT_TCO=0.7
CALIBRATION_WEIGHT_RISK=0.3

# Source Governance
SOURCE_VERIFY_MAX_AGE_DAYS=90
```

---

## 13. CSV Data Contract (Calibration)
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

참고 샘플:
- `/Users/ydmac/Documents/sap-clean-core-advisor/calibration/data/demo_synthetic.csv`

---

## 14. Tests

신규 테스트 포함 전체 38개 통과 기준:
- industry mapper
- ruleset loader precedence
- ruleset activation guard
- data quality gate
- analysis policy mode matrix
- circuit breaker
- industry-filtered calibration
- rule ↔ source mapping completeness
- source catalog schema/staleness
- analysis fallback/llm flow
- calculator regression

실행:
```bash
./.venv/bin/python -m unittest discover -s tests -v
```

---

## 15. References (as of 2026-02-19)

### Official
- [Gemini API Rate Limits](https://ai.google.dev/gemini-api/docs/rate-limits)
- [SAP Strategy / Maintenance](https://support.sap.com/en/offerings-programs/strategy.html)
- [RISE with SAP Clean Core](https://www.sap.com/products/erp/rise/methodology/clean-core.html)
- [SAP Readiness Check](https://help.sap.com/doc/bb0e7ba5158c424ab7ce010228bf1de1)
- [SAP Custom Code Migration Worklist](https://help.sap.com/doc/saphelp_nw75/7.5.5/en-US/11/84265accb6415b925bf6ee60a30362/content.htm)

### SAP Community / Benchmark
- [Joule Setup & Activation Guide](https://community.sap.com/t5/enterprise-resource-planning-blog-posts-by-sap/setup-and-activation-guide-joule-in-sap-s-4hana-private-cloud/ba-p/14325221)
- [Clean Core Extensibility](https://community.sap.com/t5/enterprise-resource-planning-blog-posts-by-sap/clean-core-extensibility-balancing-standardization-and-differentiation/ba-p/14260149)
- [ASUG S/4 Adoption Trends](https://www.asug.com/insights/the-state-of-sap-s-4hana-adoption-trends-successes-and-challenges)
- [SAPinsider Migration Benchmark](https://sapinsider.org/webinars/sap-s4hana-migration-2025/)

### Methodology
- [Another Look at Forecast Accuracy Measures](https://robjhyndman.com/publications/another-look-at-measures-of-forecast-accuracy/)
