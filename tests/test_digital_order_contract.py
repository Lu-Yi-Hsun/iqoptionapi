import unittest

from iqoptionapi.api import nested_dict
from iqoptionapi.stable_api import IQ_Option


class TestDigitalOrderContract(unittest.TestCase):
    def test_buy_digital_times_out_with_sleep_and_diagnostics(self):
        api = IQ_Option("email", "password")

        class _FakeApi:
            digital_option_placed_id = None

            def place_digital_option(self, instrument_id, amount):
                del instrument_id, amount

        api.api = _FakeApi()

        self.assertEqual(api.buy_digital(1, "instrument", timeout=0.01), (False, None))
        self.assertEqual(api.last_operation["name"], "buy_digital")
        self.assertEqual(api.last_operation["status"], "timeout")

    def test_buy_digital_records_success(self):
        api = IQ_Option("email", "password")

        class _FakeApi:
            digital_option_placed_id = None

            def place_digital_option(self, instrument_id, amount):
                del instrument_id, amount
                self.digital_option_placed_id = 9001

        api.api = _FakeApi()

        self.assertEqual(api.buy_digital(1, "instrument", timeout=1), (True, 9001))
        self.assertEqual(api.last_operation["name"], "buy_digital")
        self.assertEqual(api.last_operation["status"], "ok")
        self.assertEqual(api.last_operation["payload"]["id"], 9001)

    def test_buy_digital_spot_rejects_invalid_action(self):
        api = IQ_Option("email", "password")

        self.assertEqual(api.buy_digital_spot("EURUSD", 1, "bad", 1, timeout=0.01), -1)
        self.assertEqual(api.last_operation["name"], "buy_digital_spot")
        self.assertEqual(api.last_operation["reason"], "invalid_action")

    def test_close_digital_option_times_out_waiting_for_position(self):
        api = IQ_Option("email", "password")

        class _FakeApi:
            result = None
            order_async = nested_dict(2, dict)

        api.api = _FakeApi()

        self.assertFalse(api.close_digital_option(9001, timeout=0.01))
        self.assertEqual(api.last_operation["name"], "close_digital_option")
        self.assertEqual(api.last_operation["reason"], "position_changed_timeout")

    def test_close_digital_option_records_success(self):
        api = IQ_Option("email", "password")

        class _FakeApi:
            def __init__(self):
                self.result = None
                self.closed_external_id = None
                self.order_async = nested_dict(2, dict)
                self.order_async[9001]["position-changed"] = {
                    "msg": {"external_id": "external-9001"}
                }

            def close_digital_option(self, external_id):
                self.closed_external_id = external_id
                self.result = True

        fake = _FakeApi()
        api.api = fake

        self.assertTrue(api.close_digital_option(9001, timeout=1))
        self.assertEqual(fake.closed_external_id, "external-9001")
        self.assertEqual(api.last_operation["name"], "close_digital_option")
        self.assertEqual(api.last_operation["status"], "ok")

    def test_check_win_digital_times_out(self):
        api = IQ_Option("email", "password")

        def get_digital_position(order_id, timeout=10):
            del order_id, timeout
            return None

        api.get_digital_position = get_digital_position

        self.assertIsNone(api.check_win_digital(9001, polling_time=0, timeout=0.01))
        self.assertEqual(api.last_operation["name"], "check_win_digital")
        self.assertEqual(api.last_operation["reason"], "timeout")

    def test_check_win_digital_records_expired_profit(self):
        api = IQ_Option("email", "password")

        def get_digital_position(order_id, timeout=10):
            del order_id, timeout
            return {
                "msg": {
                    "position": {
                        "status": "closed",
                        "close_reason": "expired",
                        "pnl_realized": 18.0,
                        "buy_amount": 10.0,
                    }
                }
            }

        api.get_digital_position = get_digital_position

        self.assertEqual(api.check_win_digital(9001, polling_time=0, timeout=1), 8.0)
        self.assertEqual(api.last_operation["name"], "check_win_digital")
        self.assertEqual(api.last_operation["status"], "resolved")

    def test_check_win_digital_v2_times_out(self):
        api = IQ_Option("email", "password")

        class _FakeApi:
            order_async = nested_dict(2, dict)

        api.api = _FakeApi()

        self.assertEqual(api.check_win_digital_v2(9001, timeout=0.01), (False, None))
        self.assertEqual(api.last_operation["name"], "check_win_digital_v2")
        self.assertEqual(api.last_operation["reason"], "timeout")

    def test_check_win_digital_v2_records_default_profit(self):
        api = IQ_Option("email", "password")

        class _FakeApi:
            def __init__(self):
                self.order_async = nested_dict(2, dict)
                self.order_async[9001]["position-changed"] = {
                    "msg": {
                        "status": "closed",
                        "close_reason": "default",
                        "pnl_realized": 7.25,
                    }
                }

        api.api = _FakeApi()

        self.assertEqual(api.check_win_digital_v2(9001, timeout=1), (True, 7.25))
        self.assertEqual(api.last_operation["name"], "check_win_digital_v2")
        self.assertEqual(api.last_operation["status"], "resolved")

    def test_get_digital_spot_profit_after_sale_times_out_waiting_position(self):
        api = IQ_Option("email", "password")

        class _FakeApi:
            order_async = nested_dict(2, dict)

        api.api = _FakeApi()

        self.assertIsNone(api.get_digital_spot_profit_after_sale(9001, timeout=0.01))
        self.assertEqual(api.last_operation["name"], "get_digital_spot_profit_after_sale")
        self.assertEqual(api.last_operation["reason"], "position_changed_timeout")

    def test_get_digital_spot_profit_after_sale_records_profit(self):
        api = IQ_Option("email", "password")

        class _FakeApi:
            def __init__(self):
                self.order_async = nested_dict(2, dict)
                self.instrument_quotes_generated_raw_data = nested_dict(2, dict)
                self.order_async[9001]["position-changed"] = {
                    "msg": {
                        "instrument_id": "doEURUSD201911040628PT1MPSPT",
                        "raw_event": {
                            "instrument_underlying": "EURUSD",
                            "buy_amount": 10.0,
                            "sell_amount": 0.0,
                            "count": 1,
                            "instrument_strike_value": 1000000,
                            "extra_data": {
                                "lower_instrument_strike": 1000000,
                                "upper_instrument_strike": 1000000,
                                "lower_instrument_id": "lower-id",
                                "upper_instrument_id": "upper-id",
                            },
                            "currency_rate": 1,
                        },
                    }
                }
                self.instrument_quotes_generated_raw_data["EURUSD"][60] = {
                    "msg": {
                        "quotes": [
                            {"symbols": ["lower-id"], "price": {"bid": 4.0}},
                            {"symbols": ["upper-id"], "price": {"bid": 5.0}},
                        ]
                    }
                }

        api.api = _FakeApi()

        self.assertEqual(api.get_digital_spot_profit_after_sale(9001, timeout=1), -6.0)
        self.assertEqual(api.last_operation["name"], "get_digital_spot_profit_after_sale")
        self.assertEqual(api.last_operation["status"], "ok")


if __name__ == "__main__":
    unittest.main()
