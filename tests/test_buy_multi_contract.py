import unittest

from iqoptionapi.stable_api import IQ_Option


class TestBuyMultiContract(unittest.TestCase):
    def test_buy_multi_uses_unique_request_ids_and_preserves_order(self):
        api = IQ_Option("email", "password")

        class _FakeApi:
            def __init__(self):
                self.buy_multi_option = {}
                self.calls = []

            def buyv3(self, price, active_id, action, expiration, request_id):
                self.calls.append((price, active_id, action, expiration, request_id))
                self.buy_multi_option[request_id] = {"id": 9000 + len(self.calls)}

        fake = _FakeApi()
        api.api = fake

        ids = api.buy_multi(
            [1, 2],
            ["EURUSD-OTC", "EURUSD-OTC"],
            ["call", "put"],
            [1, 1],
            timeout=1,
        )

        self.assertEqual(ids, [9001, 9002])
        self.assertEqual(len(fake.calls), 2)
        self.assertNotEqual(fake.calls[0][4], fake.calls[1][4])
        self.assertTrue(fake.calls[0][4].startswith("buymulti-"))
        self.assertEqual(api.last_operation["name"], "buy_multi")
        self.assertEqual(api.last_operation["status"], "ok")

    def test_buy_multi_times_out_with_diagnostics(self):
        api = IQ_Option("email", "password")

        class _FakeApi:
            def __init__(self):
                self.buy_multi_option = {}

            def buyv3(self, price, active_id, action, expiration, request_id):
                del price, active_id, action, expiration, request_id

        api.api = _FakeApi()

        self.assertEqual(
            api.buy_multi([1], ["EURUSD-OTC"], ["call"], [1], timeout=0.01),
            [None],
        )
        self.assertEqual(api.last_operation["name"], "buy_multi")
        self.assertEqual(api.last_operation["status"], "timeout")

    def test_buy_multi_rejects_invalid_lengths(self):
        api = IQ_Option("email", "password")

        self.assertIsNone(api.buy_multi([1], ["EURUSD-OTC"], ["call"], [], timeout=0.01))
        self.assertEqual(api.last_operation["name"], "buy_multi")
        self.assertEqual(api.last_operation["reason"], "invalid_lengths")

    def test_buy_multi_rejects_invalid_active(self):
        api = IQ_Option("email", "password")

        class _FakeApi:
            buy_multi_option = {}

            def buyv3(self, price, active_id, action, expiration, request_id):
                raise AssertionError("buyv3 should not be called")

        api.api = _FakeApi()

        self.assertEqual(api.buy_multi([1], ["MISSING"], ["call"], [1], timeout=0.01), [None])
        self.assertEqual(api.last_operation["name"], "buy_multi")
        self.assertEqual(api.last_operation["reason"], "invalid_active")


if __name__ == "__main__":
    unittest.main()
