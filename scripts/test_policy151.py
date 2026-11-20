import copy
import hashlib
import json
import os
import argparse
import contextlib
import io
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

import chat_watchdog
import hr_job
import install_engine
import migrate_policy151
import overall_review
import preferred_locations
import release_builder

TEMPLATE = Path(__file__).resolve().parents[1]/'docs/HR-JOB-TEMPLATE.md'


def config():
    return hr_job.parse(TEMPLATE.read_text(encoding='utf-8').replace('{{岗位名称}}', '测试岗位'))


def rules(below=False, passing=False):
    job = config()
    job.update(overall_review=below, overall_review_on_pass=passing, preferred_locations=[], preferred_location_filter_enabled=True)
    job['resume'] = dict(groups={'A':['仓管']}, terms=[['A']], negative=['销售'])
    return dict(current_rules=20261115, review_policy_version=151, hr_job_config=job)


def answer(request, suitable):
    return dict(request_id=request['request_id'], suitable=suitable, reason='根据原文判断',
                pros='有相关经历', cons='需核实具体职责', quotes=['仓管'])


class Review151Tests(unittest.TestCase):
    def test_independent_switches_and_equality(self):
        for below in (False, True):
            for passing in (False, True):
                for text, enabled in (('仓管', passing), ('仓管 销售', below)):
                    with self.subTest(below=below, passing=passing, text=text):
                        req = overall_review.request(rules(below, passing), dict(keyword_text=text, read_complete=True))
                        self.assertEqual(req is not None, enabled)
                        if req:self.assertEqual(req['branch'], 'passing' if text == '仓管' else 'deduction')

    def test_review_can_veto_or_rescue_without_score_change(self):
        for text, baseline in (('仓管', 60), ('仓管 销售', 50)):
            r = rules(True, True)
            facts = dict(keyword_text=text, read_complete=True)
            self.assertFalse(hr_job.assessment(r, facts)['eligible'])
            req = overall_review.request(r, facts)
            for suitable in (True, False):
                result = hr_job.assessment(r, dict(facts, overall_review=answer(req, suitable)))
                self.assertEqual(result['eligible'], suitable)
                self.assertEqual(result['score'], baseline)

    def test_unqualified_incomplete_and_location_cannot_review(self):
        r = rules(True, True)
        for facts in (dict(keyword_text='销售', read_complete=True), dict(keyword_text='仓管', read_complete=False)):
            self.assertIsNone(overall_review.request(r, facts))
        r['hr_job_config']['preferred_locations'] = ['宁波市']
        facts = dict(keyword_text='仓管', read_complete=True, preferred_location_observation=dict(state='present', text='温州市'))
        self.assertIsNone(overall_review.request(r, facts))
        self.assertEqual(hr_job.assessment(r, facts)['trigger'], 'location_mismatch')

    def test_persona_and_evidence_invalidate_response(self):
        r = rules(False, True)
        facts = dict(keyword_text='仓管', read_complete=True)
        req = overall_review.request(r, facts)
        saved = answer(req, True)
        r['hr_job_config']['overall_review_rules'] = '当前画像变更'
        with self.assertRaisesRegex(ValueError, 'stale'):
            overall_review.validate(saved, overall_review.request(r, facts))
        with self.assertRaisesRegex(ValueError, 'original_quotes'):
            overall_review.validate(dict(answer(overall_review.request(r, facts), True), quotes=['不存在的原文']), overall_review.request(r, facts))

    def test_legacy_request_and_outstanding_response_unchanged(self):
        r = rules(True, True)
        r.pop('review_policy_version')
        facts = dict(keyword_text='仓管 销售', read_complete=True)
        before = overall_review._legacy_request(copy.deepcopy(r), copy.deepcopy(facts))
        self.assertEqual(before, overall_review.request(r, facts))
        self.assertTrue(overall_review.apply(r, dict(facts, overall_review=answer(before, True)), dict(eligible=False))['eligible'])

    def test_list_veto_even_when_score_would_pass(self):
        r = rules()
        terms = ['仓管','库存','出库','入库','盘点','装卸','包装','物流']
        r['hr_job_config']['list'] = dict(groups={'A':terms}, terms=[['A']], negative=['销售'])
        facts = dict(raw_text=' '.join(terms)+' 销售')
        result = hr_job.list_assessment(r, facts)
        self.assertGreaterEqual(result['score'], result['qualifying_score'])
        self.assertTrue(result['vetoed'])
        self.assertEqual(result['negative_penalty'], 0)
        self.assertFalse(result['eligible'])
        self.assertFalse(hr_job.list_assessment(r, dict(raw_text='仓管，不做销售'))['eligible'])
        self.assertFalse(hr_job.list_assessment(r, dict(raw_text='仓管，负责销售团队'))['eligible'])
        r.pop('review_policy_version')
        self.assertTrue(hr_job.list_assessment(r, facts)['eligible'])


class Locations151Tests(unittest.TestCase):
    def test_short_county_and_county_city_keep_administrative_identity(self):
        full=['宁波市','宁波市余姚市','台州市天台县']
        short=['宁波市','余姚市','天台县']
        self.assertEqual(preferred_locations.resolve_allowed_places(full),preferred_locations.resolve_allowed_places(short))
        job=dict(preferred_locations=short)
        for name in ('余姚市','宁波市余姚市','天台县','台州市天台县'):
            self.assertEqual(preferred_locations.evaluate(job,dict(preferred_location_observation=dict(state='present',text=name)))['state'],'match')
        self.assertEqual(preferred_locations.evaluate(job,dict(preferred_location_observation=dict(state='present',text='台州市椒江区')))['state'],'mismatch')
    def test_explicit_off_bypasses_locations_and_legacy_missing_switch_stays_enabled(self):
        job=dict(preferred_locations=['宁波市'],preferred_location_filter_enabled=False)
        facts=dict(preferred_location_observation=dict(state='present',text='温州市'))
        self.assertEqual(preferred_locations.evaluate(job,{})['state'],'disabled')
        self.assertEqual(preferred_locations.evaluate(job,facts)['state'],'disabled')
        job.pop('preferred_location_filter_enabled')
        self.assertEqual(preferred_locations.evaluate(job,facts)['state'],'mismatch')
    def test_short_target_district_uses_explicit_job_city_only(self):
        job=dict(preferred_locations=['深圳市','南山区'])
        observe=lambda text:preferred_locations.evaluate(job,dict(preferred_location_observation=dict(state='present',text=text)))['state']
        self.assertEqual(observe('深圳市南山区'),'match')
        self.assertEqual(observe('鹤岗市南山区'),'mismatch')
        self.assertEqual(observe('南山区'),'unknown')
        self.assertIsNone(preferred_locations.resolve_allowed_places(['上海市','舟山市','普陀区']))
    def observed(self, text, allowed=None):
        return preferred_locations.evaluate(dict(preferred_locations=allowed or ['宁波市','宁波市鄞州区']),
                 dict(preferred_location_observation=dict(state='present', text=text)))['state']

    def test_explicit_city_district_and_suffixes(self):
        for text in ('宁波', '宁波市', '鄞州区', '浙江省宁波市·鄞州区', '宁波市、鄞州区', '宁波鄞州'):
            self.assertEqual(self.observed(text), 'match', text)
        self.assertEqual(self.observed('宁波市北仑区'), 'mismatch')
        self.assertEqual(self.observed('宁波市、北仑区'), 'mismatch')
        self.assertEqual(self.observed('宁波市、慈溪市'), 'mismatch')
        self.assertEqual(self.observed('宁波、慈溪'), 'mismatch')

    def test_unknown_and_absent_are_distinct(self):
        job = dict(preferred_locations=['甲市'])
        self.assertEqual(preferred_locations.evaluate(job, {})['state'], 'absent')
        self.assertEqual(preferred_locations.evaluate(job, dict(preferred_location_observation=dict(state='absent')))['state'], 'absent')
        self.assertEqual(preferred_locations.evaluate(job, dict(preferred_location_observation=dict(state='unknown', reason='unique_analyzer_panel_unavailable')))['state'], 'absent')
        self.assertEqual(preferred_locations.evaluate(dict(preferred_locations=[]), {})['state'], 'disabled')

    def test_any_preference_and_ambiguous_district(self):
        self.assertEqual(self.observed('乙市、宁波市'), 'match')
        self.assertEqual(self.observed('全国'), 'match')
        self.assertEqual(self.observed('鼓楼区', ['福州市鼓楼区']), 'unknown')
        self.assertEqual(self.observed('南京市鼓楼区', ['福州市鼓楼区']), 'mismatch')
        self.assertEqual(self.observed('南山区', ['深圳市南山区']), 'unknown')
        self.assertEqual(self.observed('鹤岗市南山区', ['深圳市南山区']), 'mismatch')
        self.assertEqual(self.observed('尚未确认的新区', ['深圳市南山区']), 'unknown')
        self.assertEqual(self.observed('长沙县', ['长沙市']), 'mismatch')
        self.assertEqual(self.observed('南昌县', ['南昌市']), 'mismatch')
        self.assertEqual(self.observed('长沙', ['长沙市']), 'unknown')
        self.assertEqual(self.observed('宁波市', ['未确认新区']), 'unknown')


class Migration151Tests(unittest.TestCase):
    def test_heading_switch_and_place_list_are_separate(self):
        text=TEMPLATE.read_text(encoding='utf-8').replace('{{岗位名称}}','岗位示例')
        text+='\n温州市、龙湾区\n'
        job=hr_job.parse(text)
        self.assertFalse(job['preferred_location_filter_enabled'])
        self.assertEqual(job['preferred_locations'],['温州市','龙湾区'])
        enabled=hr_job.parse(text.replace('偏好地点筛选：关','偏好地点筛选：开'))
        self.assertTrue(enabled['preferred_location_filter_enabled'])
        self.assertEqual(hr_job.parse(text.replace('偏好地点筛选：关','## 偏好地点筛选：关')),job)
        legacy=hr_job.parse(text.replace('偏好地点筛选：关\n',''))
        self.assertTrue(legacy['preferred_location_filter_enabled'])
        with self.assertRaises(hr_job.ConfigError):
            hr_job.parse(text.replace('偏好地点筛选：关','偏好地点筛选：关\n偏好地点筛选：开'))
    def test_note_and_district_display_preserve_configuration(self):
        text=TEMPLATE.read_text(encoding='utf-8').replace('{{岗位名称}}','岗位示例')
        text=text.replace('## 偏好地点筛选','注释：以上为基准值，保留按实际平均速度上下浮动最多 5 秒。\n\n## 偏好地点筛选')
        text+='\n温州市、温州市龙湾区、温州市永嘉县\n'
        before=hr_job.parse(text)
        updated=migrate_policy151.format_document(text)
        after=hr_job.parse(updated)
        old_places=before.pop('preferred_locations');new_places=after.pop('preferred_locations')
        self.assertEqual(before,after)
        self.assertEqual(new_places,['温州市','龙湾区','永嘉县'])
        self.assertIn('\n偏好地点筛选：关\n',updated)
        self.assertNotIn('## 偏好地点筛选：关',updated)
        self.assertEqual(preferred_locations.resolve_allowed_places(old_places),preferred_locations.resolve_allowed_places(new_places))
        self.assertNotIn('注释：',updated)
        self.assertNotIn('以上为基准值',updated)
        self.assertEqual(migrate_policy151.format_document(updated),updated)
    def test_install_failure_rolls_back_code_and_all_job_files(self):
        import ledger
        import vault_crypto
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, BOSS_DESKTOP_DIR=str(Path(folder)/'desktop'), BOSS_STATE_DIR=str(Path(folder)/'state')):
            base = Path(folder)
            root = base/'skill'
            root.mkdir()
            (root/'SKILL.md').write_bytes(b'old code')
            jobs = [base/'desktop/自动招呼/02 招呼配置'/f'{i}.md' for i in range(2)]
            for job in jobs:job.parent.mkdir(parents=True,exist_ok=True);job.write_bytes(b'before')
            database = base/'ledger.sqlite3'
            ledger.connect(database).close()
            files = {'SKILL.md':b'new code','release-manifest.json':b'{"version":"1.5.1"}'}
            changes = [dict(path=str(job),before_sha256=hashlib.sha256(b'before').hexdigest(),data=b'after') for job in jobs]
            real_atomic = vault_crypto.atomic
            def fail_second(path,data):
                if Path(path) == jobs[1] and data == b'after':raise OSError('simulated activation failure')
                return real_atomic(path,data)
            with patch('install_engine.atomic',side_effect=fail_second):
                with self.assertRaisesRegex(OSError,'simulated'):
                    install_engine.install(root,files,base/'backups',database,config_changes=changes)
            self.assertEqual((root/'SKILL.md').read_bytes(),b'old code')
            self.assertFalse((root/'release-manifest.json').exists())
            for job in jobs:self.assertEqual(job.read_bytes(),b'before')
            with contextlib.closing(ledger.connect(database)) as db:
                self.assertEqual(db.execute('SELECT maintenance FROM installation_admission').fetchone()[0],0)

    def test_aliases_and_duplicate_alias(self):
        text = TEMPLATE.read_text(encoding='utf-8').replace('{{岗位名称}}','测试岗位')
        new = hr_job.parse(text)
        self.assertEqual(new, hr_job.parse(text.replace('AI优缺点判断：','AI总评：')))
        with self.assertRaises(hr_job.ConfigError):hr_job.parse(text.replace('AI优缺点判断：关', 'AI优缺点判断：关\nAI总评：关'))

    def test_migration_defaults_and_idempotence(self):
        # Exercise an actual old-layout document, including the old list label.
        text = TEMPLATE.read_text(encoding='utf-8').replace('{{岗位名称}}', 'ExampleEntity65（普工）')
        text = text.split('## AI整体复盘规则')[0]
        text = text.replace('过及格线就进行AI整体复盘：关', '').replace('过及格线就进行AI整体复盘：开','')
        text = text.replace('### 2. 否决词库','### 2. 减分词库')
        migrated = migrate_policy151.render(text, '从事装配操作', ['甲市','乙市'])
        parsed = hr_job.parse(migrated)
        self.assertTrue(parsed['overall_review'])
        self.assertFalse(parsed['overall_review_on_pass'])
        self.assertEqual(parsed['preferred_locations'], ['甲市','乙市'])
        self.assertNotIn('目标角色', parsed['overall_review_rules'])
        self.assertEqual(migrate_policy151.render(migrated, '不能覆盖', ['丙市']), migrated)
        other = hr_job.parse(migrate_policy151.render(text.replace('ExampleEntity65（普工）','仓管'), '仓库工作', []))
        self.assertFalse(other['overall_review'])
        self.assertTrue(other['overall_review_on_pass'])

    def test_joint_restore_restores_code_and_external_config(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            root, backup = base/'skill', base/'backup'
            root.mkdir();backup.mkdir()
            job = base/'desktop/自动招呼/02 招呼配置/岗位.md'
            job.parent.mkdir(parents=True)
            job.write_bytes(b'after')
            (root/'SKILL.md').write_bytes(b'new-code')
            (backup/'SKILL.md').write_bytes(b'old-code')
            (backup/'job.md').write_bytes(b'before')
            digest = lambda b: hashlib.sha256(b).hexdigest()
            record = dict(files={'SKILL.md':dict(existed=True, sha256=digest(b'old-code'))},
                config_files=[dict(path=str(job),backup='job.md',sha256=digest(b'before'),after_sha256=digest(b'after'))])
            write_order = []
            import vault_crypto
            def record_write(path, data):
                write_order.append(Path(path))
                return vault_crypto.atomic(path, data)
            with patch.dict(os.environ, BOSS_DESKTOP_DIR=str(base/'desktop')),patch('install_engine.atomic',side_effect=record_write):
                install_engine.restore(root,backup,record)
            self.assertLess(write_order.index(job), write_order.index(root/'SKILL.md'))
            self.assertEqual(job.read_bytes(), b'before')
            self.assertEqual((root/'SKILL.md').read_bytes(), b'old-code')

    def test_stable_override_keeps_default_channel(self):
        with patch('release_builder.subprocess.run') as call:
            call.return_value.stdout = 'codex/wecom-cloud-knowledge\n'
            self.assertEqual(release_builder.release_version('.', '1.5.1'), '1.5.1-beta')
            self.assertEqual(release_builder.release_version('.', '1.5.1', 'stable'), '1.5.1')


class Watchdog151Tests(unittest.TestCase):
    def test_stale_monitor_never_keeps_showing_active(self):
        state=dict(measured='active',checked_at=15)
        self.assertEqual(chat_watchdog.display_state(state,30)['measured'],'active')
        self.assertEqual(chat_watchdog.display_state(state,61)['measured'],'unknown')
        self.assertNotIn('alert',state)
    def test_watchdog_pauses_once_and_preserves_alert_for_uia_only_binding(self):
        import ledger
        from test_hr_job import document
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, BOSS_STATE_DIR=str(Path(folder)/'state')):
            root = Path(folder)
            profile=root/'Company/job.md';profile.parent.mkdir()
            profile.write_text(document(resume_words='仓管'),encoding='utf-8')
            with contextlib.closing(ledger.connect(root/'ledger.sqlite3')) as db:
                with patch.object(ledger,'PROFILE_ROOT',root),contextlib.redirect_stdout(io.StringIO()):
                    ledger.start(db,argparse.Namespace(profile=profile,target=1,max_views=2,min_score=60))
                run_id=db.execute('SELECT run_id FROM runs').fetchone()[0]
                request=root/'request.json';request.write_text('{"kind":"summary"}',encoding='utf-8')
                data=dict(handoff_kind='summary',request_file=str(request),response_file=str(root/'response.json'))
                db.execute('CREATE TABLE workflow_state(run_id TEXT PRIMARY KEY,phase TEXT,payload TEXT)')
                db.execute('INSERT INTO workflow_state VALUES (?,?,?)',(run_id,'summarize',json.dumps(data)))
                db.execute('UPDATE runs SET stop_binding=?',(json.dumps(dict(kind='uia')),))
                calls=[]
                def transport(binding,run,resume=False):
                    calls.append(resume)
                    return dict(state='unsupported',reason='自动续发不可用') if resume else dict(state='idle')
                with patch('error_alert.play'):
                    for at in (15,30,45):state=chat_watchdog.tick(db,run_id,at,transport)
                    self.assertEqual(ledger.control_state(db,run_id),'paused')
                    state=chat_watchdog.tick(db,run_id,60,transport)
                    self.assertEqual(state['alert'],'自动续发不可用')
                    with contextlib.redirect_stdout(io.StringIO()):ledger.control(db,argparse.Namespace(run=run_id,action='resume'))
                    state=chat_watchdog.tick(db,run_id,75,transport)
                    self.assertEqual(ledger.control_state(db,run_id),'running')
                    def pausing_transport(binding,run,resume=False):
                        if not resume:
                            with contextlib.redirect_stdout(io.StringIO()):ledger.control(db,argparse.Namespace(run=run,action='pause'))
                        return transport(binding,run,resume)
                    state=chat_watchdog.tick(db,run_id,76,pausing_transport)
                    saved=json.loads(db.execute('SELECT payload FROM chat_recovery_episodes WHERE run_id=?',(run_id,)).fetchone()[0])
                    self.assertTrue(saved['attempted'])
                    with contextlib.redirect_stdout(io.StringIO()):ledger.control(db,argparse.Namespace(run=run_id,action='resume'))
                    state=chat_watchdog.tick(db,run_id,90,transport)
                    self.assertEqual(ledger.control_state(db,run_id),'running')
                    state=chat_watchdog.tick(db,run_id,135,transport)
                    self.assertEqual(ledger.control_state(db,run_id),'paused')
                self.assertEqual(calls.count(True),1)
                self.assertEqual(db.execute('SELECT COUNT(*) FROM chat_recovery_episodes WHERE run_id=?',(run_id,)).fetchone()[0],1)
                # A different request earns a new budget, but a manual pause
                # breaks the three-sample sequence without replenishing it.
                request.write_text('{"kind":"summary","evidence":{"new_checkpoint":true}}',encoding='utf-8')
                with patch('error_alert.play'),contextlib.redirect_stdout(io.StringIO()):
                    ledger.control(db,argparse.Namespace(run=run_id,action='resume'))
                    chat_watchdog.tick(db,run_id,150,transport)
                    chat_watchdog.tick(db,run_id,165,transport)
                    ledger.control(db,argparse.Namespace(run=run_id,action='pause'))
                    chat_watchdog.tick(db,run_id,180,transport)
                    ledger.control(db,argparse.Namespace(run=run_id,action='resume'))
                    chat_watchdog.tick(db,run_id,195,transport)
                    self.assertEqual(calls.count(True),1)
                    chat_watchdog.tick(db,run_id,210,transport)
                    self.assertEqual(calls.count(True),1)
                    chat_watchdog.tick(db,run_id,225,transport)
                    self.assertEqual(calls.count(True),2)
                    request.write_text('{"kind":"summary","evidence":{"new_checkpoint":2}}',encoding='utf-8')
                    ledger.control(db,argparse.Namespace(run=run_id,action='resume'))
                    chat_watchdog.tick(db,run_id,240,transport)
                    chat_watchdog.tick(db,run_id,255,transport)
                    ledger.control(db,argparse.Namespace(run=run_id,action='pause'))
                    ledger.control(db,argparse.Namespace(run=run_id,action='resume'))
                    chat_watchdog.tick(db,run_id,270,transport)
                    self.assertEqual(calls.count(True),2)
                    chat_watchdog.tick(db,run_id,285,transport)
                    self.assertEqual(calls.count(True),2)
                    chat_watchdog.tick(db,run_id,300,transport)
                    self.assertEqual(calls.count(True),3)

    def test_active_sample_does_not_hide_later_idle_or_user_stop(self):
        state = dict(episode='r',attempted=True,attempted_at=0)
        state, action = chat_watchdog.transition(state,'r',dict(state='active'),15)
        self.assertEqual(action,'none')
        for at in (30,45,60,75):state, action = chat_watchdog.transition(state,'r',dict(state='idle'),at)
        self.assertEqual(action,'pause')
        self.assertTrue(state['attempted'])
        _, action = chat_watchdog.transition(state,'r',dict(state='user_stop'),90)
        self.assertEqual(action,'pause')

    def test_partial_response_does_not_reset_pending_checkpoint(self):
        with tempfile.TemporaryDirectory() as folder:
            request=Path(folder)/'request.json';response=Path(folder)/'response.json'
            request.write_text('{"kind":"summary","evidence":{}}',encoding='utf-8')
            data=dict(handoff_kind='summary',request_file=str(request),response_file=str(response))
            fingerprint=chat_watchdog.pending(data)
            response.write_text('{"pros":',encoding='utf-8')
            self.assertEqual(chat_watchdog.pending(data),fingerprint)
            response.write_text('{"pros":"已读优点","cons":"已读缺点"}',encoding='utf-8')
            self.assertIsNone(chat_watchdog.pending(data))

    def test_child_lifetime_mutex_prevents_duplicate_monitor(self):
        import local_mutex
        import sys
        with tempfile.TemporaryDirectory() as folder:
            database=Path(folder)/'state.sqlite3'
            key='chat-watchdog-instance:'+str(database.resolve())+':run1'
            with local_mutex.locked(key),patch.object(sys,'argv',['chat_watchdog.py','--db',str(database),'--run','run1']),patch('chat_watchdog.ledger.connect') as connect:
                child=threading.Thread(target=chat_watchdog.main)
                child.start();child.join(2)
                self.assertFalse(child.is_alive())
                connect.assert_not_called()

    def test_three_idles_and_unknown_reset(self):
        state = {}
        for at, obs, action in ((15,'idle','none'),(30,'idle','none'),(45,'unknown','none'),(60,'idle','none'),(75,'idle','none'),(90,'idle','recover')):
            state, got = chat_watchdog.transition(state, 'request1', dict(state=obs), at)
            self.assertEqual(got, action)

    def test_attempt_timeout_and_no_second_dispatch(self):
        state = dict(episode='r', attempted=True, attempted_at=45)
        for at, want in ((60,'none'), (75,'none'), (90,'pause')):
            state, got = chat_watchdog.transition(state, 'r', dict(state='idle'), at)
            self.assertEqual(got, want)
        state, got = chat_watchdog.transition(state, 'new-request', dict(state='idle'), 105)
        self.assertEqual(got, 'none')
        self.assertNotIn('attempted', state)

    def test_busy_long_thinking_and_paused_do_not_restart(self):
        state, _ = chat_watchdog.transition(dict(episode='r',attempted=True,attempted_at=10), 'r', dict(state='active'), 20)
        for at in (60,600):
            state, action = chat_watchdog.transition(state,'r',dict(state='active'),at)
            self.assertEqual(action,'none')
        state, action = chat_watchdog.transition(state,None,dict(state='idle'),615)
        self.assertEqual(action,'none')
        self.assertEqual(state['strikes'],0)

    def test_uia_dispatch_is_unsupported_without_mutation(self):
        with patch('chat_watchdog.subprocess.run') as native:
            result = chat_watchdog.probe(dict(kind='uia'), 'run1', resume=True)
            self.assertEqual(result['state'], 'unsupported')
            native.assert_not_called()
        with patch('chat_watchdog.subprocess.run') as native:
            result=chat_watchdog.probe(dict(kind='app_server',desktop_thread_verified=True),'run1',resume=True)
            self.assertEqual(result['state'],'unsupported')
            native.assert_not_called()


if __name__ == '__main__':unittest.main()
