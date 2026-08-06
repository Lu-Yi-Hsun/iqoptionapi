import unittest
from collections import deque

from iqoptionapi.api import IQOptionAPI


class TestInstanceState(unittest.TestCase):
    def test_runtime_caches_are_not_class_level_mutables(self):
        mutable_runtime_attrs = (
            "socket_option_opened",
            "api_option_init_all_result",
            "api_option_init_all_result_v2",
            "instrument_quites_generated_data",
            "instrument_quotes_generated_raw_data",
            "instrument_quites_generated_timestamp",
            "order_async",
            "traders_mood",
            "live_deal_data",
            "subscribe_commission_changed_data",
            "real_time_candles",
            "real_time_candles_maxdict_table",
            "candle_generated_check",
            "candle_generated_all_size_check",
            "top_assets_updated_data",
            "buy_multi_option",
        )

        for attr in mutable_runtime_attrs:
            with self.subTest(attr=attr):
                self.assertNotIn(attr, IQOptionAPI.__dict__)

    def test_instances_do_not_share_closed_option_state(self):
        first = IQOptionAPI("iqoption.com", "first@example.test", "password")
        second = IQOptionAPI("iqoption.com", "second@example.test", "password")

        payload = {"msg": {"option_id": 1001, "profit_amount": "18", "amount": "8"}}
        first.socket_option_closed[1001] = payload
        first.order_async[1001]["option-closed"] = payload

        self.assertEqual(second.socket_option_closed, {})
        self.assertEqual(second.order_async[1001], {})

    def test_instances_do_not_share_candles_or_realtime_cache(self):
        first = IQOptionAPI("iqoption.com", "first@example.test", "password")
        second = IQOptionAPI("iqoption.com", "second@example.test", "password")

        first.candles.candles_data = [{"from": 1, "open": 1.0, "close": 1.1}]
        first.real_time_candles["EURUSD-OTC"][60][1] = {"from": 1}

        self.assertIsNone(second.candles.candles_data)
        self.assertEqual(second.real_time_candles["EURUSD-OTC"][60], {})

    def test_instances_do_not_share_runtime_result_caches(self):
        first = IQOptionAPI("iqoption.com", "first@example.test", "password")
        second = IQOptionAPI("iqoption.com", "second@example.test", "password")

        first.traders_mood["EURUSD-OTC"] = {"value": 51}
        first.live_deal_data["live-deal"]["EURUSD-OTC"]["turbo"].append({"id": 10})
        first.buy_multi_option["req-1"] = {"id": 10}
        first.top_assets_updated_data["EURUSD-OTC"] = {"profit": 90}
        first.result = True
        first.balances_raw = {"msg": [{"id": 1}]}
        first.user_profile_client = {"user_id": 1}

        self.assertEqual(second.traders_mood, {})
        self.assertEqual(second.live_deal_data["live-deal"]["EURUSD-OTC"]["turbo"], deque())
        self.assertEqual(second.buy_multi_option, {})
        self.assertEqual(second.top_assets_updated_data, {})
        self.assertIsNone(second.result)
        self.assertIsNone(second.balances_raw)
        self.assertIsNone(second.user_profile_client)

    def test_close_and_websocket_alive_are_safe_before_connect(self):
        api = IQOptionAPI("iqoption.com", "first@example.test", "password")

        api.close()

        self.assertFalse(api.websocket_alive())


if __name__ == "__main__":
    unittest.main()
