import unittest

from iqoptionapi.api import nested_dict
from iqoptionapi.stable_api import IQ_Option


class TestPortfolioRequestContract(unittest.TestCase):
    def test_get_digital_position_times_out_waiting_for_position_changed(self):
        api = IQ_Option("email", "password")

        class _FakeApi:
            def __init__(self):
                self.position = None
                self.order_async = nested_dict(2, dict)

        api.api = _FakeApi()

        self.assertIsNone(api.get_digital_position(7001, timeout=0.01))
        self.assertEqual(api.last_operation["name"], "get_digital_position")
        self.assertEqual(api.last_operation["reason"], "position_changed_timeout")

    def test_get_digital_position_by_position_id_records_success(self):
        api = IQ_Option("email", "password")

        class _FakeApi:
            position = None

            def get_digital_position(self, position_id):
                self.position = {"position_id": position_id}

        api.api = _FakeApi()

        self.assertEqual(
            api.get_digital_position_by_position_id("external-1", timeout=1),
            {"position_id": "external-1"},
        )
        self.assertEqual(api.last_operation["name"], "get_digital_position_by_position_id")
        self.assertEqual(api.last_operation["status"], "ok")

    def test_position_history_timeout_and_success(self):
        api = IQ_Option("email", "password")

        class _TimeoutApi:
            position_history = None

            def get_position_history(self, instrument_type):
                del instrument_type

        api.api = _TimeoutApi()

        self.assertEqual(api.get_position_history("crypto", timeout=0.01), (False, None))
        self.assertEqual(api.last_operation["name"], "get_position_history")
        self.assertEqual(api.last_operation["status"], "timeout")

        class _SuccessApi:
            position_history = None

            def get_position_history(self, instrument_type):
                self.position_history = {"status": 2000, "msg": [instrument_type]}

        api.api = _SuccessApi()

        self.assertEqual(api.get_position_history("crypto", timeout=1), (True, ["crypto"]))
        self.assertEqual(api.last_operation["status"], "ok")

    def test_get_available_leverages_rejects_invalid_active(self):
        api = IQ_Option("email", "password")

        class _FakeApi:
            available_leverages = None

            def get_available_leverages(self, instrument_type, active_id):
                del instrument_type, active_id

        api.api = _FakeApi()

        self.assertEqual(api.get_available_leverages("crypto", "MISSING"), (False, None))
        self.assertEqual(api.last_operation["name"], "get_available_leverages")
        self.assertEqual(api.last_operation["reason"], "invalid_active")

    def test_cancel_order_and_close_position_record_success(self):
        api = IQ_Option("email", "password")

        class _FakeApi:
            def __init__(self):
                self.order_canceled = None
                self.order_data = None
                self.close_position_data = None
                self.closed_position_id = None

            def cancel_order(self, order_id):
                self.order_canceled = {"status": 2000, "msg": order_id}

            def get_order(self, order_id):
                self.order_data = {"status": 2000, "msg": {"position_id": order_id + 1}}

            def close_position(self, position_id):
                self.closed_position_id = position_id
                self.close_position_data = {"status": 2000}

        fake = _FakeApi()
        api.api = fake

        self.assertTrue(api.cancel_order(100, timeout=1))
        self.assertEqual(api.last_operation["name"], "cancel_order")
        self.assertEqual(api.last_operation["status"], "ok")

        self.assertTrue(api.close_position(100, timeout=1))
        self.assertEqual(fake.closed_position_id, 101)
        self.assertEqual(api.last_operation["name"], "close_position")
        self.assertEqual(api.last_operation["status"], "ok")

    def test_get_overnight_fee_timeout(self):
        api = IQ_Option("email", "password")

        class _FakeApi:
            overnight_fee = None

            def get_overnight_fee(self, instrument_type, active_id):
                del instrument_type, active_id

        api.api = _FakeApi()

        self.assertEqual(api.get_overnight_fee("crypto", "EURUSD-OTC", timeout=0.01), (False, None))
        self.assertEqual(api.last_operation["name"], "get_overnight_fee")
        self.assertEqual(api.last_operation["status"], "timeout")

    def test_close_position_v2_times_out_waiting_for_close_response(self):
        api = IQ_Option("email", "password")

        class _FakeApi:
            def __init__(self):
                self.order_async = nested_dict(2, dict)
                self.order_async[100]["id"] = 101
                self.close_position_data = None

            def close_position(self, position_id):
                self.closed_position_id = position_id

        fake = _FakeApi()
        api.api = fake

        self.assertFalse(api.close_position_v2(100, timeout=0.01))
        self.assertEqual(fake.closed_position_id, 101)
        self.assertEqual(api.last_operation["name"], "close_position_v2")
        self.assertEqual(api.last_operation["reason"], "close_timeout")

    def test_close_position_v2_records_success(self):
        api = IQ_Option("email", "password")

        class _FakeApi:
            def __init__(self):
                self.order_async = nested_dict(2, dict)
                self.order_async[100]["id"] = 101
                self.close_position_data = None

            def close_position(self, position_id):
                self.closed_position_id = position_id
                self.close_position_data = {"status": 2000}

        fake = _FakeApi()
        api.api = fake

        self.assertTrue(api.close_position_v2(100, timeout=1))
        self.assertEqual(fake.closed_position_id, 101)
        self.assertEqual(api.last_operation["name"], "close_position_v2")
        self.assertEqual(api.last_operation["status"], "ok")


if __name__ == "__main__":
    unittest.main()
