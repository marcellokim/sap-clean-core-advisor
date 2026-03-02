# SAP EA Support Portfolio: Clean Core Advisor

## 0. Role Fit (Enterprise Architect Support)
이 프로젝트는 “기술 데모 앱”이 아니라, SAP STAR Program의 **Enterprise Architect Support** 업무를 빠르게 수행하기 위한 실무형 포트폴리오입니다.

### JD 매핑 (1:1)
1. EA cookbook/고객 문서 작성 지원  
- 분석 결과를 임원 보고용 PDF(EA Cookbook)로 생성

2. 고객 미팅/워크샵 운영 및 번역 지원  
- EN/KO 이중 문서 템플릿과 워크샵 운영 키트 제공

3. AI adoption 지원 (Joule activation support)  
- Joule activation checklist/troubleshooting 문서 제공

4. 팀 운영 ad hoc 지원  
- 주간 리포트/미팅 프리체크/문서 QA 템플릿 제공

## 1. Core Feature: Joule Readiness AI Gap Analysis (📌 NEW)
포트폴리오 고도화를 통해 **"Joule Activation 사전 점검 체크리스트"** 기능이 추가되었습니다.
EA 인턴으로서 기술 도입 과정의 병목을 파악하고 경영진을 설득하는 역량을 보여주기 위해 기획되었습니다.

*   **인터랙티브 UI**: SAP S/4HANA Private Cloud 환경 기반 필수 선결 과제(인프라, 보안, 테스트 등) 점검
*   **Gemini 2.5 Flash 기반 갭 분석**: 고객이 체크하지 않은 항목의 위험도를 즉시 분석하고, "경영진 요약(Executive Summary)" 및 "Actionable Recommendations"를 포함한 한국어 컨설팅 리포트 자동 생성
*   **프리미엄 대시보드 UI**: SaaS 수준의 모던 CSS가 적용된 결과 화면 제공

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

## 2. Demo Flow (2-3분 설명용)

### 실행
```bash
cd /Users/ydmac/Documents/sap-clean-core-advisor
uv run streamlit run app.py
```

### 설명 순서
1. Legacy 시스템 정보 입력 (고객 프로파일)
2. Clean Core 점수/리스크/TCO 결과 확인
3. 핵심 권고사항 + Evidence Ledger 확인
4. EA Cookbook PDF 다운로드
5. 사이드바에서 EA Support Pack ZIP 다운로드

### 기본 동작 원칙
- UI에서는 실행 모드를 노출하지 않음
- 앱은 포트폴리오 데모를 위해 **Hybrid 정책으로 고정 실행**
- AI 단계 실패 시에도 자동으로 안정 모드 결과를 제공

---

## 3. Business Value

### Target Persona
- 국내 중견 제조기업 CIO / IT 리더
- ECC 6.0 + Oracle + 높은 커스텀 코드 비중 환경
- Cloud/S/4HANA 전환 압박, 그러나 초기 진단 자료 부족

### 해결하는 문제
- 초기 EA 진단 문서 준비 시간이 오래 걸림
- 전환 우선순위가 정량화되지 않음
- 임원 보고용 산출물의 일관성/추적성 부족

### 제공 가치
- 1분 내 초기 진단
- KPI(Score/TCO/Risk) 기반 의사결정 지원
- 근거 체인 기반 권고사항 제시
- 고객 미팅 직전 사용 가능한 문서 패키지 즉시 확보

---

## 4. Product Scope

### 화면에 보여주는 것
- KPI 4종(Score, 현재 TCO, 전환 후 TCO, 3년 절감)
- 리스크 요인, 핵심 권고사항
- Executive Summary / 상세 리포트
- Evidence Ledger
- PDF 다운로드

### 화면에서 숨긴 것
- 내부 상태/디버그 메타데이터(실행 ID, stage metrics, 토큰/비용, ruleset 캡션 등)
- 엔진 운영 신호(RAG/LLM/PDF 상태 카드)
- 내부 오류코드 직접 노출

---

## 5. Run & Test

### Local run
```bash
make run
```

### Test
```bash
make test
```

---

## 6. 기술 상세 문서
엔지니어링 아키텍처, 실행 정책, 회로 차단기, ruleset/calibration, 운영 환경변수는 아래 기술 부록에 분리했습니다.

- `docs/engineering/ARCHITECTURE_APPENDIX.md`

---

## 7. References

### Official
- [SAP Strategy / Maintenance](https://support.sap.com/en/offerings-programs/strategy.html)
- [RISE with SAP Clean Core](https://www.sap.com/products/erp/rise/methodology/clean-core.html)
- [SAP Readiness Check](https://help.sap.com/doc/bb0e7ba5158c424ab7ce010228bf1de1)

### SAP Community
- [Joule Setup & Activation Guide](https://community.sap.com/t5/enterprise-resource-planning-blog-posts-by-sap/setup-and-activation-guide-joule-in-sap-s-4hana-private-cloud/ba-p/14325221)
- [Clean Core Extensibility](https://community.sap.com/t5/enterprise-resource-planning-blog-posts-by-sap/clean-core-extensibility-balancing-standardization-and-differentiation/ba-p/14260149)
