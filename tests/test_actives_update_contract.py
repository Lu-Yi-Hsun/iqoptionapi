import unittest

import iqoptionapi.constants as OP_code
from iqoptionapi.stable_api import IQ_Option


class TestActivesUpdateContract(unittest.TestCase):
    def setUp(self):
        self._actives = dict(OP_code.ACTIVES)

    def tearDown(self):
        OP_code.ACTIVES = self._actives

    def test_instruments_input_to_actives_handles_timeout(self):
        api = IQ_Option("email", "password")
        api.get_instruments = lambda instrument_type, timeout=10: None

        self.assertFalse(api.instruments_input_to_ACTIVES("crypto", timeout=0.01))
        self.assertEqual(api.last_operation["name"], "instruments_input_to_ACTIVES")
        self.assertEqual(api.last_operation["reason"], "instruments_timeout")

    def test_instruments_input_to_actives_records_success(self):
        api = IQ_Option("email", "password")
        api.get_instruments = lambda instrument_type, timeout=10: {
            "instruments": [{"id": "CRYPTO_TEST", "active_id": 999001}]
        }

        self.assertTrue(api.instruments_input_to_ACTIVES("crypto", timeout=1))
        self.assertEqual(OP_code.ACTIVES["CRYPTO_TEST"], 999001)
        self.assertEqual(api.last_operation["name"], "instruments_input_to_ACTIVES")
        self.assertEqual(api.last_operation["status"], "ok")

    def test_get_all_binary_actives_handles_init_timeout(self):
        api = IQ_Option("email", "password")
        api.get_all_init = lambda timeout=30: None

        self.assertFalse(api.get_ALL_Binary_ACTIVES_OPCODE(timeout=0.01))
        self.assertEqual(api.last_operation["name"], "get_ALL_Binary_ACTIVES_OPCODE")
        self.assertEqual(api.last_operation["reason"], "init_timeout")

    def test_get_all_binary_actives_records_success(self):
        api = IQ_Option("email", "password")
        api.get_all_init = lambda timeout=30: {
            "result": {
                "binary": {"actives": {"999101": {"name": "front.TESTBIN"}}},
                "turbo": {"actives": {"999102": {"name": "front.TESTTURBO"}}},
            }
        }

        self.assertTrue(api.get_ALL_Binary_ACTIVES_OPCODE(timeout=1))
        self.assertEqual(OP_code.ACTIVES["TESTBIN"], 999101)
        self.assertEqual(OP_code.ACTIVES["TESTTURBO"], 999102)
        self.assertEqual(api.last_operation["name"], "get_ALL_Binary_ACTIVES_OPCODE")
        self.assertEqual(api.last_operation["status"], "ok")

    def test_update_actives_opcode_stops_when_binary_update_fails(self):
        api = IQ_Option("email", "password")
        api.get_ALL_Binary_ACTIVES_OPCODE = lambda timeout=30: False

        self.assertFalse(api.update_ACTIVES_OPCODE(timeout=0.01))
        self.assertEqual(api.last_operation["name"], "update_ACTIVES_OPCODE")
        self.assertEqual(api.last_operation["reason"], "binary_init_failed")

    def test_update_actives_opcode_records_success(self):
        api = IQ_Option("email", "password")
        api.get_ALL_Binary_ACTIVES_OPCODE = lambda timeout=30: True
        api.instruments_input_all_in_ACTIVES = lambda timeout=30: True

        self.assertTrue(api.update_ACTIVES_OPCODE(timeout=1))
        self.assertEqual(api.last_operation["name"], "update_ACTIVES_OPCODE")
        self.assertEqual(api.last_operation["status"], "ok")


if __name__ == "__main__":
    unittest.main()
