import unittest

import iqoptionapi.global_value as global_value
from iqoptionapi.ws.client import WebsocketClient


class TestWebsocketMessageResilience(unittest.TestCase):
    def setUp(self):
        global_value.ssl_Mutual_exclusion = False

    def tearDown(self):
        global_value.ssl_Mutual_exclusion = False

    def test_on_message_records_invalid_json_without_raising(self):
        class _FakeApi:
            websocket_last_message_error = None

        client = WebsocketClient.__new__(WebsocketClient)
        client.api = _FakeApi()

        client.on_message("{not-json")

        self.assertFalse(global_value.ssl_Mutual_exclusion)
        self.assertEqual(client.api.websocket_last_message_error["type"], "JSONDecodeError")

    def test_on_message_records_unexpected_schema_without_raising(self):
        class _FakeApi:
            websocket_last_message_error = None

        client = WebsocketClient.__new__(WebsocketClient)
        client.api = _FakeApi()

        client.on_message("{}")

        self.assertFalse(global_value.ssl_Mutual_exclusion)
        self.assertEqual(client.api.websocket_last_message_error["type"], "KeyError")


if __name__ == "__main__":
    unittest.main()
