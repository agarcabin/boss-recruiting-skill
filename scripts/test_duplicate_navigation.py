import sqlite3
import unittest
import safe_action


class DuplicateNavigationTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        self.db.row_factory=sqlite3.Row
        self.db.executescript('CREATE TABLE candidates(candidate_hash TEXT,status TEXT); CREATE TABLE message_attempts(candidate_hash TEXT,status TEXT);')
        self.db.execute("INSERT INTO candidates VALUES ('seen','skipped')")
        self.run={'evaluation_mode':'resume'}
        self.target={'duplicate_navigation':True}

    def tearDown(self):
        self.db.close()

    def check(self,action='key',key='Escape',active=None,token=None,digest='seen'):
        return safe_action.validate_candidate_target(self.db,self.run,action,self.target,active,digest,token,key)

    def test_resolved_duplicate_can_leave_without_new_active_candidate(self):
        for status in ('skipped','review','sent'):
            self.db.execute('UPDATE candidates SET status=?',(status,))
            for key in ('Escape','Right','Left'):
                self.check(key=key)

    def test_duplicate_cannot_send_or_open_unrelated_control(self):
        for action in ('invoke','mouse','send-text'):
            with self.assertRaises(ValueError): self.check(action=action)
        with self.assertRaises(ValueError): self.check(token='attempt')

    def test_unseen_or_unresolved_candidate_is_blocked(self):
        with self.assertRaises(ValueError): self.check(digest='unseen')
        for status in ('pending','unknown'):
            self.db.execute('UPDATE candidates SET status=?',(status,))
            with self.assertRaises(ValueError): self.check()

    def test_unresolved_message_is_blocked(self):
        for status in ('pending','dispatching','unknown'):
            self.db.execute('DELETE FROM message_attempts')
            self.db.execute("INSERT INTO message_attempts VALUES ('seen',?)",(status,))
            with self.assertRaises(ValueError): self.check()

    def test_active_other_candidate_and_card_mode_are_blocked(self):
        with self.assertRaises(ValueError): self.check(active={'candidate_hash':'other'})
        self.run['evaluation_mode']='card'
        with self.assertRaises(ValueError): self.check()

    def test_duplicate_flag_required(self):
        self.target={}
        with self.assertRaises(ValueError): self.check()

    def test_arrow_requires_resume_and_overlay_binding(self):
        self.target.update(class_name='turn-btn next')
        with self.assertRaises(ValueError): self.check(action='invoke')
        self.target.update(candidate_scope_runtime_id=[1],navigation_resume_runtime_id=[2])
        self.check(action='invoke')

    def test_original_active_candidate_path_is_unchanged(self):
        self.target={}
        self.check(action='invoke',active={'candidate_hash':'seen'})


if __name__=='__main__': unittest.main()
