import unittest

from iqoptionapi.stable_api import IQ_Option


class TestMoodStreamContract(unittest.TestCase):
    def test_start_mood_stream_times_out_without_busy_wait(self):
        api = IQ_Option("email", "password")
        api.suspend = 0

        class _FakeApi:
            def __init__(self):
                self.traders_mood = {}
                self.subscribe_calls = 0

            def subscribe_Traders_mood(self, active_id):
                del active_id
                self.subscribe_calls += 1

        fake = _FakeApi()
        api.api = fake

        self.assertFalse(api.start_mood_stream("EURUSD-OTC", timeout=0.01))
        self.assertGreater(fake.subscribe_calls, 0)
        self.assertEqual(api.last_operation["name"], "start_mood_stream")
        self.assertEqual(api.last_operation["status"], "timeout")

    def test_start_and_stop_mood_stream_track_subscription(self):
        api = IQ_Option("email", "password")

        class _FakeApi:
            def __init__(self):
                self.traders_mood = {76: 41}
                self.unsubscribed = []

            def subscribe_Traders_mood(self, active_id):
                self.traders_mood[active_id] = 41

            def unsubscribe_Traders_mood(self, active_id):
                self.unsubscribed.append(active_id)

        fake = _FakeApi()
        api.api = fake

        self.assertTrue(api.start_mood_stream("EURUSD-OTC", timeout=1))
        self.assertIn("EURUSD-OTC", api.subscribe_mood)

        self.assertTrue(api.stop_mood_stream("EURUSD-OTC"))
        self.assertNotIn("EURUSD-OTC", api.subscribe_mood)
        self.assertEqual(fake.unsubscribed, [76])
        self.assertEqual(api.last_operation["name"], "stop_mood_stream")
        self.assertEqual(api.last_operation["status"], "ok")

    def test_mood_stream_rejects_invalid_active(self):
        api = IQ_Option("email", "password")

        self.assertFalse(api.start_mood_stream("MISSING", timeout=0.01))
        self.assertEqual(api.last_operation["reason"], "invalid_active")
        self.assertFalse(api.stop_mood_stream("MISSING"))
        self.assertEqual(api.last_operation["reason"], "invalid_active")


if __name__ == "__main__":
    unittest.main()
