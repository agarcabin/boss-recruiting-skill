"""Timing boundaries and persistence using isolated SQLite state; no real sends."""
import contextlib
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import greeting_rate
import short_view_wait


class TimingTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(':memory:')
        self.addCleanup(self.db.close)
        self.db.row_factory = sqlite3.Row
        self.db.execute('CREATE TABLE settings(key TEXT PRIMARY KEY,value TEXT)')
        self.at = datetime(2026, 11, 13, tzinfo=timezone.utc)

    def test_top_up_and_threshold_boundaries(self):
        cases = [(0, 20, 20), (10, 20, 10), (10, 40, 30),
                 (25, 20, 0), (29.5, 40, 11), (30, None, 0), (45, None, 0)]
        for index, (elapsed, target, expected) in enumerate(cases):
            with self.subTest(elapsed=elapsed, target=target):
                with patch.object(short_view_wait.random, 'randint', return_value=target) as draw:
                    result = short_view_wait.plan(self.db, 'run', str(index), elapsed, self.at)
                self.assertEqual(result['retry_after_seconds'], expected)
                self.assertEqual(draw.call_count, int(elapsed < 30))
                if expected:
                    deadline = datetime.fromisoformat(result['retry_at'])
                    self.assertAlmostEqual(elapsed + (deadline-self.at).total_seconds(), target)

    def test_disabled_and_consumed_wait_do_not_replay(self):
        short_view_wait.set_enabled(self.db, 'run', False)
        with patch.object(short_view_wait.random, 'randint') as draw:
            self.assertEqual(short_view_wait.plan(self.db, 'run', 'disabled', 10, self.at)['state'], 'ready')
            draw.assert_not_called()
        short_view_wait.set_enabled(self.db, 'run', True)
        with patch.object(short_view_wait.random, 'randint', return_value=40):
            short_view_wait.plan(self.db, 'run', 'pending', 10, self.at)
        short_view_wait.set_enabled(self.db, 'run', False)
        short_view_wait.set_enabled(self.db, 'run', True)
        with patch.object(short_view_wait.random, 'randint') as draw:
            self.assertEqual(short_view_wait.plan(self.db, 'run', 'pending', 10, self.at)['state'], 'ready')
            draw.assert_not_called()

    def test_restart_reuses_deadline_without_resampling(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/'wait.sqlite3'
            with contextlib.closing(sqlite3.connect(path)) as db:
                db.row_factory = sqlite3.Row
                db.execute('CREATE TABLE settings(key TEXT PRIMARY KEY,value TEXT)')
                with patch.object(short_view_wait.random, 'randint', return_value=40):
                    first = short_view_wait.plan(db, 'run', 'visit', 10, self.at)
                db.commit()
            with contextlib.closing(sqlite3.connect(path)) as db:
                db.row_factory = sqlite3.Row
                with patch.object(short_view_wait.random, 'randint') as draw:
                    resumed = short_view_wait.plan(db, 'run', 'visit', 10, self.at+timedelta(seconds=5))
                    self.assertEqual(resumed['retry_after_seconds'], 25)
                    self.assertEqual(resumed['retry_at'], first['retry_at'])
                    self.assertEqual(short_view_wait.plan(db, 'run', 'visit', 10, self.at+timedelta(seconds=30))['state'], 'ready')
                    draw.assert_not_called()

    def test_short_wait_and_quota_keep_independent_deadlines(self):
        for i in range(10):
            greeting_rate.claim(self.db, str(i), self.at)
        later = self.at+timedelta(seconds=100)
        with patch.object(short_view_wait.random, 'randint', return_value=40):
            wait = short_view_wait.plan(self.db, 'run', 'visit', 10, later)
        self.assertEqual(wait['retry_after_seconds'], 30)
        self.assertEqual(greeting_rate.status(self.db, later)['retry_after_seconds'], 200)
        self.assertEqual(greeting_rate.status(self.db, self.at+timedelta(seconds=300))['state'], 'ready')


if __name__ == '__main__':
    unittest.main()
