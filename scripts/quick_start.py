"""Parse one-line recruiting requests and pause once for manual recommendation filters."""
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
    matches=[p for p in projects if str(p['company']) in text or str(p['position']) in text or ('美康' in text and '美康' in str(p['company']))]
    # Deduplicate an alias and a full-name match for the same profile.
    matches=list({str(p['profile']):p for p in matches}.values())
    if len(matches)!=1:
        return dict(state='needs_selection',matches=matches,reason='未匹配唯一企业岗位')
    project=matches[0]
    if not greeting:
        # “打美康50人” is an explicit greeting target, not a view count.
        greeting=re.search(r'(?:打|招呼)'+r'(?:美康|'+re.escape(str(project['company']))+r'|'+re.escape(str(project['position']))+r')(\d+)(?:人|个|位)',text)
    target,max_views=run_targets.resolve(int(greeting.group(1)) if greeting else None,int(viewing.group(1)) if viewing else None)
    return dict(state='await_filters',profile=project['profile'],company=project['company'],position=project['position'],
                target=target,max_views=max_views,chat_title=f"{project['company']} {project['position']} - {at.astimezone(timezone(timedelta(hours=8))).date().isoformat()}",
                approval_warning=project.get('approval')!='approved',views_explicit=bool(viewing),greetings_explicit=bool(greeting),
                next_actions=['set_current_chat_title','collapse_chat_sidebar','open_boss','confirm_already_logged_in_prompt_if_present','wait_for_manual_filters_and_reply_1'])


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--prompt');p.add_argument('--plan',type=Path)
    p.add_argument('--state-dir',type=Path,default=startup_plan.DEFAULT_ROOT)
    p.add_argument('--complete-action');p.add_argument('--db',type=Path,default=ledger.DEFAULT_DB)
    p.add_argument('--confirm-filters',action='store_true',help='Use only after the user checked filters and replied 1')
    p.add_argument('--min-score',type=int)
    args=p.parse_args()
    if args.plan:plan=startup_plan.load(args.plan)
    elif args.confirm_filters or args.complete_action:
        if not args.prompt:p.error('--plan or original --prompt required to resume')
        plan=startup_plan.find(args.prompt,args.state_dir)
    else:
        if not args.prompt:p.error('--prompt or --plan required')
        plan=parse(args.prompt,project_registry.list_projects())
        plan['min_score']=70 if args.min_score is None else args.min_score
        if plan['state']=='await_filters':plan=startup_plan.save(plan,args.prompt,args.state_dir)
    if args.complete_action:startup_plan.complete(plan,args.complete_action)
    if args.confirm_filters and plan['state']=='await_filters' and not plan.get('run'):
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
                    startup_plan.complete(plan,'wait_for_manual_filters_and_reply_1')
    plan['pending_startup_actions']=[action for action in plan.get('next_actions',[]) if action not in plan.get('startup_completed',[])]
    print(json.dumps(plan,ensure_ascii=False))


if __name__=='__main__':main()
