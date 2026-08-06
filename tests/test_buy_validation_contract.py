import unittest

from iqoptionapi.stable_api import IQ_Option


class TestBuyValidationContract(unittest.TestCase):
    def test_buy_rejects_invalid_active_without_request(self):
        api = IQ_Option("email", "password")

        class _FakeApi:
            def buyv3(self, price, active, direction, expirations, request_id):
                raise AssertionError("buyv3 should not be called")

        api.api = _FakeApi()

        self.assertEqual(api.buy(1, "MISSING", "call", 1, timeout=0.01), (False, None))
        self.assertEqual(api.last_operation["name"], "buy")
        self.assertEqual(api.last_operation["status"], "rejected")
        self.assertEqual(api.last_operation["reason"], "invalid_active")

    def test_buy_uses_timeout_parameter(self):
        api = IQ_Option("email", "password")

        class _FakeApi:
            def __init__(self):
                self.buy_multi_option = {}
                self.buy_successful = None
                self.result = None

            def buyv3(self, price, active, direction, expirations, request_id):
                del price, active, direction, expirations, request_id

        api.api = _FakeApi()

        self.assertEqual(api.buy(1, "EURUSD-OTC", "call", 1, timeout=0.01), (False, None))
        self.assertEqual(api.last_operation["name"], "buy")
        self.assertEqual(api.last_operation["status"], "timeout")
        self.assertEqual(api.last_operation["payload"]["timeout"], 0.01)

    def test_buy_rejects_invalid_timeout_without_request(self):
        api = IQ_Option("email", "password")

        class _FakeApi:
            def buyv3(self, price, active, direction, expirations, request_id):
                raise AssertionError("buyv3 should not be called")

        api.api = _FakeApi()

        self.assertEqual(api.buy(1, "EURUSD-OTC", "call", 1, timeout="bad"), (False, None))
        self.assertEqual(api.last_operation["name"], "buy")
        self.assertEqual(api.last_operation["status"], "rejected")
        self.assertEqual(api.last_operation["reason"], "invalid_timeout")

    def test_buy_by_raw_expirations_rejects_invalid_active_without_request(self):
        api = IQ_Option("email", "password")

        class _FakeApi:
            def buyv3_by_raw_expired(
                self,
                price,
                active,
                direction,
                option,
                expired,
                request_id,
            ):
                raise AssertionError("buyv3_by_raw_expired should not be called")

        api.api = _FakeApi()

        self.assertEqual(
            api.buy_by_raw_expirations(
                1,
                "MISSING",
                "call",
                "turbo",
                123456,
                timeout=0.01,
            ),
            (False, None),
        )
        self.assertEqual(api.last_operation["name"], "buy_by_raw_expirations")
        self.assertEqual(api.last_operation["status"], "rejected")
        self.assertEqual(api.last_operation["reason"], "invalid_active")

    def test_buy_by_raw_expirations_uses_timeout_parameter(self):
        api = IQ_Option("email", "password")

        class _FakeApi:
            def __init__(self):
                self.buy_multi_option = {}
                self.buy_successful = None
                self.result = None

            def buyv3_by_raw_expired(
                self,
                price,
                active,
                direction,
                option,
                expired,
                request_id,
            ):
                del price, active, direction, option, expired, request_id

        api.api = _FakeApi()

        self.assertEqual(
            api.buy_by_raw_expirations(
                1,
                "EURUSD-OTC",
                "call",
                "turbo",
                123456,
                timeout=0.01,
            ),
            (False, None),
        )
        self.assertEqual(api.last_operation["name"], "buy_by_raw_expirations")
        self.assertEqual(api.last_operation["status"], "timeout")
        self.assertEqual(api.last_operation["payload"]["timeout"], 0.01)

    def test_buy_by_raw_expirations_rejects_invalid_timeout_without_request(self):
        api = IQ_Option("email", "password")

        class _FakeApi:
            def buyv3_by_raw_expired(
                self,
                price,
                active,
                direction,
                option,
                expired,
                request_id,
            ):
                raise AssertionError("buyv3_by_raw_expired should not be called")

        api.api = _FakeApi()

        self.assertEqual(
            api.buy_by_raw_expirations(
                1,
                "EURUSD-OTC",
                "call",
                "turbo",
                123456,
                timeout="bad",
            ),
            (False, None),
        )
        self.assertEqual(api.last_operation["name"], "buy_by_raw_expirations")
        self.assertEqual(api.last_operation["status"], "rejected")
        self.assertEqual(api.last_operation["reason"], "invalid_timeout")


if __name__ == "__main__":
    unittest.main()
