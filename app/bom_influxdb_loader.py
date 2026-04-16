#!/usr/bin/env python3

import argparse
import logging
import sys
import time
import yaml
from apscheduler.schedulers.background import BackgroundScheduler
from influxdb import InfluxDBClient
from weather_au import observations

default_config_file = "/config/config.yaml"

logger = logging.getLogger(__file__)
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
fmt = logging.Formatter(
    fmt='%(asctime)s.%(msecs)03d - %(levelname)s - %(message)s',
    datefmt="%Y/%m/%d %H:%M:%S",
)
ch.setFormatter(fmt)
logger.addHandler(ch)


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--config',
        required=False,
        help=f'Config file (default: {default_config_file})',
        default=default_config_file,
    )
    return parser.parse_args()


def load_yaml_file(yaml_file):
    try:
        with open(yaml_file) as f:
            return yaml.load(f, Loader=yaml.FullLoader)
    except FileNotFoundError as e:
        logger.error(f"Could not open file: {yaml_file} - {e}")
        sys.exit(1)


def poll(influx_client, data):
    """Poll BOM observation URLs and write collected data to InfluxDB."""
    for src in data:
        state = src['state']
        logger.info(f"Polling BOM '{state}' data")
        obs_data = observations.Observations(state)
        metrics = []

        if obs_data is not None:
            for station in src.get('stations', []):
                location = station['name']
                wmo_id = station['id']
                period = obs_data.period_attribute(wmo_id, 'time-local')
                air_temp = obs_data.air_temperature(wmo_id)
                rainfall = obs_data.rainfall(wmo_id)

                logger.debug(f"Station ID: {wmo_id}")
                logger.debug(f"Time: {period}")
                logger.debug(f"Air temp: {air_temp}")
                logger.debug(f"Rainfall: {rainfall}")

                if air_temp is None or rainfall is None:
                    logger.warning(f"Missing data for station {wmo_id} ({location}), skipping")
                    continue

                metrics.append({
                    'measurement': 'weather',
                    'tags': {
                        'Location': location,
                        'id': wmo_id,
                    },
                    'time': period,
                    'fields': {
                        'air_temp': float(air_temp),
                        'rainfall_9am': float(rainfall),
                    },
                })
        else:
            logger.warning(f"No data received for {state}")

        if metrics:
            if influx_client.write_points(metrics):
                logger.info("Sent metrics to InfluxDB: success")
            else:
                logger.warning("Sent metrics to InfluxDB: failed")


def main():
    args = get_args()
    config = load_yaml_file(args.config)

    # Allow InfluxDB time to start when running under docker-compose
    time.sleep(10)

    influx_cfg = config['InfluxDb']
    influx_client = InfluxDBClient(
        host=influx_cfg['Host'],
        port=int(influx_cfg['Port']),
    )
    try:
        influx_client.create_database(influx_cfg['Database'])
        influx_client.switch_database(influx_cfg['Database'])

        scheduler = BackgroundScheduler()
        scheduler.add_job(
            poll,
            'cron',
            minute='00,15,30,45',
            args=(influx_client, config['Data']),
        )
        scheduler.start()

        try:
            while True:
                time.sleep(1)
        except (KeyboardInterrupt, SystemExit):
            pass
        finally:
            scheduler.shutdown()
    finally:
        influx_client.close()


if __name__ == '__main__':
    main()
