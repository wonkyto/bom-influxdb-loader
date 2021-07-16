#!/usr/bin/env python3

import argparse
import asyncio
import logging
import sys
import time
import yaml
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from influxdb import InfluxDBClient
from weather_au import observations

default_config_file = "/config/config.yaml"

# Set up logger
logger = logging.getLogger(__file__)
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
fmt = logging.Formatter(fmt='%(asctime)s.%(msecs)03d - '
                        + '%(levelname)s - %(message)s',
                        datefmt="%Y/%m/%d %H:%M:%S")
ch.setFormatter(fmt)
logger.addHandler(ch)


def get_args():
    """Parse the command line options

    Returns argparse object
    """

    parser = argparse.ArgumentParser()
    parser.add_argument('--config', required=False, help='Config File '
                        + 'Default: (' + default_config_file + ')',
                        default=default_config_file)
    args = parser.parse_args()
    return args


def load_yaml_file(yaml_file):
    """Load the config file info from the yaml

    Returns dict
    """
    result = None

    # Open the yaml file
    try:
        with open(yaml_file) as data_file:
            data = yaml.load(data_file, Loader=yaml.FullLoader)
        result = data
    except (FileNotFoundError) as e:
        logger.error("Could not open file: {} - {}".format(yaml_file, str(e)))
        sys.exit(1)
    return result


def poll(influx_client, data):
    """Poll the BOM URLs device, send collecte data to influxDB"""
    for src in data:
        logger.info("Polling Bom: '{}' data".format(src['state']))
        obs_data = observations.Observations(src['state'])
        metrics = []
        if obs_data is not None:
            for station in src['stations']:
                location = station['name']
                wmo_id = station['id']
                period = obs_data.period_attribute(wmo_id, 'time-local')
                airTemp = obs_data.air_temperature(wmo_id)
                rainfall = obs_data.rainfall(wmo_id)

                logger.debug("Station ID: {}".format(wmo_id))
                logger.debug("Time: {}".format(period))
                logger.debug("Air Temp: {}".format(airTemp))
                logger.debug("Rainfall: {}".format(rainfall))

                measurement = {
                    'measurement': 'weather',
                    'tags': {
                        'Location': location,
                        'id': wmo_id
                    },
                    'time': period,
                    'fields': {
                        'air_temp': float(airTemp),
                        'rainfall_9am': float(rainfall)
                    }
                }
                metrics.append(measurement)
        else:
            logger.warning("No data received for {}".format(src['state']))

        if metrics:
            if influx_client.write_points(metrics):
                logger.debug("Sending metrics to influxdb: successful")
            else:
                logger.debug("Sending metrics to influxdb: failed")


def main():
    # Get arguements
    args = get_args()
    # Load configure file
    config = load_yaml_file(args.config)

    # We will be running this container in the same docker-compose
    # configuration # as influxdb. To ensure we provide enough time
    # for influxdb to start, we wait 10 seconds
    time.sleep(10)

    # Make a connection to the InfluxDB Database
    # Create a new database if it doesn't exist
    influx_client = InfluxDBClient(host=config['InfluxDb']['Host'],
                                   port=config['InfluxDb']['Port'])
    influx_client.create_database(config['InfluxDb']['Database'])
    influx_client.switch_database(config['InfluxDb']['Database'])

    # Create a scheduler, and run the poller every 15 minutes on the minute
    scheduler = AsyncIOScheduler()
    scheduler.add_job(poll, 'cron', minute='00,15,30,45',
                      args=(influx_client, config['Data']))
    scheduler.start()

    # Execution will block here until Ctrl+C is pressed.
    try:
        asyncio.get_event_loop().run_forever()
    except (KeyboardInterrupt, SystemExit):
        pass

    influx_client.close()


if __name__ == '__main__':
    main()
