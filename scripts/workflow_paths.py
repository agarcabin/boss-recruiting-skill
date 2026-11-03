"""Internal workflow files are independent of desktop report destinations."""
import os
import re
from pathlib import Path


def workflow_dir(run_id):
    if not re.fullmatch(r'[A-Za-z0-9_-]+',str(run_id)):
        raise ValueError('invalid_workflow_run_id')
    local=Path(os.environ.get('LOCALAPPDATA') or Path.home()/'AppData'/'Local')
    folder=local/'Codex'/'recruiting-greetings'/'workflow'/str(run_id)
    folder.mkdir(parents=True,exist_ok=True)
    return folder
