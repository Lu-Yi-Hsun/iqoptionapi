import unittest

from iqoptionapi.stable_api import IQ_Option


class TestOptionRequestContract(unittest.TestCase):
    def test_get_optioninfo_times_out(self):
        api = IQ_Option("email", "password")

        class _FakeApi:
            api_game_getoptions_result = None

            def get_options(self, limit):
                del limit

        api.api = _FakeApi()

        self.assertIsNone(api.get_optioninfo(10, timeout=0.01))
        self.assertEqual(api.last_operation["name"], "get_optioninfo")
        self.assertEqual(api.last_operation["status"], "timeout")

    def test_get_optioninfo_v2_records_success(self):
        api = IQ_Option("email", "password")

        class _FakeApi:
            get_options_v2_data = None

            def get_options_v2(self, limit, instrument_types):
                del limit, instrument_types
                self.get_options_v2_data = {"msg": "ok"}

        api.api = _FakeApi()

        self.assertEqual(api.get_optioninfo_v2(10, timeout=1), {"msg": "ok"})
        self.assertEqual(api.last_operation["name"], "get_optioninfo_v2")
        self.assertEqual(api.last_operation["status"], "ok")

    def test_sell_option_clears_before_send_and_records_success(self):
        api = IQ_Option("email", "password")

        class _FakeApi:
            sold_options_respond = {"stale": True}

            def sell_option(self, options_ids):
                self.seen_ids = options_ids
                self.sold_options_respond = {"sold": options_ids}

        fake = _FakeApi()
        api.api = fake

        self.assertEqual(api.sell_option([1, 2], timeout=1), {"sold": [1, 2]})
        self.assertEqual(fake.seen_ids, [1, 2])
        self.assertEqual(api.last_operation["name"], "sell_option")
        self.assertEqual(api.last_operation["status"], "ok")

    def test_get_strike_list_timeout_and_success_contract(self):
        api = IQ_Option("email", "password")

        class _TimeoutApi:
            strike_list = None

            def get_strike_list(self, active, duration):
                del active, duration

        api.api = _TimeoutApi()

        self.assertEqual(api.get_strike_list("EURUSD", 1, timeout=0.01), (None, None))
        self.assertEqual(api.last_operation["name"], "get_strike_list")
        self.assertEqual(api.last_operation["status"], "timeout")

        class _SuccessApi:
            strike_list = None

            def get_strike_list(self, active, duration):
                del active, duration
                self.strike_list = {
                    "msg": {
                        "strike": [
                            {
                                "value": 1234567,
                                "call": {"id": "call-id"},
                                "put": {"id": "put-id"},
                            }
                        ]
                    }
                }

        api.api = _SuccessApi()

        raw, strike = api.get_strike_list("EURUSD", 1, timeout=1)
        self.assertEqual(raw["msg"]["strike"][0]["call"]["id"], "call-id")
        self.assertEqual(strike["1.234567"], {"call": "call-id", "put": "put-id"})
        self.assertEqual(api.last_operation["name"], "get_strike_list")
        self.assertEqual(api.last_operation["status"], "ok")


if __name__ == "__main__":
    unittest.main()
