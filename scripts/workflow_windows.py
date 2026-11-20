"""Windows UIA adapter for the continuous scheduler; no CUA/DOM or model API."""
from pathlib import Path
import hashlib,json,subprocess,time,uuid
import ledger,powershell_host,safe_action,ui_features,capture_resume,card_observation,fast_assessment,recruiting_rules
from windows_process import hidden_options
from workflow_paths import workflow_dir


def resume_full_text(data, ocr_text=''):
    """Keep all candidate sections, even when the main body is empty."""
    parts=[ocr_text]+[data.get(key,'') for key in (
        'keyword_text','resume_text','overview_text','expectation_text',
        'advantage_text','experience_text','education_text','project_text')]
    return '\n'.join(dict.fromkeys(part.strip() for part in parts if isinstance(part,str) and part.strip()))


class WindowsAdapter:
    def __init__(self,db,run,root,hwnd=None,allow_ocr=True):
        self.db,self.run,self.root,self.hwnd=db,run,Path(root),hwnd
        self.processed=[]
        self.allow_ocr=allow_ocr;self.observations={};self.detail_open=False
        self.folder=workflow_dir(run)

    def operation_timeout(self,default):
        deadline=getattr(self,'operation_deadline',None)
        if deadline is None:return default
        remaining=deadline-time.monotonic()
        if remaining<=0:raise subprocess.TimeoutExpired('coworker_check',10)
        return min(default,remaining)

    def operation_sleep(self,seconds):
        if self.operation_timeout(seconds)<seconds:
            raise subprocess.TimeoutExpired('coworker_check',10)
        time.sleep(seconds)

    def ps(self,name,*args):
        command=powershell_host.command(Path(__file__).with_name(name),*args)
        done=subprocess.run(command,capture_output=True,text=True,encoding='utf-8-sig',errors='replace',timeout=self.operation_timeout(15),**hidden_options())
        if done.returncode and name=='workflow-uia.ps1' and 'boss_document_unavailable' in done.stderr:
            self.operation_sleep(.2)
            done=subprocess.run(command,capture_output=True,text=True,encoding='utf-8-sig',errors='replace',timeout=self.operation_timeout(15),**hidden_options())
        if done.returncode:raise RuntimeError(done.stderr[-1800:])
        return json.loads(done.stdout)

    def query(self,action,candidate=None,processed=None):
        if not getattr(self, 'recommendation_ready', False):
            ready = self.ps('ensure-recommendation.ps1')
            if ready.get('state') != 'ready':raise RuntimeError('recommendation_page_not_ready')
            self.recommendation_ready = True
        args=['-Action',action]
        if self.hwnd:args+=['-WindowHandle',str(self.hwnd)]
        if candidate:args+=['-CardRuntime',candidate['card_runtime']]
        if processed is not None:
            path=self.folder/'cursor.json';path.write_text(json.dumps(processed),encoding='utf-8')
            args+=['-SkipFile',str(path)]
        return self.ps('workflow-uia.ps1',*args)

    def invoke(self,target,action='Invoke',key=None):
        path=self.folder/('target-'+uuid.uuid4().hex+'.json');path.write_text(json.dumps(target,ensure_ascii=False),encoding='utf-8')
        try:
            command=powershell_host.command(Path(__file__).with_name('guarded-uia-action.ps1'),'-Target',path,'-Action',action)
            if key:command+=['-Key',key]
            if getattr(self,'operation_deadline',None) is not None:
                return safe_action.dispatch(self.db,self.run,None,command,timeout=self.operation_timeout(8))
            return safe_action.dispatch(self.db,self.run,None,command)
        finally:path.unlink(missing_ok=True)

    def dismiss_related(self):
        for attempt in range(2):
            popup=self.query('RelatedClose')
            if popup.get('state')!='found':return
            self.invoke(popup['match']['target']);time.sleep(.2)
        if self.query('RelatedClose').get('state')=='found':
            raise ValueError('related_recommendations_popup_not_closed')

    def select(self,processed):
        rules=recruiting_rules.run_rules(ledger.run_row(self.db,self.run))
        if rules.get('release_policy') == 1410 and self.allow_ocr and not getattr(self,'runtime_checked',False):
            import sys
            checked=subprocess.run([sys.executable,'-I','-c','import cv2,numpy,rapidocr,onnxruntime'],
                capture_output=True,timeout=20,**hidden_options())
            if checked.returncode:
                raise RuntimeError('ocr_runtime_not_ready: '+checked.stderr.decode('utf-8',errors='replace')[-800:])
            self.runtime_checked=True
        self.dismiss_related()
        if rules.get('page_layout_policy'):
            import page_layout
            page_layout.prepare(self)
        self.processed=processed
        if not getattr(self,'page_job_recorded',False):
            observed=self.query('PageJob')
            _,_,fields=ledger.profile_check(Path(ledger.run_row(self.db,self.run)['profile_path']))
            display=observed.get('display_name')
            observed['name_mismatch']=bool(display and not all(fields[k] in display for k in ('company','position')))
            target=f"{fields['company']} {fields['position']}"
            observed['warning']=(
                f"🔴注意：BOSS右上角显示“{display}”，与本轮目标“{target}”不一致。"
                if observed['name_mismatch'] else None
            )
            self.db.execute('INSERT OR REPLACE INTO settings VALUES (?,?)',('boss_page_job/'+self.run,json.dumps(observed,ensure_ascii=False)))
            self.page_job_recorded=True
        for attempt in range(12):
            result=self.query('Select',processed=processed)
            if result['state']=='candidate':
                import card_layout
                candidates=[card for card in result.get('candidates',[result['candidate']]) if not card_layout.promo(card)]
                if rules.get('page_layout_policy'):
                    candidate=card_layout.choose(candidates,processed)
                    if candidate and not candidate.get('fully_visible',True):
                        self.invoke(candidate['card_target'],'Reveal');time.sleep(.5);continue
                    if candidate:self.hwnd=candidate['hwnd'];return candidate
                else:
                    candidate=candidates[0] if candidates else None
                    if candidate:self.hwnd=candidate['hwnd'];return candidate
            if result.get('scroll_target'):
                self.invoke(result['scroll_target'],'Scroll');time.sleep(.5)
            elif attempt<2:
                time.sleep(.5)
            else:return None
        return None

    def filter_state(self):
        return self.query('FilterState')

    def open(self,candidate,mode):
        self.hwnd=candidate.get('hwnd',self.hwnd)
        if mode in ('resume','worker_resume'):
            self.dismiss_related()
            for opening in range(2):
                if opening:
                    fresh=self.query('CardOpen',candidate)
                    if fresh.get('state')!='found':break
                    candidate=dict(candidate,open_target=fresh['match']['target'],already_open=False)
                if not candidate.get('already_open'):
                    if not candidate.get('open_target'):raise ValueError('resume_open_control_not_available')
                    self.invoke(candidate['open_target'])
                self.detail_open=True
                for attempt in range(5):
                    if self.query('ResumePresence').get('document_target'):return
                    time.sleep(.2)
            raise ValueError('resume_not_opened')

    def colleague(self,candidate,mode):
        previous=getattr(self,'operation_deadline',None)
        started=time.monotonic()
        self.operation_deadline=started+5
        try:
            result=self._colleague(candidate,mode)
            if time.monotonic()>=self.operation_deadline:
                raise subprocess.TimeoutExpired('coworker_check',5)
            return dict(result,elapsed_seconds=round(time.monotonic()-started,3))
        except subprocess.TimeoutExpired:
            return dict(state='unavailable',lookup_completed=False,
                evidence='coworker_timeout_5s',timeout_seconds=5,
                elapsed_seconds=round(time.monotonic()-started,3))
        except (OSError,RuntimeError,ValueError):
            elapsed=time.monotonic()-started
            if elapsed>=5:
                return dict(state='unavailable',lookup_completed=False,
                    evidence='coworker_timeout_5s',timeout_seconds=5,
                    elapsed_seconds=round(elapsed,3))
            raise
        finally:
            self.operation_deadline=previous

    def _colleague(self,candidate,mode):
        if mode=='card':
            folder=self.folder/('card-'+uuid.uuid4().hex)
            args=['-WindowHandle',str(self.hwnd),'-CandidateName',candidate['candidate_name'],'-CardRuntime',candidate['card_runtime'],'-OutputDirectory',str(folder)]
            try:observation=self.ps('capture-card.ps1',*args)
            except RuntimeError as exc:
                if not any(word in str(exc) for word in ('boss_window_not_foreground','card_occluded_or_target_mismatch')):raise
                observation=self.ps('capture-card.ps1',*args,'-NoImage')
            self.observations[candidate['candidate_id']]=(observation,folder/'card.uia.json',folder/'card.png')
            return dict(observation['card']['coworker_contact'],image=str(folder/'card.png'),uia_json=str(folder/'card.uia.json'),image_saved=observation.get('image_saved',False))
        observation=dict(state='unavailable',evidence='coworker_tab_not_confirmed')
        for attempt in range(2):
            tab=self.query('CoworkerTab')
            if tab.get('state')!='found':
                observation=dict(state='unavailable',evidence='coworker_header_not_found')
            if tab['state']=='found' and not tab['match']['selected'] and tab['match'].get('target'):
                self.invoke(tab['match']['target']);self.operation_sleep(.25);tab=self.query('CoworkerTab')
            if tab['state']=='found' and tab['match']['selected']:
                observation=self.ps('read-coworker-progress.ps1','-WindowHandle',str(self.hwnd),'-CoworkerTabConfirmed')
            if observation.get('state') in ('empty','records','first_record'):break
            if attempt == 0:self.operation_sleep(.3)
        return observation

    def complete_visual(self,candidate,answer):
        observation,path,image=self.observations.get(candidate['candidate_id'],(None,None,None))
        if observation is None:
            # Worker may have restarted while waiting for the local visual response.
            self.colleague(candidate,'card');observation,path,image=self.observations[candidate['candidate_id']]
        if answer['state']=='unknown':
            verified=dict(observation)
            verified['card']=dict(observation['card'],coworker_contact=dict(state='unknown',lookup_completed=False,evidence=answer['evidence']))
        else:verified=card_observation.complete(observation,answer['state'],answer['evidence'],image)
        path.write_text(json.dumps(verified,ensure_ascii=False,indent=2),encoding='utf-8')
        self.observations[candidate['candidate_id']]=(verified,path,image)
        return verified['card']['coworker_contact']

    def skip_evidence(self,candidate,mode):
        if mode!='card':return {}
        observation,path,image=self.observations[candidate['candidate_id']]
        return dict(card=observation['card'],card_evidence=dict(image=str(image),uia_json=str(path)))

    def platform_contact_state(self,candidate,mode):
        found=self.query('Greeting',candidate if mode=='card' else None)
        label=(found.get('match') or {}).get('label')
        return dict(already_contacted=found.get('state')=='found' and label in ('继续沟通','继续打招呼'),label=label)

    def read(self,candidate,mode):
        if mode=='card':
            observation,path,image=self.observations[candidate['candidate_id']]
            return dict(card=observation['card'],card_evidence=dict(image=str(image),uia_json=str(path)))
        self.dismiss_related()
        rules=recruiting_rules.run_rules(ledger.run_row(self.db,self.run))
        data=None;warning=None
        for attempt in range(2):
            try:
                data=self.query('ResumeFull' if rules.get('list_prefilter') or mode=='worker_resume' or recruiting_rules.is_domain(rules) else 'Resume');break
            except (RuntimeError,subprocess.TimeoutExpired) as exc:
                # Origin/binding failures require rebind, never classify as a bad resume.
                if any(code in str(exc) for code in ('codex_iab','external_browser','target_outside','boss_document_unavailable')):raise
                if not isinstance(exc,subprocess.TimeoutExpired) and not any(code in str(exc) for code in ('resume_scroll_scope_ambiguous','resume_scroll','ElementNotAvailable','element is not available','Scroll','SetScrollPercent')):raise
                warning=str(exc)
                if attempt==0:time.sleep(.2)
        if data is None:
            presence=self.query('ResumePresence') # Do not hide a lost binding.
            if rules.get('list_prefilter') and self.allow_ocr and presence.get('document_target'):
                data=dict(keyword_text='',resume_text='',overview_text='',read_complete=False)
            else:
                return dict(keyword_text='',read_complete=False,read_warning=warning or '正文采集失败')
        text=resume_full_text(data)
        result=dict(keyword_text=text,read_source=data.get('source','directed_resume_uia'),read_complete=data.get('read_complete',False))
        if warning:result['uia_read_warning']=warning
        if not rules.get('list_prefilter') and not recruiting_rules.is_domain(rules) and fast_assessment.evaluate(rules,result,recruiting_rules.positive_hits):
            result['resume_save_note']='关键词直接通道使用UIA正文，未执行可选长图/OCR采集，因此没有简历图片文件。'
            return result
        result['resume_save_note']=('本轮关闭了可选OCR（--no-ocr），未采集简历长图。' if not self.allow_ocr else
                                    '已通过UIA读取正文，本次未执行可选长图/OCR采集。')
        # New list-prefilter runs read the resume body through scrolling capture/OCR.
        if (rules.get('list_prefilter') or not result['read_complete']) and self.allow_ocr:
            if rules.get('current_rules'):
                import candidate_checks
                candidate_checks.require_resume(self.db,self.run,candidate['candidate_id'])
            if rules.get('list_prefilter'):
                result['read_complete']=False
            folder=self.folder/('resume-'+uuid.uuid4().hex)
            try:
                try:
                    captured=capture_resume.capture(self.db,self.run,candidate['candidate_id'],self.hwnd,folder)
                except (OSError,ValueError,subprocess.SubprocessError) as first:
                    if not rules.get('release_policy') or 'c_resume_document_missing' not in str(first) and 'c_resume_document_missing' not in str(getattr(first,'stderr','')):
                        raise
                    # Recovery is allowed only while the original list card is
                    # still uniquely exposed. Never open a next-person arrow.
                    same=self.query('CardOpen',candidate)
                    if same.get('state')!='found':raise
                    self.close()
                    retry=dict(candidate,open_target=same['match']['target'],already_open=False)
                    self.open(retry,mode)
                    folder=self.folder/('resume-retry-'+uuid.uuid4().hex)
                    captured=capture_resume.capture(self.db,self.run,candidate['candidate_id'],self.hwnd,folder)
                result['resume_evidence']=captured['resume_evidence']
                result.pop('resume_save_note',None)
                ocr_text=Path(captured['resume_evidence']['ocr_text']).read_text(encoding='utf-8-sig')
                result['keyword_text']=resume_full_text(data,ocr_text)
                result['read_source']='local_ocr_and_full_resume_uia'
                result['read_complete']=True
            except (OSError,ValueError,subprocess.SubprocessError) as exc:
                import resume_diagnostics
                result['read_warning']=str(exc)
                result['resume_save_error']=resume_diagnostics.reason(exc)
                result.pop('resume_save_note',None)
        result['readable']=bool(result.get('keyword_text','').strip())
        if rules.get('review_policy_version', 0) >= 151 and rules['hr_job_config'].get('preferred_locations') and rules['hr_job_config'].get('preferred_location_filter_enabled', True) is not False:
            try:
                observation = self.query('PreferredLocation')
            except (RuntimeError, subprocess.TimeoutExpired) as exc:
                observation = dict(state='unknown', reason=str(exc))
            evidence_path = self.folder/('preferred-location-'+uuid.uuid4().hex+'.json')
            evidence_path.write_text(json.dumps(observation, ensure_ascii=False), encoding='utf-8')
            result['preferred_location_observation'] = dict(observation, evidence_file=str(evidence_path), evidence_sha256=hashlib.sha256(evidence_path.read_bytes()).hexdigest())
        # Full raw evidence remains local; requests contain facts once per visit.
        return result

    def send(self,candidate,mode):
        found=self.query('Greeting',candidate if mode=='card' else None)
        if found['state']!='found':return dict(state='not-sent',reason='greeting_control_unavailable')
        if found['match']['label']!='打招呼':return dict(state='not-sent',reason='platform_already_contacted')
        self.invoke(found['match']['target'])
        for attempt in range(3):
            result=self.verify(candidate,mode)
            if result['state']=='sent':return result
            time.sleep(.2)
        return dict(state='unknown')

    def verify(self,candidate,mode):
        found=self.query('Greeting',candidate if mode=='card' else None)
        if found['state']=='found':
            if found['match']['label'] in ('继续沟通','继续打招呼'):return dict(state='sent')
            return dict(state='not-sent',may_retry=True)
        return dict(state='unknown')

    def favorite(self,candidate,mode):
        if not ui_features.favorite_eligible(self.db,self.run,ledger.run_candidate_hash(self.db,self.run,candidate['candidate_id'])):
            return dict(state='not_applicable')
        if mode=='card' and not self.detail_open:
            if not candidate.get('open_target'):return dict(state='pending',reason='resume_open_control_unavailable')
            self.invoke(candidate['open_target']);self.detail_open=True
        return ui_features.favorite(self.db,self.run,candidate['candidate_id'],self.hwnd)

    def close(self):
        self.detail_open=bool(self.query('ResumePresence').get('document_target'))
        if not self.detail_open:return
        found=self.query('Close')
        if found['state']=='found':self.invoke(found['match']['target'])
        else:
            document=self.query('ResumePresence').get('document_target')
            if not document:raise ValueError('resume_close_control_unavailable')
            self.invoke(document,'Key','Escape')
        self.detail_open=False

    def prefilter(self,candidate):
        folder=self.folder/('prefilter-'+uuid.uuid4().hex)
        text=(candidate.get('readable_text') or candidate.get('summary') or '').strip()
        if text:
            folder.mkdir(parents=True,exist_ok=True)
            evidence=folder/'prefilter.uia.json'
            evidence.write_text(json.dumps(candidate,ensure_ascii=False,indent=2),encoding='utf-8')
            return dict(card=dict(readable_text=text),raw_text=text,worker_stage='list',
                        card_evidence=dict(uia_json=str(evidence)))
        result=self.ps('capture-card.ps1','-WindowHandle',str(self.hwnd),'-CandidateName',candidate['candidate_name'],'-CardRuntime',candidate['card_runtime'],'-OutputDirectory',str(folder),'-NoImage')
        return dict(card=result['card'],raw_text=result['card'].get('readable_text',result.get('raw_text','')),worker_stage='list',card_evidence=dict(uia_json=str(folder/'card.uia.json')))

    def next(self,candidate,mode):
        if mode=='worker_resume':self.detail_open=bool(self.query('ResumePresence').get('document_target'))
        if mode=='worker_resume' and self.detail_open:
            before=self.query('Resume');arrow=self.query('Next')
            if arrow.get('state')=='found':
                self.invoke(arrow['match']['target'])
                for attempt in range(5):
                    after=self.query('Resume')
                    if after.get('candidate_id') and after.get('candidate_id')!=before.get('candidate_id'):
                        return dict(next_candidate=dict(candidate_id=after['candidate_id'],candidate_name=after.get('candidate_name') or '姓名未暴露',hwnd=self.hwnd,already_open=True))
                    time.sleep(.2)
            self.close();return dict(returned_to_list=True)
        # Prefer the existing next arrow only for the immediate list successor.
        if mode=='resume' and self.detail_open:
            selection=self.query('Select',processed=self.processed+[candidate['card_runtime']])
            ordered=selection.get('ordered_runtime_ids',[])
            index=ordered.index(candidate['card_runtime']) if candidate['card_runtime'] in ordered else -1
            successor=selection.get('candidate')
            immediate=index>=0 and index+1<len(ordered) and successor and ordered[index+1]==successor['card_runtime']
            if immediate:
                before=self.query('ResumePresence');arrow=self.query('Next')
                if arrow['state']=='found' and before.get('view_signature'):
                    self.invoke(arrow['match']['target'])
                    for attempt in range(5):
                        after=self.query('ResumePresence')
                        if after.get('document_target') and after!=before:
                            return dict(next_candidate=successor)
                        time.sleep(.2)
        self.close()
