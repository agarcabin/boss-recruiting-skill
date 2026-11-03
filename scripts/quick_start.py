"""Route startup to the home menu, company selection, or an explicit job."""
import argparse
import contextlib
import io
import json
import re
from datetime import datetime,timedelta,timezone
from pathlib import Path
import ledger
import project_registry
import run_targets
import startup_plan


def parse(prompt,projects,at=None):
    at=at or datetime.now(timezone(timedelta(hours=8)))
    text=re.sub(r'\s+','',prompt)
    greeting=re.search(r'(?:招呼|打招呼|投递)(?:目标|数)?[为是：:]?(\d+)(?:人|个|位)?',text)
    viewing=re.search(r'(?:查看|浏览|看)(?:目标|数)?[为是：:]?(\d+)(?:人|个|位|次)?',text)
    available=[p for p in projects if p.get('profile') and p.get('company') and p.get('position')]
    companies=[]
    for company in dict.fromkeys(p['company'] for p in available):
        jobs=[p for p in available if p['company']==company]
        companies.append(dict(company=company,position_count=len(jobs)))
    companies.extend(p for p in projects if p.get('entry_type')=='encrypted_group')
    company_matches=[p for p in available if str(p['company']) in text]
    position_matches=[p for p in available if str(p['position']) in text]
    matches=([p for p in company_matches if p in position_matches] or company_matches) if company_matches else position_matches
    if not matches:
        # Accept an unambiguous company prefix, including “帮我打ExampleEntity6250个”.
        aliases=re.findall(r'(?:帮我|给我|请)?(?:打招呼|招呼|投递|打|给)([^\d，。！？、]+?)(?=\d|开始|打招呼|$)',text)
        aliases+=re.findall(r'(?:帮|给)(?:我)?([^\d，。！？、]+?)(?=招呼|看)',text)
        names=[name.strip() for name in aliases if len(name.strip())>=2]
        matches=[p for p in available if any(str(p['company']).startswith(name) for name in names)]
    if not greeting:
        greeting=re.search(r'(?:打|招呼|投递)[^\d]*?(\d+)(?:人|个|位)',text)
    target,max_views=run_targets.resolve(int(greeting.group(1)) if greeting else None,int(viewing.group(1)) if viewing else None)
    # Deduplicate an alias and a full-name match for the same profile.
    matches=list({str(p['profile']):p for p in matches}.values())
    if re.fullmatch(r'菜单[：:]?1',text) or (not matches and not greeting and not viewing and not re.fullmatch(r'菜单[：:]?2',text)):
        return dict(state='menu',menu_level='home',target=target,max_views=max_views,
                    next_actions=['show_home_menu'])
    if re.fullmatch(r'菜单[：:]?2',text) or len(matches)!=1:
        return dict(state='needs_selection',selection_level='position' if matches else 'company',
                    companies=companies,matches=matches,target=target,max_views=max_views,
                    greetings_explicit=bool(greeting),views_explicit=bool(viewing),
                    reason='请选择企业及岗位；不默认沿用上次项目')
    project=matches[0]
    if not greeting:
        # “打ExampleEntity6250人” is an explicit greeting target, not a view count.
        greeting=re.search(r'(?:打|招呼)'+r'(?:ExampleEntity62|'+re.escape(str(project['company']))+r'|'+re.escape(str(project['position']))+r')(\d+)(?:人|个|位)',text)
    target,max_views=run_targets.resolve(int(greeting.group(1)) if greeting else None,int(viewing.group(1)) if viewing else None)
    return dict(state='ready_to_start',startup_mode='direct',profile=project['profile'],company=project['company'],position=project['position'],
                target=target,max_views=max_views,chat_title=f"{project['company']} {project['position']} - {at.astimezone(timezone(timedelta(hours=8))).date().isoformat()}",
                approval_warning=project.get('approval')!='approved',views_explicit=bool(viewing),greetings_explicit=bool(greeting),
                next_actions=['set_current_chat_title','collapse_chat_sidebar','open_boss','confirm_already_logged_in_prompt_if_present','start_direct_run'])


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--prompt');p.add_argument('--plan',type=Path)
    p.add_argument('--state-dir',type=Path,default=startup_plan.DEFAULT_ROOT)
    p.add_argument('--complete-action');p.add_argument('--db',type=Path,default=ledger.DEFAULT_DB)
    p.add_argument('--confirm-filters',action='store_true',help='Use only after the user checked filters and replied 1')
    p.add_argument('--start-direct',action='store_true',help='Start a prepared explicit-job request without manual filter confirmation')
    p.add_argument('--min-score',type=int)
    args=p.parse_args()
    if args.plan:plan=startup_plan.load(args.plan)
    elif args.confirm_filters or args.start_direct or args.complete_action:
        if not args.prompt:p.error('--plan or original --prompt required to resume')
        plan=startup_plan.find(args.prompt,args.state_dir)
    else:
        if not args.prompt:p.error('--prompt or --plan required')
        plan=parse(args.prompt,project_registry.list_projects())
        if plan['state']=='menu':
            plan.update(project_registry.build_home_menu(project_registry.list_projects(),project_registry.latest_run_readonly(args.db),locked_entry=project_registry.encrypted_entry()))
        plan['min_score']=70 if args.min_score is None else args.min_score
        if plan['state'] in ('await_filters','ready_to_start'):plan=startup_plan.save(plan,args.prompt,args.state_dir)
    if args.complete_action:startup_plan.complete(plan,args.complete_action)
    should_start=(args.confirm_filters and plan['state']=='await_filters') or (args.start_direct and plan['state']=='ready_to_start')
    if should_start and not plan.get('run'):
        with contextlib.closing(ledger.connect(args.db)) as db:
            import run_safety
            with run_safety.action_lock(db):
                plan=startup_plan.load(plan['plan_file'])
                if not plan.get('run'):
                    out=io.StringIO()
                    with contextlib.redirect_stdout(out):
                        ledger.start(db,argparse.Namespace(profile=plan['profile'],target=plan['target'],max_views=plan['max_views'],min_score=plan.get('min_score',70) if args.min_score is None else args.min_score))
                    created=json.loads(out.getvalue())
                    if created['state']!='started':
                        print(json.dumps(created,ensure_ascii=False));return
                    plan['run']=created;plan['state']='started'
                    startup_plan.complete(plan,'start_direct_run' if args.start_direct else 'wait_for_manual_filters_and_reply_1')
    plan['pending_startup_actions']=[action for action in plan.get('next_actions',[]) if action not in plan.get('startup_completed',[])]
    print(json.dumps(plan,ensure_ascii=False))


if __name__=='__main__':main()
