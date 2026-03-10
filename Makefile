PYTHON ?= ./.venv/bin/python
INDUSTRY ?= manufacturing

.PHONY: run test test-compat check-import-cycles verify-sources verify-citations verify-report-consistency verify-report-preconfirm qa-report

run:
	uv run streamlit run app.py

test:
	$(PYTHON) -m unittest discover -s tests -v

test-compat:
	$(PYTHON) -m unittest discover -s tests -p "test_compat_contracts.py" -v

check-import-cycles:
	python3 scripts/check_import_cycles.py services app.py

verify-sources:
	$(PYTHON) tools/verify_sources.py --skip-http --json

verify-citations:
	$(PYTHON) tools/verify_citations.py --json

verify-report-consistency:
	$(PYTHON) tools/verify_report_consistency.py --json

verify-report-preconfirm: verify-citations verify-report-consistency
	@echo "[ok] pre-confirm verification suite completed."

qa-report: test verify-sources verify-report-preconfirm
	@echo "[ok] report qa gate completed."
