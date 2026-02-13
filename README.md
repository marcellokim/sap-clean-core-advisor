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
| **AI 진단 리포트** | Claude + RAG로 SAP 공식 가이드 기반 전환 전략 및 리스크 분석 |
| **EA Cookbook PDF** | 분석 결과를 임원 보고용 PDF로 자동 생성 |

## 아키텍처

```
┌─────────────────────────────────────────────────┐
│                  Streamlit UI                    │
│  ┌──────────┐  ┌──────────┐  ┌───────────────┐  │
│  │Input Form│  │Dashboard │  │  PDF Download  │  │
│  │(Profile) │  │(Plotly)  │  │ (EA Cookbook)  │  │
│  └────┬─────┘  └────▲─────┘  └───────▲───────┘  │
│       │              │                │          │
├───────┼──────────────┼────────────────┼──────────┤
│       ▼              │                │          │
│  ┌─────────┐   ┌─────┴──────┐  ┌─────┴───────┐  │
│  │  Cost   │   │    LLM     │  │     PDF     │  │
│  │Calcul-  │   │  Engine    │  │  Generator  │  │
│  │ ator    │   │ (3-Chain)  │  │  (fpdf2)    │  │
│  │(Rules)  │   │            │  │             │  │
│  └─────────┘   └─────┬──────┘  └─────────────┘  │
│                       │                          │
│               ┌───────▼────────┐                 │
│               │  RAG Pipeline  │                 │
│               │  (ChromaDB +   │                 │
│               │   E5-small)    │                 │
│               └───────┬────────┘                 │
│                       │                          │
│               ┌───────▼────────┐                 │
│               │  SAP Knowledge │                 │
│               │  Base (6 docs) │                 │
│               └────────────────┘                 │
└─────────────────────────────────────────────────┘
```

### LLM 3-Chain 파이프라인

1. **Analyst Chain** – 현재 시스템의 핵심 문제점을 진단
2. **Architect Chain** – RAG 검색 결과 기반으로 Clean Core 전환 전략 수립
3. **Reporter Chain** – Executive Summary + 상세 리포트를 비즈니스 언어로 생성

## 기술 스택

- **Python 3.13** / **Streamlit** – 웹 UI
- **LangChain** + **Claude (Anthropic)** – LLM 오케스트레이션
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
# .env 파일을 편집하여 Anthropic API 키 입력
```

### 3. 앱 실행

```bash
streamlit run app.py
```

브라우저에서 `http://localhost:8501`로 접속합니다.

## 프로젝트 구조

```
sap-clean-core-advisor/
├── app.py                          # Streamlit 메인 앱
├── models/
│   ├── schemas.py                  # Pydantic 데이터 모델
│   └── __init__.py
├── services/
│   ├── cost_calculator.py          # 규칙 기반 Score/TCO/Risk 계산
│   ├── llm_engine.py               # LangChain 3-Chain 파이프라인
│   ├── rag_pipeline.py             # ChromaDB + E5 임베딩 RAG
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
└── README.md
```

## 라이선스

- Noto Sans KR 폰트: [SIL Open Font License](https://scripts.sil.org/OFL)
