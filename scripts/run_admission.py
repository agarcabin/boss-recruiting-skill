"""Installation/run-creation exclusion, enforced even for unchanged legacy callers."""
import contextlib,json,sqlite3
from pathlib import Path
import local_mutex

BUILD_ID='1.3.2'

def path(db):return str(Path(db.execute('PRAGMA database_list').fetchone()[2]).resolve())
def key(db):return 'install-admission:'+path(db).casefold()

def ensure(db):
    columns={row[1] for row in db.execute('PRAGMA table_info(runs)')}
    if not columns:return
    if 'admission_build_id' not in columns:db.execute('ALTER TABLE runs ADD COLUMN admission_build_id TEXT')
    db.execute('CREATE TABLE IF NOT EXISTS installation_admission(id INTEGER PRIMARY KEY CHECK(id=1),build_id TEXT NOT NULL,maintenance INTEGER NOT NULL,journal TEXT)')
    db.execute('INSERT OR IGNORE INTO installation_admission VALUES (1,?,0,NULL)',(BUILD_ID,))
    db.execute("""CREATE TRIGGER IF NOT EXISTS run_install_admission BEFORE INSERT ON runs
      BEGIN
        SELECT CASE WHEN (SELECT maintenance FROM installation_admission WHERE id=1)!=0
          THEN RAISE(ABORT,'installation_in_progress') END;
        SELECT CASE WHEN NEW.admission_build_id IS NULL OR NEW.admission_build_id!=(SELECT build_id FROM installation_admission WHERE id=1)
          THEN RAISE(ABORT,'reload_updated_skill_before_start') END;
      END""")

def assert_idle(db):
    has=db.execute("SELECT 1 FROM sqlite_master WHERE name='runs'").fetchone()
    if not has:return
    control=db.execute("SELECT 1 FROM sqlite_master WHERE name='run_control'").fetchone()
    if control:
        row=db.execute("SELECT 1 FROM runs r LEFT JOIN run_control c ON c.run_id=r.run_id WHERE COALESCE(c.state,'running')!='stopped' LIMIT 1").fetchone()
    else:row=db.execute('SELECT 1 FROM runs LIMIT 1').fetchone()
    if row:raise ValueError('active_recruiting_run_stop_before_update')

@contextlib.contextmanager
def start(db):
    with local_mutex.locked(key(db)):
        ensure(db)
        db.execute('BEGIN IMMEDIATE')
        try:
            state=db.execute('SELECT * FROM installation_admission WHERE id=1').fetchone()
            if state['maintenance']:raise ValueError('installation_in_progress_recover_first')
            if state['build_id']!=BUILD_ID:raise ValueError('reload_updated_skill_before_start')
            yield
            db.commit()
        except BaseException:db.rollback();raise

@contextlib.contextmanager
def maintenance(database,journal,build_id=None):
    database=Path(database);database.parent.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(database,timeout=25,isolation_level=None);db.row_factory=sqlite3.Row
    ticket=dict(restored=False,previous=None,had_guard=False)
    try:
        with local_mutex.locked('install-admission:'+str(database.resolve()).casefold()):
            db.execute('BEGIN IMMEDIATE')
            try:
                assert_idle(db)
                ticket['had_guard']=bool(db.execute("SELECT 1 FROM sqlite_master WHERE name='installation_admission'").fetchone())
                if ticket['had_guard']:ticket['had_guard']=bool(db.execute('SELECT 1 FROM installation_admission WHERE id=1').fetchone())
                if ticket['had_guard']:
                    ticket['previous']=dict(db.execute('SELECT * FROM installation_admission WHERE id=1').fetchone())
                    if ticket['previous']['maintenance']:raise ValueError('unfinished_installation_recover_first')
                # An empty first-install database is created by the normal initializer later.
                if not db.execute("SELECT 1 FROM sqlite_master WHERE name='runs'").fetchone():
                    db.execute('CREATE TABLE runs(run_id TEXT PRIMARY KEY,started_at TEXT NOT NULL,deadline_at TEXT NOT NULL,target INTEGER NOT NULL,profile_path TEXT NOT NULL,profile_hash TEXT NOT NULL,min_score INTEGER NOT NULL DEFAULT 70)')
                ensure(db)
                from vault_crypto import atomic,canonical
                atomic(Path(journal),canonical(dict(state='maintenance',database=str(database),previous=ticket['previous'],had_guard=ticket['had_guard'])))
                db.execute('UPDATE installation_admission SET maintenance=1,journal=? WHERE id=1',(str(journal),))
                db.commit()
            except BaseException:db.rollback();raise
            try:
                yield ticket
                activated_build=build_id or BUILD_ID
                atomic(Path(journal),canonical(dict(state='activation_ready',database=str(database),previous=ticket['previous'],had_guard=ticket['had_guard'],build_id=activated_build)))
                db.execute('BEGIN IMMEDIATE')
                assert_idle(db)
                db.execute('UPDATE installation_admission SET build_id=?,maintenance=0,journal=NULL WHERE id=1',(activated_build,))
                db.commit()
                # Activation is committed; a cosmetic journal write must not initiate rollback.
                try:atomic(Path(journal),canonical(dict(state='complete',database=str(database))))
                except OSError:pass
            except BaseException:
                if db.in_transaction:db.rollback()
                if ticket['restored']:restore_guard(db,ticket)
                raise
    finally:db.close()

def restore_guard(db,ticket):
    db.execute('BEGIN IMMEDIATE')
    try:
        if not ticket['had_guard']:
            db.execute('DROP TRIGGER IF EXISTS run_install_admission')
            db.execute('DROP TABLE installation_admission')
        else:
            previous=ticket['previous']
            db.execute('UPDATE installation_admission SET build_id=?,maintenance=?,journal=? WHERE id=1',(previous['build_id'],previous['maintenance'],previous['journal']))
        db.commit()
    except BaseException:db.rollback();raise
