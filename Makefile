# path: Makefile
.PHONY: install dev test lint typecheck run dashboard clean

install:
	pip install -r requirements.txt

dev:
	pip install -r requirements-dev.txt
	pip install -e .

test:
	pytest

test-coverage:
	pytest --cov=k8s_sentinel --cov-report=term-missing

lint:
	ruff check k8s_sentinel tests dashboard

typecheck:
	mypy k8s_sentinel

run:
	python run_agent.py

dashboard:
	uvicorn dashboard.main:app --reload --port 8000

clean:
	rm -rf data/*.db .pytest_cache .mypy_cache
	find . -type d -name __pycache__ -exec rm -rf {} +
