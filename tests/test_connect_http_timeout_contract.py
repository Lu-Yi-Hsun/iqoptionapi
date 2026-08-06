import unittest

import iqoptionapi.stable_api as stable_api
from iqoptionapi.stable_api import IQ_Option


class _RawApi:
    instances = []

    def __init__(self, host, email, password, request_timeout=None):
        self.host = host
        self.email = email
        self.password = password
        self.request_timeout = request_timeout
        self.session = None
        _RawApi.instances.append(self)

    def close(self):
        return None

    def set_session(self, headers=None, cookies=None):
        self.session = {"headers": headers, "cookies": cookies}

    def connect(self):
        return False, "login_failed"


class _LegacyRawApi:
    instances = []

    def __init__(self, host, email, password):
        self.host = host
        self.email = email
        self.password = password
        _LegacyRawApi.instances.append(self)

    def close(self):
        return None

    def set_session(self, headers=None, cookies=None):
        return None

    def connect(self):
        return False, "login_failed"


class TestConnectHttpTimeoutContract(unittest.TestCase):
    def setUp(self):
        self.original_raw_api = stable_api.IQOptionAPI
        _RawApi.instances = []
        _LegacyRawApi.instances = []

    def tearDown(self):
        stable_api.IQOptionAPI = self.original_raw_api

    def test_connect_passes_timeout_to_raw_http_client(self):
        stable_api.IQOptionAPI = _RawApi
        api = IQ_Option("email", "password")

        self.assertEqual(api.connect(timeout=4.5), (False, "login_failed"))

        self.assertEqual(_RawApi.instances[-1].request_timeout, 4.5)
        self.assertEqual(api.last_operation["name"], "connect")
        self.assertEqual(api.last_operation["status"], "rejected")
        self.assertEqual(api.last_operation["reason"], "login_failed")

    def test_connect_rejects_invalid_timeout_before_reconnect(self):
        stable_api.IQOptionAPI = _RawApi
        api = IQ_Option("email", "password")
        initial_instances = len(_RawApi.instances)

        for timeout in (None, 0, -1, float("inf"), float("nan"), "bad"):
            with self.subTest(timeout=timeout):
                self.assertEqual(api.connect(timeout=timeout), (False, "invalid_timeout"))

        self.assertEqual(len(_RawApi.instances), initial_instances)
        self.assertEqual(api.last_operation["name"], "connect")
        self.assertEqual(api.last_operation["status"], "rejected")
        self.assertEqual(api.last_operation["reason"], "invalid_timeout")

    def test_connect_keeps_legacy_raw_api_compatibility(self):
        stable_api.IQOptionAPI = _LegacyRawApi
        api = IQ_Option("email", "password")

        self.assertEqual(api.connect(timeout=2), (False, "login_failed"))

        self.assertGreaterEqual(len(_LegacyRawApi.instances), 1)
        self.assertEqual(api.last_operation["reason"], "login_failed")


if __name__ == "__main__":
    unittest.main()
