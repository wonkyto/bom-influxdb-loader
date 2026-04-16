VERSION = 1.1.0
IMAGE_NAME ?= wonkyto/bom-influxdb-loader:$(VERSION)

.PHONY: build build-pi build-all push lint format pytest run test

build:
	docker build --target production -t $(IMAGE_NAME) .

push:
	docker push $(IMAGE_NAME)

build-pi:
	docker buildx build --target production --platform linux/arm64 -t $(IMAGE_NAME) --push .

build-all:
	docker buildx build --target production --platform linux/amd64,linux/arm64 -t $(IMAGE_NAME) --push .

lint:
	docker compose run --rm lint

format:
	docker compose run --rm format

pytest:
	docker compose run --rm pytest

run:
	docker compose run --rm run

test:
	docker compose run --rm test
