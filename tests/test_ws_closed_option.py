import unittest

from iqoptionapi.api import nested_dict
from iqoptionapi.ws.client import WebsocketClient


class TestClosedOptionStorage(unittest.TestCase):
    def test_store_closed_option_updates_async_and_compat_cache(self):
        class _FakeApi:
            order_async = nested_dict(2, dict)
            socket_option_closed = {}

        client = WebsocketClient.__new__(WebsocketClient)
        client.api = _FakeApi()

        payload = {
            "name": "option-closed",
            "msg": {
                "option_id": 4001,
                "profit_amount": "18.00",
                "amount": "8.00",
            },
        }

        client._store_closed_option(payload)

        self.assertEqual(
            client.api.order_async[4001]["option-closed"],
            payload,
        )
        self.assertEqual(client.api.socket_option_closed[4001], payload)
        self.assertIsNone(client.api.closed_option_last_error)

    def test_store_closed_option_records_missing_option_id(self):
        class _FakeApi:
            order_async = nested_dict(2, dict)
            socket_option_closed = {}

        client = WebsocketClient.__new__(WebsocketClient)
        client.api = _FakeApi()

        client._store_closed_option({"name": "option-closed", "msg": {"amount": "8.00"}})

        self.assertEqual(
            client.api.closed_option_last_error["reason"],
            "missing_option_id",
        )
        self.assertEqual(dict(client.api.socket_option_closed), {})

    def test_store_closed_option_records_invalid_option_id(self):
        class _FakeApi:
            order_async = nested_dict(2, dict)
            socket_option_closed = {}

        client = WebsocketClient.__new__(WebsocketClient)
        client.api = _FakeApi()

        client._store_closed_option(
            {"name": "socket-option-closed", "msg": {"id": "not-a-number"}}
        )

        self.assertEqual(
            client.api.closed_option_last_error["reason"],
            "invalid_option_id",
        )
        self.assertEqual(
            client.api.closed_option_last_error["type"],
            "ValueError",
        )
        self.assertEqual(dict(client.api.socket_option_closed), {})


if __name__ == "__main__":
    unittest.main()
