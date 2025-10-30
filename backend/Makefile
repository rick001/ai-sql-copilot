PYTHON?=python
PIP?=pip
UVICORN?=uvicorn

.PHONY: run seed test

run:
	$(UVICORN) app.main:app --host 0.0.0.0 --port 8000 --reload

seed:
	$(PYTHON) app/seed.py

test:
	pytest -q

