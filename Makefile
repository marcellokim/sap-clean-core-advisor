PYTHON ?= ./.venv/bin/python
INDUSTRY ?= manufacturing

.PHONY: run test test-compat check-import-cycles verify-sources verify-citations verify-report-consistency verify-report-preconfirm verify-prune-hygiene report-compat-telemetry verify-safe-lane-promotion verify-safe-lane-promotion-strict verify-release-readiness qa-report

run:
	uv run streamlit run app.py

test:
	COMPAT_TELEMETRY_ENABLE=false COMPAT_DEPRECATION_WARN=false $(PYTHON) -m unittest discover -s tests -v

test-compat:
	COMPAT_TELEMETRY_ENABLE=false COMPAT_DEPRECATION_WARN=false $(PYTHON) -m unittest discover -s tests -p "test_compat_contracts.py" -v

check-import-cycles:
	python3 scripts/check_import_cycles.py services app.py

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
	$(PYTHON) scripts/compat_telemetry_report.py --days 7 --json

verify-safe-lane-promotion:
	@if [ -f artifacts/telemetry/compat_usage.jsonl ] && [ ! -s artifacts/telemetry/compat_usage.jsonl ]; then \
		echo "[fail] compat telemetry log exists but is empty: artifacts/telemetry/compat_usage.jsonl"; \
		echo "[hint] remove placeholder log and collect real telemetry before promotion."; \
		exit 2; \
	fi
	$(PYTHON) scripts/compat_telemetry_report.py --days 7 --json --fail-on-usage
	$(PYTHON) scripts/verify_prune_hygiene.py
	$(MAKE) test-compat

verify-safe-lane-promotion-strict:
	@mkdir -p artifacts/telemetry
	@if [ ! -f artifacts/telemetry/compat_usage.jsonl ]; then \
		echo "[fail] compat telemetry log is missing: artifacts/telemetry/compat_usage.jsonl"; \
		echo "[hint] enable runtime telemetry and collect at least one non-placeholder log before strict promotion."; \
		exit 2; \
	fi
	$(MAKE) verify-safe-lane-promotion
	$(PYTHON) scripts/compat_telemetry_report.py --days 7 --json --fail-on-usage --require-log

verify-release-readiness:
	$(PYTHON) scripts/verify_release_readiness.py --qa-runs 3 --output artifacts/qa/release_readiness.json --json

qa-report: test verify-sources verify-report-preconfirm verify-prune-hygiene
	@echo "[ok] report qa gate completed."
