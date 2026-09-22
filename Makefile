.PHONY: install run api ui test lint clean help

help:
	@echo "AskData — make targets:"
	@echo "  make install   - install Python deps"
	@echo "  make api       - run FastAPI on :8000"
	@echo "  make ui        - run Streamlit on :8501"
	@echo "  make test      - run pytest"
	@echo "  make lint      - ruff check"
	@echo "  make clean     - remove caches"

install:
	pip install -r requirements.txt

api:
	uvicorn askdata.main:app --host 0.0.0.0 --port 8000 --reload

ui:
	streamlit run src/askdata/web_ui/streamlit_app.py

test:
	pytest tests/ -v

lint:
	ruff check src/ tests/

clean:
	rm -rf __pycache__ .pytest_cache .ruff_cache .mypy_cache
	find . -type d -name "__pycache__" -exec rm -rf {} +
