"""Hybrid UIA adapter: one browser handoff covers foreground-only screenshot capture."""
from pathlib import Path
import json
import uuid

import browser_bridge
import capture_resume
import ledger
import safe_action
import ui_features
from workflow_paths import workflow_dir
from workflow_windows import WindowsAdapter


class HybridAdapter(WindowsAdapter):
    """Keep UIA work in-process; use Browser only for required screenshots."""
    def __init__(self, db, run, root, hwnd, tab_binding, allow_ocr=True):
        super().__init__(db, run, root, hwnd, allow_ocr=allow_ocr)
        self.binding = browser_bridge.validate_binding(tab_binding)
        self.bridge = browser_bridge.Bridge(db, run, self.binding)

    def capture(self, candidate, folder):
        output_dir = Path(folder).resolve()
        result = self.bridge.request('capture', dict(
            candidate=candidate, mode='resume', output_dir=str(output_dir)), timeout=180)
        capture = {key: value for key, value in result.items() if key != 'candidate'}
        return capture_resume.import_browser_capture(
            self.db, self.run, candidate['candidate_id'], output_dir, capture)


class BrowserAdapter:
    def __init__(self, db, run, root, tab_binding, allow_ocr=True):
        self.db, self.run, self.root = db, run, Path(root)
        self.allow_ocr = allow_ocr
        self.folder = workflow_dir(run)
        self.bridge = browser_bridge.Bridge(db, run, tab_binding)
        self.processed = []

    def call(self, operation, candidate=None, mode=None, timeout=120, **arguments):
        if candidate is not None:
            arguments['candidate'] = candidate
        if mode is not None:
            arguments['mode'] = mode
        return self.bridge.request(operation, arguments, timeout=timeout)

    def select(self, processed):
        self.processed = processed
        result = self.call('select', processed=processed)
        observed = result.get('page_job')
        key = 'boss_page_job/' + self.run
        if observed and not self.db.execute('SELECT 1 FROM settings WHERE key=?', (key,)).fetchone():
            _, _, fields = ledger.profile_check(Path(ledger.run_row(self.db, self.run)['profile_path']))
            display = observed.get('display_name')
            observed['name_mismatch'] = bool(display and not all(fields[k] in display for k in ('company', 'position')))
            observed['warning'] = (f"🔴注意：BOSS右上角显示“{display}”，与本轮目标“{fields['company']} {fields['position']}”不一致；按用户选定岗位继续，不暂停。"
                                   if observed['name_mismatch'] else None)
            self.db.execute('INSERT INTO settings VALUES (?,?)', (key, json.dumps(observed, ensure_ascii=False)))
        candidate = result.get('candidate')
        if candidate is None:
            return None
        if not all(candidate.get(k) for k in ('candidate_id', 'candidate_name', 'card_runtime')):
            raise ValueError('browser_plugin_candidate_identity_missing')
        return candidate

    def filter_state(self):
        return self.call('filter_state')

    def open(self, candidate, mode):
        result = self.call('open', candidate, mode)
        if result.get('state') != 'opened' or result.get('candidate_id') != candidate['candidate_id']:
            raise ValueError('resume_not_opened')

    def prefilter(self, candidate):
        return self.call('prefilter', candidate)

    def platform_contact_state(self, candidate, mode):
        result = self.call('platform_state', candidate, mode)
        if result.get('label') not in ('打招呼', '继续沟通', '继续打招呼'):
            raise ValueError('browser_plugin_greeting_control_unavailable')
        return dict(result, already_contacted=result['label'] != '打招呼')

    def colleague(self, candidate, mode):
        try:
            return self.call('colleague', candidate, mode, timeout=5)
        except ValueError as exc:
            if 'request_expired' not in str(exc):
                raise
            return dict(state='unavailable', lookup_completed=False, evidence='coworker_timeout_5s', timeout_seconds=5)

    def complete_visual(self, candidate, answer):
        return self.call('complete_visual', candidate, answer=answer)

    def skip_evidence(self, candidate, mode):
        return {}

    def read(self, candidate, mode):
        if mode == 'card':
            return self.call('read', candidate, mode, capture_images=False)
        folder = self.folder / ('browser-resume-' + uuid.uuid4().hex)
        folder.mkdir(parents=True)
        result = self.call('read', candidate, mode, timeout=180,
                           output_dir=str(folder), capture_images=self.allow_ocr)
        complete = result.get('read_complete') is True
        text = '\n'.join(dict.fromkeys(result.get(k, '').strip() for k in (
            'keyword_text', 'resume_text', 'overview_text', 'expectation_text',
            'advantage_text', 'experience_text', 'education_text', 'project_text')
            if isinstance(result.get(k), str) and result[k].strip()))
        result.update(keyword_text=text, read_source='browser_plugin', read_complete=False)
        if self.allow_ocr and complete:
            evidence = capture_resume.import_browser_capture(self.db, self.run, candidate['candidate_id'], folder, result.get('capture', {}))
            result['resume_evidence'] = evidence['resume_evidence']
            ocr_text = Path(evidence['resume_evidence']['ocr_text']).read_text(encoding='utf-8-sig').strip()
            result['keyword_text'] = '\n'.join(dict.fromkeys(part for part in (text, ocr_text) if part))
            result['read_source'] = 'browser_plugin_and_local_ocr'
            result['read_complete'] = True
        elif not self.allow_ocr:
            result['read_complete'] = complete
            result['resume_save_note'] = '本轮明确关闭OCR；使用浏览器已核验的完整可读材料。'
        else:
            result['read_warning'] = result.get('read_warning') or '浏览器未确认简历完整采集'
        return result

    def send(self, candidate, mode):
        safe_action.business_check(self.db, self.run, candidate['candidate_id'])
        state = self.platform_contact_state(candidate, mode)
        if state['already_contacted']:
            return dict(state='not-sent', reason='platform_already_contacted')
        # The scheduler has already reserved a shared rate-limit slot and saved
        # phase=verify. A lost browser reply therefore resumes with inspection.
        result = self.call('send', candidate, mode)
        if result.get('state') == 'sent' and result.get('label') not in ('继续沟通', '继续打招呼'):
            return dict(state='unknown')
        return result if result.get('state') in ('sent', 'not-sent', 'unknown') else dict(state='unknown')

    def verify(self, candidate, mode):
        result = self.call('verify', candidate, mode)
        if result.get('label') in ('继续沟通', '继续打招呼'):
            return dict(state='sent')
        if result.get('label') == '打招呼':
            return dict(state='not-sent', may_retry=True)
        return dict(state='unknown')

    def favorite(self, candidate, mode):
        return ui_features.favorite(self.db, self.run, candidate['candidate_id'],
            reader=lambda action, hwnd: dict(self.call('favorite_state', candidate, mode), target={}),
            click=lambda db, run, target: self.call('favorite', candidate, mode))

    def close(self):
        result = self.call('close')
        if result.get('state') not in ('closed', 'already_closed'):
            raise ValueError('browser_plugin_resume_close_unconfirmed')

    def next(self, candidate, mode):
        self.close()
        return dict(returned_to_list=True)
