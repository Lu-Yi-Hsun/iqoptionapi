import unittest

import iqoptionapi.global_value as global_value
import iqoptionapi.stable_api as stable_api
from iqoptionapi.stable_api import IQ_Option


class _FakeLowApi:
    connect_result = (True, None)

    def __init__(self, host, email, password):
        self.host = host
        self.email = email
        self.password = password
        self.portfolio_calls = []
        self.set_options_calls = []

    def set_session(self, headers, cookies):
        self.session = {"headers": headers, "cookies": cookies}

    def connect(self):
        return self.connect_result

    def portfolio(self, **kwargs):
        self.portfolio_calls.append(kwargs)

    def setOptions(self, option, enabled):
        self.set_options_calls.append((option, enabled))


class TestConnectContract(unittest.TestCase):
    def setUp(self):
        self._factory = stable_api.IQOptionAPI
        self._balance_id = global_value.balance_id
        global_value.balance_id = None

    def tearDown(self):
        stable_api.IQOptionAPI = self._factory
        global_value.balance_id = self._balance_id

    def test_connect_records_transport_rejection(self):
        class _RejectedApi(_FakeLowApi):
            connect_result = (False, "login_failed")

        stable_api.IQOptionAPI = _RejectedApi
        api = IQ_Option("email", "password")

        self.assertEqual(api.connect(timeout=0.01), (False, "login_failed"))
        self.assertEqual(api.last_operation["name"], "connect")
        self.assertEqual(api.last_operation["status"], "rejected")
        self.assertEqual(api.last_operation["reason"], "login_failed")

    def test_connect_records_balance_id_timeout(self):
        stable_api.IQOptionAPI = _FakeLowApi
        api = IQ_Option("email", "password")
        api.suspend = 0

        self.assertEqual(api.connect(timeout=0.01), (False, "balance_id timeout"))
        self.assertEqual(api.last_operation["name"], "connect")
        self.assertEqual(api.last_operation["status"], "timeout")
        self.assertEqual(api.last_operation["reason"], "balance_id_timeout")

    def test_connect_records_success(self):
        stable_api.IQOptionAPI = _FakeLowApi
        global_value.balance_id = 1001
        api = IQ_Option("email", "password")

        self.assertEqual(api.connect(timeout=1), (True, None))
        self.assertEqual(api.last_operation["name"], "connect")
        self.assertEqual(api.last_operation["status"], "ok")
        self.assertEqual(api.last_operation["payload"]["balance_id"], 1001)
        self.assertEqual(api.api.set_options_calls, [(1, True)])
        self.assertGreater(len(api.api.portfolio_calls), 0)


if __name__ == "__main__":
    unittest.main()
