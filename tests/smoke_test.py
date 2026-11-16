"""End-to-end smoke test. Run from the repository root:

    python tests/smoke_test.py

1. Exercises the core workflow in-process (copy-on-create, approval gate, CSV).
2. Starts the real HTTP server on a free port in an isolated temp workspace and
   drives it through the JSON API exactly like the browser does.
3. If pdflatex is available, compiles the bundled CV and cover letter for real
   and walks them through compile -> approve -> Prepared -> Applied.
"""
import importlib.util
import json
import shutil
import sys
import tempfile
import threading
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

root = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('server', root / 'app' / 'server.py')
server = importlib.util.module_from_spec(spec)
spec.loader.exec_module(server)
cfgmod = server.cfgmod


def workspace(tmp, with_cover=False):
    work = Path(tmp)
    server.ROOT = work
    server.TEMPLATES = work / 'templates'
    server.APPLICATIONS = work / 'applications'
    server.PROMPTS = work / 'prompts'
    server.TRACKER = work / 'tracker' / 'applications.csv'
    (server.TEMPLATES / 'cv').mkdir(parents=True)
    for name in ('main.tex', 'cv-format.sty'):
        shutil.copy2(root / 'templates' / 'cv' / name, server.TEMPLATES / 'cv' / name)
    if with_cover:
        shutil.copytree(root / 'templates' / 'cover-letter', server.TEMPLATES / 'cover-letter')
        shutil.copy2(root / 'templates' / 'cv' / 'photo.jpg', server.TEMPLATES / 'cv' / 'photo.jpg')
    shutil.copytree(root / 'prompts', server.PROMPTS)
    cfg = cfgmod.load_config(work / 'missing.json')
    cfg['profile'].update(full_name='Smoke Tester', email='smoke@example.org', phone='+1 555 0100',
                          location='Testville, TS', linkedin='https://www.linkedin.com/in/smoke')
    cfgmod.save_config(cfg, work / 'config.json')
    cfgmod.CONFIG_FILE = work / 'config.json'
    server.CONFIG = cfg
    return work


def part1_core_workflow():
    with tempfile.TemporaryDirectory(prefix='jobapply-') as tmp:
        workspace(tmp)
        p = {'company': 'Test GmbH', 'job_title': 'Data Intern', 'job_description': 'Python SQL ETL',
             'include_cv': True, 'include_cover': False, 'role_type': 'Werkstudent'}
        entry = server.create_application(p)
        assert entry['status'] == 'Draft'
        tex = (server.APPLICATIONS / entry['id'] / 'cv' / 'main.tex').read_text(encoding='utf-8')
        assert r'\newcommand{\ApplicantName}{Smoke Tester}' in tex, 'profile not stamped into working copy'
        assert 'Sample Candidate' in (server.TEMPLATES / 'cv' / 'main.tex').read_text(encoding='utf-8'), 'master was modified'
        assert server.compile_pdf({'id': entry['id'], 'kind': 'cv'})['message'].startswith('Missing required image assets')
        assert server.TRACKER.exists()
        try:
            server.prepare({'id': entry['id']})
            raise AssertionError('Prepared without approval')
        except ValueError:
            pass
        assert not server.all_apps()[0]['applied_at']
        print('OK: copy-on-create, profile stamping, required-photo check, approval gate, CSV initialization')


class Client:
    def __init__(self, port):
        self.base = 'http://127.0.0.1:' + str(port)

    def call(self, path, data=None, raw=False):
        req = urllib.request.Request(self.base + path)
        if data is not None:
            req.data = json.dumps(data).encode('utf-8')
            req.add_header('Content-Type', 'application/json')
            req.add_header('X-Job-Apply-Token', server.CSRF_TOKEN)
            req.add_header('Origin', self.base)
        try:
            with urllib.request.urlopen(req, timeout=max(30, server.CONFIG['server']['compile_timeout'] + 10)) as r:
                body = r.read()
                return (r.status, body if raw else json.loads(body))
        except urllib.error.HTTPError as e:
            body = e.read()
            return (e.code, body if raw else json.loads(body))


def part2_http_and_compile():
    with tempfile.TemporaryDirectory(prefix='jobapply-http-') as tmp:
        workspace(tmp, with_cover=True)
        server.APPLICATIONS.mkdir()
        server.update_tracker()
        httpd = ThreadingHTTPServer(('127.0.0.1', 0), server.Handler)
        port = httpd.server_address[1]
        server.PORT = port
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        try:
            c = Client(port)
            status, page = c.call('/', raw=True)
            assert status == 200 and server.CSRF_TOKEN.encode() in page and b'page-profile' in page
            status, health = c.call('/api/health')
            assert status == 200 and health['ok'] and health['configured'] and health['cv_template'] and health['cover_template']
            assert c.call('/api/profile')[1]['item']['profile']['full_name'] == 'Smoke Tester'

            status, body = c.call('/api/create', {'job_description': 'x', 'include_cv': True, 'company': 'NoToken'})
            # Token sent -> ok. Now prove the CSRF gate rejects a request without the token.
            req = urllib.request.Request(c.base + '/api/create', data=b'{}', headers={'Content-Type': 'application/json'})
            try:
                urllib.request.urlopen(req)
                raise AssertionError('POST without token was accepted')
            except urllib.error.HTTPError as e:
                assert e.code == 403

            status, body = c.call('/api/create', {'job_description': 'Build XR experiences in Unity.', 'company': 'Smoke & Mirrors Ltd',
                                                  'job_title': 'XR Developer', 'include_cv': True, 'include_cover': True})
            assert status == 200 and body['ok'], body
            app = body['result']
            assert app['availability'] == '20 hours/week', 'defaults from config not applied'
            cover = c.call('/api/document?id=' + app['id'] + '&kind=cover-letter')[1]['tex']
            assert r'\newcommand{\TargetCompany}{Smoke \& Mirrors Ltd}' in cover
            assert 'No changes from the original master template.' == c.call('/api/diff?id=' + app['id'] + '&kind=cv')[1]['diff']
            prompt = c.call('/api/generate-prompt', {'id': app['id'], 'kind': 'cv'})[1]['result']['prompt']
            assert 'Smoke & Mirrors Ltd' in prompt and 'Smoke Tester' in prompt
            status, saved = c.call('/api/profile', {'profile': {'headline': 'Smoke Engineer'}})
            assert status == 200 and saved['result']['profile']['headline'] == 'Smoke Engineer'
            print('OK: HTTP server, CSRF gate, profile API, defaults, stamping, prompt generation')

            engine = cfgmod.find_pdflatex(server.CONFIG['server'].get('pdflatex', ''))
            if not engine:
                print('SKIP: pdflatex not found, real compilation not tested (' + cfgmod.latex_install_hint() + ')')
                return
            for kind in ('cv', 'cover-letter'):
                status, result = c.call('/api/compile', {'id': app['id'], 'kind': kind})
                result = result.get('result', result)
                assert result.get('ok'), kind + ' compile failed: ' + json.dumps(result, indent=1)
                status, pdf = c.call('/api/pdf?id=' + app['id'] + '&kind=' + kind, raw=True)
                assert status == 200 and pdf.startswith(b'%PDF'), kind + ' PDF not served'
                status, body = c.call('/api/approve', {'id': app['id'], 'kind': kind})
                assert body['result']['documents'][kind]['status'] == 'approved'
                status, dl = c.call('/api/download?id=' + app['id'] + '&kind=' + kind + '&format=pdf', raw=True)
                assert status == 200 and dl.startswith(b'%PDF')
            status, body = c.call('/api/prepare', {'id': app['id']})
            assert body['result']['status'] == 'Prepared'
            status, body = c.call('/api/apply', {'id': app['id']})
            assert body['result']['status'] == 'Applied'
            status, csv_bytes = c.call('/api/tracker.csv', raw=True)
            assert status == 200 and b'Applied' in csv_bytes and b'Smoke & Mirrors Ltd' in csv_bytes
            print('OK: real pdflatex compile of CV + cover letter, approve, Prepared, Applied, CSV export (' + engine + ')')
        finally:
            httpd.shutdown()
            httpd.server_close()


if __name__ == '__main__':
    part1_core_workflow()
    part2_http_and_compile()
    print('Smoke test passed.')
