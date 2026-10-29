"""Portable project package behavior checks."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

import project_registry


PROFILE = """---
schema: boss-greeting-profile/v1
company: Test Company
position: Sales Manager
approval: approved
approved_by: owner
approved_at: 2026-10-20
---
## 页面核验
Test page.
## 企业与岗位事实
Test facts.
## 自动筛选条件
Test criteria.
## 评分规则
Test scoring.
## 加分项
Test bonus.
## 待人工确认
None.
## 固定招呼话术
Hello, this is an approved test greeting.
## 冲突与待确认
无
## 来源
Test source.
"""


class ProjectRegistryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.profiles = self.root / "profiles"
        self.source = self.profiles / "source"
        self.source.mkdir(parents=True)
        self.profile = self.source / "profile-test.md"
        self.profile.write_text(PROFILE, encoding="utf-8")

    def test_register_export_and_import_round_trip(self):
        project = project_registry.register_project(self.profile, "test-sales")
        self.assertEqual(project["project_id"], "test-sales")
        archive = self.root / "test.boss-project.zip"
        exported = project_registry.export_project(self.profile, archive)
        self.assertEqual(exported["state"], "exported")
        with ZipFile(archive) as package:
            self.assertEqual(set(package.namelist()), {"manifest.json", "project.json", self.profile.name})
            self.assertNotIn("candidate", package.read("manifest.json").decode("utf-8").lower())

        imported_root = self.root / "imported"
        result = project_registry.import_project(archive, imported_root)
        self.assertEqual(result["state"], "imported")
        imported = imported_root / "test-sales" / self.profile.name
        self.assertEqual(imported.read_text(encoding="utf-8"), PROFILE)
        self.assertEqual(project_registry.list_projects(imported_root)[0]["approval"], "approved")

    def test_import_rejects_duplicate_unless_overwrite_requested(self):
        archive = self.root / "test.boss-project.zip"
        project_registry.export_project(self.profile, archive)
        project_registry.import_project(archive, self.root / "imported")
        with self.assertRaisesRegex(ValueError, "project_already_exists"):
            project_registry.import_project(archive, self.root / "imported")
        self.assertEqual(project_registry.import_project(archive, self.root / "imported", overwrite=True)["state"], "imported")

    def test_greeting_default_and_triple_survive_registration_export_import(self):
        self.assertEqual(project_registry.read_project(self.profile)['greeting_mode'],'single')
        project_registry.register_project(self.profile)
        metadata=self.source/'project.json'
        config=json.loads(metadata.read_text(encoding='utf-8'))
        self.assertEqual(config['greeting_mode'],'single')
        config['greeting_mode']='triple'
        metadata.write_text(json.dumps(config),encoding='utf-8')
        archive=self.root/'triple.boss-project.zip'
        project_registry.export_project(self.profile,archive)
        imported=project_registry.import_project(archive,self.root/'imported')
        project=project_registry.list_projects(self.root/'imported')[0]
        self.assertEqual(project['greeting_mode'],'triple')
        self.assertEqual(json.loads(Path(project['metadata']).read_text(encoding='utf-8'))['greeting_mode'],'triple')

    def test_import_rejects_checksum_tampering(self):
        archive = self.root / "test.boss-project.zip"
        project_registry.export_project(self.profile, archive)
        tampered = self.root / "tampered.boss-project.zip"
        with ZipFile(archive) as source, ZipFile(tampered, "w") as target:
            for item in source.infolist():
                data = source.read(item)
                if item.filename.endswith(".md"):
                    data += b"\nchanged"
                target.writestr(item, data)
        with self.assertRaisesRegex(ValueError, "archive_checksum_mismatch"):
            project_registry.import_project(tampered, self.root / "imported")

    def test_list_ignores_unrelated_markdown(self):
        (self.profiles / "notes.md").write_text("not a profile", encoding="utf-8")
        items = project_registry.list_projects(self.profiles)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["company"], "Test Company")


if __name__ == "__main__":
    unittest.main()
