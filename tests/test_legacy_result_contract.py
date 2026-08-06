import unittest

from iqoptionapi.api import nested_dict
from iqoptionapi.stable_api import IQ_Option


class TestLegacyResultContract(unittest.TestCase):
    def test_check_win_times_out_without_busy_wait(self):
        api = IQ_Option("email", "password")

        class _ListInfoData:
            def get(self, order_id):
                del order_id
                return {"game_state": 0}

            def delete(self, order_id):
                del order_id

        class _FakeApi:
            listinfodata = _ListInfoData()

        api.api = _FakeApi()

        self.assertIsNone(api.check_win(1001, timeout=0.01))
        self.assertEqual(api.last_operation["name"], "check_win")
        self.assertEqual(api.last_operation["status"], "pending")
        self.assertEqual(api.last_operation["reason"], "timeout")

    def test_check_win_records_resolved_result(self):
        api = IQ_Option("email", "password")

        class _ListInfoData:
            deleted = None

            def get(self, order_id):
                return {"game_state": 1, "win": "win", "id": order_id}

            def delete(self, order_id):
                self.deleted = order_id

        listinfo = _ListInfoData()

        class _FakeApi:
            listinfodata = listinfo

        api.api = _FakeApi()

        self.assertEqual(api.check_win(1001, timeout=1), "win")
        self.assertEqual(listinfo.deleted, 1001)
        self.assertEqual(api.last_operation["name"], "check_win")
        self.assertEqual(api.last_operation["status"], "resolved")

    def test_check_win_v2_handles_missing_betinfo_until_timeout(self):
        api = IQ_Option("email", "password")

        def get_betinfo(order_id, timeout=10):
            del order_id, timeout
            return False, None

        api.get_betinfo = get_betinfo

        self.assertIsNone(api.check_win_v2(1001, polling_time=0, timeout=0.01))
        self.assertEqual(api.last_operation["name"], "check_win_v2")
        self.assertEqual(api.last_operation["reason"], "timeout")

    def test_check_win_v2_records_profit(self):
        api = IQ_Option("email", "password")

        def get_betinfo(order_id, timeout=10):
            del timeout
            return True, {
                "result": {
                    "data": {
                        str(order_id): {
                            "win": "win",
                            "profit": 15.0,
                            "deposit": 10.0,
                        }
                    }
                }
            }

        api.get_betinfo = get_betinfo

        self.assertEqual(api.check_win_v2(1001, polling_time=0, timeout=1), 5.0)
        self.assertEqual(api.last_operation["name"], "check_win_v2")
        self.assertEqual(api.last_operation["status"], "resolved")

    def test_check_win_v3_uses_normalized_closed_option_profit(self):
        api = IQ_Option("email", "password")

        class _FakeApi:
            def __init__(self):
                self.order_async = nested_dict(2, dict)
                self.order_async[1001]["option-closed"] = {
                    "msg": {"profit_amount": "15.00", "amount": "10.00"}
                }

        api.api = _FakeApi()

        self.assertEqual(api.check_win_v3(1001, timeout=1), 5.0)
        self.assertEqual(api.last_operation["name"], "check_win_v3")
        self.assertEqual(api.last_operation["status"], "resolved")

    def test_check_win_v3_times_out(self):
        api = IQ_Option("email", "password")

        class _FakeApi:
            order_async = nested_dict(2, dict)

        api.api = _FakeApi()

        self.assertIsNone(api.check_win_v3(1001, timeout=0.01))
        self.assertEqual(api.last_operation["name"], "check_win_v3")
        self.assertEqual(api.last_operation["reason"], "timeout")


if __name__ == "__main__":
    unittest.main()
