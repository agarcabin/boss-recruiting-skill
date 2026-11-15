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


def match_projects(text, projects):
    """Intersect company and job matches; ambiguity never picks a default job."""
    def names(project, key):
        values = project.get(key+'_aliases') or [project[key]]
        return [re.sub(r'\s+', '', str(value)) for value in values if value]

    company_matches = [p for p in projects if any(name in text for name in names(p, 'company'))]
    if not company_matches:
        request = re.sub(r'^(?:(?:帮我|给我|请|麻烦|开始|打招呼|投递|招呼|查看|浏览|看|打|给))+', '', text)
        def prefix_matches(project, name, length):
            prefix, tail = name[:length], request[length:]
            return (not prefix.isdigit() and request.startswith(prefix) and
                    (not tail or re.match(r'^\d+(?:人|个|位|次|$)', tail) or
                     tail in ('开始','开始打招呼','打招呼','招呼') or
                     any(tail.startswith(job) for job in names(project,'position'))))
        prefixes = [(p, len(name[:length])) for p in projects for name in names(p, 'company')
                    for length in range(2, len(name)) if prefix_matches(p,name,length)]
        if prefixes:
            longest = max(length for _, length in prefixes)
            company_matches = [p for p, length in prefixes if length == longest]
    position_matches = [p for p in projects if any(name in text for name in names(p, 'position'))]
    if company_matches and position_matches:
        matches = [p for p in company_matches if p in position_matches]
    else:
        matches = company_matches or position_matches
    return list({str(p['profile']): p for p in matches}.values())


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
    matches=match_projects(text,available)
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
    return dict(state='ready_to_start',startup_mode='direct',profile=project['profile'],company=project['company'],position=project['position'],position_display=project.get('position_display',project['position']),display_name=project.get('display_name'),provenance=project.get('provenance'),
                target=target,max_views=max_views,chat_title=f"{project['company']} {project['position']} - {at.astimezone(timezone(timedelta(hours=8))).date().isoformat()}",
                approval_warning=project.get('approval')!='approved',views_explicit=bool(viewing),greetings_explicit=bool(greeting),
                next_actions=['set_current_chat_title','collapse_chat_sidebar','open_boss_in_codex','confirm_already_logged_in_prompt_if_present','start_direct_run'])


def prepare(prompt, db_path=None, root=None):
    """Every entry, menu choice and continuation reads the local folder anew."""
    import local_catalog
    catalog = local_catalog.scan(root)
    projects = catalog['projects']
    latest = project_registry.latest_run_readonly(db_path)
    plan = parse(prompt, projects)
    command = re.sub(r'\s+', '', prompt)
    common = dict(companies=catalog['companies'], config_root=catalog['root'],
                  config_errors=catalog['errors'], config_folder_missing=catalog['missing'],
                  project_count=len(catalog['companies']), position_count=len(projects))
    if command in ('2', '菜单2', '菜单：2', '菜单:2', '查看所有', '查看所有企业', '查看本地企业', '查看已有项目'):
        plan.update(state='needs_selection', selection_level='company', matches=[],
                    next_actions=['show_local_companies'])
    elif command in ('3', '4', '5', '6'):
        action = {'3':'create_local_project', '4':'show_update_menu', '5':'test_environment', '6':'exit_greetings'}[command]
        plan = dict(state='menu_action', menu_choice=int(command), next_actions=[action],
                    template=str(Path(catalog['root'])/'岗位填写模板.md'))
    elif command in ('1', '继续', '继续上次', '继续上次项目'):
        selected = next((p for p in projects if latest and str(p['profile']) == str(latest.get('profile_path'))), None)
        if selected:
            if latest.get('resumable') and latest.get('run_state') in ('running','paused','login_required'):
                plan = dict(state='ready_to_resume', profile=selected['profile'], run_id=latest['run_id'],
                            company=selected['company'], position=selected['position'], next_actions=['resume_existing_run'])
            else:
                plan = parse(selected['company']+' '+selected['position'], [selected])
        else:
            plan.update(state='menu', reason='上次岗位已移除、配置不可用或暂无记录，请从本地企业重新选择')
    elif plan['state'] == 'needs_selection' and not plan.get('matches'):
        plan.update(state='menu', reason='未唯一匹配本地企业及岗位，请选择菜单或本地企业')
    if plan['state'] == 'menu':
        home = project_registry.build_home_menu(projects, latest)
        # Counts include company folders with no runnable jobs, too.
        home['menu_items'][1] = f"2. 查看所有本地企业（共 {len(catalog['companies'])} 家企业，{len(projects)} 个岗位）"
        home['menu_text'] = home['menu_title']+'\n\n'+'\n'.join(home['menu_items'])
        plan.update(home, menu_level='home')
    plan.update(common)
    return plan


def refresh_selected(plan, db_path=None):
    """A saved plan cannot start a removed, archived or malformed local job."""
    import local_catalog
    catalog = local_catalog.scan()
    selected = next((p for p in catalog['projects'] if str(p['profile']) == str(plan.get('profile'))), None)
    if selected is None:
        fallback = prepare('菜单1', db_path)
        fallback.update(reason='所选岗位已移除或配置不可用，请重新选择',
                        target=plan.get('target', ledger.DEFAULT_TARGET), max_views=plan.get('max_views', ledger.DEFAULT_MAX_VIEWS))
        return fallback
    plan.update(company=selected['company'], position=selected['position'],
                position_display=selected.get('position_display', selected['position']))
    return plan


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--prompt');p.add_argument('--plan',type=Path)
    p.add_argument('--state-dir',type=Path,default=startup_plan.DEFAULT_ROOT)
    p.add_argument('--complete-action');p.add_argument('--db',type=Path,default=ledger.DEFAULT_DB)
    p.add_argument('--confirm-filters',action='store_true',help='Use only after the user checked filters and replied 1')
    p.add_argument('--start-direct',action='store_true',help='Start a prepared explicit-job request without manual filter confirmation')
    p.add_argument('--min-score',type=int)
    p.add_argument('--short-view-wait',action=argparse.BooleanOptionalAction,default=None)
    args=p.parse_args()
    if args.plan:plan=startup_plan.load(args.plan)
    elif args.confirm_filters or args.start_direct or args.complete_action:
        if not args.prompt:p.error('--plan or original --prompt required to resume')
        plan=startup_plan.find(args.prompt,args.state_dir)
    else:
        if not args.prompt:p.error('--prompt or --plan required')
        plan=prepare(args.prompt,args.db)
        plan['browser_target']='codex_iab'
        plan['short_view_wait']=True if args.short_view_wait is None else args.short_view_wait
        plan['min_score']=70 if args.min_score is None else args.min_score
        if plan['state'] in ('await_filters','ready_to_start'):plan=startup_plan.save(plan,args.prompt,args.state_dir)
    if args.complete_action:startup_plan.complete(plan,args.complete_action)
    should_start=(args.confirm_filters and plan['state']=='await_filters') or (args.start_direct and plan['state']=='ready_to_start')
    if should_start and not plan.get('run'):
        plan=refresh_selected(plan,args.db)
        if plan['state'] not in ('await_filters','ready_to_start'):
            print(json.dumps(plan,ensure_ascii=False));return
        with contextlib.closing(ledger.connect(args.db)) as db:
            import run_safety
            with run_safety.action_lock(db):
                plan=startup_plan.load(plan['plan_file'])
                if not plan.get('run'):
                    out=io.StringIO()
                    with contextlib.redirect_stdout(out):
                        ledger.start(db,argparse.Namespace(profile=plan['profile'],target=plan['target'],max_views=plan['max_views'],short_view_wait=plan.get('short_view_wait',True) if args.short_view_wait is None else args.short_view_wait,min_score=plan.get('min_score',70) if args.min_score is None else args.min_score))
                    created=json.loads(out.getvalue())
                    if created['state']!='started':
                        print(json.dumps(created,ensure_ascii=False));return
                    plan['run']=created;plan['state']='started'
                    startup_plan.complete(plan,'start_direct_run' if args.start_direct else 'wait_for_manual_filters_and_reply_1')
    plan['pending_startup_actions']=[action for action in plan.get('next_actions',[]) if action not in plan.get('startup_completed',[])]
    print(json.dumps(plan,ensure_ascii=False))


if __name__=='__main__':main()
