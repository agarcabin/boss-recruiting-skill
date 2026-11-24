"""Classify archived resume images using recorded review and delivery evidence."""
import json
from pathlib import Path


CATEGORIES = ('已招呼简历', 'AI复盘捞回简历', 'AI复盘过滤简历', '未招呼简历')


def category(result, send_status):
    reviewed = result.get('trigger') == 'ai_overall_review'
    if reviewed and result.get('ai_review_suitable') is False:
        return 'AI复盘过滤简历'
    if send_status != 'sent':
        return '未招呼简历'
    if (reviewed and result.get('ai_review_suitable') is True
            and result.get('score') is not None and result.get('qualifying_score') is not None
            and result['score'] < result['qualifying_score']):
        return 'AI复盘捞回简历'
    return '已招呼简历'


def image_folder(runtime, name):
    if name not in CATEGORIES:
        raise ValueError('resume_archive_category_invalid')
    base = Path(runtime) / '简历图片'
    for item in CATEGORIES:
        (base / item).mkdir(parents=True, exist_ok=True)
    return base / name


def reclassify(db, row, runtime):
    """Relocate one candidate's images and repair live references before export."""
    if not row['resume_image_path']:
        return
    result = json.loads(row['eligibility_json'] or '{}')
    target_folder = image_folder(runtime, category(result, row['send_status']))
    base = target_folder.parent.resolve()
    moves = []
    fields = ('resume_image_path', 'resume_marked_image_path')
    for field in fields:
        if not row[field]:
            continue
        source = Path(row[field])
        # Older/external archives remain in place; this only handles this date's images.
        if not source.resolve().is_relative_to(base):
            continue
        target = target_folder / source.name
        if source.resolve() == target.resolve():
            continue
        moves.append((source, target))
        if field == 'resume_marked_image_path' and source.with_suffix('.json').is_file():
            moves.append((source.with_suffix('.json'), target.with_suffix('.json')))
    # Preflight the entire group: never replace another candidate's evidence.
    for source, target in moves:
        if not source.is_file():
            raise ValueError('resume_archive_source_missing: ' + str(source))
        if target.exists():
            raise ValueError('resume_archive_category_collision: ' + str(target))
    if not moves:
        return
    mapping = {variant: str(target) for source, target in moves
               for variant in (str(source), source.as_posix())}

    def replace(item):
        if isinstance(item, dict):return {key: replace(value) for key, value in item.items()}
        if isinstance(item, list):return [replace(value) for value in item]
        if isinstance(item, str):return mapping.get(item, item)
        return item

    moved = []
    db.execute('SAVEPOINT resume_image_category')
    try:
        for source, target in moves:
            source.rename(target)
            moved.append((source, target))
        payload = replace(json.loads(row['evaluation_input'] or '{}'))
        db.execute('''UPDATE assessments SET resume_image_path=?,resume_marked_image_path=?,
            evaluation_input=?,report_written=0 WHERE run_id=? AND candidate_hash=?''',
            (replace(row['resume_image_path']), replace(row['resume_marked_image_path']),
             json.dumps(payload, ensure_ascii=False), row['run_id'], row['candidate_hash']))
        has_state = db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='workflow_state'").fetchone()
        state = db.execute('SELECT payload FROM workflow_state WHERE run_id=?', (row['run_id'],)).fetchone() if has_state else None
        if state:
            updated = replace(json.loads(state['payload'] or '{}'))
            db.execute('UPDATE workflow_state SET payload=? WHERE run_id=?',
                       (json.dumps(updated, ensure_ascii=False), row['run_id']))
        db.execute('RELEASE SAVEPOINT resume_image_category')
    except Exception:
        db.execute('ROLLBACK TO SAVEPOINT resume_image_category')
        db.execute('RELEASE SAVEPOINT resume_image_category')
        for source, target in reversed(moved):
            target.rename(source)
        raise
