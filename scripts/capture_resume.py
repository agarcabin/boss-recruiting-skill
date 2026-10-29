"""Fail-fast capture -> OCR for an already registered candidate. Never sends or scores."""
from __future__ import annotations
import argparse
import contextlib
import json
import os
import subprocess
import sys
from pathlib import Path
import ledger
import candidate_checks
import powershell_host
import run_safety


def check_candidate(db,run_id,candidate_id,generation):
    # OCR remains optional; when used it follows the highest-priority colleague check.
    candidate_checks.require_resume(db,run_id,candidate_id)
    return ledger.run_row(db,run_id)


def capture(db, run_id, candidate_id, hwnd, output_dir, execute=None):
    execute = execute or subprocess.run
    generation = ledger.run_row(db, run_id)['generation']
    check_candidate(db, run_id, candidate_id, generation)
    scripts = Path(__file__).resolve().parent
    py = sys.executable
    db_file = run_safety.db_path(db)
    managed = [py, str(scripts / 'managed_helper.py'), '--db', db_file,
               '--run', run_id, '--generation', str(generation), '--']
    output_dir = Path(output_dir).resolve()
    host_command = powershell_host.command(scripts / 'resume_capture.ps1',
        '-WindowHandle', hwnd, '-OutputDir', output_dir, '-PythonPath', py,
        '-SafetyPythonPath', py, '-Run', run_id, '-LedgerDb', db_file, '-Generation', generation)
    # Fresh directory prevents leftover files from a failed candidate passing validation.
    output_dir.mkdir(parents=True, exist_ok=False)

    def stage(command):
        check_candidate(db, run_id, candidate_id, generation)
        result = execute(managed + command, check=True, capture_output=True, text=True, encoding='utf-8-sig',
                         env={**os.environ, 'PYTHONUTF8': '1', 'PYTHONIOENCODING': 'utf-8'})
        payload = json.loads(result.stdout.strip())
        check_candidate(db, run_id, candidate_id, generation)
        return payload

    result = stage(host_command)
    if result.get('state') != 'captured' or result.get('bottomConfirmed') is not True:
        raise ValueError('capture_not_complete_no_ocr')
    image = Path(result.get('longImage', '')).resolve()
    if image != output_dir / 'resume-long.png' or not image.is_file() or not image.stat().st_size:
        raise ValueError('capture_image_missing_or_outside_candidate_directory')
    text = output_dir / 'resume.ocr.txt'
    detail = output_dir / 'resume.ocr.json'
    ocr = stage([py, str(scripts / 'resume_image_pipeline.py'), 'rapidocr', '--image', str(image),
                 '--text-output', str(text), '--json-output', str(detail), '--tile-height', '1200', '--overlap', '150'])
    if ocr.get('state') != 'ok' or not text.is_file() or not text.read_text(encoding='utf-8-sig').strip() or not detail.is_file():
        raise ValueError('ocr_not_complete_no_assessment')
    if json.loads(detail.read_text(encoding='utf-8-sig')).get('state') != 'ok':
        raise ValueError('ocr_evidence_not_ok')
    return {'state': 'ready_for_assessment', 'run_id': run_id, 'candidate_id': candidate_id,
            'generation': generation, 'resume_evidence': {'image': str(image), 'ocr_text': str(text), 'ocr_json': str(detail)}}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--db', type=Path, default=ledger.DEFAULT_DB)
    p.add_argument('--run', required=True)
    p.add_argument('--candidate-id', required=True)
    p.add_argument('--hwnd', required=True, type=int)
    p.add_argument('--output-dir', required=True, type=Path)
    a = p.parse_args()
    try:
        with contextlib.closing(ledger.connect(a.db)) as db:
            result = capture(db, a.run, a.candidate_id, a.hwnd, a.output_dir)
        print(json.dumps(result, ensure_ascii=False))
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        result = {'state': 'failed', 'error': str(exc), 'assessment_started': False, 'automatic_retry': False}
        if isinstance(exc, subprocess.CalledProcessError):
            result['detail'] = (exc.stderr or exc.stdout or '')[-3000:]
        print(json.dumps(result, ensure_ascii=False))
        raise SystemExit(1)


if __name__ == '__main__':
    main()
