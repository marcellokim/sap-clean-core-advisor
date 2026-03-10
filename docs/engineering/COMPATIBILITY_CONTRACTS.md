# Compatibility Contracts

이 문서는 리팩터링 중에도 유지해야 하는 호환성 경계(compat contract)를 정리합니다.
`make test-compat`는 아래 계약이 깨졌을 때 즉시 실패하도록 설계되어 있습니다.

## 1. `services.analysis_service`

### Public surface
- `AnalysisPolicy` → `services.application.analysis_runner.AnalysisPolicy`를 그대로 재수출
- `AnalysisResult` → `services.application.analysis_runner.AnalysisResult`를 그대로 재수출
- `run_analysis` → `services.application.analysis_runner.run_analysis`를 그대로 재수출
- `analyze_customer_input(customer_input, lang="ko", policy=None)`

### Contract
- 입력
  - `customer_input`: `models.schemas.CustomerInput` 인스턴스
  - `lang`: locale 문자열
  - `policy`: `AnalysisPolicy | None`
- 출력
  - `run_analysis(...)`가 반환한 `AnalysisResult`를 그대로 반환
- 예외
  - `run_analysis(...)`가 던진 예외를 감추거나 변환하지 않음
- 부수효과
  - `policy`가 없으면 `AnalysisPolicy.from_env()`로 런타임 정책을 해석
  - `DISABLE_CACHE=1`이면 Streamlit cache를 우회하고 직접 `run_analysis(...)` 호출

## 2. `services.infrastructure.pdf.fpdf_renderer`

### Public surface
- `FPDFRenderer.render(output, customer)`

### Contract
- 입력
  - `output`: `models.schemas.AdvisorOutput`
  - `customer`: `models.schemas.CustomerInput`
- 출력
  - `services.pdf_generator.generate_pdf(...)`가 생성한 `bytes`를 그대로 반환
- 예외
  - 폰트/레이아웃/기타 PDF 예외를 래퍼 내부에서 삼키지 않음
- 부수효과
  - 별도 상태 저장 없음 (PDF 생성기 위임만 수행)

## 3. `services.infrastructure.rag.chroma_provider`

### Public surface
- `ChromaRAGProvider()`
- `ChromaRAGProvider.get_context_bundle(erp_version, modules, pain_points)`

### Contract
- 입력
  - `erp_version`: ERP 버전 문자열
  - `modules`: 모듈명 문자열 리스트
  - `pain_points`: 자유 텍스트
- 출력
  - `services.rag_pipeline.RAGContextBundle` 반환
- 예외
  - 벡터 스토어 초기화/조회 예외를 래퍼 내부에서 삼키지 않음
- 부수효과
  - 생성자에서 `get_cached_vector_store()`를 호출해 벡터 스토어 warm-up 수행
  - `get_context_bundle(...)`는 `get_context_bundle_for_input(...)`에 동일 인자를 전달
