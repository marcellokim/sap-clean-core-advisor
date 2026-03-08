# SAP EA Support Portfolio: Clean Core Advisor

SAP STAR Program의 **Enterprise Architect Support** 역할을 목표로 만든 실무형 포트폴리오 프로젝트입니다.  
핵심 목표는 다음 2가지입니다.

1. 고객 미팅 전/중/후에 바로 활용 가능한 EA 산출물을 빠르게 생성  
2. Clean Core 전환 의사결정을 정량 지표(Score/TCO/Risk)와 근거 체인으로 지원

---

## 1) 왜 이 프로젝트인가 (Role Fit)

### JD 매핑 (1:1)

| 공고 역할 | 프로젝트 대응 |
|---|---|
| EA cookbook 및 고객 문서 작성 지원 | 분석 결과를 PDF로 생성, EA Cookbook 템플릿/케이스 제공 (`docs/ea-cookbook/*`) |
| 고객 미팅/워크샵 번역·운영 지원 | KO/EN 아젠다, 스크립트, 회의록·액션아이템 템플릿 제공 (`docs/workshop-kit/*`) |
| AI adoption 지원 (예: Joule activation) | Joule Readiness 체크리스트 + Gap Analysis 제공 (`ui/joule_checklist.py`, `services/domain/joule_readiness_engine.py`) |
| 팀 운영 ad hoc 지원 | 주간 리포트/프리체크/문서 QA 템플릿 제공 (`docs/ops-toolkit/*`) |

---

## 2) 핵심 기능

### A. Clean Core Assessment
- Legacy 입력값 기반 결정론적 계산:
  - Clean Core Score
  - TCO (현재/전환 후/3년 절감)
  - Risk Level & Risk Factors
- 권고사항 + Evidence Ledger(근거 등급 A/B/C/D) 제공
- Executive Summary / Detailed Report 생성
- EA Cookbook PDF 다운로드

### B. Joule Readiness Gap Analysis
- SAP S/4HANA Private Cloud + Joule 활성화 전 체크리스트
- 미완료 항목 기반 리스크/권고/임원 요약 생성

### C. EA Support Pack
- 사이드바에서 KO/EN/ALL 문서 ZIP 즉시 다운로드

---

## 3) 아키텍처 요약

```text
Input Form
 -> Ruleset Resolution (generated opt-in > industry > base)
 -> Deterministic Calculator (Score/TCO/Risk)
 -> RAG Context (optional, soft-fail)
 -> LLM Report (optional, fallback)
 -> Evidence Ledger
 -> PDF Render (soft-fail)
 -> Streamlit Dashboard
```

### 설계 원칙
- **Deterministic first**: 같은 입력이면 같은 KPI 수치
- **Soft-fail**: AI 단계 실패 시에도 결과 제공 중단 금지
- **Traceability**: 권고사항 근거를 claim 단위로 추적

---

## 4) 실행 방법

### 요구사항
- Python 3.13+
- [uv](https://docs.astral.sh/uv/)

### 설치
```bash
uv sync
```

### 실행
```bash
make run
# 또는
uv run streamlit run app.py
```

---

## 5) 품질 검증

```bash
make test
make verify-sources
```

- `make test`: 단위 테스트
- `make verify-sources`: 출처 카탈로그 스키마/노후도 검증

> 참고: 과거 backtest/calibrate 도구는 현재 브랜치에서 제거되었습니다.

---

## 6) 2~3분 데모 시나리오 (영상 없이 발표용)

1. 고객 프로파일 입력 (업종, ERP/DB, 사용자, 커스텀 규모)
2. KPI 확인 (Score/TCO/Risk)
3. 권고사항 + Evidence Ledger 확인
4. PDF 다운로드
5. 사이드바에서 EA Support Pack ZIP 다운로드

---

## 7) 산출물 위치

### EA Cookbook
- `docs/ea-cookbook/EA_Cookbook_Template_KO.md`
- `docs/ea-cookbook/EA_Cookbook_Template_EN.md`
- `docs/ea-cookbook/CaseStudy_Manufacturing_v1.pdf`
- `docs/ea-cookbook/CaseStudy_Retail_v1.pdf`

### Workshop Kit
- `docs/workshop-kit/Workshop_Agenda_KO.md`
- `docs/workshop-kit/Workshop_Agenda_EN.md`
- `docs/workshop-kit/Workshop_Script_KO.md`
- `docs/workshop-kit/Workshop_Script_EN.md`
- `docs/workshop-kit/Minutes_Template.md`
- `docs/workshop-kit/Decision_Log.csv`
- `docs/workshop-kit/Action_Items.csv`

### Joule Playbook
- `docs/joule-playbook/Joule_Activation_Checklist_KO.md`
- `docs/joule-playbook/Joule_Activation_Checklist_EN.md`
- `docs/joule-playbook/Joule_Troubleshooting_KO.md`
- `docs/joule-playbook/Joule_Troubleshooting_EN.md`

### Ops Toolkit
- `docs/ops-toolkit/Weekly_Status_Template.md`
- `docs/ops-toolkit/Customer_Meeting_Precheck.md`
- `docs/ops-toolkit/Document_QA_Checklist.md`

---

## 8) 기술 스택

- UI: Streamlit, Plotly
- Validation/Schema: Pydantic
- LLM: Gemini, GLM (provider abstraction)
- RAG: ChromaDB + HuggingFace Embeddings
- PDF: fpdf2
- Build/Test: uv, unittest, Make
- CI: GitHub Actions (`.github/workflows/ci.yml`)

---

## 9) 문서

- 엔지니어링 부록: `docs/engineering/ARCHITECTURE_APPENDIX.md`
- 학습 커리큘럼: `docs/Study_Curriculum_KO.md`

---

## 10) 참고 링크

### Official
- [SAP Strategy / Maintenance](https://support.sap.com/en/offerings-programs/strategy.html)
- [RISE with SAP Clean Core](https://www.sap.com/products/erp/rise/methodology/clean-core.html)
- [SAP Readiness Check](https://help.sap.com/doc/bb0e7ba5158c424ab7ce010228bf1de1)

### SAP Community
- [Joule Setup & Activation Guide](https://community.sap.com/t5/enterprise-resource-planning-blog-posts-by-sap/setup-and-activation-guide-joule-in-sap-s-4hana-private-cloud/ba-p/14325221)
- [Clean Core Extensibility](https://community.sap.com/t5/enterprise-resource-planning-blog-posts-by-sap/clean-core-extensibility-balancing-standardization-and-differentiation/ba-p/14260149)

