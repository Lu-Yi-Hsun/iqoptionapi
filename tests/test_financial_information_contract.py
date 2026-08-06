import unittest

from iqoptionapi.stable_api import IQ_Option


class TestFinancialInformationContract(unittest.TestCase):
    def test_get_financial_information_times_out(self):
        api = IQ_Option("email", "password")

        class _FakeApi:
            financial_information = None

            def get_financial_information(self, active_id):
                del active_id

        api.api = _FakeApi()

        self.assertIsNone(api.get_financial_information(1, timeout=0.01))
        self.assertEqual(api.last_operation["name"], "get_financial_information")
        self.assertEqual(api.last_operation["status"], "timeout")

    def test_get_financial_information_records_success(self):
        api = IQ_Option("email", "password")

        class _FakeApi:
            financial_information = None

            def get_financial_information(self, active_id):
                self.financial_information = {"active_id": active_id}

        api.api = _FakeApi()

        self.assertEqual(api.get_financial_information(76, timeout=1), {"active_id": 76})
        self.assertEqual(api.last_operation["name"], "get_financial_information")
        self.assertEqual(api.last_operation["status"], "ok")


if __name__ == "__main__":
    unittest.main()
