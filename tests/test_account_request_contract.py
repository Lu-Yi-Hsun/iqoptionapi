import unittest

import iqoptionapi.global_value as global_value
import iqoptionapi.stable_api as stable_api
from iqoptionapi.stable_api import IQ_Option


class _Profile:
    msg = None


class TestAccountRequestContract(unittest.TestCase):
    def setUp(self):
        global_value.balance_id = 10

    def test_get_leader_board_times_out(self):
        api = IQ_Option("email", "password")

        class _FakeApi:
            leaderboard_deals_client = None

            def Get_Leader_Board(self, *args):
                self.args = args

        api.api = _FakeApi()

        stable_api.Country.ID["TEST"] = 999

        self.assertIsNone(api.get_leader_board("TEST", 1, 2, 3, timeout=0.01))
        self.assertEqual(api.last_operation["name"], "get_leader_board")
        self.assertEqual(api.last_operation["status"], "timeout")

    def test_get_instruments_records_success(self):
        api = IQ_Option("email", "password")

        class _FakeApi:
            instruments = None

            def get_instruments(self, instrument_type):
                self.instruments = {"instruments": [{"type": instrument_type}]}

        api.api = _FakeApi()

        self.assertEqual(
            api.get_instruments("crypto", timeout=1),
            {"instruments": [{"type": "crypto"}]},
        )
        self.assertEqual(api.last_operation["name"], "get_instruments")
        self.assertEqual(api.last_operation["status"], "ok")

    def test_get_all_init_v2_times_out(self):
        api = IQ_Option("email", "password")

        class _FakeApi:
            api_option_init_all_result_v2 = None

            def get_api_option_init_all_v2(self):
                pass

        api.api = _FakeApi()

        self.assertIsNone(api.get_all_init_v2(timeout=0.01))
        self.assertEqual(api.last_operation["name"], "get_all_init_v2")
        self.assertEqual(api.last_operation["status"], "timeout")

    def test_get_profile_ansyc_times_out(self):
        api = IQ_Option("email", "password")

        class _FakeApi:
            profile = _Profile()

        api.api = _FakeApi()

        self.assertIsNone(api.get_profile_ansyc(timeout=0.01))
        self.assertEqual(api.last_operation["name"], "get_profile_ansyc")
        self.assertEqual(api.last_operation["status"], "timeout")

    def test_get_balances_records_success(self):
        api = IQ_Option("email", "password")

        class _FakeApi:
            balances_raw = None

            def get_balances(self):
                self.balances_raw = {"msg": [{"amount": 100}]}

        api.api = _FakeApi()

        self.assertEqual(api.get_balances(timeout=1), {"msg": [{"amount": 100}]})
        self.assertEqual(api.last_operation["name"], "get_balances")
        self.assertEqual(api.last_operation["status"], "ok")

    def test_reset_practice_balance_times_out(self):
        api = IQ_Option("email", "password")

        class _FakeApi:
            training_balance_reset_request = None

            def reset_training_balance(self):
                pass

        api.api = _FakeApi()

        self.assertIsNone(api.reset_practice_balance(timeout=0.01))
        self.assertEqual(api.last_operation["name"], "reset_practice_balance")
        self.assertEqual(api.last_operation["status"], "timeout")

    def test_get_balance_and_currency_handle_missing_balances(self):
        api = IQ_Option("email", "password")

        class _FakeApi:
            balances_raw = None

            def get_balances(self):
                pass

        api.api = _FakeApi()

        self.assertIsNone(api.get_balance(timeout=0.01))
        self.assertEqual(api.last_operation["name"], "get_balance")
        self.assertEqual(api.last_operation["reason"], "balances_timeout")

        self.assertIsNone(api.get_currency(timeout=0.01))
        self.assertEqual(api.last_operation["name"], "get_currency")
        self.assertEqual(api.last_operation["reason"], "balances_timeout")

    def test_get_balance_and_currency_record_success(self):
        api = IQ_Option("email", "password")

        class _FakeApi:
            balances_raw = None

            def get_balances(self):
                self.balances_raw = {
                    "msg": [
                        {"id": 10, "amount": 123.45, "currency": "USD"},
                    ]
                }

        api.api = _FakeApi()

        self.assertEqual(api.get_balance(timeout=1), 123.45)
        self.assertEqual(api.last_operation["name"], "get_balance")
        self.assertEqual(api.last_operation["status"], "ok")

        self.assertEqual(api.get_currency(timeout=1), "USD")
        self.assertEqual(api.last_operation["name"], "get_currency")
        self.assertEqual(api.last_operation["status"], "ok")

    def test_get_balance_mode_handles_missing_profile(self):
        api = IQ_Option("email", "password")

        class _FakeApi:
            profile = _Profile()

        api.api = _FakeApi()

        self.assertIsNone(api.get_balance_mode(timeout=0.01))
        self.assertEqual(api.last_operation["name"], "get_balance_mode")
        self.assertEqual(api.last_operation["reason"], "profile_timeout")

    def test_get_balance_mode_records_success(self):
        api = IQ_Option("email", "password")

        class _ProfileWithBalance:
            msg = {"balances": [{"id": 10, "type": 4}]}

        class _FakeApi:
            profile = _ProfileWithBalance()

        api.api = _FakeApi()

        self.assertEqual(api.get_balance_mode(timeout=1), "PRACTICE")
        self.assertEqual(api.last_operation["name"], "get_balance_mode")
        self.assertEqual(api.last_operation["status"], "ok")

    def test_change_balance_handles_missing_profile(self):
        api = IQ_Option("email", "password")

        class _FakeApi:
            profile = _Profile()

        api.api = _FakeApi()

        self.assertFalse(api.change_balance("PRACTICE", timeout=0.01))
        self.assertEqual(api.last_operation["name"], "change_balance")
        self.assertEqual(api.last_operation["reason"], "profile_timeout")

    def test_change_balance_rejects_invalid_mode_without_exit(self):
        api = IQ_Option("email", "password")

        class _ProfileWithBalance:
            msg = {"balances": [{"id": 10, "type": 4}]}

        class _FakeApi:
            profile = _ProfileWithBalance()

        api.api = _FakeApi()

        self.assertFalse(api.change_balance("BAD", timeout=1))
        self.assertEqual(api.last_operation["name"], "change_balance")
        self.assertEqual(api.last_operation["reason"], "invalid_mode")

    def test_change_balance_records_success(self):
        api = IQ_Option("email", "password")

        class _ProfileWithBalance:
            msg = {
                "balances": [
                    {"id": 11, "type": 1},
                    {"id": 22, "type": 4},
                ]
            }

        class _FakeApi:
            profile = _ProfileWithBalance()

            def __init__(self):
                self.portfolio_calls = []

            def portfolio(self, **kwargs):
                self.portfolio_calls.append(kwargs)

        fake = _FakeApi()
        api.api = fake

        self.assertTrue(api.change_balance("PRACTICE", timeout=1))
        self.assertEqual(global_value.balance_id, 22)
        self.assertEqual(api.last_operation["name"], "change_balance")
        self.assertEqual(api.last_operation["status"], "ok")
        self.assertTrue(fake.portfolio_calls)


if __name__ == "__main__":
    unittest.main()
