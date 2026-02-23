.PHONY: test lint check

test:
	cd backend && python3 -m pytest tests/ -v

lint:
	cd backend && python3 -m ruff check .

check: lint test
