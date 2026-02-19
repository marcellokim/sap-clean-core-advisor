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
	$(PYTHON) tools/backtest_ruleset.py --industry $(INDUSTRY)

calibrate:
	$(PYTHON) tools/calibrate_ruleset.py --industry $(INDUSTRY)

