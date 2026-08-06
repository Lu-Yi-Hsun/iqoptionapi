import unittest

import iqoptionapi.constants as OP_code
from iqoptionapi.api import nested_dict
from iqoptionapi.stable_api import IQ_Option


class TestCandleStreamContract(unittest.TestCase):
    def test_stop_one_candle_stream_returns_status_and_unsubscribes(self):
        api = IQ_Option("email", "password")
        api.suspend = 0
        api.subscribe_candle.append("EURUSD-OTC,60")

        class _FakeApi:
            def __init__(self):
                self.candle_generated_check = nested_dict(2, dict)
                self.unsubscribed = []

            def unsubscribe(self, active_id, size):
                self.unsubscribed.append((active_id, size))

        fake = _FakeApi()
        fake.candle_generated_check["EURUSD-OTC"][60] = True
        api.api = fake

        self.assertTrue(api.stop_candles_one_stream("EURUSD-OTC", 60, timeout=1))
        self.assertNotIn("EURUSD-OTC,60", api.subscribe_candle)
        self.assertEqual(fake.unsubscribed, [(OP_code.ACTIVES["EURUSD-OTC"], 60)])
        self.assertEqual(api.last_operation["name"], "stop_candles_one_stream")
        self.assertEqual(api.last_operation["status"], "ok")

    def test_stop_all_candle_stream_returns_status_and_unsubscribes(self):
        api = IQ_Option("email", "password")
        api.suspend = 0
        api.subscribe_candle_all_size.append("EURUSD-OTC")

        class _FakeApi:
            def __init__(self):
                self.candle_generated_all_size_check = nested_dict(1, dict)
                self.unsubscribed = []

            def unsubscribe_all_size(self, active_id):
                self.unsubscribed.append(active_id)

        fake = _FakeApi()
        fake.candle_generated_all_size_check["EURUSD-OTC"] = True
        api.api = fake

        self.assertTrue(api.stop_candles_all_size_stream("EURUSD-OTC", timeout=1))
        self.assertNotIn("EURUSD-OTC", api.subscribe_candle_all_size)
        self.assertEqual(fake.unsubscribed, [OP_code.ACTIVES["EURUSD-OTC"]])
        self.assertEqual(api.last_operation["name"], "stop_candles_all_size_stream")
        self.assertEqual(api.last_operation["status"], "ok")

    def test_stop_candle_stream_rejects_invalid_input(self):
        api = IQ_Option("email", "password")

        self.assertFalse(api.stop_candles_stream("EURUSD-OTC", 999))
        self.assertEqual(api.last_operation["reason"], "invalid_size")
        self.assertFalse(api.stop_candles_one_stream("MISSING", 60, timeout=0.01))
        self.assertEqual(api.last_operation["reason"], "invalid_active")
        self.assertFalse(api.stop_candles_all_size_stream("MISSING", timeout=0.01))
        self.assertEqual(api.last_operation["reason"], "invalid_active")


if __name__ == "__main__":
    unittest.main()
