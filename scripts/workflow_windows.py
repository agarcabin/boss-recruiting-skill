"""Windows UIA adapter for the continuous scheduler; no CUA/DOM or model API."""
from pathlib import Path
import hashlib,json,subprocess,time,uuid
import ledger,powershell_host,safe_action,ui_features,capture_resume,card_observation,fast_assessment,recruiting_rules
from windows_process import hidden_options


class WindowsAdapter:
    def __init__(self,db,run,root,hwnd=None,allow_ocr=True):
        self.db,self.run,self.root,self.hwnd=db,run,Path(root),hwnd
        self.allow_ocr=allow_ocr;self.observations={};self.detail_open=False
        self.folder=self.root/'.workflow'/run;self.folder.mkdir(parents=True,exist_ok=True)

    def ps(self,name,*args):
        command=powershell_host.command(Path(__file__).with_name(name),*args)
        done=subprocess.run(command,capture_output=True,text=True,encoding='utf-8-sig',timeout=15,**hidden_options())
        if done.returncode and name=='workflow-uia.ps1' and 'boss_document_unavailable' in done.stderr:
            time.sleep(.2)
            done=subprocess.run(command,capture_output=True,text=True,encoding='utf-8-sig',timeout=15,**hidden_options())
        if done.returncode:raise RuntimeError(done.stderr[-1800:])
        return json.loads(done.stdout)

    def query(self,action,candidate=None,processed=None):
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
            return safe_action.dispatch(self.db,self.run,None,command)
        finally:path.unlink(missing_ok=True)

    def select(self,processed):
        self.processed=processed
        for attempt in range(3):
            result=self.query('Select',processed=processed)
            if result['state']=='candidate':
                candidate=result['candidate'];self.hwnd=candidate['hwnd'];return candidate
            if result.get('scroll_target'):
                self.invoke(result['scroll_target'],'Scroll');time.sleep(.2)
            else:return None
        return None

    def open(self,candidate,mode):
        self.hwnd=candidate.get('hwnd',self.hwnd)
        if mode=='resume':
            if not candidate.get('already_open'):
                if not candidate.get('open_target'):raise ValueError('resume_open_control_not_available')
                self.invoke(candidate['open_target'])
            self.detail_open=True
            for attempt in range(5):
                if self.query('ResumePresence').get('document_target'):return
                time.sleep(.2)
            raise ValueError('resume_not_opened')

    def colleague(self,candidate,mode):
        if mode=='card':
            folder=self.folder/('card-'+uuid.uuid4().hex)
            args=['-WindowHandle',str(self.hwnd),'-CandidateName',candidate['candidate_name'],'-CardRuntime',candidate['card_runtime'],'-OutputDirectory',str(folder)]
            try:observation=self.ps('capture-card.ps1',*args)
            except RuntimeError as exc:
                if not any(word in str(exc) for word in ('boss_window_not_foreground','card_occluded_or_target_mismatch')):raise
                observation=self.ps('capture-card.ps1',*args,'-NoImage')
            self.observations[candidate['candidate_id']]=(observation,folder/'card.uia.json',folder/'card.png')
            return dict(observation['card']['coworker_contact'],image=str(folder/'card.png'),uia_json=str(folder/'card.uia.json'),image_saved=observation.get('image_saved',False))
        observation=self.ps('read-coworker-progress.ps1','-WindowHandle',str(self.hwnd))
        if observation['state']=='unavailable' and 'tab_not_confirmed' in observation.get('evidence',''):
            tab=self.query('CoworkerTab')
            if tab['state']=='found' and not tab['match']['selected'] and tab['match'].get('target'):
                self.invoke(tab['match']['target']);tab=self.query('CoworkerTab')
            if tab['state']=='found' and tab['match']['selected']:
                observation=self.ps('read-coworker-progress.ps1','-WindowHandle',str(self.hwnd),'-CoworkerTabConfirmed')
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

    def read(self,candidate,mode):
        if mode=='card':
            observation,path,image=self.observations[candidate['candidate_id']]
            return dict(card=observation['card'],card_evidence=dict(image=str(image),uia_json=str(path)))
        data=self.query('Resume');text=data.get('keyword_text','')
        result=dict(keyword_text=text,read_source=data.get('source','directed_resume_uia'))
        rules=recruiting_rules.run_rules(ledger.run_row(self.db,self.run))
        if fast_assessment.evaluate(rules,result,recruiting_rules.positive_hits):
            result['resume_save_note']='关键词直接通道使用UIA正文，未执行可选长图/OCR采集，因此没有简历图片文件。'
            return result
        # Overview text is useful for a direct rule, but does not prove that a
        # canvas-rendered resume body was read. Test body length independently.
        body=data.get('resume_text',text)
        result['resume_save_note']=('本轮关闭了可选OCR（--no-ocr），未采集简历长图。' if not self.allow_ocr else
                                    '已通过UIA读取正文，本次未执行可选长图/OCR采集。')
        if len(body.strip())<80 and self.allow_ocr:
            folder=self.folder/('resume-'+uuid.uuid4().hex)
            try:
                captured=capture_resume.capture(self.db,self.run,candidate['candidate_id'],self.hwnd,folder)
                result['resume_evidence']=captured['resume_evidence']
                result.pop('resume_save_note',None)
                ocr_text=Path(captured['resume_evidence']['ocr_text']).read_text(encoding='utf-8-sig')
                result['keyword_text']='\n'.join(part for part in (ocr_text,data.get('overview_text','')) if part)
                result['read_source']='local_ocr_and_overview_uia'
            except (OSError,ValueError,subprocess.SubprocessError) as exc:
                import resume_diagnostics
                result['read_warning']=str(exc)
                result['resume_save_error']=resume_diagnostics.reason(exc)
                result.pop('resume_save_note',None)
        # Full raw evidence remains local; requests contain facts once per visit.
        return result

    def send(self,candidate,mode):
        found=self.query('Greeting',candidate if mode=='card' else None)
        if found['state']!='found':return dict(state='not-sent',reason='greeting_control_unavailable')
        if found['match']['label']!='打招呼':return dict(state='not-sent',reason='platform_already_contacted')
        import greeting_rate
        rate=greeting_rate.claim(self.db,ledger.run_candidate_hash(self.db,self.run,candidate['candidate_id']))
        if rate['state']=='rate_limited':return rate
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
        if not self.detail_open:return
        found=self.query('Close')
        if found['state']=='found':self.invoke(found['match']['target'])
        else:
            document=self.query('ResumePresence').get('document_target')
            if not document:raise ValueError('resume_close_control_unavailable')
            self.invoke(document,'Key','Escape')
        self.detail_open=False

    def next(self,candidate,mode):
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
