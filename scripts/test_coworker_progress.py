"""Boundary tests for the explicitly OLD => SKIP coworker rule."""
import unittest
from datetime import datetime, timedelta, timezone

import coworker_progress


class CoworkerProgressTests(unittest.TestCase):
    def setUp(self):
        self.at = datetime(2026, 10, 26, 10, 0, tzinfo=coworker_progress.CN_TZ)

    def result(self, stamp):
        return coworker_progress.evaluate({"state": "first_record", "first_greeting_at": stamp,
                                           "evidence": "UIA first coworker entry"}, self.at)

    def test_screenshot_first_date_is_old_and_skipped(self):
        self.assertEqual(self.result("2026-06-05 09:22")["action"], "skip")

    def test_exact_seven_days_and_newer_continue(self):
        self.assertEqual(self.result("2026-10-19 10:00")["action"], "continue")
        self.assertEqual(self.result("2026-10-25 09:22")["action"], "continue")
        self.assertEqual(self.result("2026-10-19 09:59:59")["action"], "skip")

    def test_timezone_offsets_compare_the_same_instant(self):
        self.assertEqual(self.result("2026-10-19T02:00:00+00:00")["action"], "continue")

    def test_empty_is_not_the_same_as_missing_or_unreadable(self):
        self.assertEqual(coworker_progress.evaluate(
            {"state": "empty", "evidence": "UIA panel explicitly empty"}, self.at)["action"], "continue")
        self.assertEqual(coworker_progress.evaluate(None, self.at)["action"], "review")
        self.assertEqual(self.result("昨天")["action"], "review")
        self.assertEqual(self.result("2026-10-27 10:00")["action"], "review")
        self.assertEqual(coworker_progress.evaluate({"state":"empty"}, self.at)["action"], "review")

    def test_not_found_continues_only_after_completed_lookup(self):
        observation = {"state": "not_found", "lookup_completed": True,
                       "evidence": "Unique visible BOSS document queried; coworker header absent"}
        result = coworker_progress.evaluate(observation, self.at)
        self.assertEqual(result["action"], "continue")
        self.assertEqual(result["state"], "not_found")
        self.assertTrue(result["lookup_completed"])
        self.assertEqual(coworker_progress.evaluate(result, self.at)["action"], "continue")
        for broken in ({**observation, "lookup_completed": False},
                       {**observation, "evidence": ""},
                       {**observation, "first_greeting_at": "2026-01-01 10:00"},
                       {**observation, "state": "unavailable"}):
            self.assertEqual(coworker_progress.evaluate(broken, self.at)["action"], "review")


if __name__ == "__main__":
    unittest.main()
