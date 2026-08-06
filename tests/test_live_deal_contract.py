import unittest
from collections import deque

from iqoptionapi.api import nested_dict
from iqoptionapi.stable_api import IQ_Option


class TestLiveDealContract(unittest.TestCase):
    def test_subscribe_live_deal_rejects_invalid_active(self):
        api = IQ_Option("email", "password")

        class _FakeApi:
            live_deal_data = nested_dict(3, deque)

            def Subscribe_Live_Deal(self, name, active_id, deal_type):
                del name, active_id, deal_type

        api.api = _FakeApi()

        self.assertFalse(api.subscribe_live_deal("live-deal", "MISSING", "turbo", 10))
        self.assertEqual(api.last_operation["name"], "subscribe_live_deal")
        self.assertEqual(api.last_operation["reason"], "invalid_active")

    def test_subscribe_live_deal_rejects_invalid_name(self):
        api = IQ_Option("email", "password")

        class _FakeApi:
            live_deal_data = nested_dict(3, deque)

            def Subscribe_Live_Deal(self, name, active_id, deal_type):
                del name, active_id, deal_type

        api.api = _FakeApi()

        self.assertFalse(api.subscribe_live_deal("bad-name", "EURUSD-OTC", "turbo", 10))
        self.assertEqual(api.last_operation["name"], "subscribe_live_deal")
        self.assertEqual(api.last_operation["reason"], "invalid_name")

    def test_subscribe_live_deal_initializes_bounded_buffer(self):
        api = IQ_Option("email", "password")

        class _FakeApi:
            def __init__(self):
                self.live_deal_data = nested_dict(3, deque)
                self.calls = []

            def Subscribe_Live_Deal(self, name, active_id, deal_type):
                self.calls.append((name, active_id, deal_type))

        fake = _FakeApi()
        api.api = fake

        self.assertTrue(api.subscribe_live_deal("live-deal", "EURUSD-OTC", "turbo", 2))
        self.assertEqual(fake.calls, [("live-deal", 76, "turbo")])
        self.assertEqual(
            fake.live_deal_data["live-deal"]["EURUSD-OTC"]["turbo"].maxlen,
            2,
        )
        self.assertEqual(api.last_operation["name"], "subscribe_live_deal")
        self.assertEqual(api.last_operation["status"], "ok")

    def test_unscribe_live_deal_clears_buffer(self):
        api = IQ_Option("email", "password")

        class _FakeApi:
            def __init__(self):
                self.live_deal_data = nested_dict(3, deque)
                self.live_deal_data["live-deal"]["EURUSD-OTC"]["turbo"] = deque(
                    [{"id": 1}],
                    10,
                )
                self.calls = []

            def Unscribe_Live_Deal(self, name, active_id, deal_type):
                self.calls.append((name, active_id, deal_type))

        fake = _FakeApi()
        api.api = fake

        self.assertTrue(api.unscribe_live_deal("live-deal", "EURUSD-OTC", "turbo"))
        self.assertEqual(fake.calls, [("live-deal", 76, "turbo")])
        self.assertEqual(len(fake.live_deal_data["live-deal"]["EURUSD-OTC"]["turbo"]), 0)
        self.assertEqual(api.last_operation["name"], "unscribe_live_deal")
        self.assertEqual(api.last_operation["status"], "ok")

    def test_unscribe_live_deal_rejects_invalid_name(self):
        api = IQ_Option("email", "password")

        class _FakeApi:
            live_deal_data = nested_dict(3, deque)

            def Unscribe_Live_Deal(self, name, active_id, deal_type):
                del name, active_id, deal_type

        api.api = _FakeApi()

        self.assertFalse(api.unscribe_live_deal("bad-name", "EURUSD-OTC", "turbo"))
        self.assertEqual(api.last_operation["name"], "unscribe_live_deal")
        self.assertEqual(api.last_operation["reason"], "invalid_name")

    def test_pop_live_deal_returns_none_when_empty(self):
        api = IQ_Option("email", "password")

        class _FakeApi:
            live_deal_data = nested_dict(3, deque)

        api.api = _FakeApi()

        self.assertIsNone(api.pop_live_deal("live-deal", "EURUSD-OTC", "turbo"))
        self.assertEqual(api.last_operation["name"], "pop_live_deal")
        self.assertEqual(api.last_operation["status"], "empty")

    def test_clear_live_deal_rejects_invalid_buffersize(self):
        api = IQ_Option("email", "password")

        class _FakeApi:
            live_deal_data = nested_dict(3, deque)

        api.api = _FakeApi()

        self.assertFalse(api.clear_live_deal("live-deal", "EURUSD-OTC", "turbo", 0))
        self.assertEqual(api.last_operation["name"], "clear_live_deal")
        self.assertEqual(api.last_operation["reason"], "invalid_buffersize")


if __name__ == "__main__":
    unittest.main()
