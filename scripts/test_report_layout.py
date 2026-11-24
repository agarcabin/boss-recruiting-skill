import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from openpyxl import load_workbook
import candidate_log
import ledger
import report_layout
import report_snapshot
import report_store
import stop_controller


class ReportLayoutTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.db = ledger.connect(self.root/'ledger.sqlite3')
        self.addCleanup(self.db.close)
        self.profile = self.root/'profile.md'
        self.profile.write_text('---\nschema: boss-greeting-profile/v1\ncompany: Sample\nposition: Role\n---\n', encoding='utf-8')
        self.stamp = '2026-11-17T10:00:00+08:00'
        self.db.execute('INSERT INTO runs(run_id,started_at,deadline_at,target,profile_path,profile_hash,rule_snapshot,evaluation_mode,stop_reason,admission_build_id) VALUES (?,?,?,?,?,?,?,?,?,(SELECT build_id FROM installation_admission WHERE id=1))',
                        ('run',self.stamp,'',10,str(self.profile),'hash','{"csv_reports":true}','resume','manual_stop'))
        self.db.execute('INSERT INTO run_control(run_id,state,updated_at) VALUES (?,?,?)', ('run','stopped',self.stamp))
        candidate_log.table(self.db)
        report_store.capture(self.db,'run',self.profile)
        self.db.execute('INSERT INTO assessments(run_id,candidate_hash,candidate_name,started_at,ended_at,overall_score,hard_requirements,decision,pros,cons,electronic_enabled,send_status,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)',
                        ('run','candidate','Sample',self.stamp,self.stamp,60,'true','skip','sample','sample',0,'not-sent',self.stamp))
        self.canonical = report_store.destination(self.db,self.root,self.stamp,self.profile)

    def test_snapshot_reuses_one_path_and_final_cleans_only_owned_snapshots(self):
        first = report_snapshot.create(self.db,'run',self.root,self.stamp)
        second = report_snapshot.create(self.db,'run',self.root,self.stamp)
        self.assertEqual(first,second)
        self.assertEqual(first.parent,self.canonical.parent/'运行记录'/'记录快照')
        self.assertEqual(len(list(first.parent.glob('*.xlsx'))),1)
        other = first.parent/'Other-快照.xlsx'
        other.write_bytes(b'unrelated')
        sidecar=self.canonical.with_suffix('.data');sidecar.mkdir();(sidecar/'rows.csv').write_text('old CSV')
        result = stop_controller.final_report(self.db,'run',self.root)
        self.assertEqual(result,self.canonical)
        self.assertFalse(first.exists())
        self.assertTrue(other.exists())
        report_layout.verify(self.db,result,self.stamp,self.profile)
        self.assertFalse(list(self.canonical.parent.glob('*.data')))

    def test_failed_snapshot_replace_preserves_existing_file(self):
        path = report_snapshot.create(self.db,'run',self.root,self.stamp)
        before = path.read_bytes()
        with patch('report_snapshot.os.replace',side_effect=PermissionError('open in Excel')):
            with self.assertRaises(PermissionError):report_snapshot.create(self.db,'run',self.root,self.stamp)
        self.assertEqual(path.read_bytes(),before)
        self.assertFalse(list(path.parent.glob('.snapshot-*')))

    def test_missing_final_does_not_delete_snapshot_or_csv(self):
        snapshot = report_snapshot.create(self.db,'run',self.root,self.stamp)
        data=self.canonical.with_suffix('.data');data.mkdir();(data/'rows.csv').write_text('preserve')
        with self.assertRaises(ValueError):report_layout.cleanup(self.db,self.canonical,self.stamp,self.profile)
        self.assertTrue(snapshot.exists());self.assertTrue((data/'rows.csv').exists())

    def test_snapshot_with_uncovered_records_is_kept(self):
        snapshot = report_snapshot.create(self.db,'run',self.root,self.stamp)
        wb=load_workbook(snapshot);sheet=wb['详细信息'];headers=[c.value for c in sheet[1]]
        extra=[None]*len(headers)
        for key,value in zip(('运行编号','候选人标识哈希','开始时间'),('missing-run','missing-person',self.stamp)):
            extra[headers.index(key)]=value
        sheet.append(extra);wb.save(snapshot);wb.close()
        candidate_log.workbook(self.db,self.root,self.stamp,profile_path=self.profile)
        self.assertTrue(report_layout.cleanup(self.db,self.canonical,self.stamp,self.profile))
        self.assertTrue(snapshot.exists())

    def test_move_updates_archived_paths_and_json_links(self):
        folder=self.canonical.parent/'简历图片';folder.mkdir(parents=True)
        image=folder/'sample.png';image.write_bytes(b'sample')
        payload=json.dumps(dict(resume_evidence=dict(image=str(image))))
        self.db.execute('UPDATE assessments SET resume_image_path=?,evaluation_input=?',(str(image),payload))
        report_layout.move_assets(self.db,self.canonical.parent)
        row=self.db.execute('SELECT resume_image_path,evaluation_input FROM assessments').fetchone()
        new=self.canonical.parent/'运行记录'/'简历图片'/'sample.png'
        self.assertEqual(row[0],str(new));self.assertTrue(new.exists())
        self.assertEqual(json.loads(row[1])['resume_evidence']['image'],str(new))
        self.assertFalse(folder.exists())
        self.assertEqual(report_layout.move_assets(self.db,self.canonical.parent),[])

    def test_archive_path_uses_runtime_directory(self):
        self.assertEqual(candidate_log.daily_dir(self.root,self.stamp),self.canonical.parent/'运行记录')

    def test_cleanup_rejects_paths_outside_day(self):
        with self.assertRaises(ValueError):report_layout.checked(self.root/'outside.data',self.canonical.parent)


if __name__ == '__main__':unittest.main()
