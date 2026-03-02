# Architecture Appendix (Engineering)

이 문서는 메인 README에서 분리한 기술 상세 부록입니다.  
면접 데모에서는 README 본문(비즈니스 관점)을 우선 사용하고, 기술 질문이 들어오면 본 문서를 참고합니다.

## 1. Runtime Architecture

```text
Input Form
 -> Ruleset Resolution (generated opt-in > industry > base)
 -> Deterministic Calculator (Score/TCO/Risk)
 -> RAG Context (optional, soft-fail)
 -> LLM Report (Gemini/GLM, optional, fallback)
 -> Evidence Ledger
 -> PDF Render (soft-fail)
 -> Streamlit Dashboard
```

핵심 원칙:
- 같은 입력 = 같은 KPI 수치
- LLM 실패 ≠ 제품 실패 (fallback 유지)
- 근거 추적(Evidence Ledger) 가능

## 2. Analysis Policy

`AnalysisPolicy` 필드:
- `analysis_mode`: `deterministic | hybrid | llm_only`
- `rag_enabled`
- `llm_enabled`
- `timeout_ms`
- `use_circuit_breaker`

포트폴리오 UI 기본:
- `app.py`에서 `analysis_mode="hybrid"`로 고정 호출
- 모드 선택 UI는 비노출

## 3. Circuit Breaker & Error Taxonomy

### Circuit Breaker
- LLM/RAG 각각 독립 breaker
- 실패 누적 임계치 도달 시 Open 상태
- Open 기간 동안 즉시 스킵

### 주요 에러코드
- `ERR_LLM_DISABLED`
- `ERR_LLM_RATE_LIMIT`
- `ERR_LLM_AUTH`
- `ERR_LLM_PROVIDER`
- `ERR_PROVIDER_NOT_SUPPORTED`
- `ERR_RAG_UNAVAILABLE`
- `ERR_PDF_LAYOUT_OVERFLOW`
- `ERR_PDF_FONT`
- `ERR_PDF_UNKNOWN`

## 4. Ruleset / Calibration

### Ruleset
- `config/rulesets/base.yaml`
- `config/rulesets/industries/*.yaml`
- `config/rulesets/generated/*.yaml`

우선순위:
1. generated (`RULESET_ALLOW_GENERATED=true`일 때만)
2. industry
3. base

### Calibration/Backtest
- `tools/backtest_ruleset.py`
- `tools/calibrate_ruleset.py`
- industry canonical profile 기준 필터링 후 평가
- report 출력: `calibration/reports/*.md`, `calibration/reports/*.json`

## 5. Evidence Ledger

필드:
- `claim_id`
- `claim_text`
- `evidence_grade` (A/B/C/D)
- `input_facts`
- `rule_ids`
- `rag_sources`
- `reference_source_ids`

등급:
- A: 입력 사실 + 규칙 ID
- B: 규칙 ID
- C: RAG 출처
- D: 약한 근거

## 6. Key Environment Variables

```bash
# Runtime
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

# Provider keys
GOOGLE_API_KEY=
GEMINI_MODEL=gemini-2.0-flash-lite
GLM_API_KEY=
GLM_MODEL=glm-5
GLM_API_BASE_URL=https://open.bigmodel.cn/api/paas/v4

# Cost estimate
LLM_PRICE_INPUT_PER_1M=0.075
LLM_PRICE_OUTPUT_PER_1M=0.30
LLM_MONTHLY_REQUESTS=1000
LLM_TOKEN_ESTIMATE_CHAR_DIVISOR=4

# RAG
RAG_ENABLE=true
RAG_OFFLINE_ALLOW=true
RAG_WARMUP_ON_START=false
RAG_MAX_CONTEXT_CHARS=6000
RAG_CB_FAILURE_THRESHOLD=3
RAG_CB_OPEN_SEC=120

# Ruleset / calibration
RULESET_DIR=config/rulesets
RULESET_GENERATED_DIR=config/rulesets/generated
RULESET_ALLOW_GENERATED=false
CALIBRATION_MIN_SAMPLES=20
CALIBRATION_WEIGHT_TCO=0.7
CALIBRATION_WEIGHT_RISK=0.3

# Sources
SOURCE_VERIFY_MAX_AGE_DAYS=90
```

## 7. Engineering Validation Commands

```bash
make test
make verify-sources
make backtest INDUSTRY=manufacturing
make calibrate INDUSTRY=manufacturing
```

