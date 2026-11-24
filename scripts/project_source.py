"""Display provenance and retain local changes against a signed cloud baseline."""
import json
from pathlib import Path

IGNORED = {'created_at', 'updated_at', 'provenance'}
LABELS = {'cloud': ' ☁️', 'local': '（本地）', 'self': '（自建）'}


def root_for(profile):
    profile = Path(profile).resolve()
    for parent in profile.parents:
        if parent.name == 'profiles':
            return parent.parent
    return None


def baseline(root):
    import project_vault
    if root is None or not project_vault.vault_path(root).is_file():
        return {}
    data = project_vault.load(root)
    return project_vault.safe_files(data) if data else {}


def semantic(meta):
    return {k: v for k, v in meta.items() if k not in IGNORED}


def text(value):
    return value.decode('utf-8-sig').replace('\r\n', '\n')


def classify(profile, meta, files=None, root=None):
    profile = Path(profile).resolve()
    provenance = meta.get('provenance') or {}
    if provenance.get('kind') == 'local':
        return dict(provenance)
    root = Path(root).resolve() if root else root_for(profile)
    files = baseline(root) if files is None else files
    name = profile.relative_to(root).as_posix() if root and profile.is_relative_to(root) else None
    old_meta = files.get(str(Path(name).with_name('project.json')).replace('\\', '/')) if name else None
    old_meta = json.loads(old_meta.decode('utf-8-sig')) if old_meta else None
    if meta.get('origin', 'user') == 'user':
        if old_meta and old_meta.get('origin') == 'bundle' and old_meta.get('project_id') == meta.get('project_id'):
            return dict(kind='local', cloud_project_id=meta['project_id'], cloud_profile=name)
        return dict(kind='self')
    if old_meta and name in files:
        same = semantic(meta) == semantic(old_meta) and text(profile.read_bytes()) == text(files[name])
        return dict(kind='cloud' if same else 'local', cloud_project_id=old_meta.get('project_id'), cloud_profile=name)
    if root and (root/'references/project-vault.json').is_file():
        return dict(kind='local', cloud_project_id=meta.get('project_id'))
    return dict(kind='cloud', cloud_project_id=meta.get('project_id'))


def display(position, provenance):
    return position + LABELS[provenance['kind']]


def copy_provenance(meta):
    result = dict(meta)
    provenance = result.get('provenance') or {}
    if result.get('origin') == 'bundle' or provenance.get('kind') in ('cloud', 'local'):
        result['origin'] = 'user'
        result['provenance'] = dict(kind='local', cloud_project_id=provenance.get('cloud_project_id') or result.get('project_id'), cloud_profile=provenance.get('cloud_profile'))
    else:
        result['origin'] = 'user'
        result['provenance'] = dict(kind='self')
    return result


def preserve(files, root, collision_error):
    """Return install inputs, including transactional provenance migrations."""
    import project_vault
    root = Path(root).resolve()
    old = baseline(root)
    preserved = set()
    migrations = {}
    for name in files:
        if not name.endswith('/project.json'):
            continue
        path = root/name
        if not path.is_file():
            continue
        current = json.loads(path.read_text(encoding='utf-8-sig'))
        incoming = json.loads(files[name].decode('utf-8-sig'))
        profile = path.parent/current.get('profile', 'profile.md')
        if not profile.is_file():
            candidates = [root/n for n in old if str(Path(n).parent) == str(Path(name).parent) and n.endswith('.md')]
            profile = candidates[0] if len(candidates) == 1 else profile
        source = classify(profile, current, old, root)
        if source['kind'] == 'cloud':
            continue
        same_id = bool(current.get('project_id')) and current['project_id'] == incoming.get('project_id')
        allowed = same_id and (incoming.get('origin') == 'user' or source['kind'] == 'local' and source.get('cloud_project_id') == incoming.get('project_id'))
        if not allowed:
            raise ValueError(collision_error)
        preserved.add(Path(name).parent.as_posix())
        if source['kind'] == 'local':
            updated = dict(current, origin='user', provenance=source)
            if updated != current:
                migrations[name] = project_vault.crypto.canonical(updated)
    # An incoming profile without metadata cannot overwrite a local project.
    for name in files:
        meta_path = (root/name).parent/'project.json'
        if meta_path.is_file() and meta_path.relative_to(root).as_posix() not in files:
            current = json.loads(meta_path.read_text(encoding='utf-8-sig'))
            if current.get('origin') == 'user':
                raise ValueError(collision_error)
    return {**{n: v for n, v in files.items() if Path(n).parent.as_posix() not in preserved}, **migrations}
