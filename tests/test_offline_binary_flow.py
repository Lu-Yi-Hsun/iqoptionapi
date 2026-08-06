import threading
import time
import unittest

from iqoptionapi.api import nested_dict
from iqoptionapi.stable_api import IQ_Option
from iqoptionapi.ws.client import WebsocketClient


class TestOfflineBinaryFlow(unittest.TestCase):
    def test_buy_option_closed_check_win_v4_flow_without_broker(self):
        api = IQ_Option("email", "password")

        class _FakeApi:
            def __init__(self):
                self.buy_multi_option = {}
                self.result = None
                self.buy_successful = None
                self.socket_option_closed = {}
                self.order_async = nested_dict(2, dict)
                self.request_id = ""

            def buyv3(self, price, active, direction, expirations, request_id):
                del price, active, direction, expirations
                self.request_id = request_id

                def complete():
                    time.sleep(0.01)
                    self.buy_multi_option[request_id] = {"id": 7001}
                    self.result = True

                threading.Thread(target=complete).start()

        fake = _FakeApi()
        api.api = fake

        accepted, order_id = api.buy(2, "EURUSD-OTC", "call", 1)

        self.assertTrue(accepted)
        self.assertEqual(order_id, 7001)
        self.assertTrue(fake.request_id.startswith("buy-"))
        self.assertEqual(api.last_operation["name"], "buy")
        self.assertEqual(api.last_operation["status"], "ok")

        client = WebsocketClient.__new__(WebsocketClient)
        client.api = fake
        client._store_closed_option({
            "name": "option-closed",
            "msg": {
                "option_id": order_id,
                "profit_amount": "3.64",
                "amount": "2.00",
            },
        })

        resolved, profit = api.check_win_v4(order_id, timeout=1)

        self.assertTrue(resolved)
        self.assertAlmostEqual(profit, 1.64)
        self.assertEqual(api.last_operation["name"], "check_win_v4")
        self.assertEqual(api.last_operation["status"], "resolved")
        self.assertIn(api.last_operation["reason"], {"socket_option_closed", "option_closed"})


if __name__ == "__main__":
    unittest.main()
