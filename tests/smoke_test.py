"""Run from repository root: python3 tests/smoke_test.py"""
import importlib.util
import json
import shutil
import tempfile
from pathlib import Path

root = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('server', root/'app'/'server.py')
server = importlib.util.module_from_spec(spec)
spec.loader.exec_module(server)

with tempfile.TemporaryDirectory(prefix='jobapply-') as tmp:
    work = Path(tmp)
    server.ROOT = work
    server.TEMPLATES = work/'templates'
    server.APPLICATIONS = work/'applications'
    server.PROMPTS = work/'prompts'
    server.TRACKER = work/'tracker'/'applications.csv'
    (server.TEMPLATES/'cv').mkdir(parents=True)
    shutil.copy2(root/'templates'/'cv'/'main.tex',server.TEMPLATES/'cv'/'main.tex')
    shutil.copy2(root/'templates'/'cv'/'cv-format.sty',server.TEMPLATES/'cv'/'cv-format.sty')
    p={'company':'Test GmbH','job_title':'Data Intern','job_description':'Python SQL ETL',
       'include_cv':True,'include_cover':False,'role_type':'Werkstudent'}
    entry = server.create_application(p)
    assert entry['status'] == 'Draft'
    assert (server.APPLICATIONS/entry['id']/'cv'/'main.tex').exists()
    assert server.compile_pdf({'id':entry['id'],'kind':'cv'})['message'].startswith('Missing required image assets')
    assert server.TRACKER.exists()
    try:
        server.prepare({'id':entry['id']})
        raise AssertionError('Prepared without approval')
    except ValueError:
        pass
    assert not server.all_apps()[0]['applied_at']
    print('OK: copy-on-create, required-photo check, approval gate, CSV initialization')
print('Smoke test passed.')
