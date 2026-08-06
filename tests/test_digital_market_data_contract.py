import unittest

from iqoptionapi.api import nested_dict
from iqoptionapi.stable_api import IQ_Option


class TestDigitalMarketDataContract(unittest.TestCase):
    def test_get_digital_underlying_times_out(self):
        api = IQ_Option("email", "password")

        class _FakeApi:
            underlying_list_data = None

            def get_digital_underlying(self):
                pass

        api.api = _FakeApi()

        self.assertIsNone(api.get_digital_underlying_list_data(timeout=0.01))
        self.assertEqual(api.last_operation["name"], "get_digital_underlying_list_data")
        self.assertEqual(api.last_operation["status"], "timeout")

    def test_get_digital_underlying_records_success(self):
        api = IQ_Option("email", "password")

        class _FakeApi:
            underlying_list_data = None

            def get_digital_underlying(self):
                self.underlying_list_data = {"underlying": []}

        api.api = _FakeApi()

        self.assertEqual(api.get_digital_underlying_list_data(timeout=1), {"underlying": []})
        self.assertEqual(api.last_operation["name"], "get_digital_underlying_list_data")
        self.assertEqual(api.last_operation["status"], "ok")

    def test_get_instrument_quotes_generated_data_times_out(self):
        api = IQ_Option("email", "password")

        class _FakeApi:
            instrument_quotes_generated_raw_data = nested_dict(2, dict)

        api.api = _FakeApi()

        self.assertIsNone(
            api.get_instrument_quites_generated_data("EURUSD", 1, timeout=0.01)
        )
        self.assertEqual(api.last_operation["name"], "get_instrument_quites_generated_data")
        self.assertEqual(api.last_operation["status"], "timeout")

    def test_get_instrument_quotes_generated_data_records_success(self):
        api = IQ_Option("email", "password")

        class _FakeApi:
            instrument_quotes_generated_raw_data = nested_dict(2, dict)

        api.api = _FakeApi()
        api.api.instrument_quotes_generated_raw_data["EURUSD"][60] = {"msg": "ok"}

        self.assertEqual(
            api.get_instrument_quites_generated_data("EURUSD", 1, timeout=1),
            {"msg": "ok"},
        )
        self.assertEqual(api.last_operation["name"], "get_instrument_quites_generated_data")
        self.assertEqual(api.last_operation["status"], "ok")

    def test_get_realtime_strike_list_times_out_waiting_quotes(self):
        api = IQ_Option("email", "password")

        class _FakeApi:
            instrument_quites_generated_data = nested_dict(2, dict)
            instrument_quites_generated_timestamp = nested_dict(2, dict)

        api.api = _FakeApi()

        self.assertIsNone(api.get_realtime_strike_list("EURUSD", 1, timeout=0.01))
        self.assertEqual(api.last_operation["name"], "get_realtime_strike_list")
        self.assertEqual(api.last_operation["reason"], "quotes_timeout")

    def test_get_realtime_strike_list_records_success(self):
        api = IQ_Option("email", "password")

        class _FakeApi:
            instrument_quites_generated_data = nested_dict(2, dict)
            instrument_quites_generated_timestamp = nested_dict(2, dict)

        api.api = _FakeApi()
        api.api.instrument_quites_generated_data["EURUSD"][60] = {
            "call-id": 50,
            "put-id": 40,
        }
        api.api.instrument_quites_generated_timestamp["EURUSD"][60] = 123
        api.get_realtime_strike_list_temp_data = {
            "1.234567": {"call": "call-id", "put": "put-id"}
        }
        api.get_realtime_strike_list_temp_expiration = 123

        self.assertEqual(
            api.get_realtime_strike_list("EURUSD", 1, timeout=1),
            {
                "1.234567": {
                    "call": {"profit": 50, "id": "call-id"},
                    "put": {"profit": 40, "id": "put-id"},
                }
            },
        )
        self.assertEqual(api.last_operation["name"], "get_realtime_strike_list")
        self.assertEqual(api.last_operation["status"], "ok")


if __name__ == "__main__":
    unittest.main()
