"""A fresh, read-only inventory of company folders and runnable job documents."""
from pathlib import Path
import re

import project_registry
import project_vault
import workspace_paths


def folder_label(name):
    return re.sub(r'^\d+[\s._-]+', '', name)


def linked(path):
    return path.is_symlink() or getattr(path, 'is_junction', lambda: False)()


def scan(root=None):
    root = Path(root) if root is not None else workspace_paths.configs_dir()
    projects, companies, errors = [], [], []
    if not root.is_dir():
        return dict(root=str(root), projects=[], companies=[], errors=[], missing=True)
    for folder in sorted(root.iterdir(), key=lambda p: p.name.casefold()):
        if not folder.is_dir() or linked(folder) or folder.name.startswith(('.', '_')):
            continue
        jobs = []
        for path in sorted(folder.glob('*.md')):
            if linked(path) or not path.resolve().is_relative_to(root.resolve()):
                continue
            try:
                if not project_vault.selectable(path):
                    continue
                ok, reason, _ = __import__('ledger').profile_check(path)
                if not ok:
                    raise ValueError(reason)
                job = project_registry.read_project(path)
                job['company_aliases'] = list(dict.fromkeys([job['company'], folder.name, folder_label(folder.name)]))
                job['company_folder'] = str(folder)
                job['position_aliases'] = list(dict.fromkeys([job['position'], path.stem,
                    re.sub(r'（[^）]*）|\([^)]*\)', '', job['position']).strip()]))
                jobs.append(job)
            except (OSError, ValueError) as exc:
                errors.append(dict(company=folder_label(folder.name), file=str(path), message=str(exc)))
        jobs = project_registry.sort_projects(jobs)
        projects.extend(jobs)
        companies.append(dict(company=folder_label(folder.name), folder=str(folder),
                              position_count=len(jobs), positions=jobs))
    return dict(root=str(root), projects=projects, companies=companies, errors=errors, missing=False)
