PYTHON ?= ./.venv/bin/python
INDUSTRY ?= manufacturing

.PHONY: run test verify-sources backtest calibrate

run:
	uv run streamlit run app.py

test:
	$(PYTHON) -m unittest discover -s tests -v

verify-sources:
	$(PYTHON) tools/verify_sources.py --skip-http --json

backtest:
	@echo "[deprecated] backtest workflow has been removed in this branch."
	@echo "Use: make test && make verify-sources"

calibrate:
	@echo "[deprecated] calibrate workflow has been removed in this branch."
	@echo "Use: make test && make verify-sources"
