"""Fail-fast capture -> OCR for an already registered candidate. Never sends or scores."""
from __future__ import annotations
import argparse
import base64
import contextlib
import json
import os
import subprocess
import sys
from pathlib import Path
import ledger
import candidate_checks
import capture_control
import powershell_host
import run_safety
from windows_process import hidden_options,decode_output


def check_candidate(db,run_id,candidate_id,generation):
    # OCR remains optional; when used it follows the highest-priority colleague check.
    run = capture_control.require_running(db,run_id,generation)
    candidate_checks.require_resume(db,run_id,candidate_id)
    return run


def capture(db, run_id, candidate_id, hwnd, output_dir, execute=None):
    generation = ledger.run_row(db,run_id)['generation']
    try:
        return _capture(db,run_id,candidate_id,hwnd,output_dir,execute)
    except (OSError,ValueError,subprocess.SubprocessError) as exc:
        capture_control.raise_if_interrupted(db,run_id,generation,exc)
        import resume_diagnostics
        detail=resume_diagnostics.reason(exc)
        stage='电子简历OCR/文件校验' if 'ocr' in detail.lower() else '电子简历采集/保存'
        resume_diagnostics.record(db,run_id,candidate_id,stage,exc)
        raise


def import_browser_capture(db, run_id, candidate_id, output_dir, capture, execute=None):
    """Validate Browser screenshots, then stitch/OCR locally without window APIs."""
    execute = execute or subprocess.run
    generation = ledger.run_row(db, run_id)['generation']
    check_candidate(db, run_id, candidate_id, generation)
    folder = Path(output_dir).resolve()
    if (capture.get('candidate_id') != candidate_id or capture.get('topConfirmed') is not True
            or capture.get('bottomConfirmed') is not True or capture.get('contentStable') is not True
            or capture.get('occluded') is not False or not capture.get('evidence')):
        raise ValueError('browser_capture_not_complete_no_ocr')
    pages = capture.get('pages')
    if not isinstance(pages, list) or not 1 <= len(pages) <= 100:
        raise ValueError('browser_capture_pages_required')
    from resume_image_pipeline import read_image
    paths, offsets = [], []
    width = None
    end = 0
    for index, page in enumerate(pages):
        if 'jpeg_base64' in page:
            encoded = page['jpeg_base64']
            if not isinstance(encoded, str) or len(encoded) > 20000000:
                raise ValueError('browser_capture_invalid_image_bytes')
            try:
                raw = base64.b64decode(encoded, validate=True)
            except ValueError as exc:
                raise ValueError('browser_capture_invalid_image_bytes') from exc
            if not raw.startswith(b'\xff\xd8\xff'):
                raise ValueError('browser_capture_jpeg_bytes_required')
            source = folder / f'page-{index+1:03d}.jpg'
            with source.open('xb') as image_file:
                image_file.write(raw)
        else:
            source = Path(page['image']).resolve()
        offset = page.get('offset')
        if (source.parent != folder or source.suffix.lower() not in ('.jpg', '.jpeg')
                or source.is_symlink() or not source.is_file() or not source.stat().st_size):
            raise ValueError('browser_capture_image_outside_candidate_directory')
        pixels = read_image(source)
        height, current_width = pixels.shape[:2]
        if (type(offset) is not int or offset < 0 or (not offsets and offset != 0)
                or (offsets and (offset <= offsets[-1] or offset > end))
                or (width is not None and width != current_width)):
            raise ValueError('browser_capture_offsets_gap_or_size_mismatch')
        width, end = current_width, offset + height
        if end > 200000 or width * end > 150000000:
            raise ValueError('browser_capture_image_too_large')
        paths.append(source)
        offsets.append(offset)
    startup = dict(capture, provider='browser-plugin', run_id=run_id, generation=generation)
    (folder / 'resume-capture.json').write_text(json.dumps(startup, ensure_ascii=False), encoding='utf-8')
    image = folder / 'resume-long.png'
    text, detail = folder / 'resume.ocr.txt', folder / 'resume.ocr.json'
    pipeline = str(Path(__file__).with_name('resume_image_pipeline.py'))

    def stage(*arguments):
        check_candidate(db, run_id, candidate_id, generation)
        done = execute([sys.executable, pipeline, *map(str, arguments)], check=True,
                       capture_output=True, timeout=180, **hidden_options())
        check_candidate(db, run_id, candidate_id, generation)
        return json.loads(decode_output(done.stdout))

    stage('stitch', '--pages', *paths, '--offsets', ','.join(map(str, offsets)),
          '--output', image, '--no-mask-left-arrow')
    ocr = stage('rapidocr', '--image', image, '--text-output', text, '--json-output', detail,
                '--tile-height', '1200', '--overlap', '150')
    if (ocr.get('state') != 'ok' or not image.is_file() or not text.is_file()
            or not text.read_text(encoding='utf-8-sig').strip() or not detail.is_file()
            or json.loads(detail.read_text(encoding='utf-8-sig')).get('state') != 'ok'):
        raise ValueError('ocr_not_complete_no_assessment')
    if any(marker in text.read_text(encoding='utf-8-sig') for marker in ('该牛人近期受同行BOSS欢迎', '热搜牛人', '相关推荐')):
        raise ValueError('resume_capture_occluded_by_recommendations')
    return dict(state='ready_for_assessment', resume_evidence=dict(
        image=str(image), ocr_text=str(text), ocr_json=str(detail), capture_json=str(folder / 'resume-capture.json')))


def _capture(db, run_id, candidate_id, hwnd, output_dir, execute=None):
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
        result = execute(managed + command, check=True, capture_output=True,
                         env={**os.environ, 'PYTHONUTF8': '1', 'PYTHONIOENCODING': 'utf-8'}, **hidden_options())
        payload = json.loads(decode_output(result.stdout).strip())
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
    ocr_body=text.read_text(encoding='utf-8-sig')
    if any(marker in ocr_body for marker in ('该牛人近期受同行BOSS欢迎','热搜牛人','相关推荐')):
        raise ValueError('resume_capture_occluded_by_recommendations')
    if result.get('captureMode') == 'single_page' and '牛人' not in ocr_body:
        raise ValueError('resume_single_page_bottom_marker_missing')
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
    except capture_control.CaptureInterrupted as exc:
        print(json.dumps(dict(state='interrupted',error=str(exc),assessment_started=False),ensure_ascii=False))
        raise SystemExit(20)
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        result = {'state': 'failed', 'error': str(exc), 'assessment_started': False, 'automatic_retry': False}
        if isinstance(exc, subprocess.CalledProcessError):
            result['detail'] = decode_output(exc.stderr or exc.stdout)[-3000:]
        print(json.dumps(result, ensure_ascii=False))
        raise SystemExit(1)


if __name__ == '__main__':
    main()
