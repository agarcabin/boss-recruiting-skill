"""One persistent recruiting scheduler; model handoffs are local files, not user prompts."""
from __future__ import annotations
import argparse,contextlib,io,json,os,time
from pathlib import Path
from argparse import Namespace
import ledger,candidate_log,candidate_checks,coworker_progress,recruiting_rules
import fast_assessment,report_batch,run_safety
import ui_features,short_view_wait,greeting_rate
from workflow_paths import workflow_dir


def call(fn,db,**values):
    out=io.StringIO()
    with contextlib.redirect_stdout(out):fn(db,Namespace(**values))
    result=json.loads(out.getvalue())
    if result.get('state') in ('error','blocked'):raise ValueError(result.get('reason',result['state']))
    return result


class Runner:
    def __init__(self,db,run_id,adapter,root):
        self.db,self.run,self.adapter,self.root=db,run_id,adapter,Path(root)
        candidate_log.table(db)
        db.execute('''CREATE TABLE IF NOT EXISTS workflow_state(run_id TEXT PRIMARY KEY,
            phase TEXT NOT NULL,payload TEXT NOT NULL,updated_at TEXT NOT NULL)''')
        row=db.execute('SELECT * FROM workflow_state WHERE run_id=?',(run_id,)).fetchone()
        self.phase=row['phase'] if row else 'select'
        self.data=json.loads(row['payload']) if row else dict(processed=[],visits=0)
        self._saved=(row['phase'],row['payload']) if row else None
        self.folder=workflow_dir(run_id)
        self.save()

    def save(self):
        previous_phase=self._saved[0] if self._saved else None
        if previous_phase != self.phase or 'phase_started_elapsed' not in self.data:
            self.data['phase_started_elapsed']=ledger.active_elapsed_seconds(self.db,self.run)
        payload=json.dumps(self.data,ensure_ascii=False)
        if self._saved==(self.phase,payload):return
        self.db.execute('INSERT INTO workflow_state VALUES (?,?,?,?) ON CONFLICT(run_id) DO UPDATE SET phase=excluded.phase,payload=excluded.payload,updated_at=excluded.updated_at',
                        (self.run,self.phase,payload,ledger.iso(ledger.now())))
        self._saved=(self.phase,payload)

    def status(self,state=None):
        page_job=self.db.execute('SELECT value FROM settings WHERE key=?',('boss_page_job/'+self.run,)).fetchone()
        if state is None:
            control=ledger.control_state(self.db,self.run)
            cached=self.data.get('scheduler_state',self.phase)
            state=control if control!='running' else self.phase if cached in ('paused','login_required','stopped') else cached
        return dict(state=state,phase=self.phase,run_id=self.run,page_job=json.loads(page_job[0]) if page_job else None,
                    candidate=self.data.get('candidate'),request_file=self.data.get('request_file'),
                    response_file=self.data.get('response_file'),visits=self.data.get('visits',0),
                    warnings=self.data.get('warnings',[]),error=self.data.get('error'),
                    rate_limit=self.data.get('rate_limit'),short_view_wait=self.data.get('short_view_wait'),
                    last_result=self.data.get('last_result'),exports=self.data.get('exports',[]))

    def handoff(self,kind,payload):
        path=self.folder/(self.data['visit_hash']+'-'+kind+'.json')
        response=path.with_suffix('.response.json')
        if not path.exists():path.write_text(json.dumps(dict(kind=kind,candidate=self.data['candidate'],evidence=payload),ensure_ascii=False,indent=2),encoding='utf-8')
        self.data.update(request_file=str(path),response_file=str(response),handoff_kind=kind)
        return self.status('needs_'+kind)

    def response(self):
        path=self.data.get('response_file')
        if path and Path(path).is_file():return json.loads(Path(path).read_text(encoding='utf-8-sig'))
        return None

    def record_payload(self,payload):
        candidate=self.data['candidate']
        common=dict(candidate_id=candidate['candidate_id'],candidate_name=candidate['candidate_name'],
                    started_at=self.data['started_at'],coworker_progress=self.data.get('coworker'))
        common.update(payload)
        common.update(candidate_id=candidate['candidate_id'],candidate_name=candidate['candidate_name'])
        result=call(lambda db,args:candidate_log.record(db,args,common),self.db,run=self.run,output_root=self.root)
        self.data['decision']=result['decision']
        self.data.setdefault('warnings',[]).extend(result.get('warnings',[]))
        return result

    def worker_skip(self,decision,reason,score):
        facts=self.data.get('facts',{})
        self.record_payload(dict(facts,decision=decision,overall_score=score,electronic_resume_enabled=False,hard_requirements=False,pros=reason,cons='同事记录未检查',coworker_progress=None))

    def step(self):
        # Pause/end lives in this scheduler, not in duplicate per-action guards.
        state=ledger.control_state(self.db,self.run)
        if state!='running':return self.status(state)
        run=ledger.run_row(self.db,self.run);mode=run['evaluation_mode']
        candidate=self.data.get('candidate',{});cid=candidate.get('candidate_id')
        phase=self.phase
        if phase=='select':
            reason=run_safety.quantity_reason(self.db,self.run)
            if reason:
                self.phase='complete';self.data['completion_reason']=reason
                return self.status('complete')
            candidate=self.data.pop('prefetched',None) or self.adapter.select(self.data.get('processed',[]))
            if candidate is None:return self.status('needs_page')
            self.data.update(candidate=candidate,warnings=[],attempts=0)
            self.phase='open';return None
        if phase=='open':
            if mode!='worker_resume':self.adapter.open(candidate,mode)
            active=ledger.ensure_candidate(self.db,self.run,cid,new_visit=True)
            self.data.update(visit_hash=active['candidate_hash'],started_at=active['started_at'])
            self.data['visit_started_active']=short_view_wait.active_clock(self.db,self.run)
            self.data['excluded_wait_seconds']=0
            self.phase=('worker_read' if candidate.get('already_open') else 'worker_list') if mode=='worker_resume' else 'coworker';return None
        if phase=='worker_list':
            facts=self.adapter.prefilter(candidate);self.data['facts']=facts
            match=recruiting_rules.worker_match(recruiting_rules.run_rules(run),facts)
            if not match['eligible']:
                self.worker_skip('skip','列表未命中关键词',match['score']);self.phase='finish';return None
            self.phase='worker_open';return None
        if phase=='worker_open':
            self.adapter.open(candidate,'worker_resume');self.phase='worker_read';return None
        if phase=='worker_read':
            facts=self.adapter.read(candidate,'worker_resume');facts['worker_stage']='resume';self.data['facts']=facts
            match=recruiting_rules.worker_match(recruiting_rules.run_rules(run),facts)
            browse=self.data.setdefault('worker_browse',dict(misses=0,seen=[]))
            if not facts.get('keyword_text','').strip() or facts.get('read_complete') is False:
                self.worker_skip('review','正文不可读，未判断关键词',0);self.phase='finish';return None
            if not match['eligible']:
                browse['misses']+=1
                self.worker_skip('skip','电子简历全文未命中关键词',match['score']);self.phase='finish';return None
            browse['misses']=0;self.phase='coworker';return None
        if phase=='coworker':
            observation=self.data.get('coworker')
            if observation is None:observation=self.adapter.colleague(candidate,mode)
            self.data['coworker']=observation
            if mode=='card' and observation.get('state')=='unknown':
                answer=self.response()
                if answer:
                    observation=self.adapter.complete_visual(candidate,answer)
                    self.data.pop('request_file',None);self.data.pop('response_file',None)
                    self.data.pop('handoff_kind',None)
                else:return self.handoff('card_visual',observation)
            result=candidate_checks.record(self.db,self.run,cid,observation,'card' if mode=='card' else 'resume')
            self.data['coworker']=observation
            if not result['may_continue']:
                evidence=self.adapter.skip_evidence(candidate,mode) if hasattr(self.adapter,'skip_evidence') else {}
                payload=dict(decision='skip' if result.get('skip') else 'review',overall_score=0,
                    electronic_resume_enabled=False,hard_requirements=False,
                    card=dict(coworker_contact=observation),pros='同事检查先处理，未作岗位评估',cons=str(result.get('reason',result['action'])))
                if mode=='worker_resume':payload.update(self.data.get('facts',{}))
                payload.update(evidence);self.record_payload(payload)
                self.phase='finish';return None
            self.phase='assess' if mode=='worker_resume' else 'read';return None
        if phase=='read':
            facts=self.adapter.read(candidate,mode)
            self.data['facts']=facts;self.phase='assess';return None
        if phase=='assess':
            facts=dict(self.data['facts'])
            rules=recruiting_rules.run_rules(run)
            if recruiting_rules.is_domain(rules) and facts.get('read_complete') is False:
                self.record_payload(dict(facts,decision='review',overall_score=0,electronic_resume_enabled=False,hard_requirements=False,pros='正文未完整读取，尚未完成评分',cons='保留实际材料，未发送'))
                self.phase='finish';return None
            if self.data.get('handoff_kind')=='assessment':
                answer=self.response()
                if not answer:return self.status('needs_assessment')
                payload=dict(facts,**answer)
            elif mode=='worker_resume':
                result=recruiting_rules.worker_match(rules,facts)
                payload=dict(facts,decision='greet' if result['eligible'] else 'skip',overall_score=result['score'],electronic_resume_enabled=True,hard_requirements=False,electronic=dict(score=result['score'],evidence='电子简历全文关键词判断'),pros='命中普工关键词',cons='未读取字段保持未知')
            elif mode=='card':
                result=recruiting_rules.evaluate(rules,facts,run['min_score'])
                payload=dict(facts,decision='greet' if result['eligible'] else 'skip',overall_score=result['score'],
                             electronic_resume_enabled=False,hard_requirements=False,pros='列表关键词判断',cons='未读取的字段记未知')
            else:
                result=recruiting_rules.domain_group_score(rules,facts,run['min_score']) if recruiting_rules.is_domain(rules) else fast_assessment.evaluate(rules,facts,recruiting_rules.positive_hits)
                if result and not result.get('scoring_complete',True):result=None
                if result:
                    result.setdefault('score_before_experience',result['score'])
                    payload=fast_assessment.fill(facts,result)
                else:
                    answer=self.response()
                    if answer:payload=dict(facts,**answer)
                    else:return self.handoff('assessment',facts)
            self.record_payload(payload)
            self.data.pop('request_file',None);self.data.pop('response_file',None)
            self.data.pop('handoff_kind',None)
            self.phase='send' if self.data['decision']=='greet' else 'favorite';return None
        if phase=='send':
            reservation=call(ledger.reserve,self.db,run=self.run,candidate_id=cid)
            if reservation['state']=='rate_limited':
                self.data.setdefault('rate_wait_started',short_view_wait.active_clock(self.db,self.run))
                self.data['rate_limit']=reservation
                return self.status('rate_limited')
            if self.data.get('rate_wait_started') is not None:
                self.data['excluded_wait_seconds']=self.data.get('excluded_wait_seconds',0)+max(0,short_view_wait.active_clock(self.db,self.run)-self.data.pop('rate_wait_started'))
            self.data.pop('rate_limit',None)
            if reservation['state']=='already_sent':self.phase='favorite';return None
            self.data['token']=reservation['token'];self.data['attempts']+=1
            # Persist before dispatch: a restarted worker verifies, it does not blindly resend.
            self.phase='verify';self.save()
            try:result=self.adapter.send(candidate,mode)
            except (OSError,RuntimeError,ValueError) as exc:result=dict(state='unknown',error=str(exc))
            if result.get('state')=='rate_limited':
                self.data.setdefault('rate_wait_started',short_view_wait.active_clock(self.db,self.run))
                self.phase='send';self.data['rate_limit']=result;self.data['attempts']-=1
                return self.status('rate_limited')
            call(ledger.resolve,self.db,token=self.data['token'],result=result.get('state','unknown'))
            self.data['send_result']=result
            return None
        if phase=='verify':
            result=self.data.get('send_result')
            if not result or result.get('state')=='unknown':
                result=self.adapter.verify(candidate,mode)
                actual=result.get('state','unknown')
                call(ledger.resolve,self.db,token=self.data['token'],result=actual if actual in ('sent','not-sent') else 'unknown')
            if result and result.get('may_retry') and self.data['attempts']<2:
                self.phase='send';self.data.pop('send_result',None);return None
            call(candidate_log.sync,self.db,run=self.run,candidate_id=cid,output_root=self.root)
            first=self.db.execute('SELECT status FROM candidates WHERE candidate_hash=?',(self.data['visit_hash'],)).fetchone()
            self.data['sent']=bool(first and first['status']=='sent')
            if self.data['sent'] and recruiting_rules.run_greeting_mode(run)=='triple':self.phase='followups'
            else:self.phase='favorite'
            return None
        if phase=='followups':
            answer=self.response()
            if not answer:return self.handoff('followups',dict(first_sent=True,mode='triple'))
            self.data['followups']=answer;self.phase='favorite';return None
        if phase=='favorite':
            if ui_features.favorite_eligible(self.db,self.run,self.data['visit_hash']):
                try:self.data['favorite']=self.adapter.favorite(candidate,mode)
                except (OSError,RuntimeError,ValueError) as exc:self.data.setdefault('warnings',[]).append('收藏待补：'+str(exc))
            self.phase='finish';return None
        if phase=='finish':
            row=self.db.execute('SELECT decision FROM assessments WHERE run_id=? AND candidate_hash=?',(self.run,self.data['visit_hash'])).fetchone()
            has_record=self.db.execute('SELECT 1 FROM candidates WHERE candidate_hash=?',(self.data['visit_hash'],)).fetchone()
            if row and row['decision']!='greet' and not has_record:
                call(ledger.note,self.db,run=self.run,candidate_id=cid,result='review' if row['decision']=='review' else 'skipped')
                call(candidate_log.sync,self.db,run=self.run,candidate_id=cid,output_root=self.root)
            stamp=ledger.iso(ledger.now())
            call(candidate_log.finalize_timing,self.db,run=self.run,candidate_id=cid,ended_at=stamp,output_root=self.root)
            call(ledger.candidate_finish,self.db,run=self.run,candidate_id=cid,ended_at=stamp)
            self.phase='next';return None
        if phase=='next':
            report_batch.flush_now(self.db)
            processed=self.data.get('processed',[])+([candidate['card_runtime']] if candidate.get('card_runtime') else [])
            count=self.data.get('visits',0)+1
            reason=run_safety.quantity_reason(self.db,self.run)
            completed=dict(candidate=candidate,sent=self.data.get('sent',False),favorite=self.data.get('favorite'),warnings=self.data.get('warnings',[]))
            if reason:
                self.data=dict(processed=processed,visits=count,last_result=completed)
                self.phase='complete';self.data['completion_reason']=reason
                return self.status('complete')
            elapsed=max(0,short_view_wait.active_clock(self.db,self.run)-self.data.get('visit_started_active',0)-self.data.get('excluded_wait_seconds',0))
            wait=short_view_wait.plan(self.db,self.run,self.data['visit_hash'],elapsed)
            self.data['short_view_wait']=wait
            quota=greeting_rate.status(self.db)
            # Await both deadlines before selecting the next candidate.
            if wait['retry_after_seconds'] or quota['retry_after_seconds']:
                self.data['rate_limit']=quota
                return self.status('short_view_wait' if wait['retry_after_seconds'] else 'rate_limited')
            browse=self.data.get('worker_browse',dict(misses=0,seen=[]))
            if mode=='worker_resume' and browse['misses']>=5:
                self.adapter.close();navigation=dict(returned_to_list=True)
            else:navigation=self.adapter.next(candidate,mode)
            if navigation and navigation.get('returned_to_list'):browse=dict(misses=0,seen=[])
            if mode=='worker_resume' and navigation and navigation.get('next_candidate'):
                key=navigation['next_candidate']['candidate_id']
                if key in browse['seen']:
                    self.adapter.close();navigation=None;browse=dict(misses=0,seen=[])
                else:browse['seen'].append(key)
            self.data=dict(processed=processed,visits=count,last_result=completed,worker_browse=browse)
            if navigation and navigation.get('next_candidate'):
                self.data['prefetched']=dict(navigation['next_candidate'],already_open=True)
            self.phase='select';return None
        return self.status()

    def advance(self):
        # A handoff may span invocations; only changes in this slice are exported.
        with report_batch.batch(self.db) as reports:
            while True:
                before=self.phase
                try:
                    result=self.step();self.data.pop('error',None)
                except (OSError,RuntimeError,ValueError) as exc:
                    self.data['error']=str(exc);result=self.status('needs_attention')
                if self.phase!=before:self.data.pop('scheduler_state',None)
                self.save()
                if result or self.phase=='select':break
            self.data['scheduler_state']=result['state'] if result else 'candidate_complete'
            self.save()
            reports['flush']=self.phase in ('select','complete') or ledger.control_state(self.db,self.run)=='stopped'
        if reports['warnings']:
            self.data.setdefault('warnings',[]).extend(reports['warnings']);self.save()
        if reports['exports']:
            self.data['exports']=reports['exports'];self.save()
        return self.status(result['state'] if result else 'candidate_complete')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--db',type=Path,default=ledger.DEFAULT_DB);p.add_argument('--run',required=True)
    p.add_argument('--output-root',type=Path,default=Path.home()/'Desktop');p.add_argument('--hwnd',type=int)
    p.add_argument('--status',action='store_true');p.add_argument('--worker',action='store_true');p.add_argument('--launch',action='store_true')
    p.add_argument('--browser-binding',type=Path,help='Required current-chat Codex IAB binding')
    p.add_argument('--no-ocr',action='store_true',help='Disable optional fallback OCR')
    args=p.parse_args()
    if args.browser_binding:os.environ['BOSS_BROWSER_BINDING']=str(args.browser_binding.resolve())
    if not args.status and not os.environ.get('BOSS_BROWSER_BINDING'):p.error('codex_iab_binding_required; open BOSS with open_in_codex and bind-boss-browser.ps1')
    if args.launch:
        from launch_progress import launch_process
        import sys
        pythonw=Path(sys.executable).with_name('pythonw.exe')
        command=[str(pythonw),'-X','utf8',__file__,'--db',str(args.db),'--run',args.run,'--output-root',str(args.output_root),'--worker']
        if args.hwnd:command+=['--hwnd',str(args.hwnd)]
        if args.no_ocr:command+=['--no-ocr']
        process=launch_process(command);print(json.dumps(dict(state='runner_started',pid=process.pid,run_id=args.run)));return
    with contextlib.closing(ledger.connect(args.db)) as db:
        from workflow_windows import WindowsAdapter
        adapter=WindowsAdapter(db,args.run,args.output_root,args.hwnd,allow_ocr=not args.no_ocr)
        runner=Runner(db,args.run,adapter,args.output_root)
        if args.status:print(json.dumps(runner.status(),ensure_ascii=False));return
        # One scheduler owns this run. No lock is acquired for individual UI actions.
        with run_safety.action_lock(db):
            table='workflow_owner'
            db.execute('CREATE TABLE IF NOT EXISTS workflow_owner(run_id TEXT PRIMARY KEY,pid INTEGER,birth REAL)')
            owner=db.execute('SELECT * FROM workflow_owner WHERE run_id=?',(args.run,)).fetchone()
            if owner:
                try:alive=abs(run_safety.process_birth(owner['pid'])-owner['birth'])<.0001
                except (OSError,ProcessLookupError):alive=False
                if alive:raise ValueError('runner_already_running')
            db.execute('INSERT OR REPLACE INTO workflow_owner VALUES (?,?,?)',(args.run,os.getpid(),run_safety.process_birth(os.getpid())))
        try:
            while True:
                result=runner.advance()
                if result['state']=='complete':
                    run_safety.request_stop(db,args.run,runner.data.get('completion_reason','quantity_complete'))
                    import stop_controller
                    stop_controller.finalize(db,args.run,args.output_root,interrupt=False)
                    result.update(stop_controller.report_status(db,args.run))
                if not args.worker:print(json.dumps(result,ensure_ascii=False));break
                if result['state'] in ('complete','stopped','needs_attention','needs_page'):break
                time.sleep(1 if result['state']=='rate_limited' else .5 if result['state']!='candidate_complete' else 0)
        finally:db.execute('DELETE FROM workflow_owner WHERE run_id=? AND pid=?',(args.run,os.getpid()))


if __name__=='__main__':main()
