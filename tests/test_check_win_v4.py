import unittest

from iqoptionapi.stable_api import IQ_Option


class TestCheckWinV4(unittest.TestCase):

    def test_check_win_v4_timeout_and_settled_results(self):
        api = IQ_Option("email", "password")

        class _FakeSocket:
            socket_option_closed = {
                1001: {"msg": {"win": "equal", "sum": "12.50", "win_amount": "12.50"}},
                1002: {"msg": {"win": "win", "sum": "8.00", "win_amount": "18.00"}},
                1003: {"msg": {"win": "loose", "sum": "5.00", "win_amount": "0"}},
            }

        api.api = _FakeSocket()

        self.assertEqual(api.check_win_v4(1001, timeout=1), (True, 0.0))
        self.assertEqual(api.check_win_v4(1002, timeout=1), (True, 10.0))
        self.assertEqual(api.check_win_v4(1003, timeout=1), (True, -5.0))

    def test_check_win_v4_pending_then_timeout(self):
        api = IQ_Option("email", "password")

        class _FakeSocket:
            socket_option_closed = {}

        api.api = _FakeSocket()
        self.assertEqual(api.check_win_v4(9999, timeout=1), (False, None))

    def test_check_win_v4_reads_option_closed_async_order(self):
        api = IQ_Option("email", "password")

        class _FakeSocket:
            socket_option_closed = {}
            order_async = {
                2001: {
                    "option-closed": {
                        "msg": {
                            "option_id": 2001,
                            "profit_amount": "18.00",
                            "amount": "8.00",
                        }
                    }
                }
            }

        api.api = _FakeSocket()
        self.assertEqual(api.check_win_v4(2001, timeout=1), (True, 10.0))

    def test_check_win_v4_accepts_socket_option_closed_string_key(self):
        api = IQ_Option("email", "password")

        class _FakeSocket:
            socket_option_closed = {
                "3001": {"msg": {"win": "win", "sum": "2.00", "win_amount": "3.64"}}
            }
            order_async = {}

        api.api = _FakeSocket()
        resolved, profit = api.check_win_v4(3001, timeout=1)
        self.assertTrue(resolved)
        self.assertAlmostEqual(profit, 1.64)

    def test_check_win_v4_loss_prefers_amount_over_large_sum(self):
        api = IQ_Option("email", "password")

        class _FakeSocket:
            socket_option_closed = {
                4001: {
                    "msg": {
                        "win": "loose",
                        "sum": "999999.15",
                        "amount": "1.00",
                        "win_amount": "0",
                    }
                }
            }
            order_async = {}

        api.api = _FakeSocket()

        resolved, profit = api.check_win_v4(4001, timeout=1)

        self.assertTrue(resolved)
        self.assertEqual(profit, -1.0)
