import sys
import os
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

# weather_au is only available inside Docker; stub it so tests can run locally
weather_au_mock = MagicMock()
sys.modules.setdefault('weather_au', weather_au_mock)
sys.modules.setdefault('weather_au.observations', weather_au_mock.observations)
