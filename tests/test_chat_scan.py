"""Offline tests for request handling, source boundaries, and result classification."""
import base64
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
spec = importlib.util.spec_from_file_location('chat_scan', ROOT / 'scripts/chat_scan.py')
worker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(worker)
GOOD = {'repository_url': 'https://github.com/example/skills'}
CLEAN = json.loads((ROOT / 'reports/teach-me-cloud-2026-11-21.json').read_text())

class ChatScanTests(unittest.TestCase):
    def test_accepts_root_url_and_normalizes_git_suffix(self):
        self.assertEqual(worker.validate_request({'repository_url': GOOD['repository_url'] + '.git/'})['repository'], 'example/skills')

    def test_rejects_external_or_credential_urls(self):
        for url in ('https://evil.test/a/b', 'https://github.com@evil.test/a/b', 'http://github.com/a/b', 'https://github.com/a/b?x=1', 'https://github.com/a/b/tree/main'):
            with self.subTest(url=url), self.assertRaises(ValueError):
                worker.validate_request({'repository_url': url})

    def test_rejects_unknown_parameters_and_unsafe_paths(self):
        with self.assertRaises(ValueError):
            worker.validate_request(dict(GOOD, command='anything'))
        for path in ('../escape', '/absolute', 'a/../../b', 'a\\b', 'a/.git/config', 'a//b'):
            with self.subTest(path=path), self.assertRaises(ValueError):
                worker.validate_request(dict(GOOD, skill_path=path))

    def test_request_ids_are_bounded_relative_files(self):
        self.assertEqual(worker.request_id('.scan-requests/test-12345.json'), 'test-12345')
        for path in ('../test-12345.json', '.scan-requests/short.json', '.scan-requests/a/b.json', '.scan-requests/UPPERCASE.json'):
            with self.subTest(path=path), self.assertRaises(ValueError):
                worker.request_id(path)

    def test_ambiguous_skills_need_selection(self):
        self.assertIsNone(worker.select_skill(None, ['a', 'b']))
        self.assertEqual(worker.select_skill(None, ['a']), 'a')
        with self.assertRaises(ValueError):
            worker.select_skill('missing', ['a'])
        with self.assertRaises(ValueError):
            worker.select_skill(None, [])

    def test_tree_truncation_is_an_error(self):
        def api(endpoint):
            return {'sha': 'a'*40, 'commit': {'tree': {'sha': 'b'*40}}} if '/commits/' in endpoint else {'truncated': True}
        with self.assertRaises(ValueError):
            worker.source_tree(worker.validate_request(GOOD), api)

    def test_materializes_verified_blob(self):
        data = b'# Teaching instructions\n'
        sha = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        entries = [{'path': 'skill/SKILL.md', 'type': 'blob', 'mode': '100644', 'size': len(data), 'sha': sha}]
        def api(endpoint):
            return {'encoding': 'base64', 'content': base64.b64encode(data).decode()}
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'candidate'
            manifest = worker.materialize('example/skills', entries, 'skill', target, api)
            self.assertEqual((target/'SKILL.md').read_bytes(), data)
            self.assertEqual(manifest[0]['sha256'], hashlib.sha256(data).hexdigest())

    def test_rejects_symlinks_submodules_and_large_files(self):
        for entry in ({'type': 'blob', 'mode': '120000', 'size': 5}, {'type': 'commit', 'mode': '160000'}, {'type': 'blob', 'mode': '100644', 'size': worker.MAX_BLOB+1}):
            with self.subTest(entry=entry), tempfile.TemporaryDirectory() as tmp, self.assertRaises(ValueError):
                worker.materialize('a/b', [dict(entry, path='skill/SKILL.md')], 'skill', Path(tmp)/'candidate', lambda _: self.fail('must not download'))

    def test_blob_mismatch_rejected(self):
        with tempfile.TemporaryDirectory() as tmp, self.assertRaises(ValueError):
            worker.materialize('a/b', [{'path': 'SKILL.md', 'type': 'blob', 'mode': '100644', 'size': 1, 'sha': 'a'*40}], '.', Path(tmp)/'candidate', lambda _: {'encoding': 'base64', 'content': 'Yg=='})

    def test_real_clean_report_classification(self):
        self.assertEqual(worker.classify(CLEAN, 0), 'no_findings')
        self.assertEqual(worker.classify(CLEAN, 1), 'needs_review')
        self.assertEqual(worker.classify(CLEAN, 2), 'scan_error')

    def test_findings_and_incomplete_are_distinct(self):
        report = copy.deepcopy(CLEAN)
        report['issues'] = [{'severity': 'MEDIUM'}]
        self.assertEqual(worker.classify(report, 1), 'needs_review')
        report['analysis_completeness']['is_complete'] = False
        self.assertEqual(worker.classify(report, 1), 'incomplete')
        report['execution_successful'] = False
        self.assertEqual(worker.classify(report, 1), 'scan_error')

    def test_invalid_request_produces_correlated_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            old = os.getcwd()
            try:
                os.chdir(tmp)
                Path('.scan-requests').mkdir()
                Path('.scan-requests/test-12345.json').write_text('{}')
                result = worker.run_request('.scan-requests/test-12345.json')
                self.assertEqual(result['state'], 'scan_error')
                self.assertEqual(result['request_id'], 'test-12345')
                self.assertTrue(Path('chat-results/test-12345/result.json').is_file())
            finally:
                os.chdir(old)

    def test_publish_rejects_wrong_request(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, GITHUB_REPOSITORY='a/b', GH_TOKEN='test-placeholder'):
            folder = Path(tmp)/'test-12345'
            folder.mkdir()
            (folder/'result.json').write_text('{"request_id":"another-id"}')
            with self.assertRaises(ValueError):
                worker.publish(folder, lambda *a, **k: self.fail('must not publish'))

    def test_pipeline_keeps_read_token_out_of_scanner(self):
        data = b'# Skill\n'
        sha = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        def api(endpoint):
            if '/commits/' in endpoint:
                return {'sha': 'a'*40, 'commit': {'tree': {'sha': 'b'*40}}}
            if '/git/trees/' in endpoint:
                return {'tree': [{'path': 'SKILL.md', 'type': 'blob', 'mode': '100644', 'size': len(data), 'sha': sha}]}
            if '/git/blobs/' in endpoint:
                return {'encoding': 'base64', 'content': base64.b64encode(data).decode()}
            return {'private': False}
        def scanner(args, **kwargs):
            self.assertNotIn('SOURCE_READ_TOKEN', kwargs['env'])
            self.assertNotIn('GH_TOKEN', kwargs['env'])
            Path(args[-1]).write_text(json.dumps(CLEAN))
            return subprocess.CompletedProcess(args, 0)
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, SOURCE_READ_TOKEN='read-placeholder', GH_TOKEN='write-placeholder'), patch.object(worker.subprocess, 'run', side_effect=scanner):
            old = os.getcwd()
            try:
                os.chdir(tmp)
                Path('.scan-requests').mkdir()
                Path('.scan-requests/test-12345.json').write_text(json.dumps(GOOD))
                result = worker.run_request('.scan-requests/test-12345.json', api=api)
                self.assertEqual(result['skillspector_state'], 'no_findings')
                self.assertEqual(result['state'], 'incomplete')
                self.assertEqual(result['malware']['status'], 'missing')
                self.assertEqual(result['deployment_eligibility'], 'blocked')
                self.assertEqual(result['source_commit'], 'a'*40)
            finally:
                os.chdir(old)

    def test_private_candidate_is_rejected_before_download(self):
        with tempfile.TemporaryDirectory() as tmp:
            old = os.getcwd()
            try:
                os.chdir(tmp)
                Path('.scan-requests').mkdir()
                Path('.scan-requests/test-12345.json').write_text(json.dumps(GOOD))
                result = worker.run_request('.scan-requests/test-12345.json', api=lambda _: {'private': True})
                self.assertEqual(result['state'], 'scan_error')
                self.assertIn('public candidate', result['error'])
            finally:
                os.chdir(old)

    def test_publish_report_before_completion_marker(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, GITHUB_REPOSITORY='a/b', GH_TOKEN='test-placeholder'):
            folder = Path(tmp)/'test-12345'
            folder.mkdir()
            (folder/'result.json').write_text('{"request_id":"test-12345"}')
            (folder/'report.json').write_text('{}')
            calls = []
            worker.publish(folder, lambda endpoint, **kwargs: calls.append((endpoint, kwargs)))
            self.assertTrue(calls[0][0].endswith('/report.json'))
            self.assertTrue(calls[1][0].endswith('/result.json'))
            self.assertNotIn('sha', calls[1][1]['data'])

if __name__ == '__main__':
    unittest.main()
