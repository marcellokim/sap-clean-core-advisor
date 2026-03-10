# Document QA Checklist (Customer-facing)

## Automated Gate (must pass before handoff)
- [ ] `make qa-report` passed (test + source + pre-confirm)
- [ ] `make test-compat` passed (compatibility wrappers unchanged)
- [ ] `make verify-sources` result is empty (`[]`)
- [ ] `make verify-citations` has no HIGH issues
- [ ] `make verify-report-consistency` has no HIGH issues

## Blocking Rules (Fail-Fast)
- [ ] `ERR_REPORT_VALIDATION` not raised
- [ ] No `REPORT_PRECONFIRM_HIGH_*` warning in output payload
- [ ] PDF status is `ok` (handoff build)

## Content Quality
- [ ] Numbers in summary == numbers in dashboard
- [ ] Risk text matches current ruleset version
- [ ] TCO is labeled as decision proxy estimate

## Evidence Quality
- [ ] Each recommendation has rule IDs
- [ ] Source IDs are populated
- [ ] No claim with only D-grade in final handoff

## Delivery Quality
- [ ] KO/EN terminology lock applied
- [ ] Decision log + action items attached
- [ ] Version/date stamped

## Failure Response SOP
- [ ] HIGH issue 발생 시 PDF 공유 금지, 분석 산출물 JSON과 warning code 첨부
- [ ] Source issue 발생 시 `tools/snapshot_sources.py --offline --update-catalog --json`로 스냅샷/해시 갱신
- [ ] 수정 후 `make qa-report` 재실행하여 green 확인
