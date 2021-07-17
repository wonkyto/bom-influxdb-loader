# bom-influxdb-loader
I have noticed regular drop outs and performance degredation on our NBN FttN service, and wanted to see if these drop outs correlated with the weather, specifically rain, and temperature. 

So I wrote a script which will collect data from the [BOM](http://www.bom.gov.au/) and insert it into an influxDB table, for display in grafana, along side the NBN service metrics (speed test, ping speed, packet drop).

It relies on a fork of the [tonyallan/weather-au](https://github.com/tonyallan/weather-au) repo, which is made available here: [wonkyto/weather-au](https://github.com/wonkyto/weather-au). This was forked at 0.0.7 and simply adds the ability to get the observation timestamp, and the rainfall since 9am from the data. A pull request has been made back to *tonyallan* to incorporate it back into the original package - if this happens I will update this package to reflect this.

## Docker
Development has been done using docker to facilitate a standard environment.

### Building the docker image
The docker image can be built in the following way:
```bash
make build
```
You'll want to build the image when you have finished development, or if you make any changes to the Dockerfile including python dependencies
### Testing the script
During development it is time consuming to build a new container, so you can simply mount the script into the existing container for testing. The python script can be tested in the following way:
```bash
make test
```
### Linting the script
During development you can run flake8 on the script:
```bash
make flake8
```

### Running the script
Once you have finished development, build the docker image, and run it using:
```bash
make run
```

## Configuration
The container requires a configuration file to be present.
### config/config.yaml
Here we define the following:
 * InfluxDb: Your InfluxDB endpoint and db
 * BOM source state and station ids.

See [config.yaml](config/config.yaml) for an example.

## Building
We will push the image to docker hub. Given this is created to run on x86 or raspi, we'll build two images.
```
# On amd64
docker build -t wonkyto/bom-influxdb-loader:1.0.1-amd64 .
docker push wonkyto/bom-influxdb-loader:1.0.1-amd64

# On raspi
docker build -t wonkyto/bom-influxdb-loader:1.0.1-arm32v6 .
docker push wonkyto/bom-influxdb-loader:1.0.1-arm32v6

# Enable experimental mode to ~/.docker/config.json
"experimental": "enabled"

# make multi arch
docker manifest create wonkyto/bom-influxdb-loader:1.0.1 wonkyto/bom-influxdb-loader:1.0.1-amd64 wonkyto/bom-influxdb-loader:1.0.1-arm32v6
docker manifest annotate wonkyto/bom-influxdb-loader:1.0.1 wonkyto/bom-influxdb-loader:1.0.1-arm32v6 --os linux --arch arm
docker manifest push wonkyto/bom-influxdb-loader:1.0.1 --purge
docker manifest create wonkyto/bom-influxdb-loader:latest wonkyto/bom-influxdb-loader:1.0.1-amd64 wonkyto/bom-influxdb-loader:1.0.1-arm32v6
docker manifest annotate wonkyto/bom-influxdb-loader:latest wonkyto/bom-influxdb-loader:1.0.1-arm32v6 --os linux --arch arm
docker manifest push wonkyto/bom-influxdb-loader:latest --purge
