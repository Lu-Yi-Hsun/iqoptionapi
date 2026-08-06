import time
import unittest

from iqoptionapi.stable_api import IQ_Option


class TestOpenTimeContract(unittest.TestCase):
    def test_get_all_open_time_returns_none_when_binary_init_times_out(self):
        api = IQ_Option("email", "password")
        api.get_all_init_v2 = lambda timeout=30: None

        self.assertIsNone(api.get_all_open_time(timeout=0.01))
        self.assertEqual(api.last_operation["name"], "get_all_open_time")
        self.assertEqual(api.last_operation["reason"], "binary_init_timeout")

    def test_get_all_open_time_returns_none_when_digital_underlying_times_out(self):
        api = IQ_Option("email", "password")
        api.get_all_init_v2 = lambda timeout=30: {
            "binary": {"actives": {}},
            "turbo": {"actives": {}},
        }
        api.get_digital_underlying_list_data = lambda timeout=30: None

        self.assertIsNone(api.get_all_open_time(timeout=0.01))
        self.assertEqual(api.last_operation["name"], "get_all_open_time")
        self.assertEqual(api.last_operation["reason"], "digital_underlying_timeout")

    def test_get_all_open_time_records_success(self):
        api = IQ_Option("email", "password")
        now = time.time()
        api.get_all_init_v2 = lambda timeout=30: {
            "binary": {
                "actives": {
                    "76": {
                        "name": "front.EURUSD",
                        "enabled": True,
                        "is_suspended": False,
                    }
                }
            },
            "turbo": {"actives": {}},
        }
        api.get_digital_underlying_list_data = lambda timeout=30: {
            "underlying": [
                {
                    "underlying": "EURUSD",
                    "schedule": [{"open": now - 1, "close": now + 1}],
                }
            ]
        }
        api.get_instruments = lambda instrument_type, timeout=30: {
            "instruments": [
                {
                    "name": instrument_type.upper(),
                    "schedule": [{"open": now - 1, "close": now + 1}],
                }
            ]
        }

        open_time = api.get_all_open_time(timeout=1)

        self.assertTrue(open_time["binary"]["EURUSD"]["open"])
        self.assertTrue(open_time["digital"]["EURUSD"]["open"])
        self.assertTrue(open_time["crypto"]["CRYPTO"]["open"])
        self.assertEqual(api.last_operation["name"], "get_all_open_time")
        self.assertEqual(api.last_operation["status"], "ok")

    def test_get_all_open_time_tolerates_digital_response_without_underlying(self):
        api = IQ_Option("email", "password")
        now = time.time()
        api.get_all_init_v2 = lambda timeout=30: {
            "binary": {
                "actives": {
                    "76": {
                        "name": "front.EURUSD-OTC",
                        "enabled": True,
                        "is_suspended": False,
                    }
                }
            },
            "turbo": {"actives": {}},
        }
        api.get_digital_underlying_list_data = lambda timeout=30: {"message": "partial"}
        api.get_instruments = lambda instrument_type, timeout=30: {
            "instruments": [
                {
                    "name": instrument_type.upper(),
                    "schedule": [{"open": now - 1, "close": now + 1}],
                }
            ]
        }

        open_time = api.get_all_open_time(timeout=1)

        self.assertTrue(open_time["binary"]["EURUSD-OTC"]["open"])
        self.assertEqual(api.last_operation["name"], "get_all_open_time")
        self.assertEqual(api.last_operation["status"], "ok")
        self.assertEqual(api.last_operation["payload"]["digital_status"], "missing_underlying")


if __name__ == "__main__":
    unittest.main()
