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
	docker compose -f docker/docker-compose.yml build

docker-up:
	docker compose -f docker/docker-compose.yml up -d

docker-down:
	docker compose -f docker/docker-compose.yml down

clean:
	rm -rf vector_store __pycache__ src/__pycache__ src/**/__pycache__
	find . -name "*.pyc" -delete
