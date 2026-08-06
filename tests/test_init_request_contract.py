import unittest

from iqoptionapi.stable_api import IQ_Option


class TestInitRequestContract(unittest.TestCase):
    def test_get_all_init_times_out_when_broker_never_answers(self):
        api = IQ_Option("email", "password")

        class _FakeApi:
            api_option_init_all_result = None

            def get_api_option_init_all(self):
                pass

        api.api = _FakeApi()

        self.assertIsNone(api.get_all_init(timeout=0.01))
        self.assertEqual(api.last_operation["name"], "get_all_init")
        self.assertEqual(api.last_operation["status"], "timeout")

    def test_get_all_init_records_success(self):
        api = IQ_Option("email", "password")

        class _FakeApi:
            api_option_init_all_result = None

            def get_api_option_init_all(self):
                self.api_option_init_all_result = {"isSuccessful": True, "result": {}}

        api.api = _FakeApi()

        self.assertEqual(api.get_all_init(timeout=1), {"isSuccessful": True, "result": {}})
        self.assertEqual(api.last_operation["name"], "get_all_init")
        self.assertEqual(api.last_operation["status"], "ok")

    def test_get_all_init_times_out_after_reconnect_failures(self):
        api = IQ_Option("email", "password")
        api.suspend = 0
        reconnects = []

        class _FakeApi:
            api_option_init_all_result = None

            def get_api_option_init_all(self):
                raise RuntimeError("transport down")

        api.api = _FakeApi()
        api.connect = lambda: reconnects.append(True)

        self.assertIsNone(api.get_all_init(timeout=0.01))
        self.assertGreater(len(reconnects), 0)
        self.assertEqual(api.last_operation["name"], "get_all_init")
        self.assertEqual(api.last_operation["status"], "timeout")


if __name__ == "__main__":
    unittest.main()
