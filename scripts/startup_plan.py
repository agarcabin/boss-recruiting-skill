"""Persist a prepared request so reply 1 resumes the same task."""
from pathlib import Path
import hashlib,json,os,tempfile,uuid

DEFAULT_ROOT=Path(os.environ.get('LOCALAPPDATA',str(Path.home())))/'Codex'/'recruiting-greetings'/'startup'


def save(plan,prompt,root=DEFAULT_ROOT):
    root=Path(root);root.mkdir(parents=True,exist_ok=True)
    result=dict(plan,plan_id=uuid.uuid4().hex,prompt=prompt,startup_completed=[],run=None)
    path=root/(result['plan_id']+'.json');result['plan_file']=str(path.resolve())
    write(path,result)
    return result


def write(path,plan):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent,delete=False,suffix='.tmp',mode='w',encoding='utf-8') as stream:
        json.dump(plan,stream,ensure_ascii=False,indent=2);temporary=Path(stream.name)
    try:os.replace(temporary,path)
    finally:temporary.unlink(missing_ok=True)


def load(path):
    result=json.loads(Path(path).read_text(encoding='utf-8-sig'))
    result['plan_file']=str(Path(path).resolve())
    return result


def find(prompt,root=DEFAULT_ROOT):
    matches=[]
    for path in Path(root).glob('*.json'):
        plan=load(path)
        if plan.get('prompt')==prompt:matches.append((path.stat().st_mtime_ns,plan))
    if not matches:raise ValueError('no_prepared_request; prepare first or pass --plan')
    return max(matches,key=lambda item:item[0])[1]


def complete(plan,action):
    if action not in plan['startup_completed']:plan['startup_completed'].append(action)
    write(plan['plan_file'],plan)
    return plan
