.PHONY: install install-linux run build-index build-index-force rebuild-kb eval-kb test docker-build docker-up docker-down clean

PYTHON ?= python3

install:
	$(PYTHON) -m pip install -r requirements.txt

install-linux:
	bash scripts/install_linux.sh

run:
	$(PYTHON) scripts/run_server.py --reload

build-index:
	$(PYTHON) scripts/build_index.py

build-index-force:
	$(PYTHON) scripts/build_index.py --force

rebuild-kb:
	$(PYTHON) scripts/rebuild_kb.py --force

eval-kb:
	$(PYTHON) scripts/evaluate_kb.py --mode all

test:
	$(PYTHON) scripts/test_api.py

docker-build:
	docker compose -f docker/docker-compose.yml build

docker-up:
	docker compose -f docker/docker-compose.yml up -d

docker-down:
	docker compose -f docker/docker-compose.yml down

clean:
	rm -rf vector_store __pycache__ src/__pycache__ src/**/__pycache__
	find . -name "*.pyc" -delete
