import unittest

from iqoptionapi.stable_api import IQ_Option


class TestDigitalOrderResilienceContract(unittest.TestCase):
    def test_buy_digital_spot_accepts_string_order_id(self):
        api = IQ_Option("email", "password")

        class _Timesync:
            server_timestamp = 1700000000

        class _FakeApi:
            def __init__(self):
                self.timesync = _Timesync()
                self.digital_option_placed_id = None

            def place_digital_option(self, instrument_id, amount):
                del instrument_id, amount
                self.digital_option_placed_id = "digital-9001"

        api.api = _FakeApi()

        self.assertEqual(
            api.buy_digital_spot("EURUSD", 1, "call", 1, timeout=1),
            (True, "digital-9001"),
        )
        self.assertEqual(api.last_operation["name"], "buy_digital_spot")
        self.assertEqual(api.last_operation["status"], "ok")
        self.assertEqual(api.last_operation["payload"]["id"], "digital-9001")

    def test_buy_digital_spot_rejects_invalid_timeout_without_request(self):
        api = IQ_Option("email", "password")

        class _FakeApi:
            def place_digital_option(self, instrument_id, amount):
                raise AssertionError("place_digital_option should not be called")

        api.api = _FakeApi()

        self.assertEqual(
            api.buy_digital_spot("EURUSD", 1, "call", 1, timeout="bad"),
            (False, None),
        )
        self.assertEqual(api.last_operation["name"], "buy_digital_spot")
        self.assertEqual(api.last_operation["status"], "rejected")
        self.assertEqual(api.last_operation["reason"], "invalid_timeout")

    def test_check_win_v4_rejects_invalid_timeout(self):
        api = IQ_Option("email", "password")

        class _FakeApi:
            socket_option_closed = {}
            order_async = {}

        api.api = _FakeApi()

        self.assertEqual(api.check_win_v4(9001, timeout="bad"), (False, None))
        self.assertEqual(api.last_operation["name"], "check_win_v4")
        self.assertEqual(api.last_operation["status"], "rejected")
        self.assertEqual(api.last_operation["reason"], "invalid_timeout")

    def test_check_win_digital_v2_rejects_invalid_timeout(self):
        api = IQ_Option("email", "password")

        class _FakeApi:
            order_async = {}

        api.api = _FakeApi()

        self.assertEqual(api.check_win_digital_v2(9001, timeout="bad"), (False, None))
        self.assertEqual(api.last_operation["name"], "check_win_digital_v2")
        self.assertEqual(api.last_operation["status"], "rejected")
        self.assertEqual(api.last_operation["reason"], "invalid_timeout")


if __name__ == "__main__":
    unittest.main()
