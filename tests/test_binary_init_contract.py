import unittest

from iqoptionapi.stable_api import IQ_Option


def _init_payload():
    return {
        "result": {
            "turbo": {
                "actives": {
                    "76": {
                        "name": "front.EURUSD",
                        "option": {"profit": {"commission": 15}},
                    }
                }
            },
            "binary": {
                "actives": {
                    "77": {
                        "name": "front.GBPUSD",
                        "option": {"profit": {"commission": 20}},
                    }
                }
            },
        }
    }


class TestBinaryInitContract(unittest.TestCase):
    def test_get_binary_option_detail_handles_init_timeout(self):
        api = IQ_Option("email", "password")
        api.get_all_init = lambda timeout=30: None

        self.assertIsNone(api.get_binary_option_detail(timeout=0.01))
        self.assertEqual(api.last_operation["name"], "get_binary_option_detail")
        self.assertEqual(api.last_operation["reason"], "init_timeout")

    def test_get_binary_option_detail_records_success(self):
        api = IQ_Option("email", "password")
        api.get_all_init = lambda timeout=30: _init_payload()

        detail = api.get_binary_option_detail(timeout=1)

        self.assertEqual(detail["EURUSD"]["turbo"]["name"], "front.EURUSD")
        self.assertEqual(detail["GBPUSD"]["binary"]["name"], "front.GBPUSD")
        self.assertEqual(api.last_operation["name"], "get_binary_option_detail")
        self.assertEqual(api.last_operation["status"], "ok")

    def test_get_all_profit_handles_init_timeout(self):
        api = IQ_Option("email", "password")
        api.get_all_init = lambda timeout=30: None

        self.assertIsNone(api.get_all_profit(timeout=0.01))
        self.assertEqual(api.last_operation["name"], "get_all_profit")
        self.assertEqual(api.last_operation["reason"], "init_timeout")

    def test_get_all_profit_records_success(self):
        api = IQ_Option("email", "password")
        api.get_all_init = lambda timeout=30: _init_payload()

        profit = api.get_all_profit(timeout=1)

        self.assertEqual(profit["EURUSD"]["turbo"], 0.85)
        self.assertEqual(profit["GBPUSD"]["binary"], 0.8)
        self.assertEqual(api.last_operation["name"], "get_all_profit")
        self.assertEqual(api.last_operation["status"], "ok")


if __name__ == "__main__":
    unittest.main()
