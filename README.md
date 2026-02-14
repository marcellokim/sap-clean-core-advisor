# RISE with SAP: Clean Core Assessment & TCO Simulator

AI 기반 SAP 레거시 시스템 진단 및 전환 전략 도우미

## 프로젝트 배경

국내 중견기업 CIO가 15년 된 SAP ECC 시스템을 RISE with SAP(S/4HANA Cloud)으로 전환하려 할 때, **"현재 시스템의 기술 부채가 얼마나 심각한지"**, **"전환하면 비용이 얼마나 절감되는지"** 를 숫자로 증명하기 어렵습니다.

이 도구는 고객의 레거시 시스템 정보를 입력받아 **Clean Core Score**, **TCO 비교 분석**, **기술 부채 히트맵**을 자동 산출하고, AI가 **임원 보고용 Executive Summary**를 생성합니다. 결과물은 **EA Cookbook PDF**로 다운로드할 수 있습니다.

## 핵심 기능

| 기능 | 설명 |
|------|------|
| **Clean Core Score** | 커스텀 코드 비중, ERP 버전, DB 유형, 모듈 복잡도를 종합하여 0-100점 산출 |
| **기술 부채 히트맵** | 모듈별 커스텀 심각도 × 업계 가중치로 규칙 기반 기술 부채 시각화 |
| **TCO Simulator** | 현재 vs 전환 후 총 소유 비용 비교 (3년 절감액 포함) |
| **AI 진단 리포트** | Gemini + RAG 기반 리포트 생성 (실패 시 규칙 기반 자동 폴백) |
| **EA Cookbook PDF** | 분석 결과를 임원 보고용 PDF로 자동 생성 |
| **Evidence Ledger** | 권고사항별 근거 체인(입력 사실/룰 ID/RAG 출처)과 근거 등급(A-D) 제공 |
| **Rule Versioning** | 계산 결과에 `ruleset_version`과 `applied_rule_ids`를 기록해 재현성 확보 |
| **Structured Observability** | 단계별 처리시간(ms), 생성 모드, 에러코드를 구조화 로그로 출력 |

## 아키텍처

```
┌─────────────────────────────────────────────────┐
│                  Streamlit UI                  │
│  ┌──────────┐  ┌──────────┐  ┌───────────────┐ │
│  │Input Form│  │Dashboard │  │  PDF Download │ │
│  └────┬─────┘  └────▲─────┘  └───────▲───────┘ │
│       │              │                │         │
├───────┼──────────────┼────────────────┼─────────┤
│       ▼              │                │         │
│  ┌───────────────────────────────────────────┐  │
│  │            Analysis Service               │  │
│  │ (계산 → RAG → LLM 시도 → 폴백 → PDF)      │  │
│  └───────┬───────────────┬───────────┬───────┘  │
│          │               │           │          │
│    ┌─────▼─────┐   ┌─────▼─────┐   ┌─▼────────┐ │
│    │Cost Engine│   │RAG Pipeline│   │PDF Gen   │ │
│    │(Rules)    │   │(Chroma+E5) │   │(fpdf2)   │ │
│    └───────────┘   └─────┬──────┘   └──────────┘ │
│                          │                        │
│                    ┌─────▼─────┐                  │
│                    │LLM Provider│                 │
│                    │(Gemini)    │                 │
│                    └────────────┘                 │
└─────────────────────────────────────────────────┘
```

### 리포트 생성 정책

1. 기본 모드: **single-pass LLM** (요청 1회)
2. 선택 모드: `LLM_PIPELINE_MODE=three_chain` (실험/고품질)
3. 실패 모드: 쿼터/네트워크/Provider 오류 시 **규칙 기반 리포트 자동 폴백**

### 안정성/검증 원칙

1. **LLM 실패는 제품 실패가 아님**: LLM 오류 시 규칙 기반 리포트로 즉시 폴백
2. **같은 입력 = 같은 수치/근거**: `RULESET_VERSION` 기준으로 계산 수치와 룰 trace 재현 가능
3. **근거 체인 공개**: 각 권고사항에 대해 Claim-Rule-Source를 함께 제시
4. **오류코드 표준화**: LLM/RAG/PDF 오류를 `ERR_*` 코드로 일관 처리
5. **관측성 내장**: `calc_ms/rag_ms/llm_ms/pdf_ms/total_ms`를 결과 메타와 로그에 기록

## 기술 스택

- **Python 3.13** / **Streamlit** – 웹 UI
- **LangChain** + **Gemini (Google)** – LLM 오케스트레이션
- **ChromaDB** + **multilingual-e5-small** – 다국어 RAG 파이프라인
- **Plotly** – 인터랙티브 차트 (게이지, 레이더, 바 차트)
- **fpdf2** + **Noto Sans KR** – 한글 PDF 생성
- **Pydantic** – 데이터 검증

## 설치 및 실행

### 1. 환경 설정

```bash
# 저장소 클론
git clone <repository-url>
cd sap-clean-core-advisor

# Python 가상환경 생성 (uv 사용)
uv sync

# 또는 pip 사용
pip install -e .
```

### 2. API 키 설정

```bash
cp .env.example .env
# .env 파일을 편집하여 Google Gemini API 키 입력
```

### 2-1. 환경변수 (기본값)

```bash
LLM_PROVIDER=gemini
LLM_PIPELINE_MODE=single
LLM_MAX_RETRIES=2
LLM_BASE_DELAY_SEC=5
LLM_DISABLE=false
RAG_MAX_CONTEXT_CHARS=6000
```

### 3. 앱 실행

```bash
streamlit run app.py
```

브라우저에서 `http://localhost:8501`로 접속합니다.

### 4. 테스트 실행

```bash
python -m unittest discover -s tests -v
```

## 프로젝트 구조

```
sap-clean-core-advisor/
├── app.py                          # Streamlit 메인 앱
├── models/
│   ├── schemas.py                  # Pydantic 데이터 모델
│   └── __init__.py
├── services/
│   ├── analysis_service.py         # 계산/RAG/LLM/폴백/PDF 오케스트레이션
│   ├── cost_calculator.py          # 규칙 기반 Score/TCO/Risk 계산
│   ├── error_codes.py              # 표준 에러코드 taxonomy
│   ├── llm_provider.py             # LLM provider 인터페이스 (payload/sections/error)
│   ├── llm_engine.py               # Gemini provider 구현 (single/three_chain)
│   ├── rag_pipeline.py             # ChromaDB + E5 임베딩 RAG 컨텍스트 공급자
│   ├── pdf_generator.py            # EA Cookbook PDF 생성
│   └── __init__.py
├── ui/
│   ├── input_form.py               # 고객 입력 폼
│   ├── dashboard.py                # Plotly 대시보드
│   └── __init__.py
├── data/
│   ├── clean_core_strategy.md      # SAP Clean Core 전략 가이드
│   ├── rise_with_sap.md            # RISE with SAP 프로그램
│   ├── btp_use_cases.md            # BTP 활용 사례
│   ├── tco_benchmarks.md           # TCO 벤치마크 데이터
│   ├── migration_best_practices.md # 마이그레이션 모범 사례
│   ├── sap_modules_overview.md     # SAP 모듈별 기술 특성
│   └── fonts/
│       └── NotoSansKR-Regular.ttf  # 한글 PDF용 폰트
├── pyproject.toml
├── .env.example
├── tests/
│   ├── test_cost_calculator.py
│   ├── test_analysis_service.py
│   ├── test_pdf_generator.py
│   ├── test_error_codes.py
│   ├── test_evidence_ledger.py
│   └── test_validation_warnings.py
└── README.md
```

## 라이선스

- Noto Sans KR 폰트: [SIL Open Font License](https://scripts.sil.org/OFL)
