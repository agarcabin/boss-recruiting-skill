"""Small, checked local hooks; preserves unrelated installed-version modifications."""
from pathlib import Path
import re


FILES = ('project_registry.py', 'ledger.py', 'recruiting_rules.py', 'coworker_progress.py', 'workflow_runner.py')


def once(text, old, new):
    if text.count(old) != 1:
        raise ValueError('安装文件结构已变化：'+old[:70])
    return text.replace(old, new, 1)


def patched(name, text):
    if 'hr_job' in text:
        raise ValueError('文件已包含HR配置逻辑，请先检查版本：'+name)
    if name == 'project_registry.py':
        anchor = 'def front_matter(path: Path) -> dict[str, str]:\n    content = path.read_text(encoding="utf-8-sig")\n'
        return once(text, anchor, anchor+'    import hr_job\n    if hr_job.is_hr(content):\n        return hr_job.fields(path, content)\n')
    if name == 'ledger.py':
        anchor = 'def profile_check(path: Path) -> tuple[bool, str, dict[str, str]]:\n    if not path.is_file():\n        return False, "profile_missing", {}\n    content = path.read_text(encoding="utf-8-sig")\n'
        return once(text, anchor, anchor+'''    import hr_job
    if hr_job.is_hr(content):
        try:
            return True, 'ready', hr_job.fields(path, content)
        except (ValueError, OSError) as exc:
            return False, str(exc), {}
''')
    if name == 'recruiting_rules.py':
        anchor = 'def snapshot(profile: Path, fields: dict, greeting_mode: str | None = None) -> dict:\n'
        text = once(text, anchor, anchor+'''    import hr_job
    if hr_job.is_hr(profile.read_text(encoding='utf-8-sig')):
        return hr_job.snapshot(profile)
''')
        anchor = 'def evaluate(rules: dict, payload: dict, min_score: int) -> dict:\n'
        text = once(text, anchor, anchor+'''    if 'hr_job_config' in rules:
        import hr_job
        return hr_job.assessment(rules, payload)
''')
        anchor = 'def list_match(rules, payload):\n'
        return once(text, anchor, anchor+'''    if 'hr_job_config' in rules:
        import hr_job
        return hr_job.list_assessment(rules, payload)
''')
    if name == 'coworker_progress.py':
        text = once(text, 'def evaluate(observation: dict | None, at: datetime | None = None) -> dict:',
                    'def evaluate(observation: dict | None, at: datetime | None = None, threshold_days=7) -> dict:')
        text = once(text, '"threshold_days": 7,', '"threshold_days": threshold_days,')
        text = once(text, 'if stamp>=at-timedelta(days=7):', 'if stamp>=at-timedelta(days=threshold_days):')
        text = once(text, ",reason='coworker_within_or_exactly_7_days')", ",reason=f'coworker_within_or_exactly_{threshold_days:g}_days')")
        text = once(text, "reason='all_coworker_contacts_older_than_7_days')", "reason=f'all_coworker_contacts_older_than_{threshold_days:g}_days')")
        return once(text, '    result = evaluate(observation, at)\n', "    result = evaluate(observation, at, rules.get('hr_job_config', {}).get('coworker_days', 7))\n")
    if name == 'workflow_runner.py':
        text = once(text, '        phase=self.phase\n', "        phase=self.phase\n        hr_timing = 'hr_job_config' in recruiting_rules.run_rules(run)\n")
        pattern = r"(?m)^( +)(call\(ledger\.electronic_opened,self\.db,run=self\.run,candidate_id=cid\))$"
        text, count = re.subn(pattern, r"\1\2\n\1if hr_timing:self.data['resume_started_active']=short_view_wait.active_clock(self.db,self.run)", text)
        if count != 3:
            raise ValueError('未找到三个简历打开计时入口')
        anchor = "            if self.data.get('handoff_kind')=='assessment':\n"
        text = once(text, anchor, '''            if hr_timing:
                result=recruiting_rules.evaluate(rules,facts,run['min_score'])
                payload=fast_assessment.fill(facts,result)
            elif self.data.get('handoff_kind')=='assessment':
''')
        text = once(text, "            if reason:\n                self.data=dict(processed=processed,visits=count,last_result=completed)",
                    "            if reason and not hr_timing:\n                self.data=dict(processed=processed,visits=count,last_result=completed)")
        start = text.index("            clock_key='resume_started_active' if worker_v2")
        end = text.index("            self.data['short_view_wait']=wait", start)
        old = text[start:end]
        text = text[:start]+'''            if hr_timing:
                import hr_view_wait
                wait=hr_view_wait.runner_wait(self,run)
            else:
'''+''.join('    '+line+'\n' for line in old.splitlines())+text[end:]
        anchor = "            self.data['short_view_wait']=wait\n"
        text = once(text, anchor, anchor+'''            if reason and hr_timing:
                if wait['retry_after_seconds']:return self.status('short_view_wait')
                self.data=dict(processed=processed,visits=count,last_result=completed)
                self.phase='complete';self.data['completion_reason']=reason
                return self.status('complete')
''')
        return once(text, "pros='列表未命中岗位词库，未打开简历' if matched['readable'] else '列表卡片不可读，未作岗位评估',",
                    "pros=('列表命中跳过词：'+'、'.join(h['word'] for h in matched['negative_hits'])) if matched.get('negative_hits') else ('列表未命中岗位词库，未打开简历' if matched['readable'] else '列表卡片不可读，未作岗位评估'),")
    raise ValueError(name)


def patch_root(root):
    root = Path(root)
    changes = {name: patched(name, (root/name).read_text(encoding='utf-8-sig')) for name in FILES}
    for name, content in changes.items():
        (root/name).write_text(content, encoding='utf-8', newline='\n')


if __name__ == '__main__':
    import sys
    patch_root(sys.argv[1])
