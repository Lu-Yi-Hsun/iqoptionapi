import unittest

from iqoptionapi.stable_api import IQ_Option


class TestUserRequestContract(unittest.TestCase):
    def test_get_user_profile_client_times_out(self):
        api = IQ_Option("email", "password")

        class _FakeApi:
            user_profile_client = None

            def Get_User_Profile_Client(self, user_id):
                del user_id

        api.api = _FakeApi()

        self.assertIsNone(api.get_user_profile_client(10, timeout=0.01))
        self.assertEqual(api.last_operation["name"], "get_user_profile_client")
        self.assertEqual(api.last_operation["status"], "timeout")

    def test_get_user_profile_client_records_success(self):
        api = IQ_Option("email", "password")

        class _FakeApi:
            user_profile_client = None

            def Get_User_Profile_Client(self, user_id):
                self.user_profile_client = {"user_id": user_id}

        api.api = _FakeApi()

        self.assertEqual(api.get_user_profile_client(10, timeout=1), {"user_id": 10})
        self.assertEqual(api.last_operation["name"], "get_user_profile_client")
        self.assertEqual(api.last_operation["status"], "ok")

    def test_request_leaderboard_userinfo_deals_client_times_out(self):
        api = IQ_Option("email", "password")
        api.suspend = 0

        class _FakeApi:
            leaderboard_userinfo_deals_client = None

            def Request_Leaderboard_Userinfo_Deals_Client(self, user_id, country_id):
                del user_id, country_id

        api.api = _FakeApi()

        self.assertIsNone(
            api.request_leaderboard_userinfo_deals_client(10, 30, timeout=0.01)
        )
        self.assertEqual(
            api.last_operation["name"],
            "request_leaderboard_userinfo_deals_client",
        )
        self.assertEqual(api.last_operation["status"], "timeout")

    def test_request_leaderboard_userinfo_deals_client_records_success(self):
        api = IQ_Option("email", "password")

        class _FakeApi:
            leaderboard_userinfo_deals_client = None

            def Request_Leaderboard_Userinfo_Deals_Client(self, user_id, country_id):
                self.leaderboard_userinfo_deals_client = {
                    "isSuccessful": True,
                    "user_id": user_id,
                    "country_id": country_id,
                }

        api.api = _FakeApi()

        self.assertEqual(
            api.request_leaderboard_userinfo_deals_client(10, 30, timeout=1),
            {"isSuccessful": True, "user_id": 10, "country_id": 30},
        )
        self.assertEqual(
            api.last_operation["name"],
            "request_leaderboard_userinfo_deals_client",
        )
        self.assertEqual(api.last_operation["status"], "ok")

    def test_get_users_availability_times_out(self):
        api = IQ_Option("email", "password")
        api.suspend = 0

        class _FakeApi:
            users_availability = None

            def Get_Users_Availability(self, user_id):
                del user_id

        api.api = _FakeApi()

        self.assertIsNone(api.get_users_availability(10, timeout=0.01))
        self.assertEqual(api.last_operation["name"], "get_users_availability")
        self.assertEqual(api.last_operation["status"], "timeout")

    def test_get_users_availability_records_success(self):
        api = IQ_Option("email", "password")

        class _FakeApi:
            users_availability = None

            def Get_Users_Availability(self, user_id):
                self.users_availability = {"user_id": user_id, "online": True}

        api.api = _FakeApi()

        self.assertEqual(
            api.get_users_availability(10, timeout=1),
            {"user_id": 10, "online": True},
        )
        self.assertEqual(api.last_operation["name"], "get_users_availability")
        self.assertEqual(api.last_operation["status"], "ok")


if __name__ == "__main__":
    unittest.main()
