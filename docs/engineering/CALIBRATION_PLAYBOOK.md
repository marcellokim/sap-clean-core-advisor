# Calibration Playbook

## 목적

이 문서는 SAP Clean Core Advisor의 deterministic score / risk / recommendation calibration을
**benchmark-driven**, **explainable**, **regression-safe** 방식으로 반복 운영하기 위한 실무 가이드다.

핵심 원칙:
- deterministic-first 유지
- 업종별 ruleset 설명 가능성 유지
- benchmark 없는 감 조정 금지
- 모든 변경은 테스트/문서/artifact와 함께 검증

---

## 현재 기준선 (2026-03-11)

- Benchmark fixture: `tests/fixtures/demo_benchmark.yaml`
- Evaluation harness: `tools/evaluate_demo_benchmark.py`
- Regression guards:
  - `tests/test_calibration_regressions.py`
  - `tests/test_evaluate_demo_benchmark.py`
- Current promotion gate:
  - benchmark score / risk / recommendation coverage **100% 유지**
- Scope note:
  - `make verify-prune-hygiene`는 legacy `backtest`/`calibrate` 명칭 재유입만 막으며, benchmark fixture/harness 자체는 계속 유지된다
- Latest P4 working stance:
  - P3의 “추가 aggressive rescaling 보류” 결론은 유지
  - 먼저 benchmark를 sharper하게 만들어 closest pair / headroom drift를 더 일찍 잡는다
  - sharpened benchmark가 실제 miss를 만들 때만 최소 범위 calibration 변경을 검토한다

### P4 benchmark snapshot (2026-03-11)
- Latest benchmark coverage: **16/16** score / risk / recommendation pass
- 가장 가까운 score pair:
  - `retail_low_risk_promo` `81.7` ↔ `mfg_s4_stable` `81.9` (gap `0.2`)
  - `mfg_high_custom_factory` `21.6` ↔ `extreme_high_custom_ratio` `22.1` (gap `0.5`)
  - `extreme_multi_axis_pain` `44.3` ↔ `extreme_short_timeline` `45.1` (gap `0.8`)
- 현재 sharpened sentinel headroom:
  - `extreme_high_custom_ratio` lower/upper `0.8 / 0.8`
  - `extreme_multi_axis_pain` lower/upper `0.8 / 0.8`
  - `extreme_short_timeline` lower/upper `0.8 / 0.8`
- 해석:
  - baseline range를 넓게 유지하는 케이스와, 분별력 보호를 위해 의도적으로 좁게 pinning한 sentinel 케이스를 구분해서 본다
  - 좁은 headroom은 “전역 목표값”이 아니라 sharpened benchmark의 의도적 감시 포인트여야 한다

---

## 관련 파일

### 주요 구현 touchpoints
- `services/cost_calculator.py`
- `config/rulesets/base.yaml`
- `config/rulesets/industries/manufacturing.yaml`
- `config/rulesets/industries/retail.yaml`
- `config/rulesets/industries/finance.yaml`
- `services/domain/recommendation_engine.py`

### 평가/회귀 도구
- `tests/fixtures/demo_benchmark.yaml`
  - pair/headroom intent는 fixture `metadata`에 함께 남긴다
- `tools/evaluate_demo_benchmark.py`
- `tests/test_calibration_regressions.py`
- `tests/test_evaluate_demo_benchmark.py`

### 산출물
- `artifacts/calibration/demo_benchmark_eval.json`
- `artifacts/calibration/demo_benchmark_eval.md`

---

## 언제 튜닝할 것인가

튜닝을 고려할 조건:
- 서로 다른 데모 입력인데 score/TCO가 과하게 비슷하게 보일 때
- 특정 업종만 유독 좁은 분포를 보일 때
- recommendation/risk는 맞지만 score 분별력이 약할 때
- benchmark `tuning_signals`가 좁은 gap / 좁은 headroom case를 반복적으로 보여줄 때

튜닝을 보류할 조건:
- benchmark coverage가 이미 100%이고 추가 개선폭이 작을 때
- score 분산 개선이 가능해도 slack이 지나치게 작아질 때
- 특정 1~2 케이스만 좋아지고 전체 설명력이 악화될 때

---

## 운영 절차

### 1) Baseline freeze
다음 3가지를 현재 상태로 고정한다.
- benchmark fixture
- benchmark eval artifact
- 핵심 샘플 기대값 / README 설명

권장 커맨드:
```bash
make test
make verify-sources
./.venv/bin/python tools/evaluate_demo_benchmark.py --json
```

### 2) Benchmark 읽기
다음 항목을 본다.
- coverage (`score_range_hit_rate`, `risk_exact_match_rate`, `recommendation_coverage_rate`)
- `tuning_signals.score_distribution`
- `tuning_signals.current_annual_tco_distribution`
- `tuning_signals.projected_annual_tco_distribution`
- `tuning_signals.closest_score_pairs`
- `tuning_signals.narrowest_score_headroom_to_min/max`

### 3) Benchmark sharpening first
code/ruleset tuning 전에 먼저 benchmark expectation을 sharpen한다.

- `closest_score_pairs`에서 gap이 특히 작은 케이스에 ordering / minimum-gap expectation을 추가한다.
- pair ordering rationale은 fixture `metadata.tuning_expectations.closest_score_pairs`에 기록한다.
- harness gate를 추가로 걸 경우에는 fixture `metadata.signal_assertions` 계열을 함께 관리한다.
- `narrowest_score_headroom_*` hotspot은 score window를 무작정 줄이지 말고,
  그 케이스가 broad-slack baseline인지, 아니면 의도적으로 좁힌 sentinel인지 먼저 분류한다.
- sentinel로 고정할 때는 “왜 이 케이스를 좁게 pinning하는지”를 fixture rationale / 문서에 남긴다.
- sharpened benchmark가 여전히 모두 통과하면 **no-change**를 기본값으로 둔다.
- sharpened benchmark에서만 miss가 발생하면 그때 `services/cost_calculator.py` / ruleset tuning 후보를 연다.

### 4) Candidate 설계
한 번에 **1~2개 parameter family**만 건드린다.

추천 순서:
1. `custom_program_density` 계열
2. `module weighted severity` 계열
3. `database size penalty` 계열
4. industry `score_weights`
5. risk threshold / recommendation gate는 2차 조정으로 미룬다

### 5) Candidate 검증
후보안마다 아래를 비교한다.
- benchmark coverage 유지 여부
- score span / stddev 개선 여부
- closest score pair gap 개선 여부
- narrowest headroom 악화 여부
- 특정 업종만 좋아지는지 여부

### 6) Promotion / rollback 결정
채택 기준:
- benchmark coverage 100% 유지
- 설명 가능한 parameter 변경
- 전체 분별력 개선
- README / tests / artifacts 동반 갱신

롤백 기준:
- benchmark miss 발생
- slack이 과도하게 줄어듦
- recommendation/risk 품질 저하
- 업종별 편향 증가

---

## 현재 harness에서 보는 신호

`tools/evaluate_demo_benchmark.py`는 아래 `tuning_signals`를 제공한다.

- `score_distribution`
- `current_annual_tco_distribution`
- `projected_annual_tco_distribution`
- `tco_savings_3yr_distribution`
- `closest_score_pairs`
- `narrowest_score_headroom_to_min`
- `narrowest_score_headroom_to_max`

활용 팁:
- `closest_score_pairs`는 “숫자가 너무 비슷해 보이는” 케이스를 찾는 데 우선 사용
- `narrowest_score_headroom_*`는 과튜닝 위험을 보는 데 사용
- P4에서는 “pair gap 개선”과 “headroom intent가 문서화된 sentinel인지”를 함께 확인해야 한다
- stddev/span이 좋아져도 headroom이 너무 얇아지면 채택하지 않음

---

## 권장 검증 루프

### 빠른 루프
```bash
./.venv/bin/python -m unittest tests.test_calibration_regressions -v
./.venv/bin/python -m unittest tests.test_evaluate_demo_benchmark -v
./.venv/bin/python tools/evaluate_demo_benchmark.py --json
```

### 승격 루프
```bash
make test
make verify-sources
./.venv/bin/python tools/evaluate_demo_benchmark.py --json
```

---

## 문서화 규칙

Calibration 관련 동작이 바뀌면 아래를 함께 갱신한다.
- `README.md`
- 관련 테스트 기대값
- benchmark artifact
- 필요 시 이 playbook의 gate / 운영 절차

문서에는 최소한 다음이 남아야 한다.
- 무엇을 바꿨는지
- 왜 바꿨는지
- 어떤 benchmark evidence가 있었는지
- 왜 채택/보류했는지

---

## 실무 의사결정 규칙

- **강한 근거가 없으면 no-change가 정답**일 수 있다.
- score 분산을 늘리기 위해 risk/recommendation 일관성을 희생하지 않는다.
- code/ruleset tuning보다 benchmark sharpening을 먼저 시도한다.
- global rescaling보다 좁은 parameter-family 조정이 우선이다.
- benchmark가 100%라고 끝이 아니라, `tuning_signals`로 “체감상 비슷한 숫자” 문제를 본다.
- 반대로 `tuning_signals`가 약간 개선되어도 slack이 급격히 줄면 채택하지 않는다.

---

## 다음 사이클 체크리스트

- [ ] benchmark fixture가 현재 제품 기대와 맞는가
- [ ] closest score pair가 실제로 문제 케이스인가
- [ ] 좁은 headroom 케이스가 accidental over-tuning이 아니라 의도된 sentinel인가
- [ ] 선택한 parameter family가 explainable한가
- [ ] README / tests / artifacts를 함께 갱신했는가
- [ ] `make test` 통과
- [ ] `make verify-sources` 통과
- [ ] benchmark coverage 100% 유지
