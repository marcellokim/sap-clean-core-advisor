PYTHON ?= ./.venv/bin/python
INDUSTRY ?= manufacturing
COMPAT_TELEMETRY_LOG_PATH ?= artifacts/telemetry/compat_usage.jsonl
IMPORT_BUDGET_REPEATS ?= 5
IMPORT_BUDGET_TARGETS ?= app analysis_runner

.PHONY: run test test-compat check-import-cycles measure-import-budget verify-sources verify-citations verify-report-consistency verify-report-preconfirm verify-prune-hygiene report-compat-telemetry verify-safe-lane-promotion verify-safe-lane-promotion-nonstrict verify-safe-lane-promotion-strict verify-safe-lane-promotion-core verify-release-readiness qa-report

run:
	uv run streamlit run app.py

test:
	COMPAT_TELEMETRY_ENABLE=false COMPAT_DEPRECATION_WARN=false $(PYTHON) -m unittest discover -s tests -v

test-compat:
	COMPAT_TELEMETRY_ENABLE=false COMPAT_DEPRECATION_WARN=false $(PYTHON) -m unittest discover -s tests -p "test_compat_contracts.py" -v

check-import-cycles:
	python3 scripts/check_import_cycles.py services app.py

measure-import-budget:
	$(PYTHON) tools/measure_import_budget.py --repeats $(IMPORT_BUDGET_REPEATS) --targets $(IMPORT_BUDGET_TARGETS) --output artifacts/perf/import_budget.json --modules-output artifacts/perf/import_modules.json --json

verify-sources:
	$(PYTHON) tools/verify_sources.py --skip-http --json

verify-citations:
	COMPAT_TELEMETRY_ENABLE=false COMPAT_DEPRECATION_WARN=false $(PYTHON) tools/verify_citations.py --json

verify-report-consistency:
	COMPAT_TELEMETRY_ENABLE=false COMPAT_DEPRECATION_WARN=false $(PYTHON) tools/verify_report_consistency.py --json

verify-report-preconfirm: verify-citations verify-report-consistency
	@echo "[ok] pre-confirm verification suite completed."

verify-prune-hygiene:
	$(PYTHON) scripts/verify_prune_hygiene.py

report-compat-telemetry:
	COMPAT_TELEMETRY_LOG_PATH=$(COMPAT_TELEMETRY_LOG_PATH) $(PYTHON) scripts/compat_telemetry_report.py --days 7 --json --log-path $(COMPAT_TELEMETRY_LOG_PATH)

verify-safe-lane-promotion: verify-safe-lane-promotion-nonstrict

verify-safe-lane-promotion-nonstrict:
	@echo "[warn] running non-strict safe-lane gate (telemetry evidence is not enforced)."
	COMPAT_TELEMETRY_LOG_PATH=$(COMPAT_TELEMETRY_LOG_PATH) $(PYTHON) scripts/compat_telemetry_report.py --days 7 --json --log-path $(COMPAT_TELEMETRY_LOG_PATH) --fail-on-usage
	$(MAKE) verify-safe-lane-promotion-core

verify-safe-lane-promotion-core:
	$(PYTHON) scripts/verify_prune_hygiene.py
	$(MAKE) test-compat

verify-safe-lane-promotion-strict:
	@mkdir -p $(dir $(COMPAT_TELEMETRY_LOG_PATH))
	@if [ ! -f "$(COMPAT_TELEMETRY_LOG_PATH)" ]; then \
		echo "[fail] strict safe-lane gate blocked: telemetry log is missing: $(COMPAT_TELEMETRY_LOG_PATH)"; \
		echo "[hint] run workload with COMPAT_TELEMETRY_ENABLE=true before promotion."; \
		exit 2; \
	fi
	@if [ ! -s "$(COMPAT_TELEMETRY_LOG_PATH)" ]; then \
		echo "[fail] strict safe-lane gate blocked: telemetry log is empty: $(COMPAT_TELEMETRY_LOG_PATH)"; \
		echo "[hint] placeholder file is not accepted; collect real telemetry evidence first."; \
		exit 2; \
	fi
	COMPAT_TELEMETRY_LOG_PATH=$(COMPAT_TELEMETRY_LOG_PATH) $(PYTHON) scripts/compat_telemetry_report.py --days 7 --json --log-path $(COMPAT_TELEMETRY_LOG_PATH) --fail-on-usage --require-log --fail-on-invalid-rows
	$(MAKE) verify-safe-lane-promotion-core

verify-release-readiness:
	$(PYTHON) scripts/verify_release_readiness.py --qa-runs 3 --safe-lane-mode strict --output artifacts/qa/release_readiness.json --json

qa-report: test verify-sources verify-report-preconfirm verify-prune-hygiene
	@echo "[ok] report qa gate completed."
