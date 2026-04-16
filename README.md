# bom-influxdb-loader
I have noticed regular drop outs and performance degradation on our NBN FttN service, and wanted to see if these drop outs correlated with the weather, specifically rain and temperature.

So I wrote a script which will collect data from the [BOM](http://www.bom.gov.au/) and insert it into an InfluxDB table, for display in Grafana alongside NBN service metrics (speed test, ping, packet drop).

It uses the [tonyallan/weather-au](https://github.com/tonyallan/weather-au) library to fetch BOM observations. The package is installed directly from GitHub as the PyPI release predates the addition of the `rainfall()` and `period_attribute()` methods this project depends on.

## Configuration

Edit `config/config.yaml` before running:

```yaml
InfluxDb:
  Host: 'localhost'
  Port: '8086'
  Database: 'bom-observations'
Data:
  - state: 'NSW'
    stations:
      - name: 'Bellambi'
        id: '94749'
      - name: 'Sydney'
        id: '94768'
```

Station IDs are WMO IDs from the BOM observations feed.

## Development

All operations run via Docker using `make`. Build the production image first:

```bash
make build
```

| Command       | Description                                              |
|---------------|----------------------------------------------------------|
| `make build`  | Build the production Docker image                        |
| `make run`    | Run the loader (mounts `./config`)                       |
| `make test`   | Run the script with live-mounted `./app` (no rebuild needed) |
| `make lint`   | Lint with ruff                                           |
| `make format` | Check formatting with ruff                               |
| `make pytest` | Run the unit test suite                                  |

## Building for multiple platforms

Multi-platform builds use `docker buildx`. If you haven't set it up:

```bash
brew install docker-buildx
mkdir -p ~/.docker/cli-plugins
ln -sfn /opt/homebrew/opt/docker-buildx/bin/docker-buildx ~/.docker/cli-plugins/docker-buildx
docker buildx create --name multiplatform --driver docker-container --use
docker buildx inspect --bootstrap
```

Then:

```bash
make build-pi    # linux/arm64 (Raspberry Pi 4+)
make build-all   # linux/amd64 + linux/arm64, pushed to Docker Hub
```
