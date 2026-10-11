# Beemer — common tasks.  `make help` lists them.
PY      ?= .venv/bin/python
PORT    ?= 8501
IMAGE   ?= beemer

.PHONY: help setup run start stop status update snapshot bootstrap publish test health docker-build docker-run clean api web new api-test web-build web-e2e compose

help:            ## list targets
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-13s %s\n", $$1, $$2}'

setup:           ## create .venv and install dependencies
	@[ -x $(PY) ] || python3 -m venv .venv
	$(PY) -m pip install -q --upgrade pip && $(PY) -m pip install -q -r requirements.txt

run: setup       ## run the app in the foreground (like a host would, from the repo root)
	$(PY) -m streamlit run app/main.py --server.port $(PORT) --server.address 127.0.0.1

start:           ## start in the background (start.sh)
	./start.sh
stop:            ## stop the background app
	./start.sh --stop
status:          ## is it running?
	./start.sh --status

update:          ## full daily data update (prices + stale fundamentals + metrics)
	$(PY) update_data.py
snapshot:        ## prices-only refresh
	$(PY) update_data.py --prices-only
bootstrap:       ## download the published data snapshot if data is missing
	$(PY) bootstrap.py
publish:         ## upload local data to the data-latest GitHub release (needs gh auth)
	./scripts/publish_data.sh

test:            ## render every page headlessly
	$(PY) scripts/smoke_test.py
health:          ## health-check a running app:  make health URL=https://…
	./scripts/healthcheck.sh $(URL)

docker-build:    ## build the container image
	docker build -t $(IMAGE) .
docker-run:      ## run the container on PORT
	docker run --rm -p $(PORT):8501 $(IMAGE)

api:             ## Spring Boot API on :8080 (new stack)
	cd backend && mvn -q -DskipTests spring-boot:run
web:             ## React dev server on :5173 (new stack)
	cd frontend && npm run dev -- --host 127.0.0.1 --port 5173
new:             ## API + React in the background (start-new.sh)
	./start-new.sh
api-test:        ## Java unit tests against Python golden files
	cd backend && mvn -B test
web-build:       ## production frontend build
	cd frontend && npm ci && npm run build
web-e2e:         ## Playwright smoke (API on :8080, set BEEMER_WEB if not using preview)
	cd frontend && npm run test:e2e
compose:         ## new stack in Docker (API, nginx, pipeline). Streamlit image is separate.
	docker compose up --build

clean:           ## remove the virtualenv and caches (keeps data)
	rm -rf .venv __pycache__ app/__pycache__ app/views/__pycache__
