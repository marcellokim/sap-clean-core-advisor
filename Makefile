PYTHON ?= ./.venv/bin/python
INDUSTRY ?= manufacturing

.PHONY: run test verify-sources verify-citations verify-report-consistency verify-report-preconfirm backtest calibrate

run:
	uv run streamlit run app.py

test:
	$(PYTHON) -m unittest discover -s tests -v

verify-sources:
	$(PYTHON) tools/verify_sources.py --skip-http --json

verify-citations:
	$(PYTHON) tools/verify_citations.py --json

verify-report-consistency:
	$(PYTHON) tools/verify_report_consistency.py --json

verify-report-preconfirm: verify-citations verify-report-consistency
	@echo "[ok] pre-confirm verification suite completed."

backtest:
	@echo "[deprecated] backtest workflow has been removed in this branch."
	@echo "Use: make test && make verify-sources"

calibrate:
	@echo "[deprecated] calibrate workflow has been removed in this branch."
	@echo "Use: make test && make verify-sources"
