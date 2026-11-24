import sqlite3
import unittest
from unittest import mock

import card_layout
import greeting_view_wait
import workflow_windows


class AdaptiveTimingTest(unittest.TestCase):
    def db(self, completed=3):
        db = sqlite3.connect(':memory:')
        db.row_factory = sqlite3.Row
        db.execute('CREATE TABLE candidate_progress(run_id TEXT, finished_at TEXT)')
        for _ in range(completed):
            db.execute("INSERT INTO candidate_progress VALUES('r','2026-11-18T00:00:00+00:00')")
        return db

    def test_slow_run_reduces_wait_by_five_seconds(self):
        with mock.patch('ledger.active_elapsed_seconds', return_value=210):
            adjusted, meta = greeting_view_wait.adaptive_config(
                self.db(), 'r', {'minimum_seconds': 30, 'rest_seconds': 30})
        self.assertEqual(adjusted['minimum_seconds'], 25)
        self.assertEqual(adjusted['rest_seconds'], 25)
        self.assertEqual(meta['speed_seconds'], 70)
        self.assertEqual(meta['adjust_seconds'], -5)

    def test_fast_run_increases_wait_by_five_seconds(self):
        with mock.patch('ledger.active_elapsed_seconds', return_value=60):
            adjusted, meta = greeting_view_wait.adaptive_config(
                self.db(), 'r', {'minimum_seconds': 30, 'rest_seconds': 30})
        self.assertEqual(adjusted['minimum_seconds'], 35)
        self.assertEqual(adjusted['rest_seconds'], 35)
        self.assertEqual(meta['speed_seconds'], 20)
        self.assertEqual(meta['adjust_seconds'], 5)

    def test_pace_within_twenty_five_percent_keeps_wait(self):
        with mock.patch('ledger.active_elapsed_seconds', return_value=105):
            adjusted, meta = greeting_view_wait.adaptive_config(
                self.db(), 'r', {'minimum_seconds': 30, 'rest_seconds': 30})
        self.assertEqual(adjusted['minimum_seconds'], 30)
        self.assertEqual(adjusted['rest_seconds'], 30)
        self.assertEqual(meta['speed_seconds'], 35)
        self.assertEqual(meta['adjust_seconds'], 0)

    def test_short_configured_wait_is_not_adjusted(self):
        with mock.patch('ledger.active_elapsed_seconds', return_value=210):
            adjusted, meta = greeting_view_wait.adaptive_config(
                self.db(), 'r', {'minimum_seconds': 25, 'rest_seconds': 30})
        self.assertEqual(adjusted['minimum_seconds'], 25)
        self.assertEqual(adjusted['rest_seconds'], 30)
        self.assertEqual(meta['adjust_seconds'], 0)

    def test_plan_persists_adjusted_view_and_rest(self):
        db = self.db()
        db.execute('CREATE TABLE candidates(run_id TEXT,candidate_hash TEXT,status TEXT)')
        for index in range(5):
            candidate_hash = 'visit-1' if index == 0 else str(index)
            db.execute("INSERT INTO candidates VALUES('r',?,'sent')", (candidate_hash,))
        with mock.patch('ledger.active_elapsed_seconds', return_value=210):
            result = greeting_view_wait.plan(
                db, 'r', 'visit-1', 10, {'minimum_seconds': 30, 'rest_seconds': 30}, 0)
        self.assertEqual(result['view_wait_seconds'], 15)
        self.assertEqual(result['rest_seconds'], 25)
        self.assertEqual(result['base_view_seconds'], 30)
        self.assertEqual(result['adjust_seconds'], -5)

    def test_promo_markers_and_class_are_detected(self):
        self.assertTrue(card_layout.promo(
            {'candidate_name': '尹**', 'summary': '热搜牛人推荐 查看更多'}))
        self.assertTrue(card_layout.promo({'candidate_name': '广告牛人推荐'}))
        self.assertTrue(card_layout.promo({
            'candidate_name': '某',
            'summary': '普通文本',
            'card_target': {'class_name': 'candidate-card-wrap anonymous-geek-guide-card'},
        }))
        self.assertFalse(card_layout.promo(
            {'candidate_name': '陈书群', 'summary': '广告销售 超声波焊'}))

    def test_choose_skips_promo_card(self):
        promo = {'card_runtime': '1', 'bounds': {'x': 0, 'y': 0}, 'summary': '热搜牛人推荐'}
        real = {'card_runtime': '2', 'bounds': {'x': 0, 'y': 10}, 'summary': '周进 普工'}
        self.assertEqual(card_layout.choose([promo, real], [])['card_runtime'], '2')

    def test_select_scrolls_and_retries_before_returning_candidate(self):
        adapter = object.__new__(workflow_windows.WindowsAdapter)
        adapter.db = object()
        adapter.run = 'r'
        adapter.hwnd = 1
        adapter.allow_ocr = False
        adapter.page_job_recorded = True
        adapter.runtime_checked = True
        adapter.dismiss_related = lambda: None
        real = {'candidate_id': 'x', 'candidate_name': '周进', 'summary': '周进 普工',
                'card_runtime': 'r', 'hwnd': 1,
                'card_target': {'class_name': 'candidate-card-wrap'},
                'bounds': {'x': 0, 'y': 0}}
        responses = [
            {'state': 'no_visible_candidate', 'scroll_target': {'name': 'list'}},
            {'state': 'no_visible_candidate', 'scroll_target': {'name': 'list'}},
            {'state': 'candidate', 'candidate': real, 'candidates': [real]},
        ]
        calls = {'query': 0, 'scroll': 0}

        def query(action, processed=None):
            calls['query'] += 1
            return responses[min(calls['query'] - 1, len(responses) - 1)]

        adapter.query = query
        adapter.invoke = lambda target, action=None: calls.__setitem__('scroll', calls['scroll'] + 1)
        with mock.patch.object(workflow_windows.time, 'sleep', return_value=None), \
                mock.patch.object(workflow_windows.recruiting_rules, 'run_rules', return_value={}), \
                mock.patch.object(workflow_windows.ledger, 'run_row',
                                  return_value={'profile_path': 'profile.md'}):
            selected = adapter.select([])
        self.assertEqual(selected['candidate_name'], '周进')
        self.assertEqual(calls['scroll'], 2)

    def test_select_skips_promo_candidate_card(self):
        adapter = object.__new__(workflow_windows.WindowsAdapter)
        adapter.db = object()
        adapter.run = 'r'
        adapter.hwnd = 1
        adapter.allow_ocr = False
        adapter.page_job_recorded = True
        adapter.runtime_checked = True
        adapter.dismiss_related = lambda: None
        promo = {'candidate_id': 'p', 'candidate_name': '尹**',
                 'summary': '热搜牛人推荐 查看更多', 'card_runtime': 'p', 'hwnd': 1,
                 'card_target': {'class_name': 'candidate-card-wrap anonymous-geek-guide-card'},
                 'bounds': {'x': 0, 'y': 0}}
        real = {'candidate_id': 'x', 'candidate_name': '周进', 'summary': '周进 普工',
                'card_runtime': 'r', 'hwnd': 1,
                'card_target': {'class_name': 'candidate-card-wrap'},
                'bounds': {'x': 0, 'y': 0}}
        responses = [
            {'state': 'candidate', 'candidate': promo, 'candidates': [promo],
             'scroll_target': {'name': 'list'}},
            {'state': 'candidate', 'candidate': real, 'candidates': [real]},
        ]
        calls = {'query': 0, 'scroll': 0}

        def query(action, processed=None):
            calls['query'] += 1
            return responses[min(calls['query'] - 1, len(responses) - 1)]

        adapter.query = query
        adapter.invoke = lambda target, action=None: calls.__setitem__('scroll', calls['scroll'] + 1)
        with mock.patch.object(workflow_windows.time, 'sleep', return_value=None), \
                mock.patch.object(workflow_windows.recruiting_rules, 'run_rules', return_value={}), \
                mock.patch.object(workflow_windows.ledger, 'run_row',
                                  return_value={'profile_path': 'profile.md'}):
            selected = adapter.select([])
        self.assertEqual(selected['candidate_name'], '周进')
        self.assertEqual(calls['scroll'], 1)


if __name__ == '__main__':
    unittest.main()
