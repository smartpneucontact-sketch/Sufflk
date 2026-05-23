.PHONY: install install-dev install-ui test eval lint serve ui ingest docker clean

PYTHON ?= python3

install:
	$(PYTHON) -m pip install -e .

install-dev:
	$(PYTHON) -m pip install -e .[dev]

install-ui:
	$(PYTHON) -m pip install -e .[ui]

test:
	SITE_COPILOT_USE_MOCK_LLM=1 pytest -q

eval:
	SITE_COPILOT_USE_MOCK_LLM=1 $(PYTHON) -m evals.run_evals

eval-live:
	$(PYTHON) -m evals.run_evals

lint:
	ruff check .

serve:
	uvicorn site_copilot.api.main:app --reload --port 8000

ui:
	streamlit run src/site_copilot/ui/streamlit_app.py

ingest:
	$(PYTHON) -m site_copilot.rag.ingest --query "interior column cover reinforcing"

docker:
	docker compose -f infra/docker-compose.yml up --build

clean:
	rm -rf .venv .pytest_cache .ruff_cache .mypy_cache traces .chroma build dist *.egg-info
	find . -name __pycache__ -type d -exec rm -rf {} +
