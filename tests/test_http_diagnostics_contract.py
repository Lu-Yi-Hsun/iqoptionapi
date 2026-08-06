import unittest

from iqoptionapi.stable_api import IQ_Option


class _RawApi:
    websocket_last_message_error = None
    closed_option_last_error = None
    http_last_request = {
        "method": "POST",
        "url": "https://auth.iqoption.com/api/v2/login",
        "timeout": 30,
    }
    http_last_error = {
        "type": "TimeoutError",
        "message": "network stalled",
        "method": "POST",
        "url": "https://auth.iqoption.com/api/v2/login",
        "timeout": 30,
    }


class TestHttpDiagnosticsContract(unittest.TestCase):
    def test_stable_api_exposes_http_transport_diagnostics(self):
        api = IQ_Option("email", "password")
        api.api = _RawApi()

        diagnostics = api.get_api_diagnostics()

        self.assertEqual(diagnostics["http_last_request"], _RawApi.http_last_request)
        self.assertEqual(diagnostics["http_last_error"], _RawApi.http_last_error)


if __name__ == "__main__":
    unittest.main()
