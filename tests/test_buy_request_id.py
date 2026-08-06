import unittest
import threading
import time

from iqoptionapi.stable_api import IQ_Option


class TestBuyRequestId(unittest.TestCase):
    def test_buy_uses_unique_request_ids(self):
        api = IQ_Option("email", "password")

        class _FakeApi:
            def __init__(self):
                self.request_ids = []
                self.buy_multi_option = {}
                self.result = None
                self.buy_successful = None

            def buyv3(self, price, active, direction, expirations, request_id):
                del price, active, direction, expirations
                self.request_ids.append(request_id)

                def complete():
                    time.sleep(0.01)
                    self.buy_multi_option[request_id] = {"id": len(self.request_ids)}
                    self.result = True

                threading.Thread(target=complete).start()

        fake = _FakeApi()
        api.api = fake

        first = api.buy(1, "EURUSD-OTC", "call", 1)
        second = api.buy(1, "EURUSD-OTC", "put", 1)

        self.assertEqual(first, (True, 1))
        self.assertEqual(second, (True, 2))
        self.assertEqual(len(fake.request_ids), 2)
        self.assertNotEqual(fake.request_ids[0], fake.request_ids[1])

    def test_buy_by_raw_expirations_uses_unique_request_ids(self):
        api = IQ_Option("email", "password")

        class _FakeApi:
            def __init__(self):
                self.request_ids = []
                self.buy_multi_option = {}
                self.result = None
                self.buy_successful = None

            def buyv3_by_raw_expired(self, price, active, direction, option, expired, request_id):
                del price, active, direction, option, expired
                self.request_ids.append(request_id)

                def complete():
                    time.sleep(0.01)
                    self.buy_multi_option[request_id] = {"id": len(self.request_ids)}
                    self.result = True

                threading.Thread(target=complete).start()

        fake = _FakeApi()
        api.api = fake

        first = api.buy_by_raw_expirations(1, "EURUSD-OTC", "call", "turbo", 123)
        second = api.buy_by_raw_expirations(1, "EURUSD-OTC", "put", "turbo", 124)

        self.assertEqual(first, (True, 1))
        self.assertEqual(second, (True, 2))
        self.assertEqual(len(fake.request_ids), 2)
        self.assertNotEqual(fake.request_ids[0], fake.request_ids[1])


if __name__ == "__main__":
    unittest.main()
