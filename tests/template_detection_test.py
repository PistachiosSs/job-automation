"""Run from the project root: python3 tests/template_detection_test.py."""
import base64
import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('server', ROOT / 'app' / 'server.py')
server = importlib.util.module_from_spec(spec)
spec.loader.exec_module(server)
SAMPLE = '\\documentclass{article}\n\\begin{document}\nSample cover letter\n\\end{document}\n'


class TemplateDetectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='jobapply-templates-')
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.patch = patch.multiple(
            server, TEMPLATES=self.work / 'templates',
            APPLICATIONS=self.work / 'applications',
            TRACKER=self.work / 'tracker' / 'applications.csv',
            PROMPTS=self.work / 'prompts')
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.cover = server.TEMPLATES / 'cover-letter'
        self.cover.mkdir(parents=True)
        server.PROMPTS.mkdir()
        (server.PROMPTS / 'cover-letter-prompt.md').write_text('Preserve the template.')

    def get(self, path):
        handler = server.Handler.__new__(server.Handler)
        handler.path = path
        responses = []
        handler.json = lambda obj, code=200: responses.append((code, obj))
        handler.error = lambda message, code=400: responses.append((code, {'message': str(message)}))
        handler.do_GET()
        return responses[0]

    def create(self):
        return server.create_application({
            'company': 'Test', 'job_title': 'Developer',
            'job_description': '3D graphics', 'include_cover': True})

    def test_sample_detected_and_copied_with_assets_without_changing_master(self):
        master = self.cover / 'cover_letter_master.tex'
        master.write_text(SAMPLE)
        (self.cover / 'assets').mkdir()
        (self.cover / 'assets' / 'signature.png').write_bytes(b'test asset')
        self.assertTrue(self.get('/api/health')[1]['cover_template'])
        entry = self.create()
        self.assertEqual(entry['documents']['cover-letter']['status'], 'draft')
        document = server.APPLICATIONS / entry['id'] / 'cover-letter' / 'main.tex'
        self.assertEqual(document.read_text(), SAMPLE)
        self.assertEqual((document.parent / 'assets' / 'signature.png').read_bytes(), b'test asset')
        self.assertIn(SAMPLE, server.create_prompt({'id': entry['id'], 'kind': 'cover-letter'})['prompt'])
        query = '?id=' + entry['id'] + '&kind=cover-letter'
        self.assertEqual(self.get('/api/document' + query)[1]['tex'], SAMPLE)
        self.assertEqual(self.get('/api/diff' + query)[1]['diff'], 'No changes from the original master template.')
        server.save_source({'id': entry['id'], 'kind': 'cover-letter', 'tex': SAMPLE.replace('Sample', 'Tailored')})
        code, result = self.get('/api/diff' + query)
        self.assertEqual(code, 200)
        self.assertIn('+Tailored cover letter', result['diff'])
        self.assertEqual(master.read_text(), SAMPLE)
        self.assertFalse((self.cover / 'main.tex').exists())

    def test_main_tex_takes_precedence(self):
        (self.cover / 'cover_letter_master.tex').write_text(SAMPLE)
        preferred = SAMPLE.replace('Sample', 'Preferred')
        (self.cover / 'main.tex').write_text(preferred)
        entry = self.create()
        working = server.APPLICATIONS / entry['id'] / 'cover-letter' / 'main.tex'
        self.assertEqual(working.read_text(), preferred)
        query = '?id=' + entry['id'] + '&kind=cover-letter'
        self.assertEqual(self.get('/api/diff' + query)[1]['diff'], 'No changes from the original master template.')

    def test_missing_template_is_not_reported_ready(self):
        (self.cover / 'README.md').write_text('Instructions only')
        self.assertFalse(self.get('/api/health')[1]['cover_template'])
        entry = self.create()
        self.assertEqual(entry['documents']['cover-letter']['status'], 'missing_template')
        query = '?id=' + entry['id'] + '&kind=cover-letter'
        self.assertEqual(self.get('/api/diff' + query)[0], 404)

    def test_readiness_updates_when_sample_added_or_removed(self):
        self.assertFalse(self.get('/api/health')[1]['cover_template'])
        master = self.cover / 'cover_letter_master.tex'
        master.write_text(SAMPLE)
        self.assertTrue(self.get('/api/health')[1]['cover_template'])
        master.unlink()
        self.assertFalse(self.get('/api/health')[1]['cover_template'])

    def test_upload_sample_reports_ready(self):
        result = server.import_templates({
            'kind': 'cover-letter', 'filename': 'cover_letter_master.tex',
            'data': base64.b64encode(SAMPLE.encode()).decode()})
        self.assertTrue(result['ready'])
        self.assertTrue(self.get('/api/health')[1]['cover_template'])

    def test_master_changes_only_affect_new_applications(self):
        master = self.cover / 'cover_letter_master.tex'
        master.write_text(SAMPLE)
        old = self.create()
        updated = SAMPLE.replace('Sample', 'Updated')
        master.write_text(updated)
        new = self.create()
        for entry, expected in [(old, SAMPLE), (new, updated)]:
            self.assertEqual((server.APPLICATIONS / entry['id'] / 'cover-letter' / 'main.tex').read_text(), expected)

    def test_cover_alias_does_not_change_cv_detection(self):
        cv = server.TEMPLATES / 'cv'
        cv.mkdir()
        (cv / 'cover_letter_master.tex').write_text(SAMPLE)
        self.assertIsNone(server.template_source('cv'))
        (cv / 'main.tex').write_text(SAMPLE)
        self.assertEqual(server.template_source('cv'), cv / 'main.tex')
        with self.assertRaises(ValueError):
            server.template_source('../cover-letter')


if __name__ == '__main__':
    unittest.main()
