import json
import threading
import time
import unittest

import iqoptionapi.global_value as global_value
from iqoptionapi.api import IQOptionAPI


class TestWebsocketSendLock(unittest.TestCase):
    def setUp(self):
        global_value.ssl_Mutual_exclusion = False
        global_value.ssl_Mutual_exclusion_write = False

    def tearDown(self):
        global_value.ssl_Mutual_exclusion = False
        global_value.ssl_Mutual_exclusion_write = False

    def test_send_websocket_request_releases_global_write_flag_on_error(self):
        class FailingWebsocket:
            def send(self, data):
                del data
                raise RuntimeError("send failed")

        class Client:
            wss = FailingWebsocket()

        api = IQOptionAPI("iqoption.com", "email", "password")
        api.websocket_client = Client()

        with self.assertRaises(RuntimeError):
            api.send_websocket_request("sendMessage", {"name": "test"})

        self.assertFalse(global_value.ssl_Mutual_exclusion_write)

    def test_send_websocket_request_serializes_same_instance_writes(self):
        class SerializingWebsocket:
            def __init__(self):
                self.active = 0
                self.max_active = 0
                self.sent = []
                self.lock = threading.Lock()

            def send(self, data):
                with self.lock:
                    self.active += 1
                    self.max_active = max(self.max_active, self.active)
                time.sleep(0.01)
                self.sent.append(json.loads(data)["request_id"])
                with self.lock:
                    self.active -= 1

        class Client:
            def __init__(self):
                self.wss = SerializingWebsocket()

        api = IQOptionAPI("iqoption.com", "email", "password")
        api.websocket_client = Client()

        threads = [
            threading.Thread(
                target=api.send_websocket_request,
                args=("sendMessage", {"name": "test"}, str(index)),
                kwargs={"no_force_send": False},
            )
            for index in range(5)
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertEqual(api.websocket_client.wss.max_active, 1)
        self.assertEqual(sorted(api.websocket_client.wss.sent), ["0", "1", "2", "3", "4"])
        self.assertFalse(global_value.ssl_Mutual_exclusion_write)


if __name__ == "__main__":
    unittest.main()
