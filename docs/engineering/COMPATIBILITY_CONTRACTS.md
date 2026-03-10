# Compatibility Contracts

이 문서는 리팩터링 중에도 유지해야 하는 호환성 경계(compat contract)를 정리합니다.
`make test-compat`는 아래 계약이 깨졌을 때 즉시 실패하도록 설계되어 있습니다.

## Safe-lane 정책 (2026-03-10 기준)

- 아래 호환 래퍼 3종은 **이번 사이클에서 물리 삭제하지 않고** safe-lane으로 유지합니다.
- 호출 시 `compat_wrapper_used` telemetry 이벤트를 남기고 `DeprecationWarning` 경고를 발행합니다.
- 목표 제거 시점: **2026-06-30 이후 다음 안정화 사이클**(telemetry 사용량이 0일 때).
- telemetry 로그 기본 경로: `artifacts/telemetry/compat_usage.jsonl`
- 테스트 실행 중에는 로그 오염 방지를 위해 telemetry 파일 기록을 기본 비활성화합니다(`COMPAT_TELEMETRY_INCLUDE_TESTS=false`).

### Safe-lane 승격(삭제 후보 전환) 점검 명령

```bash
make report-compat-telemetry
make verify-safe-lane-promotion
```

- `make report-compat-telemetry`: 최근 7일 래퍼 호출량 JSON 요약 출력
- `make verify-safe-lane-promotion`: 7일 호출량 0건 + prune hygiene + `make test-compat` 통과 여부를 일괄 검증

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
  - compat telemetry 이벤트 기록 (`contract=services.analysis_service.analyze_customer_input`)

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
  - compat telemetry 이벤트 기록 (`contract=services.infrastructure.pdf.fpdf_renderer.FPDFRenderer.render`)

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
  - compat telemetry 이벤트 기록
    - `contract=services.infrastructure.rag.chroma_provider.ChromaRAGProvider.__init__`
    - `contract=services.infrastructure.rag.chroma_provider.ChromaRAGProvider.get_context_bundle`
