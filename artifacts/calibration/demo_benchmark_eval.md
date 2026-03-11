# Demo Benchmark Evaluation

- Generated at: `2026-03-11T11:06:00Z`
- Fixture: `tests/fixtures/demo_benchmark.yaml`
- Total cases: `16`

## Summary Metrics

- Score range hit rate: `16/16 (100.0%)`
- Risk exact match rate: `16/16 (100.0%)`
- Rule any-match rate: `16/16 (100.0%)`
- Recommendation coverage rate: `16/16 (100.0%)`
- Fully matched case rate: `16/16 (100.0%)`
- Signal assertion pass rate: `3/3 (100.0%)`
- Benchmark gate: `PASS`

## Tuning Signals

- Score dispersion: avg `51.7`, min `21.6`, max `88.5`, span `66.9`, stddev `22.3`
- Current annual TCO dispersion: avg `1.58`, min `0.49`, max `3.11`, span `2.62`, stddev `0.68`
- Projected annual TCO dispersion: avg `1.45`, min `0.47`, max `2.90`, span `2.43`, stddev `0.65`

### Closest Score Pairs

- `retail_low_risk_promo` `81.7` ↔ `mfg_s4_stable` `81.9` (gap `0.2`)
- `mfg_high_custom_factory` `21.6` ↔ `extreme_high_custom_ratio` `22.1` (gap `0.5`)
- `extreme_multi_axis_pain` `44.3` ↔ `extreme_short_timeline` `45.1` (gap `0.8`)

### Narrowest Score Headroom (to lower bound)

- `extreme_high_custom_ratio` headroom `0.8` within expected `21.3-22.9`
- `extreme_multi_axis_pain` headroom `0.8` within expected `43.5-45.1`
- `extreme_short_timeline` headroom `0.8` within expected `44.3-45.9`

### Narrowest Score Headroom (to upper bound)

- `extreme_high_custom_ratio` headroom `0.8` within expected `21.3-22.9`
- `extreme_multi_axis_pain` headroom `0.8` within expected `43.5-45.1`
- `extreme_short_timeline` headroom `0.8` within expected `44.3-45.9`

## Signal Assertions

- Overall: `PASS` (`3/3` passed)

### Pairwise Gap Assertions

- `PASS` score: `mfg_s4_stable` `81.9` > `retail_low_risk_promo` `81.7` (gap `0.2` vs expected `>= 0.2`)
  - Reason: Keep the healthy manufacturing S/4 baseline slightly above the retail promo baseline.
- `PASS` score: `extreme_high_custom_ratio` `22.1` > `mfg_high_custom_factory` `21.6` (gap `0.5` vs expected `>= 0.5`)
  - Reason: Preserve visible separation between heavy factory customization pressure and the pure custom-ratio edge case.
- `PASS` score: `extreme_short_timeline` `45.1` > `extreme_multi_axis_pain` `44.3` (gap `0.8` vs expected `>= 0.8`)
  - Reason: Keep the six-axis pain fallback case distinct from the short-timeline finance stress case.

## Industry Differentiation Summary

| Profile | Cases | Avg Score | Min | Max | Span | Risk Distribution |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| base | 3 | 61.7 | 44.3 | 88.5 | 44.2 | High=1, Low=1, Medium=1 |
| finance | 4 | 49.2 | 30.8 | 86.8 | 56.0 | High=3, Low=1 |
| manufacturing | 5 | 41.6 | 21.6 | 81.9 | 60.3 | High=4, Low=1 |
| retail | 4 | 59.3 | 35.9 | 81.7 | 45.8 | High=2, Low=2 |

## Case Results

### mfg_ecc_foundation — 한빛정밀

- Industry/Profile: `제조` / `manufacturing`
- Score: expected `40.0-46.0` → actual `42.7` (PASS)
- Risk: expected `High` → actual `High` (PASS)
- Expected rules(any): `RISK_BS7_MAINSTREAM_END_2027, RISK_DB_NOT_HANA, RISK_PAIN_POINTS_DUAL_AXIS` → matched `RISK_BS7_MAINSTREAM_END_2027, RISK_DB_NOT_HANA, RISK_PAIN_POINTS_DUAL_AXIS` (PASS)
- Expected recommendations(any): `REC_DB_TO_HANA, REC_PAIN_FIN_CLOSE, REC_PAIN_INTEGRATION` → matched `REC_DB_TO_HANA, REC_PAIN_FIN_CLOSE, REC_PAIN_INTEGRATION` (PASS)
- Overall: `PASS`
- Notes: Manufacturing baseline with ECC + Oracle debt and dual-axis close/integration pain signals.

### mfg_high_custom_factory — 대한기어

- Industry/Profile: `제조` / `manufacturing`
- Score: expected `20.8-22.4` → actual `21.6` (PASS)
- Risk: expected `High` → actual `High` (PASS)
- Expected rules(any): `RISK_CUSTOM_RATIO_HIGH, RISK_HIGH_CUSTOM_MODULES_3PLUS, RISK_TIMELINE_TOO_SHORT_FOR_CUSTOM, RISK_PAIN_POINTS_MULTI_AXIS` → matched `RISK_CUSTOM_RATIO_HIGH, RISK_HIGH_CUSTOM_MODULES_3PLUS, RISK_TIMELINE_TOO_SHORT_FOR_CUSTOM, RISK_PAIN_POINTS_MULTI_AXIS` (PASS)
- Expected recommendations(any): `REC_SCORE_LT_30, REC_CUSTOM_RATIO_OVER_40, REC_HIGH_CUSTOM_MODULE_BTP, REC_TIMELINE_TIGHT_PHASED` → matched `REC_SCORE_LT_30, REC_CUSTOM_RATIO_OVER_40, REC_HIGH_CUSTOM_MODULE_BTP, REC_TIMELINE_TIGHT_PHASED` (PASS)
- Overall: `PASS`
- Notes: Manufacturing heavy-custom extreme with four high-custom modules and compressed timeline.

### mfg_s4_stable — 미래소재

- Industry/Profile: `제조업` / `manufacturing`
- Score: expected `81.1-82.7` → actual `81.9` (PASS)
- Risk: expected `Low` → actual `Low` (PASS)
- Expected rules(any): `SCORE_DATABASE_HANA, RISK_LEVEL_LOW_RULE` → matched `SCORE_DATABASE_HANA, RISK_LEVEL_LOW_RULE` (PASS)
- Expected recommendations(any): `REC_PAIN_AI_DATA, REC_LOW_RISK_GOVERNANCE, REC_LOW_RISK_KPI_MONITORING` → matched `REC_PAIN_AI_DATA, REC_LOW_RISK_GOVERNANCE, REC_LOW_RISK_KPI_MONITORING` (PASS)
- Overall: `PASS`
- Notes: Healthy manufacturing S/4 baseline to ensure low-risk recommendations still surface actionable governance items.

### mfg_large_db_wave — 동명화학

- Industry/Profile: `mfg` / `manufacturing`
- Score: expected `37.0-43.0` → actual `39.9` (PASS)
- Risk: expected `High` → actual `High` (PASS)
- Expected rules(any): `RISK_DB_SIZE_LARGE, RISK_DB_NOT_HANA, RISK_HIGH_CUSTOM_MODULES_PRESENT` → matched `RISK_DB_SIZE_LARGE, RISK_DB_NOT_HANA, RISK_HIGH_CUSTOM_MODULES_PRESENT` (PASS)
- Expected recommendations(any): `REC_DB_TO_HANA, REC_HIGH_CUSTOM_MODULE_BTP, REC_PAIN_INTEGRATION` → matched `REC_DB_TO_HANA, REC_HIGH_CUSTOM_MODULE_BTP, REC_PAIN_INTEGRATION` (PASS)
- Overall: `PASS`
- Notes: Manufacturing large-database case intended to pressure archive/wave-planning behavior.

### retail_low_risk_promo — 리테일플러스

- Industry/Profile: `유통` / `retail`
- Score: expected `80.9-82.5` → actual `81.7` (PASS)
- Risk: expected `Low` → actual `Low` (PASS)
- Expected rules(any): `SCORE_DATABASE_HANA, RISK_LEVEL_LOW_RULE` → matched `SCORE_DATABASE_HANA, RISK_LEVEL_LOW_RULE` (PASS)
- Expected recommendations(any): `REC_PAIN_PERFORMANCE, REC_LOW_RISK_GOVERNANCE, REC_LOW_RISK_KPI_MONITORING` → matched `REC_PAIN_PERFORMANCE, REC_LOW_RISK_GOVERNANCE, REC_LOW_RISK_KPI_MONITORING` (PASS)
- Overall: `PASS`
- Notes: Retail low-risk reference that still requires performance tuning around promotion peaks.

### retail_peak_volume_short_timeline — 스타커머스

- Industry/Profile: `유통/리테일` / `retail`
- Score: expected `33.0-39.0` → actual `35.9` (PASS)
- Risk: expected `High` → actual `High` (PASS)
- Expected rules(any): `RISK_TIMELINE_TOO_SHORT_FOR_CUSTOM, RISK_DB_NOT_HANA, RISK_PAIN_POINTS_DUAL_AXIS` → matched `RISK_TIMELINE_TOO_SHORT_FOR_CUSTOM, RISK_DB_NOT_HANA, RISK_PAIN_POINTS_DUAL_AXIS` (PASS)
- Expected recommendations(any): `REC_DB_TO_HANA, REC_TIMELINE_TIGHT_PHASED, REC_PAIN_UPGRADE_COMPAT` → matched `REC_DB_TO_HANA, REC_TIMELINE_TIGHT_PHASED, REC_PAIN_UPGRADE_COMPAT` (PASS)
- Overall: `PASS`
- Notes: Retail peak-volume scenario with tight timeline and mixed performance/upgrade pressure.

### retail_integration_security — 옴니채널마트

- Industry/Profile: `retail` / `retail`
- Score: expected `69.0-75.0` → actual `72.3` (PASS)
- Risk: expected `Low` → actual `Low` (PASS)
- Expected rules(any): `SCORE_DATABASE_HANA, RISK_PAIN_POINTS_DUAL_AXIS, RISK_LEVEL_LOW_RULE` → matched `SCORE_DATABASE_HANA, RISK_PAIN_POINTS_DUAL_AXIS, RISK_LEVEL_LOW_RULE` (PASS)
- Expected recommendations(any): `REC_PAIN_INTEGRATION, REC_PAIN_SECURITY, REC_LOW_RISK_GOVERNANCE` → matched `REC_PAIN_INTEGRATION, REC_PAIN_SECURITY, REC_LOW_RISK_GOVERNANCE` (PASS)
- Overall: `PASS`
- Notes: Retail omnichannel case to preserve integration and access-control recommendations without inflating core risk.

### finance_core_banking_ecc — 신한코어

- Industry/Profile: `금융` / `finance`
- Score: expected `28.0-34.0` → actual `30.8` (PASS)
- Risk: expected `High` → actual `High` (PASS)
- Expected rules(any): `RISK_DB_NOT_HANA, RISK_HIGH_CUSTOM_MODULES_PRESENT, RISK_PAIN_POINTS_DUAL_AXIS` → matched `RISK_DB_NOT_HANA, RISK_HIGH_CUSTOM_MODULES_PRESENT, RISK_PAIN_POINTS_DUAL_AXIS` (PASS)
- Expected recommendations(any): `REC_DB_TO_HANA, REC_HIGH_CUSTOM_MODULE_BTP, REC_PAIN_FIN_CLOSE, REC_PAIN_SECURITY` → matched `REC_DB_TO_HANA, REC_HIGH_CUSTOM_MODULE_BTP, REC_PAIN_FIN_CLOSE, REC_PAIN_SECURITY` (PASS)
- Overall: `PASS`
- Notes: Finance ECC case with regulated-process pressure and elevated customization in FI/CO.

### finance_s4_regulated_low — 안심보험

- Industry/Profile: `금융/보험` / `finance`
- Score: expected `84.0-90.0` → actual `86.8` (PASS)
- Risk: expected `Low` → actual `Low` (PASS)
- Expected rules(any): `SCORE_DATABASE_HANA, RISK_LEVEL_LOW_RULE` → matched `SCORE_DATABASE_HANA, RISK_LEVEL_LOW_RULE` (PASS)
- Expected recommendations(any): `REC_PAIN_SECURITY, REC_LOW_RISK_GOVERNANCE, REC_LOW_RISK_KPI_MONITORING` → matched `REC_PAIN_SECURITY, REC_LOW_RISK_GOVERNANCE, REC_LOW_RISK_KPI_MONITORING` (PASS)
- Overall: `PASS`
- Notes: Low-risk finance benchmark that should still emit security/governance follow-up actions.

### finance_eos_legacy — 제일캐피탈

- Industry/Profile: `banking` / `finance`
- Score: expected `31.0-38.0` → actual `34.3` (PASS)
- Risk: expected `High` → actual `High` (PASS)
- Expected rules(any): `RISK_ERP_EOS_IMMINENT, RISK_DB_NOT_HANA, RISK_TIMELINE_TOO_SHORT_FOR_CUSTOM` → matched `RISK_ERP_EOS_IMMINENT, RISK_DB_NOT_HANA, RISK_TIMELINE_TOO_SHORT_FOR_CUSTOM` (PASS)
- Expected recommendations(any): `REC_DB_TO_HANA, REC_PAIN_UPGRADE_COMPAT, REC_PAIN_SECURITY` → matched `REC_DB_TO_HANA, REC_PAIN_UPGRADE_COMPAT, REC_PAIN_SECURITY` (PASS)
- Overall: `PASS`
- Notes: Legacy finance estate for EOS pressure with upgrade and audit pain signals.

### base_public_sector_balanced — 시민서비스청

- Industry/Profile: `공공` / `base`
- Score: expected `49.0-56.0` → actual `52.3` (PASS)
- Risk: expected `Medium` → actual `Medium` (PASS)
- Expected rules(any): `RISK_DB_NOT_HANA, RISK_PAIN_POINTS_DUAL_AXIS, RISK_LEVEL_MEDIUM_RULE` → matched `RISK_DB_NOT_HANA, RISK_PAIN_POINTS_DUAL_AXIS, RISK_LEVEL_MEDIUM_RULE` (PASS)
- Expected recommendations(any): `REC_DB_TO_HANA, REC_PAIN_PERFORMANCE, REC_PAIN_AI_DATA` → matched `REC_DB_TO_HANA, REC_PAIN_PERFORMANCE, REC_PAIN_AI_DATA` (PASS)
- Overall: `PASS`
- Notes: Base-profile fallback case to verify non-mapped industries still receive sensible medium-risk guidance.
- Resolution warnings: INDUSTRY_MAPPING_FALLBACK_TO_BASE

### base_greenfield_modern — 헬스플로우

- Industry/Profile: `Healthcare` / `base`
- Score: expected `86.0-92.0` → actual `88.5` (PASS)
- Risk: expected `Low` → actual `Low` (PASS)
- Expected rules(any): `SCORE_DATABASE_HANA, RISK_LEVEL_LOW_RULE` → matched `SCORE_DATABASE_HANA, RISK_LEVEL_LOW_RULE` (PASS)
- Expected recommendations(any): `REC_PAIN_AI_DATA, REC_LOW_RISK_GOVERNANCE, REC_LOW_RISK_KPI_MONITORING` → matched `REC_PAIN_AI_DATA, REC_LOW_RISK_GOVERNANCE, REC_LOW_RISK_KPI_MONITORING` (PASS)
- Overall: `PASS`
- Notes: Base-profile modern reference for unknown industry aliases with healthy S/4 posture.
- Resolution warnings: INDUSTRY_MAPPING_FALLBACK_TO_BASE

### extreme_high_custom_ratio — 커스텀헤비

- Industry/Profile: `제조` / `manufacturing`
- Score: expected `21.3-22.9` → actual `22.1` (PASS)
- Risk: expected `High` → actual `High` (PASS)
- Expected rules(any): `RISK_CUSTOM_RATIO_HIGH, RISK_HIGH_CUSTOM_MODULES_3PLUS, RISK_SCORE_LT_HIGH_THRESHOLD` → matched `RISK_CUSTOM_RATIO_HIGH, RISK_HIGH_CUSTOM_MODULES_3PLUS, RISK_SCORE_LT_HIGH_THRESHOLD` (PASS)
- Expected recommendations(any): `REC_SCORE_LT_30, REC_CUSTOM_RATIO_OVER_40, REC_HIGH_CUSTOM_MODULE_BTP` → matched `REC_SCORE_LT_30, REC_CUSTOM_RATIO_OVER_40, REC_HIGH_CUSTOM_MODULE_BTP` (PASS)
- Overall: `PASS`
- Notes: Pure high-custom-ratio edge case to stress score floor behavior and BTP decoupling recommendation coverage.

### extreme_huge_db — 메가데이터유통

- Industry/Profile: `유통` / `retail`
- Score: expected `44.0-50.0` → actual `47.2` (PASS)
- Risk: expected `High` → actual `High` (PASS)
- Expected rules(any): `RISK_DB_SIZE_LARGE, RISK_DB_NOT_HANA, RISK_PAIN_POINTS_DUAL_AXIS` → matched `RISK_DB_SIZE_LARGE, RISK_DB_NOT_HANA, RISK_PAIN_POINTS_DUAL_AXIS` (PASS)
- Expected recommendations(any): `REC_DB_TO_HANA, REC_PAIN_PERFORMANCE, REC_PAIN_INTEGRATION` → matched `REC_DB_TO_HANA, REC_PAIN_PERFORMANCE, REC_PAIN_INTEGRATION` (PASS)
- Overall: `PASS`
- Notes: Huge-database retail edge case for archive-first migration guidance.

### extreme_short_timeline — 패스트뱅크

- Industry/Profile: `finance` / `finance`
- Score: expected `44.3-45.9` → actual `45.1` (PASS)
- Risk: expected `High` → actual `High` (PASS)
- Expected rules(any): `RISK_TIMELINE_TOO_SHORT_FOR_CUSTOM, RISK_DB_NOT_HANA, RISK_PAIN_POINTS_DUAL_AXIS` → matched `RISK_TIMELINE_TOO_SHORT_FOR_CUSTOM, RISK_DB_NOT_HANA, RISK_PAIN_POINTS_DUAL_AXIS` (PASS)
- Expected recommendations(any): `REC_DB_TO_HANA, REC_TIMELINE_TIGHT_PHASED, REC_PAIN_UPGRADE_COMPAT` → matched `REC_DB_TO_HANA, REC_TIMELINE_TIGHT_PHASED, REC_PAIN_UPGRADE_COMPAT` (PASS)
- Overall: `PASS`
- Notes: Finance short-timeline edge case for staged-wave planning pressure.

### extreme_multi_axis_pain — 멀티액시스코

- Industry/Profile: `UnknownVertical` / `base`
- Score: expected `43.5-45.1` → actual `44.3` (PASS)
- Risk: expected `High` → actual `High` (PASS)
- Expected rules(any): `RISK_PAIN_POINTS_MULTI_AXIS, RISK_DB_NOT_HANA, RISK_LEVEL_HIGH_RULE` → matched `RISK_PAIN_POINTS_MULTI_AXIS, RISK_DB_NOT_HANA, RISK_LEVEL_HIGH_RULE` (PASS)
- Expected recommendations(any): `REC_PAIN_FIN_CLOSE, REC_PAIN_PERFORMANCE, REC_PAIN_UPGRADE_COMPAT, REC_PAIN_INTEGRATION, REC_PAIN_AI_DATA, REC_PAIN_SECURITY` → matched `REC_PAIN_FIN_CLOSE, REC_PAIN_PERFORMANCE, REC_PAIN_UPGRADE_COMPAT, REC_PAIN_INTEGRATION, REC_PAIN_AI_DATA, REC_PAIN_SECURITY` (PASS)
- Overall: `PASS`
- Notes: Base fallback edge case with six simultaneous pain-point categories to validate differentiated recommendation coverage.
- Resolution warnings: INDUSTRY_MAPPING_FALLBACK_TO_BASE
