# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

All operations run via Docker. Build the image first before running `run` or `test`.

```bash
make build       # Build production Docker image (wonkyto/bom-influxdb-loader:<VERSION>)
make build-pi    # Build arm64 image and push to Docker Hub
make build-all   # Build amd64+arm64 multi-platform image and push to Docker Hub
make run         # Run the loader (mounts ./config:/config)
make test        # Run the script in a container with live-mounted ./app and ./config
make lint        # ruff check (runs inside Docker dev image)
make format      # ruff format --check (runs inside Docker dev image)
make pytest      # Run pytest suite (runs inside Docker dev image)
```

The `test` target mounts `./app` into the container so you can iterate without rebuilding.
`build-pi` and `build-all` require `docker buildx` with a multi-platform builder (`docker buildx create --name multiplatform --driver docker-container --use`).

## Architecture

This is a single-file Python app (`app/bom-influxdb-loader.py`) that runs as a long-lived Docker container.

**Data flow:**
1. On startup, reads `config/config.yaml` for InfluxDB connection details and a list of BOM states + station WMO IDs.
2. Waits 10 seconds (to allow InfluxDB to start in docker-compose), then connects to InfluxDB and creates the database if missing.
3. Schedules `poll()` via `APScheduler` to fire every 15 minutes (`:00`, `:15`, `:30`, `:45`).
4. `poll()` fetches weather observations for each configured state using the `weather_au` library (wonkyto fork of tonyallan/weather-au, installed from source in the Dockerfile), extracts air temperature and rainfall-since-9am per station, and batch-writes them as `weather` measurements to InfluxDB.

**External dependency note:** The `weather_au` package is not on PyPI — it is cloned from `https://github.com/wonkyto/weather-au.git` and installed from the built wheel during the Docker image build. This fork adds `period_attribute()` (observation timestamp) and `rainfall()` which are not in the upstream package.

**Configuration (`config/config.yaml`):**
- `InfluxDb.Host/Port/Database` — InfluxDB connection (Port is read as a string from YAML; cast to int before use).
- `Data` — list of `{state, stations[{name, id}]}` entries. `state` is a BOM state code (e.g. `NSW`). `id` is a WMO station ID string.

## Testing

Unit tests live in `tests/test_bom_influxdb_loader.py`. `tests/conftest.py` adds `app/` to `sys.path` so the module can be imported. The `weather_au` package (only available inside Docker) is always mocked in tests — never call `observations.Observations` without patching it.

Run tests via Docker: `make pytest`. To run a single test locally (if dependencies are installed): `pytest tests/test_bom_influxdb_loader.py::TestPoll::test_skips_write_when_no_stations`.
