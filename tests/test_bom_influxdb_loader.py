import pytest
import yaml
from unittest.mock import MagicMock, patch

import bom_influxdb_loader as loader


class TestLoadYamlFile:
    def test_loads_valid_yaml(self, tmp_path):
        config = {'InfluxDb': {'Host': 'localhost', 'Port': '8086'}}
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump(config))

        result = loader.load_yaml_file(str(config_file))

        assert result == config

    def test_exits_on_missing_file(self, tmp_path):
        with pytest.raises(SystemExit):
            loader.load_yaml_file(str(tmp_path / "nonexistent.yaml"))


class TestPoll:
    def _make_obs(self, air_temp="20.5", rainfall="1.2", period="2024-01-01T12:00:00"):
        obs = MagicMock()
        obs.air_temperature.return_value = air_temp
        obs.rainfall.return_value = rainfall
        obs.period_attribute.return_value = period
        return obs

    def _make_data(self, stations=None):
        if stations is None:
            stations = [{'name': 'Bellambi', 'id': '94749'}]
        return [{'state': 'NSW', 'stations': stations}]

    def test_sends_metrics_for_each_station(self):
        influx = MagicMock()
        influx.write_points.return_value = True
        data = self._make_data(stations=[
            {'name': 'Bellambi', 'id': '94749'},
            {'name': 'Sydney', 'id': '94768'},
        ])
        with patch('bom_influxdb_loader.observations.Observations', return_value=self._make_obs()):
            loader.poll(influx, data)

        points = influx.write_points.call_args[0][0]
        assert len(points) == 2
        assert points[0]['tags']['Location'] == 'Bellambi'
        assert points[1]['tags']['Location'] == 'Sydney'

    def test_fields_are_floats(self):
        influx = MagicMock()
        influx.write_points.return_value = True
        with patch('bom_influxdb_loader.observations.Observations', return_value=self._make_obs(air_temp="22.3", rainfall="0.4")):
            loader.poll(influx, self._make_data())

        points = influx.write_points.call_args[0][0]
        assert isinstance(points[0]['fields']['air_temp'], float)
        assert isinstance(points[0]['fields']['rainfall_9am'], float)
        assert points[0]['fields']['air_temp'] == 22.3
        assert points[0]['fields']['rainfall_9am'] == 0.4

    def test_skips_write_when_observations_is_none(self):
        influx = MagicMock()
        with patch('bom_influxdb_loader.observations.Observations', return_value=None):
            loader.poll(influx, self._make_data())

        influx.write_points.assert_not_called()

    def test_skips_write_when_no_stations(self):
        influx = MagicMock()
        with patch('bom_influxdb_loader.observations.Observations', return_value=self._make_obs()):
            loader.poll(influx, self._make_data(stations=[]))

        influx.write_points.assert_not_called()

    def test_measurement_name_and_tags(self):
        influx = MagicMock()
        influx.write_points.return_value = True
        with patch('bom_influxdb_loader.observations.Observations', return_value=self._make_obs(period="2024-06-01T09:00:00")):
            loader.poll(influx, self._make_data())

        point = influx.write_points.call_args[0][0][0]
        assert point['measurement'] == 'weather'
        assert point['tags']['id'] == '94749'
        assert point['time'] == "2024-06-01T09:00:00"

    def test_polls_multiple_states(self):
        influx = MagicMock()
        influx.write_points.return_value = True
        data = [
            {'state': 'NSW', 'stations': [{'name': 'Bellambi', 'id': '94749'}]},
            {'state': 'VIC', 'stations': [{'name': 'Melbourne', 'id': '95936'}]},
        ]
        with patch('bom_influxdb_loader.observations.Observations', return_value=self._make_obs()):
            loader.poll(influx, data)

        assert influx.write_points.call_count == 2

    def test_skips_station_with_missing_air_temp(self):
        influx = MagicMock()
        data = self._make_data(stations=[
            {'name': 'Bellambi', 'id': '94749'},
            {'name': 'Sydney', 'id': '94768'},
        ])
        obs = self._make_obs()
        obs.air_temperature.side_effect = lambda wmo_id: None if wmo_id == '94749' else "20.5"
        with patch('bom_influxdb_loader.observations.Observations', return_value=obs):
            loader.poll(influx, data)

        points = influx.write_points.call_args[0][0]
        assert len(points) == 1
        assert points[0]['tags']['Location'] == 'Sydney'

    def test_skips_station_with_missing_rainfall(self):
        influx = MagicMock()
        obs = self._make_obs(rainfall=None)
        with patch('bom_influxdb_loader.observations.Observations', return_value=obs):
            loader.poll(influx, self._make_data())

        influx.write_points.assert_not_called()

    def test_influx_client_closed_after_scheduler_exception(self):
        """InfluxDB client is closed in the finally block even when an exception occurs."""
        influx = MagicMock()
        influx.create_database.side_effect = RuntimeError("connection refused")

        with pytest.raises(RuntimeError):
            with patch('bom_influxdb_loader.load_yaml_file', return_value={
                'InfluxDb': {'Host': 'localhost', 'Port': '8086', 'Database': 'test'},
                'Data': [],
            }):
                with patch('bom_influxdb_loader.InfluxDBClient', return_value=influx):
                    with patch('bom_influxdb_loader.time.sleep'):
                        with patch('bom_influxdb_loader.get_args') as mock_args:
                            mock_args.return_value.config = '/config/config.yaml'
                            loader.main()

        influx.close.assert_called_once()
