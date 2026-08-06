import logging
import unittest

from iqoptionapi.api import IQOptionAPI


class _Resource:
    url = "resource"


class _Response:
    text = "{}"

    def __init__(self, headers=None, cookies=None):
        self.headers = headers or {}
        self.cookies = _Cookies(cookies or {})

    def raise_for_status(self):
        return None


class _Session:
    def __init__(self, headers=None, cookies=None, response=None):
        self.calls = []
        self.headers = headers or {}
        self.cookies = _Cookies(cookies or {})
        self.response = response or _Response()
        self.verify = True
        self.trust_env = True

    def request(self, **kwargs):
        self.calls.append(kwargs)
        return self.response


class _Cookies:
    def __init__(self, values=None):
        self.values = values or {}

    def get_dict(self):
        return dict(self.values)


class _FailingSession(_Session):
    def request(self, **kwargs):
        self.calls.append(kwargs)
        raise TimeoutError("network stalled")


class TestHttpTimeoutContract(unittest.TestCase):
    def test_send_http_request_uses_default_timeout(self):
        api = IQOptionAPI("iqoption.com", "email", "password")
        api.session = _Session()

        api.send_http_request(_Resource(), "GET")

        self.assertEqual(api.session.calls[0]["timeout"], 30)

    def test_send_http_request_uses_configured_timeout(self):
        api = IQOptionAPI("iqoption.com", "email", "password", request_timeout=7.5)
        api.session = _Session()

        api.send_http_request(_Resource(), "POST", data={"a": 1})

        self.assertEqual(api.session.calls[0]["timeout"], 7.5)

    def test_raw_http_client_rejects_invalid_request_timeout(self):
        for timeout in (None, 0, -1, float("inf"), float("nan"), "bad"):
            with self.subTest(timeout=timeout):
                with self.assertRaises(ValueError):
                    IQOptionAPI("iqoption.com", "email", "password", request_timeout=timeout)

    def test_send_http_request_v2_uses_configured_timeout(self):
        api = IQOptionAPI("iqoption.com", "email", "password", request_timeout=3)
        api.session = _Session()

        api.send_http_request_v2("https://example.test/api", "POST")

        self.assertEqual(api.session.calls[0]["timeout"], 3)

    def test_send_http_request_records_http_error_diagnostics(self):
        api = IQOptionAPI("iqoption.com", "email", "password", request_timeout=2)
        api.session = _FailingSession()

        with self.assertRaises(TimeoutError):
            api.send_http_request(_Resource(), "GET")

        self.assertEqual(
            api.http_last_request,
            {
                "method": "GET",
                "url": "https://iqoption.com/api/resource",
                "timeout": 2,
            },
        )
        self.assertEqual(api.http_last_error["type"], "TimeoutError")
        self.assertEqual(api.http_last_error["method"], "GET")
        self.assertEqual(api.http_last_error["url"], "https://iqoption.com/api/resource")
        self.assertEqual(api.http_last_error["timeout"], 2)

    def test_send_http_request_v2_records_http_error_diagnostics(self):
        api = IQOptionAPI("iqoption.com", "email", "password", request_timeout=4)
        api.session = _FailingSession()

        with self.assertRaises(TimeoutError):
            api.send_http_request_v2("https://auth.iqoption.com/api/v2/login", "POST")

        self.assertEqual(api.http_last_error["type"], "TimeoutError")
        self.assertEqual(api.http_last_error["method"], "POST")
        self.assertEqual(api.http_last_error["url"], "https://auth.iqoption.com/api/v2/login")
        self.assertEqual(api.http_last_error["timeout"], 4)

    def test_send_http_request_v2_redacts_headers_and_cookies_in_debug_logs(self):
        api = IQOptionAPI("iqoption.com", "email", "password", request_timeout=3)
        api.session = _Session(
            headers={
                "Authorization": "Bearer secret-token",
                "User-Agent": "iqoptionapi-test",
            },
            cookies={
                "ssid": "secret-cookie",
                "tracking": "also-sensitive-cookie",
            },
        )

        with self.assertLogs("iqoptionapi.api", level=logging.DEBUG) as logs:
            api.send_http_request_v2("https://example.test/api", "POST")

        joined = "\n".join(logs.output)
        self.assertIn("Authorization': '<redacted>'", joined)
        self.assertIn("User-Agent': 'iqoptionapi-test'", joined)
        self.assertIn("ssid': '<redacted>'", joined)
        self.assertIn("tracking': '<redacted>'", joined)
        self.assertNotIn("secret-token", joined)
        self.assertNotIn("secret-cookie", joined)
        self.assertNotIn("also-sensitive-cookie", joined)

    def test_send_http_request_v2_redacts_response_headers_and_cookies_in_debug_logs(self):
        api = IQOptionAPI("iqoption.com", "email", "password", request_timeout=3)
        api.session = _Session(
            response=_Response(
                headers={
                    "Set-Cookie": "ssid=response-secret",
                    "Content-Type": "application/json",
                },
                cookies={
                    "ssid": "response-cookie",
                    "tracking": "response-tracking-cookie",
                },
            )
        )

        with self.assertLogs("iqoptionapi.api", level=logging.DEBUG) as logs:
            api.send_http_request_v2("https://example.test/api", "POST")

        joined = "\n".join(logs.output)
        self.assertIn("Set-Cookie': '<redacted>'", joined)
        self.assertIn("Content-Type': 'application/json'", joined)
        self.assertIn("ssid': '<redacted>'", joined)
        self.assertIn("tracking': '<redacted>'", joined)
        self.assertNotIn("response-secret", joined)
        self.assertNotIn("response-cookie", joined)
        self.assertNotIn("response-tracking-cookie", joined)


if __name__ == "__main__":
    unittest.main()
