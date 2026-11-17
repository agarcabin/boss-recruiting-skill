"""Export a labelled point-in-time workbook without Excel automation."""
from datetime import datetime
import sqlite3
import uuid


def create(db,run_id,root,stamp=None):
    import candidate_log,ledger,report_store
    run=ledger.run_row(db,run_id)
    stamp=stamp or ledger.iso(ledger.now())
    canonical=report_store.destination(db,root,stamp,run['profile_path'])
    folder=canonical.parent/'记录快照'
    folder.mkdir(parents=True,exist_ok=True)
    target=folder/(canonical.stem+'-快照-'+datetime.now().strftime('%H%M%S')+'-'+uuid.uuid4().hex[:6]+'.xlsx')
    candidate_log.table(db)
    if db.in_transaction:raise ValueError('report_requires_committed_candidate_data')
    snapshot=sqlite3.connect(':memory:');snapshot.row_factory=sqlite3.Row
    workbook=None
    try:
        db.backup(snapshot)
        workbook=candidate_log._render_workbook(snapshot,root,stamp,
            profile_path=run['profile_path'],_destination=target,_return_workbook=True)
        note=workbook.create_sheet('快照说明')
        note.append(['此文件为打开时的记录快照，不自动刷新；最新数据以运行记录为准。'])
        note.column_dimensions['A'].width=100
        workbook.save(target)
    finally:
        if workbook is not None:workbook.close()
        snapshot.close()
    return target
