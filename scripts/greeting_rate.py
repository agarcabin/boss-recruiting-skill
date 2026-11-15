"""Transaction helper and compatibility responses; no local sending quota."""
from contextlib import contextmanager


@contextmanager
def transaction(db):
    owns = not db.in_transaction
    if owns:db.execute('BEGIN IMMEDIATE')
    try:
        yield
        if owns:db.commit()
    except BaseException:
        if owns:db.rollback()
        raise


def status(db, at=None):
    return dict(state='ready', enabled=False, used=None, remaining=None,
                retry_after_seconds=0, retry_at=None)


def claim(db, candidate_hash, at=None):
    return status(db, at)
