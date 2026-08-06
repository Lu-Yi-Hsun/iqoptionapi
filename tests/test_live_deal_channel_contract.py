import unittest

from iqoptionapi.ws.chanels.subscribe import Subscribe_live_deal
from iqoptionapi.ws.chanels.unsubscribe import Unscribe_live_deal


class _FakeApi:
    def __init__(self):
        self.sent = []

    def send_websocket_request(self, name, msg, request_id=""):
        self.sent.append((name, msg, request_id))


class TestLiveDealChannelContract(unittest.TestCase):
    def test_subscribe_live_deal_sends_routing_filters(self):
        api = _FakeApi()

        Subscribe_live_deal(api)("live-deal", 76, "turbo")

        channel, msg, request_id = api.sent[0]
        self.assertEqual(channel, "subscribeMessage")
        self.assertEqual(request_id, "")
        self.assertEqual(msg["name"], "live-deal")
        self.assertEqual(
            msg["params"]["routingFilters"],
            {"instrument_active_id": 76, "instrument_type": "turbo"},
        )

    def test_subscribe_live_deal_rejects_invalid_name(self):
        api = _FakeApi()

        with self.assertRaises(ValueError):
            Subscribe_live_deal(api)("bad-name", 76, "turbo")

        self.assertEqual(api.sent, [])

    def test_unsubscribe_live_deal_sends_routing_filters(self):
        api = _FakeApi()

        Unscribe_live_deal(api)("live-deal-binary-option-placed", 76, "binary")

        channel, msg, request_id = api.sent[0]
        self.assertEqual(channel, "unsubscribeMessage")
        self.assertEqual(request_id, "")
        self.assertEqual(msg["name"], "live-deal-binary-option-placed")
        self.assertEqual(
            msg["params"]["routingFilters"],
            {"active_id": 76, "option_type": "binary"},
        )

    def test_unsubscribe_live_deal_rejects_invalid_name(self):
        api = _FakeApi()

        with self.assertRaises(ValueError):
            Unscribe_live_deal(api)("bad-name", 76, "turbo")

        self.assertEqual(api.sent, [])


if __name__ == "__main__":
    unittest.main()
