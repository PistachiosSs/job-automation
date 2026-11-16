"""Unit tests for config.py and the profile integration in server.py.

Run from the project root:
    python -m unittest discover -s tests -p "*_test.py" -v
"""
import importlib.util
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


server = load('server', ROOT / 'app' / 'server.py')
setup = load('setup', ROOT / 'setup.py')
cfgmod = server.cfgmod  # the one module object shared by server.py and setup.py
assert setup.cfgmod is cfgmod

PROFILE = {'full_name': 'Ada & Co_Lovelace', 'headline': '100% Engineer', 'email': 'ada@example.org',
           'phone': '+44 1', 'location': 'London, UK', 'linkedin': 'https://www.linkedin.com/in/ada_l',
           'github': '', 'portfolio': 'https://ada.example/{x}', 'photo': '', 'target_field': 'Data Science'}


class LatexEscapeTests(unittest.TestCase):
    def test_special_characters_are_escaped(self):
        self.assertEqual(cfgmod.latex_escape('A & B 100% #1 _ {x} ~ ^'),
                         r'A \& B 100\% \#1 \_ \{x\} \textasciitilde{} \textasciicircum{}')

    def test_backslash_is_escaped_first(self):
        self.assertEqual(cfgmod.latex_escape(r'a\b'), r'a\textbackslash{}b')

    def test_url_only_strips_breaking_characters(self):
        self.assertEqual(cfgmod.latex_url('https://x.y/a_b?c=1&d=2 {z}\\'), 'https://x.y/a_b?c=1&d=2z')


class ConfigFileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='jobapply-config-')
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'config.json'

    def test_missing_file_gives_defaults(self):
        cfg = cfgmod.load_config(self.path)
        self.assertEqual(cfg, cfgmod.DEFAULT_CONFIG)
        self.assertFalse(cfgmod.is_configured(cfg))

    def test_broken_file_gives_defaults(self):
        self.path.write_text('{not json', encoding='utf-8')
        self.assertEqual(cfgmod.load_config(self.path)['server']['port'], 8765)

    def test_partial_file_is_merged_and_unknown_keys_dropped(self):
        self.path.write_text(json.dumps({'profile': {'full_name': 'X', 'bogus': 1}, 'server': {'port': '9000'}}), encoding='utf-8')
        cfg = cfgmod.load_config(self.path)
        self.assertEqual(cfg['profile']['full_name'], 'X')
        self.assertEqual(cfg['profile']['email'], 'sample@example.com')
        self.assertNotIn('bogus', cfg['profile'])
        self.assertEqual(cfg['server']['port'], 9000)

    def test_save_roundtrip_and_validation(self):
        cfg = cfgmod.load_config(self.path)
        cfg['profile'].update(PROFILE)
        cfg['server']['port'] = '8800'
        saved = cfgmod.save_config(cfg, self.path)
        self.assertEqual(saved['server']['port'], 8800)
        self.assertEqual(cfgmod.load_config(self.path)['profile']['full_name'], 'Ada & Co_Lovelace')
        self.assertTrue(cfgmod.is_configured(saved))
        cfg['server']['port'] = 80
        with self.assertRaises(ValueError):
            cfgmod.save_config(cfg, self.path)
        cfg['server']['port'] = 'abc'
        with self.assertRaises(ValueError):
            cfgmod.save_config(cfg, self.path)

    def test_example_config_is_valid(self):
        cfg = cfgmod.load_config(ROOT / 'config.example.json')
        self.assertEqual(set(cfg), {'profile', 'defaults', 'server'})
        self.assertFalse(cfgmod.is_configured(cfg), 'example must stay a placeholder')


class StampingTests(unittest.TestCase):
    def test_personal_macros_are_filled_and_escaped(self):
        tex = ROOT.joinpath('templates', 'cv', 'main.tex').read_text(encoding='utf-8')
        out = cfgmod.stamp_personal_fields(tex, PROFILE)
        self.assertIn(r'\newcommand{\ApplicantName}{Ada \& Co\_Lovelace}', out)
        self.assertIn(r'\newcommand{\ApplicantHeadline}{100\% Engineer}', out)
        self.assertIn(r'\newcommand{\ApplicantLinkedIn}{https://www.linkedin.com/in/ada_l}', out)
        self.assertIn(r'\newcommand{\ApplicantPortfolio}{https://ada.example/x}', out)
        self.assertIn(r'\newcommand{\ApplicantGitHub}{}', out, 'empty values keep the template default')
        self.assertNotIn('Sample Candidate', out.split(r'\begin{document}')[1])

    def test_only_macro_lines_change(self):
        tex = 'A\n\\newcommand{\\ApplicantName}{Old}\nB \\ApplicantName\n'
        self.assertEqual(cfgmod.stamp_personal_fields(tex, {'full_name': 'New'}),
                         'A\n\\newcommand{\\ApplicantName}{New}\nB \\ApplicantName\n')
        self.assertEqual(cfgmod.stamp_personal_fields('no macros', PROFILE), 'no macros')

    def test_cover_letter_job_fields(self):
        tex = ROOT.joinpath('templates', 'cover-letter', 'cover_letter_master.tex').read_text(encoding='utf-8')
        out = cfgmod.stamp_job_fields(tex, {'company': 'Rocket & Sons', 'job_title': 'XR Dev', 'availability': '20 hours/week', 'start_date': 'immediately'})
        self.assertIn(r'\newcommand{\TargetCompany}{Rocket \& Sons}', out)
        self.assertIn(r'\newcommand{\TargetPosition}{XR Dev}', out)
        self.assertIn(r'\newcommand{\AvailabilitySentence}{I am available to start immediately and can work 20 hours/week.}', out)
        untouched = cfgmod.stamp_job_fields(tex, {'company': 'Company not specified', 'job_title': ''})
        self.assertIn(r'\newcommand{\TargetCompany}{[COMPANY NAME]}', untouched)

    def test_availability_sentence_variants(self):
        self.assertEqual(cfgmod.availability_sentence('', ''), '')
        self.assertEqual(cfgmod.availability_sentence('10 h/week', ''), 'I can work 10 h/week.')
        self.assertEqual(cfgmod.availability_sentence('', 'May'), 'I am available to start May.')


class PdflatexDiscoveryTests(unittest.TestCase):
    def test_explicit_path_wins(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake = Path(tmp) / 'pdflatex.exe'
            fake.write_bytes(b'')
            self.assertEqual(cfgmod.find_pdflatex(str(fake)), str(fake))

    def test_missing_everywhere_returns_none(self):
        with patch.object(cfgmod.shutil, 'which', return_value=None), \
                patch.object(cfgmod.os.path, 'isfile', return_value=False), \
                patch.object(cfgmod.glob, 'glob', return_value=[]):
            self.assertIsNone(cfgmod.find_pdflatex(''))
        self.assertIn('pdflatex', cfgmod.latex_install_hint())


class ServerIntegrationTests(unittest.TestCase):
    """create_application stamps the working copy; /api/profile reads and writes config."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='jobapply-server-')
        self.addCleanup(self.temp.cleanup)
        work = Path(self.temp.name)
        shutil.copytree(ROOT / 'templates', work / 'templates')
        (work / 'prompts').mkdir()
        (work / 'prompts' / 'cv-prompt.md').write_text('Act as an expert in [Data Science].', encoding='utf-8')
        self.config_file = work / 'config.json'
        photo = work / 'me.jpg'
        photo.write_bytes(b'\xff\xd8myphoto')
        cfg = cfgmod.load_config(self.config_file)
        cfg['profile'].update(PROFILE, photo=str(photo))
        cfg['defaults'].update(availability='8 hours/week', start_date='1 March', category='3D Artist', role_type='Praktikum')
        cfgmod.save_config(cfg, self.config_file)
        self.patches = [
            patch.multiple(server, ROOT=work, TEMPLATES=work / 'templates', APPLICATIONS=work / 'applications',
                           TRACKER=work / 'tracker' / 'applications.csv', PROMPTS=work / 'prompts', CONFIG=cfg),
            patch.object(cfgmod, 'CONFIG_FILE', self.config_file),
        ]
        for p in self.patches:
            p.start()
            self.addCleanup(p.stop)

    def get(self, path):
        handler = server.Handler.__new__(server.Handler)
        handler.path = path
        out = []
        handler.json = lambda obj, code=200: out.append((code, obj))
        handler.error = lambda message, code=400: out.append((code, {'message': str(message)}))
        handler.do_GET()
        return out[0]

    def test_working_copies_are_personalised_but_masters_untouched(self):
        entry = server.create_application({'job_description': 'Blender and Unity', 'company': 'Rocket & Sons',
                                           'job_title': 'XR Dev', 'include_cv': True, 'include_cover': True})
        app_dir = server.APPLICATIONS / entry['id']
        cv = (app_dir / 'cv' / 'main.tex').read_text(encoding='utf-8')
        cover = (app_dir / 'cover-letter' / 'main.tex').read_text(encoding='utf-8')
        self.assertIn(r'\newcommand{\ApplicantName}{Ada \& Co\_Lovelace}', cv)
        self.assertIn(r'\newcommand{\ApplicantEmail}{ada@example.org}', cover)
        self.assertIn(r'\newcommand{\TargetCompany}{Rocket \& Sons}', cover)
        self.assertIn('I am available to start 1 March and can work 8 hours/week.', cover)
        self.assertEqual((app_dir / 'cv' / 'photo.jpg').read_bytes(), b'\xff\xd8myphoto')
        self.assertEqual(entry['availability'], '8 hours/week')
        self.assertEqual(entry['category'], '3D Artist')
        master = (server.TEMPLATES / 'cv' / 'main.tex').read_text(encoding='utf-8')
        self.assertIn('Sample Candidate', master)
        self.assertNotEqual((server.TEMPLATES / 'cv' / 'photo.jpg').read_bytes(), b'\xff\xd8myphoto')
        self.assertEqual(self.get('/api/diff?id=' + entry['id'] + '&kind=cv')[1]['diff'],
                         'No changes from the original master template.', 'profile stamping is not a user change')
        prompt = server.create_prompt({'id': entry['id'], 'kind': 'cv'})['prompt']
        self.assertIn('[Data Science]', prompt)
        self.assertIn('Ada', prompt)

    def test_explicit_form_values_override_defaults(self):
        entry = server.create_application({'job_description': 'x', 'include_cv': True, 'availability': '30 hours/week', 'role_type': 'Thesis'})
        self.assertEqual(entry['availability'], '30 hours/week')
        self.assertEqual(entry['role_type'], 'Thesis')
        self.assertEqual(entry['start_date'], '1 March')

    def test_profile_endpoints(self):
        code, body = self.get('/api/profile')
        self.assertEqual(code, 200)
        self.assertTrue(body['item']['configured'])
        self.assertEqual(body['item']['profile']['email'], 'ada@example.org')
        result = server.save_profile({'profile': {'full_name': 'Grace Hopper', 'ignored': 'x'}, 'server': {'port': 8801, 'open_browser': False}})
        self.assertEqual(result['profile']['full_name'], 'Grace Hopper')
        self.assertEqual(result['profile']['email'], 'ada@example.org', 'unspecified keys are kept')
        self.assertEqual(result['server']['port'], 8801)
        self.assertFalse(result['server']['open_browser'])
        self.assertEqual(json.loads(self.config_file.read_text(encoding='utf-8'))['profile']['full_name'], 'Grace Hopper')
        self.assertEqual(server.CONFIG['profile']['full_name'], 'Grace Hopper')
        with self.assertRaises(ValueError):
            server.save_profile({'server': {'port': 1}})

    def test_health_reports_setup_state(self):
        code, body = self.get('/api/health')
        self.assertEqual(code, 200)
        self.assertTrue(body['configured'])
        self.assertEqual(body['profile_name'], PROFILE['full_name'])
        self.assertIn(body['engine'], ('pdflatex', 'missing'))
        self.assertEqual(body['cv_missing_assets'], [])

    def test_compile_without_pdflatex_gives_install_hint(self):
        entry = server.create_application({'job_description': 'x', 'include_cv': True})
        with patch.object(server, 'pdflatex_path', return_value=None):
            result = server.compile_pdf({'id': entry['id'], 'kind': 'cv'})
        self.assertFalse(result['ok'])
        self.assertIn('pdflatex is not installed', result['message'])


class SetupScriptTests(unittest.TestCase):
    def test_non_interactive_setup_writes_config_from_example(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'config.json'
            with patch.object(cfgmod, 'CONFIG_FILE', target), patch('builtins.print'):
                self.assertEqual(setup.main(['--yes']), 0)
            self.assertTrue(target.is_file())
            self.assertEqual(cfgmod.load_config(target)['defaults']['role_type'], 'Werkstudent')

    def test_check_only_does_not_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'config.json'
            with patch.object(cfgmod, 'CONFIG_FILE', target), patch('builtins.print'):
                setup.main(['--check'])
            self.assertFalse(target.exists())

    def test_wizard_accepts_defaults_and_clears_with_dash(self):
        cfg = cfgmod.load_config(Path(os.devnull))
        answers = iter(['Grace Hopper'] + [''] * (len(cfgmod.PROFILE_FIELDS) - 1) + ['-'] + [''] * (len(cfgmod.DEFAULT_FIELDS) - 1) + ['8899'])
        with patch('builtins.input', lambda _prompt: next(answers)), patch('builtins.print'):
            out = setup.wizard(cfg)
        self.assertEqual(out['profile']['full_name'], 'Grace Hopper')
        self.assertEqual(out['profile']['email'], 'sample@example.com')
        self.assertEqual(out['defaults']['role_type'], '')
        self.assertEqual(out['server']['port'], '8899')


if __name__ == '__main__':
    unittest.main()
