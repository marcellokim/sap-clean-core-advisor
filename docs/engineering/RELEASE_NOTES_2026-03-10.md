# Release Notes — Refactor/Optimization/Prune Cycle (2026-03-10)

## 1) Scope

- 기간: 2026-03-10
- 기준 계획: `.omx/plans/repo-refactor-optimization-prune-v3-2026-03-10.md`
- 릴리즈 성격: 구조 리팩토링 + 품질/호환성 게이트 강화 + safe-lane 운영 자동화

## 2) Delivered

### A. 구조 리팩토링 (P1)
- `services/application/analysis_runner.py` 책임 분리
  - `report_content.py`, `report_preflight.py`, `llm_costs.py`, `llm_runtime.py`로 분해
- `app.py` UI 구성 분리
  - `ui/styles.py`, `ui/sidebar.py`로 분리

### B. 최적화 (P2)
- `ANALYSIS_TIMEOUT_MS=0` 경로에서 불필요한 ThreadPool 생성 제거
- 마이크로벤치(모킹 LLM) 기준 timeout 경로 오버헤드 측정 지표 확보

### C. Fast lane 정리 (P3)
- `services/industry_filter.py` 제거 유지
- deprecated make target 재유입 방지 게이트 추가
  - `scripts/verify_prune_hygiene.py`
  - `make verify-prune-hygiene`

### D. Safe lane 운영화 (P3~P4)
- 호환 래퍼 deprecate + telemetry 도입
  - 대상: `analysis_service`, `fpdf_renderer`, `chroma_provider`
- telemetry 리포트/승격 검증 자동화
  - `scripts/compat_telemetry_report.py`
  - `make report-compat-telemetry`
  - `make verify-safe-lane-promotion`

### E. 최종 안정화 게이트 (P4)
- `scripts/verify_release_readiness.py` 추가
- `make verify-release-readiness` 추가
  - `make qa-report` 3회 연속
  - `make test-compat`
  - `make check-import-cycles`
  - `make verify-safe-lane-promotion`
  - 결과 JSON 산출: `artifacts/qa/release_readiness.json`

## 3) KPI Snapshot

- `analysis_runner.py`: **692 → 439 lines**
- `app.py`: **355 → 196 lines**
- 테스트 수(최근 구간): **50 → 59**
- `test_compat_contracts`: **7 → 10**

## 4) Verification Evidence (2026-03-10)

- 최종 게이트: `make verify-release-readiness` **PASS**
- 아티팩트: `artifacts/qa/release_readiness.json`
- 최근 실행 시각(UTC): `2026-03-10T05:02:33.490792Z`
- 핵심 판정:
  - `ok: true`
  - `qa_runs_required: 3`
  - `commands_executed: 6`
  - `verify-safe-lane-promotion` 내 7일 telemetry: `total_events_in_window=0`

## 5) CI Changes

- CI 필수 게이트:
  - `make qa-report`
  - `make verify-safe-lane-promotion`
- 테스트/검증 단계의 synthetic telemetry 오염 방지:
  - `COMPAT_TELEMETRY_ENABLE=false`
  - `COMPAT_DEPRECATION_WARN=false`

## 6) Operational Notes

- Safe-lane 래퍼 제거 목표일: `2026-06-30` 이후 재평가
- 승격(삭제 후보 전환) 기준:
  - `make verify-safe-lane-promotion` 통과
  - telemetry 7일 0건 유지

## 7) Rollback Guide (Commit-level)

문제 발생 시 아래 커밋 단위로 선택 revert:

- `208178f` final release-readiness gate
- `ccdff9e` CI safe-lane gate wiring
- `e1db644` telemetry report/promotion gate
- `9ca3312` compat wrapper telemetry/deprecation
- `de49abe` prune hygiene gate
- `a1e134c` no-timeout path optimization
- `6fc9fe9` app/runner 슬림화

권장 절차:
1. `git revert --no-edit <sha>`
2. `make verify-release-readiness`
3. 결과 JSON(`artifacts/qa/release_readiness.json`) 재생성 후 비교
