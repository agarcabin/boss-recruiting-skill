"""Daily runtime assets and verified cleanup of temporary report exports."""
import json
from pathlib import Path
import shutil
import zipfile

from openpyxl import load_workbook


def checked(path, day_folder):
    path, day_folder = Path(path).absolute(), Path(day_folder).resolve()
    path.resolve().relative_to(day_folder)
    for parent in (path, *path.parents):
        if parent.is_symlink() or getattr(parent, 'is_junction', lambda: False)():
            raise ValueError('report_layout_link_forbidden')
        if parent == day_folder:
            break
    if path.resolve() == day_folder:
        raise ValueError('report_layout_daily_root_forbidden')
    return path


def record_keys(path):
    workbook = load_workbook(path, read_only=True, data_only=True)
    try:
        rows = iter(workbook['详细信息'].values)
        headers = next(rows)
        indices = [headers.index(key) for key in ('运行编号', '候选人标识哈希', '开始时间')]
        return {tuple(row[i] for i in indices) for row in rows if row[indices[0]]}
    finally:
        workbook.close()


def verify(db, path, stamp, profile):
    import daily_metrics, report_store
    path = Path(path)
    expected = (report_store.owner(db), report_store.day(stamp), report_store.for_profile(db, profile)['job'])
    if not path.is_file() or not report_store.owned(path, expected):
        raise ValueError('final_report_missing_or_owner_mismatch')
    with zipfile.ZipFile(path) as archive:
        if archive.testzip() or any(name.startswith(('xl/queryTables/', 'xl/connections')) for name in archive.namelist()):
            raise ValueError('final_report_invalid_or_csv_dependent')
    expected_keys = {(row['run_id'], row['candidate_hash'], row['started_at'])
                     for row in daily_metrics.rows(db, profile, stamp)}
    if record_keys(path) != expected_keys:
        raise ValueError('final_report_record_coverage_mismatch')
    return expected_keys


def cleanup(db, canonical, stamp, profile):
    import report_store
    canonical = Path(canonical)
    covered = verify(db, canonical, stamp, profile)
    job = report_store.for_profile(db, profile)['job']
    date = report_store.day(stamp)
    owner = (report_store.owner(db), date, job)
    errors = []
    for folder in (canonical.parent/'运行记录'/'记录快照', canonical.parent/'记录快照'):
        checked(folder, canonical.parent)
        for path in folder.glob(canonical.stem+'-快照*.xlsx'):
            try:
                checked(path, canonical.parent)
                if not report_store.owned(path, owner) or not record_keys(path).issubset(covered):
                    raise ValueError('snapshot_not_covered_by_final_report')
                path.unlink()
            except (OSError, ValueError) as exc:
                errors.append(str(path)+': '+str(exc))
    # Only individually named sidecars under this job's verified daily folder.
    for folder in (canonical.with_suffix('.data'), canonical.parent/'运行记录'/(canonical.stem+'.data')):
        checked(folder, canonical.parent)
        if folder.is_dir():
            try:
                # Preflight every entry, so no linked directory is followed.
                for child in folder.rglob('*'):
                    checked(child, canonical.parent)
                shutil.rmtree(folder)
            except (OSError, ValueError) as exc:
                errors.append(str(folder)+': '+str(exc))
    if db.execute("SELECT 1 FROM sqlite_master WHERE name='report_sync'").fetchone():
        db.execute('DELETE FROM report_sync WHERE day=? AND job=?', (date, job))
    key = 'report_cleanup_pending/'+date+'/'+job
    if errors:
        db.execute('INSERT OR REPLACE INTO settings VALUES (?,?)', (key, json.dumps(errors, ensure_ascii=False)))
    else:
        db.execute('DELETE FROM settings WHERE key=?', (key,))
    return errors


def move_assets(db, day_folder):
    """Move a known date's assets; preserve files and repair recorded links."""
    day_folder = Path(day_folder)
    runtime = checked(day_folder/'运行记录', day_folder)
    runtime.mkdir(parents=True, exist_ok=True)
    mappings = []
    sources = [day_folder/name for name in ('简历图片', '简历OCR', '记录快照')]
    sources += list(day_folder.glob('*.data'))
    for source in sources:
        checked(source, day_folder)
        target = checked(runtime/source.name, day_folder)
        if not source.exists():
            continue
        if target.exists():
            raise ValueError('report_layout_move_conflict: '+str(target))
        # Validate the entire named subtree before moving it.
        for child in source.rglob('*'):
            checked(child, day_folder)
        source.rename(target)
        mappings.append((str(source), str(target)))

    def replace(value):
        if not isinstance(value, str):
            return value
        try:
            parsed = json.loads(value)
        except (ValueError, TypeError):
            parsed = None
        if isinstance(parsed, (dict, list)):
            def walk(item):
                if isinstance(item, dict):return {key:walk(child) for key,child in item.items()}
                if isinstance(item, list):return [walk(child) for child in item]
                return replace(item) if isinstance(item, str) else item
            changed = walk(parsed)
            return json.dumps(changed, ensure_ascii=False) if changed != parsed else value
        for old, new in mappings:
            for left, right in ((old, new), (old.replace('\\', '/'), new.replace('\\', '/')),
                                (old.replace('\\', '\\\\'), new.replace('\\', '\\\\'))):
                value = value.replace(left, right)
        return value

    fields = {'assessments': ('resume_image_path', 'resume_ocr_text_path', 'resume_ocr_json_path',
                             'resume_marked_image_path', 'card_image_path', 'card_uia_path', 'pdf_path',
                             'evaluation_input', 'eligibility_json'),
              'runs': ('report_path',), 'workflow_state': ('payload',),
              'report_sync': ('data_dir',)}
    for table, columns in fields.items():
        available = {row[1] for row in db.execute('PRAGMA table_info('+table+')')}
        for column in columns:
            if column not in available:
                continue
            for row in db.execute('SELECT rowid,'+column+' FROM '+table+' WHERE '+column+' IS NOT NULL').fetchall():
                changed = replace(row[1])
                if changed != row[1]:
                    db.execute('UPDATE '+table+' SET '+column+'=? WHERE rowid=?', (changed, row[0]))
    return mappings
