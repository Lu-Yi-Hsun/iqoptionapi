import unittest

import iqoptionapi.global_value as global_value
from iqoptionapi.ws.objects.candles import Candles
from iqoptionapi.stable_api import IQ_Option


class TestCandlesContract(unittest.TestCase):
    def setUp(self):
        global_value.check_websocket_if_connect = 1

    def test_get_candles_returns_sorted_rows(self):
        api = IQ_Option("email", "password")

        class _FakeApi:
            def __init__(self):
                self.candles = Candles()
                self.requests = []

            def getcandles(self, active_id, interval, count, endtime):
                self.requests.append((active_id, interval, count, endtime))
                self.candles.candles_data = [
                    {"from": 300, "open": 1.2, "close": 1.3},
                    {"from": 100, "open": 1.0, "close": 1.1},
                    {"from": 200, "open": 1.1, "close": 1.2},
                ]

        fake = _FakeApi()
        api.api = fake

        candles = api.get_candles("EURUSD-OTC", 60, 3, 999, timeout=1)

        self.assertEqual([candle["from"] for candle in candles], [100, 200, 300])
        self.assertEqual(len(fake.requests), 1)
        self.assertTrue(api.last_operation["payload"]["request_id"].startswith("candles-"))

    def test_get_candles_passes_request_id_when_supported(self):
        api = IQ_Option("email", "password")

        class _FakeApi:
            def __init__(self):
                self.candles = Candles()
                self.request_id = None

            def getcandles(self, active_id, interval, count, endtime, request_id=""):
                del active_id, interval, count, endtime
                self.request_id = request_id
                self.candles.candles_data = [{"from": 100, "open": 1.0, "close": 1.1}]

        fake = _FakeApi()
        api.api = fake

        api.get_candles("EURUSD-OTC", 60, 1, 999, timeout=1)

        self.assertTrue(fake.request_id.startswith("candles-"))
        self.assertEqual(api.last_operation["payload"]["request_id"], fake.request_id)

    def test_get_candles_normalizes_high_low_aliases_and_volume(self):
        api = IQ_Option("email", "password")

        class _FakeApi:
            def __init__(self):
                self.candles = Candles()

            def getcandles(self, active_id, interval, count, endtime):
                del active_id, interval, count, endtime
                self.candles.candles_data = [
                    {"from": 100, "open": 1.0, "close": 1.1, "max": 1.2, "min": 0.9},
                    {"from": 200, "open": 1.1, "close": 1.0, "high": 1.3, "low": 0.8},
                ]

        api.api = _FakeApi()

        candles = api.get_candles("EURUSD-OTC", 60, 2, 999, timeout=1)

        self.assertEqual(candles[0]["high"], 1.2)
        self.assertEqual(candles[0]["low"], 0.9)
        self.assertEqual(candles[0]["volume"], 0)
        self.assertEqual(candles[1]["max"], 1.3)
        self.assertEqual(candles[1]["min"], 0.8)
        self.assertEqual(candles[1]["volume"], 0)

    def test_get_candles_rejects_invalid_input_without_request(self):
        api = IQ_Option("email", "password")

        class _FakeApi:
            def __init__(self):
                self.candles = Candles()
                self.requests = []

            def getcandles(self, active_id, interval, count, endtime):
                self.requests.append((active_id, interval, count, endtime))

        fake = _FakeApi()
        api.api = fake

        self.assertEqual(api.get_candles("MISSING", 60, 3, 999, timeout=1), [])
        self.assertEqual(api.get_candles("EURUSD-OTC", 0, 3, 999, timeout=1), [])
        self.assertEqual(api.get_candles("EURUSD-OTC", 60, 0, 999, timeout=1), [])
        self.assertEqual(fake.requests, [])


if __name__ == "__main__":
    unittest.main()
