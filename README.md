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

### Sidebar Export
- `EA Support Pack Language` 선택
- `Download EA Support Pack` 클릭

### Test Suite
```bash
./.venv/bin/python -m unittest discover -s tests -v
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
 -> Industry Mapper (alias normalization)
 -> Ruleset Loader (generated > industry > base)
 -> Deterministic Calculator (Score/TCO/Risk)
 -> RAG (soft-fail)
 -> LLM (optional, soft-fail)
 -> Fallback report
 -> Evidence Ledger (Rule ↔ Source link)
 -> PDF generation (soft-fail)
 -> Dashboard / Download
```

### Key Files
- `/Users/ydmac/Documents/sap-clean-core-advisor/services/analysis_service.py`
- `/Users/ydmac/Documents/sap-clean-core-advisor/services/cost_calculator.py`
- `/Users/ydmac/Documents/sap-clean-core-advisor/services/ruleset_loader.py`
- `/Users/ydmac/Documents/sap-clean-core-advisor/services/industry_mapper.py`
- `/Users/ydmac/Documents/sap-clean-core-advisor/services/reference_mapper.py`

---

## 5. Deterministic Calculation Policy

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

## 6. Evidence Ledger

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

## 7. Industry Ruleset & Calibration

### Ruleset Files
- `/Users/ydmac/Documents/sap-clean-core-advisor/config/rulesets/base.yaml`
- `/Users/ydmac/Documents/sap-clean-core-advisor/config/rulesets/industries/manufacturing.yaml`
- `/Users/ydmac/Documents/sap-clean-core-advisor/config/rulesets/industries/retail.yaml`
- `/Users/ydmac/Documents/sap-clean-core-advisor/config/rulesets/industries/finance.yaml`
- `/Users/ydmac/Documents/sap-clean-core-advisor/config/rulesets/generated/`

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

---

## 8. Source Governance

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

## 9. Failure Modes & Mitigation

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

5. PDF 실패
- `ERR_PDF_*`, 화면 결과 유지

---

## 10. Environment Variables

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

## 11. CSV Data Contract (Calibration)
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

## 12. Tests

신규 테스트 포함 전체 27개 통과 기준:
- industry mapper
- ruleset loader precedence
- data quality gate
- rule ↔ source mapping completeness
- source catalog schema/staleness
- analysis fallback/llm flow
- calculator regression

실행:
```bash
./.venv/bin/python -m unittest discover -s tests -v
```

---

## 13. References (as of 2026-02-16)

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
