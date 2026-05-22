.PHONY: install demo test clean

install:
	pip install -r requirements.txt -r requirements-dev.txt

demo:
	python -m src.generate_data
	python main.py

test:
	pytest tests/ -v

clean:
	rm -rf outputs/ __pycache__ src/__pycache__ .pytest_cache .coverage
