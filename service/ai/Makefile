.PHONY: install install-linux run build-index test docker-build docker-up docker-down clean

install:
	pip install -r requirements.txt

install-linux:
	bash scripts/install_linux.sh

run:
	python scripts/run_server.py --reload

build-index:
	python scripts/build_index.py

build-index-force:
	python scripts/build_index.py --force

test:
	python scripts/test_api.py

docker-build:
	docker compose build

docker-up:
	docker compose up -d

docker-down:
	docker compose down

clean:
	rm -rf vector_store __pycache__ src/__pycache__ src/**/__pycache__
	find . -name "*.pyc" -delete
