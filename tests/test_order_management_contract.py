import unittest

from iqoptionapi.stable_api import IQ_Option


class TestOrderManagementContract(unittest.TestCase):
    def test_buy_order_times_out_waiting_for_order_id(self):
        api = IQ_Option("email", "password")

        class _FakeApi:
            buy_order_id = None

            def buy_order(self, **kwargs):
                self.kwargs = kwargs

        api.api = _FakeApi()

        self.assertEqual(
            api.buy_order("crypto", "BTCUSD", "buy", 1, 1, "market", timeout=0.01),
            (False, None),
        )
        self.assertEqual(api.last_operation["name"], "buy_order")
        self.assertEqual(api.last_operation["reason"], "buy_order_id_timeout")

    def test_buy_order_records_success(self):
        api = IQ_Option("email", "password")

        class _FakeApi:
            def __init__(self):
                self.buy_order_id = None
                self.order_data = None

            def buy_order(self, **kwargs):
                del kwargs
                self.buy_order_id = 501

            def get_order(self, order_id):
                self.order_data = {"status": 2000, "msg": {"status": "filled", "id": order_id}}

        api.api = _FakeApi()

        self.assertEqual(
            api.buy_order("crypto", "BTCUSD", "buy", 1, 1, "market", timeout=1),
            (True, 501),
        )
        self.assertEqual(api.last_operation["name"], "buy_order")
        self.assertEqual(api.last_operation["status"], "ok")

    def test_change_auto_margin_call_timeout(self):
        api = IQ_Option("email", "password")

        class _FakeApi:
            auto_margin_call_changed_respond = None

            def change_auto_margin_call(self, id_name, id_value, auto_margin_call):
                del id_name, id_value, auto_margin_call

        api.api = _FakeApi()

        self.assertEqual(
            api.change_auto_margin_call("order_id", 10, False, timeout=0.01),
            (False, None),
        )
        self.assertEqual(api.last_operation["name"], "change_auto_margin_call")
        self.assertEqual(api.last_operation["status"], "timeout")

    def test_change_order_records_success(self):
        api = IQ_Option("email", "password")

        class _FakeApi:
            def __init__(self):
                self.tpsl_changed_respond = None
                self.auto_margin_call_changed_respond = None

            def change_order(self, **kwargs):
                self.change_order_kwargs = kwargs
                self.tpsl_changed_respond = {"status": 2000, "msg": {"changed": True}}

            def change_auto_margin_call(self, id_name, id_value, auto_margin_call):
                del id_name, id_value, auto_margin_call
                self.auto_margin_call_changed_respond = {"status": 2000, "msg": {}}

        api.api = _FakeApi()

        self.assertEqual(
            api.change_order(
                "order_id",
                10,
                "percent",
                10,
                "percent",
                20,
                False,
                False,
                timeout=1,
            ),
            (True, {"changed": True}),
        )
        self.assertEqual(api.last_operation["name"], "change_order")
        self.assertEqual(api.last_operation["status"], "ok")

    def test_change_order_rejects_invalid_id_name(self):
        api = IQ_Option("email", "password")

        self.assertEqual(
            api.change_order("bad", 10, None, None, None, None, False, False),
            (False, None),
        )
        self.assertEqual(api.last_operation["name"], "change_order")
        self.assertEqual(api.last_operation["reason"], "invalid_id_name")


if __name__ == "__main__":
    unittest.main()
