# SAP Clean Core Advisor 마스터 커리큘럼

이 프로젝트는 단순한 데모 애플리케이션이 아니라, **SAP Enterprise Architect(EA) Support 업무를 실제 수행할 수 있도록 설계된 실전형 패키지**입니다. 결정론적 규칙 엔진을 코어로 삼고, LLM과 RAG를 부가적(보조적)으로 활용해 높은 신뢰성을 보장하는 아키텍처를 가지고 있습니다.

이 프로젝트를 완벽히 이해하고 마스터하기 위한 6주 완성 커리큘럼을 제안합니다.

---

## Phase 1: 비즈니스 도메인 및 아키텍처 기초 (1주차)
**목표**: SAP Clean Core로의 전환 로직과 프로젝트 전체의 뼈대를 이해하고 UI 구성을 파악합니다.

* **필독 문서**:
  * `README.md` (특히 3. Core Design Principles, 4. Architecture, 5. Execution Policy)
  * `pyproject.toml` (어떤 라이브러리를 사용했는지 종속성 파악)
* **코드 분석**:
  * `app.py`: Streamlit을 활용한 프레임워크와 화면 구성, UI 이벤트 흐름 파악
  * `config/settings.py` 및 `.env`: 환경 변수 목록과 Analysis Mode(`deterministic`, `hybrid`, `llm_only`)의 차이 파악
* **실습**:
  * 로컬에서 `uv run streamlit run app.py` 실행하여 데모 구동
  * Sidebar에서 결과물을 Export하여 실물 파일(PDF/Markdown) 형태 확인

---

## Phase 2: 핵심 비즈니스 로직 - 결정론적 평가 엔진 (2주차)
**목표**: LLM 없이도 동작하는 프로젝트의 핵심, TCO/Risk/Score 계산 규칙을 마스터합니다. "같은 입력 = 같은 근거 수치"라는 설계 철학을 코드로 확인합니다.

* **코드 분석**:
  * `config/rulesets/base.yaml`, `config/rulesets/industries/*.yaml`: 평가 규칙(Rule)들의 기준, 가중치 산정 방식 구조 파악
  * `services/ruleset_loader.py` & `services/industry_mapper.py`: 고객 데이터가 입력되었을 때 산업군별로 어떤 룰셋이(기본 룰 vs 산업 특화 룰) 우선 조회되는지 계층 메커니즘 분석
  * `services/cost_calculator.py`: 입력 데이터를 기반으로 TCO와 Risk를 계산하는 수학적 추정(Decision Proxy Estimate) 로직
* **주요 개념**:
  * Maintenance Timeline Rule(예: BS7 2027년, 2030년 마이그레이션 기한 적용) 로직 이해

---

## Phase 3: 도메인 지식 거버넌스 (룰셋/출처 검증) (3주차)
**목표**: 산업군 룰셋 계층과 출처 검증 체계를 이해하고, 분석 품질을 안정적으로 유지하는 운영 루틴을 익힙니다.

* **코드 분석**:
  * `services/ruleset_loader.py`, `config/rulesets/*`: generated > industry > base 우선순위와 fallback 흐름
  * `services/industry_mapper.py`, `config/industry_aliases.yaml`: 업종 정규화와 canonical profile 매핑
  * `tools/verify_sources.py`, `docs/sources.yaml`: 출처 카탈로그 스키마/노후도 검증 로직
* **실습**:
  * `make verify-sources` 실행 후 결과 JSON 해석
  * `config/rulesets/generated/`를 ON/OFF(`RULESET_ALLOW_GENERATED`)하며 적용 규칙 우선순위 확인

---

## Phase 4: AI 파이프라인과 장애 복구(Fallback) 설계 (4주차)
**목표**: RAG와 LLM을 연동하는 구조 및 API 장애, 권한 오류, Rate Limit 등에서 시스템을 터뜨리지 않는 Soft-fail/Fallback 설계를 익힙니다.

* **코드 분석**:
  * `services/rag_pipeline.py` & `services/infrastructure/rag/chroma_provider.py`
  * `services/llm_provider.py`(또는 BaseLLMProvider) 및 파생된 `gemini_provider.py`, `glm_provider.py`
* **주요 흐름(Orchestration)**:
  * `services/application/analysis_runner.py`: Deterministic 엔진 -> RAG -> LLM -> Fallback 리포트 병합으로 이어지는 파이프라인 제어 흐름 분석
  * Evidence Ledger 계층 (어떻게 근거 Grade(A/B/C/D)가 산정되는가?)

---

## Phase 5: EA 산출물 생성 및 거버넌스 관리 (5주차)
**목표**: 생성된 평가 리포트를 실제 고객용 파일로 변환하는 계층과 지식 데이터의 출처 관리를 학습합니다.

* **코드 분석**:
  * `services/pdf_generator.py` 및 `fpdf_renderer.py`: PDF 템플릿 렌더링
  * `docs/ea-cookbook/*`, `docs/workshop-kit/*` 등 고객 워크샵/진단용 매뉴얼 및 템플릿 구조
  * `tools/verify_sources.py`: `docs/sources.yaml`에 등재된 링크들의 유효성을 정기 검사(스텔 데이터/접근 차단 확인)하는 배치 스크립트 작성 기법

---

## Phase 6: 마스터 검증 과제 및 테스트 코드 확장 (6주차)
**목표**: 시스템 전체 계층에 대한 이해를 바탕으로 직접 기능을 추가하고 검증합니다.

* **코드 유지보수 및 테스트**:
  * `tests/` 디렉토리 단위 테스트 탐구 (특히 모의 객체(Mock)를 통한 API 오류 발생 테스트)
  * `make test` 로 모든 TC 통과 확인
* **🚀 최종 마스터를 위한 실무 과제**:
  1. **신규 산업 룰 적용**: `healthcare.yaml` 등 임의의 산업군 룰 베이스를 `config/rulesets/industries`에 만들고 테스트 통과시키기
  2. **LLM 확장**: `OpenAIProvider` 또는 `ClaudeProvider` 모듈을 `services/infrastructure/llm/` 하위에 새로 추가하여 `app.py` 연동
  3. **Fallback 시뮬레이션**: 강제로 잘못된 API Key를 입력하거나 `LLM_DISABLE=true`로 변경해 `hybrid` 모드에서 시스템이 어떻게 Fallback 리포트를 유지하는지 디버깅해보기

---
**💡 학습 팁**:
단순히 위에서 아래로 코드를 읽기보다, **"만약 LLM API 서버가 다운되면 프로그램이 어떻게 돌아가는가?"**, **"새로운 산업군의 TCO를 튜닝하고 싶을 땐 어디를 수정해야 하는가?"** 와 같은 실무적인 질문(Use-case)을 던지며 코드를 쫓아가는 것이 가장 빠릅니다.
