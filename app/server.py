#!/usr/bin/env python3
"""Job Apply: local-only browser app. No OpenAI API key or cloud AI calls.

Launch: python3 app/server.py
Uses stdlib only; pdflatex must be installed to compile PDFs.
"""
import argparse
import base64
import csv
import difflib
import io
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import threading
import uuid
import webbrowser
import zipfile
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent.parent
PUBLIC = Path(__file__).resolve().parent / 'static'
TEMPLATES = ROOT / 'templates'
APPLICATIONS = ROOT / 'applications'
PROMPTS = ROOT / 'prompts'
TRACKER = ROOT / 'tracker' / 'applications.csv'
FIELDS = ['id','company','job_title','category','role_type','location','job_url','created_at',
          'prepared_at','applied_at','status','cv_status','cover_letter_status','cv_pdf','cover_letter_pdf','notes']
MAX_BODY = 25 * 1024 * 1024
PORT = 8765
CSRF_TOKEN = secrets.token_urlsafe(24)


def now():
    return datetime.now().astimezone().isoformat(timespec='seconds')


def slug(s):
    return (re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')[:45] or 'application')


def kind_dir(kind):
    if kind not in ('cv', 'cover-letter'):
        raise ValueError('Invalid document kind')
    return kind


def folder_for(app_id):
    if not re.fullmatch(r'\d{8}-[a-z0-9-]{1,60}-[a-f0-9]{8}', app_id):
        raise ValueError('Invalid application ID')
    path = APPLICATIONS / app_id
    if not path.is_dir():
        raise FileNotFoundError('Application not found')
    return path


def read_manifest(app_id):
    return json.loads((folder_for(app_id) / 'manifest.json').read_text(encoding='utf-8'))


def write_manifest(entry):
    path = folder_for(entry['id']) / 'manifest.json'
    path.write_text(json.dumps(entry, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    update_tracker()


def all_apps():
    out = []
    for file in sorted(APPLICATIONS.glob('*/manifest.json')):
        try:
            out.append(json.loads(file.read_text(encoding='utf-8')))
        except (OSError, ValueError):
            pass
    return sorted(out, key=lambda p: p.get('created_at',''), reverse=True)


def update_tracker():
    TRACKER.parent.mkdir(parents=True, exist_ok=True)
    with TRACKER.open('w', encoding='utf-8-sig', newline='') as f:
        wr = csv.DictWriter(f, fieldnames=FIELDS)
        wr.writeheader()
        for a in all_apps():
            row = {k: a.get(k,'') for k in FIELDS}
            row['cv_status'] = a.get('documents',{}).get('cv',{}).get('status','not_requested')
            row['cover_letter_status'] = a.get('documents',{}).get('cover-letter',{}).get('status','not_requested')
            # Paths are intentionally local; remote Google Sheets cannot open a localhost-only file.
            row['cv_pdf'] = str((folder_for(a['id'])/'cv'/'main.pdf').resolve()) if (folder_for(a['id'])/'cv'/'main.pdf').exists() else ''
            row['cover_letter_pdf'] = str((folder_for(a['id'])/'cover-letter'/'main.pdf').resolve()) if (folder_for(a['id'])/'cover-letter'/'main.pdf').exists() else ''
            wr.writerow(row)


def template_source(kind):
    """Find a master without renaming or modifying the user's template files."""
    origin = TEMPLATES / kind_dir(kind)
    names = ('main.tex', 'cover_letter_master.tex') if kind == 'cover-letter' else ('main.tex',)
    return next((origin / name for name in names if (origin / name).is_file()), None)


def copy_template(kind, target):
    source = template_source(kind)
    if source is None:
        return False
    origin = TEMPLATES / kind_dir(kind)
    shutil.copytree(origin, target, dirs_exist_ok=True, ignore=shutil.ignore_patterns('*.aux','*.log','*.pdf','*.out','*.synctex.gz','*.fls','*.fdb_latexmk'))
    if source.name != 'main.tex':
        shutil.copy2(source, target / 'main.tex')
    return True


def create_application(p):
    jd = str(p.get('job_description','')).strip()
    if not jd: raise ValueError('Paste a job description first')
    company = str(p.get('company','')).strip() or 'Company not specified'
    job_title = str(p.get('job_title','')).strip() or 'Position not specified'
    app_id = datetime.now().strftime('%Y%m%d') + '-' + slug(company) + '-' + uuid.uuid4().hex[:8]
    requested = {k: bool(p.get('include_cv' if k=='cv' else 'include_cover')) for k in ('cv','cover-letter')}
    if not any(requested.values()): raise ValueError('Select at least one document')
    loc = APPLICATIONS / app_id
    loc.mkdir(parents=True)
    documents = {}
    for kind in ('cv','cover-letter'):
        copied = copy_template(kind, loc / kind) if requested[kind] else False
        documents[kind] = {'requested': requested[kind], 'status': ('draft' if copied else 'missing_template') if requested[kind] else 'not_requested', 'approved_at': ''}
    entry = {'id':app_id,'created_at':now(),'company':company,'job_title':job_title,
             'category':str(p.get('category','other'))[:60], 'role_type':str(p.get('role_type',''))[:60],
             'availability':str(p.get('availability',''))[:140], 'start_date':str(p.get('start_date',''))[:80],
             'job_url':str(p.get('job_url',''))[:1500], 'location':str(p.get('location',''))[:160],
             'job_description':jd[:60000], 'notes':str(p.get('notes',''))[:3000],
             'documents':documents,'prepared_at':'','applied_at':'','status':'Draft'}
    write_manifest(entry)
    return entry


def save_source(p):
    entry = read_manifest(p['id'])
    kind = kind_dir(p['kind'])
    if not entry['documents'][kind]['requested']: raise ValueError('Document not requested for this application')
    raw = p.get('tex','')
    if not isinstance(raw,str) or not (20 < len(raw) < 250000): raise ValueError('Invalid LaTeX source')
    if '\\begin{document}' not in raw or '\\end{document}' not in raw:
        raise ValueError('Expected a complete main.tex document')
    doc = folder_for(entry['id']) / kind
    doc.mkdir(exist_ok=True)
    old = doc / 'main.tex'
    if old.exists() and old.read_text(encoding='utf-8') == raw:
        return entry
    old.write_text(raw, encoding='utf-8')
    for s in ('.pdf','.aux','.log','.out'):
        (doc/('main'+s)).unlink(missing_ok=True)
    entry['documents'][kind].update(status='draft',approved_at='')
    entry['prepared_at'] = '' if not entry['applied_at'] else entry['prepared_at']
    if not entry['applied_at']: entry['status'] = 'Draft'
    write_manifest(entry)
    return entry


def missing_image_assets(tex, folder):
    names = re.findall(r'\\includegraphics\s*(?:\[[^\]]*\])?\s*\{([^}]+)\}',tex)
    missing = []
    for name in names:
        if '\\' in name: continue  # TeX macro-expanded paths cannot be checked statically.
        file = folder / name
        if not file.exists() and not any((folder/(name+ext)).exists() for ext in ('.png','.jpg','.jpeg','.pdf')):
            missing.append(name)
    return missing


def compile_pdf(p):
    entry = read_manifest(p['id'])
    kind = kind_dir(p['kind'])
    doc = folder_for(entry['id'])/kind
    tex_file = doc/'main.tex'
    if not tex_file.exists(): raise ValueError('Missing '+kind+' LaTeX template. Upload it first.')
    tex = tex_file.read_text(encoding='utf-8')
    # Never serve a previous PDF or retain an old approval after a failed recompile.
    (doc/'main.pdf').unlink(missing_ok=True)
    entry['documents'][kind].update(status='draft',approved_at='')
    if not entry['applied_at']:
        entry['status'] = 'Draft'
        entry['prepared_at'] = ''
    write_manifest(entry)
    missing = missing_image_assets(tex,doc)
    if missing:
        return {'ok':False,'message':'Missing required image assets: '+', '.join(missing), 'missing_assets':missing}
    compiler = shutil.which('pdflatex')
    if not compiler:
        return {'ok':False,'message':'pdflatex is not installed. Install BasicTeX or MacTeX on your Mac.'}
    env = os.environ.copy()
    env['openout_any'] = 'p'
    try:
        result = subprocess.run([compiler,'-no-shell-escape','-interaction=nonstopmode','-halt-on-error','-file-line-error','main.tex'],
                                cwd=str(doc), text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                timeout=35, env=env)
    except subprocess.TimeoutExpired:
        return {'ok':False,'message':'LaTeX compilation exceeded 35 seconds'}
    except OSError as e:
        return {'ok':False,'message':str(e)}
    if result.returncode != 0 or not (doc/'main.pdf').exists():
        # Hide local environment paths where possible; include useful TeX diagnostics only.
        relevant = [line.strip() for line in result.stdout.splitlines() if line.startswith('!') or 'Error' in line or line.startswith('main.tex:') or 'not found' in line]
        return {'ok':False,'message':'LaTeX compilation failed','log':'\n'.join(relevant[-12:]) or '\n'.join(result.stdout.splitlines()[-15:])}
    entry['documents'][kind]['status'] = 'compiled'
    entry['documents'][kind]['approved_at'] = ''
    if not entry['applied_at']:
        entry['status'] = 'Draft'
        entry['prepared_at'] = ''
    write_manifest(entry)
    return {'ok':True,'pages':'PDF generated','url':'/api/pdf?id='+entry['id']+'&kind='+kind+'&v='+uuid.uuid4().hex[:8]}


def approve(p):
    entry = read_manifest(p['id'])
    kind = kind_dir(p['kind'])
    doc = folder_for(entry['id'])/kind
    if not (doc/'main.pdf').exists() or entry['documents'][kind]['status'] not in ('compiled','approved'):
        raise ValueError('Compile this document successfully before approving')
    entry['documents'][kind].update(status='approved',approved_at=now())
    write_manifest(entry)
    return entry


def prepare(p):
    entry = read_manifest(p['id'])
    checks = [(k,d) for k,d in entry['documents'].items() if d['requested']]
    if not checks or any(d['status'] != 'approved' or not (folder_for(entry['id'])/k/'main.pdf').exists() for k,d in checks):
        raise ValueError('Compile and approve every requested document before marking Prepared')
    if not entry['prepared_at']: entry['prepared_at'] = now()
    entry['status'] = 'Applied' if entry['applied_at'] else 'Prepared'
    write_manifest(entry)
    return entry


def apply(p):
    entry = read_manifest(p['id'])
    if not entry['prepared_at']: raise ValueError('Mark this application Prepared first')
    if not entry['applied_at']: entry['applied_at'] = now()
    entry['status'] = 'Applied'
    write_manifest(entry)
    return entry


def update_metadata(p):
    entry = read_manifest(p['id'])
    for k,n in [('company',120),('job_title',140),('category',80),('role_type',80),('location',140),('job_url',1500),('notes',3000)]:
        if k in p: entry[k] = str(p[k])[:n]
    write_manifest(entry)
    return entry


def create_prompt(p):
    entry = read_manifest(p['id'])
    kind = kind_dir(p['kind'])
    doc = folder_for(entry['id'])/kind
    tex = (doc/'main.tex').read_text(encoding='utf-8') if (doc/'main.tex').exists() else ''
    policy = (PROMPTS / ('cv-prompt.md' if kind=='cv' else 'cover-letter-prompt.md')).read_text(encoding='utf-8')
    preamble = '''JOB APPLY HANDOFF — DOCUMENT CONTENT ONLY\nYou are editing an existing LaTeX document for a specific vacancy. Preserve template commands and facts.\nThis prompt is being copied manually from a local browser app; you cannot access or write to the local app directly.\nIf the supplied policy asks for missing information, ask before making those changes.\nReturn a complete main.tex source block. This is a draft; the user will review and compile it locally.\n\n'''
    return {'prompt':preamble+'INSTRUCTIONS:\n'+policy+'\n\nJOB DETAILS:\nCompany: '+entry['company']+'\nJob title: '+entry['job_title']+'\nRole type: '+entry['role_type']+'\nWeekly availability: '+entry['availability']+'\nStart date: '+entry['start_date']+'\nURL: '+entry['job_url']+'\n\nJOB DESCRIPTION:\n'+entry['job_description']+'\n\nCURRENT main.tex:\n```latex\n'+tex+'\n```'}


def safe_relative(path):
    p = Path(path.replace('\\','/'))
    if p.is_absolute() or any(x in ('..','') for x in p.parts) or len(p.parts)>6: raise ValueError('Unsafe filename')
    return p


def import_templates(p):
    kind = kind_dir(p['kind'])
    filename = str(p.get('filename',''))
    data64 = str(p.get('data',''))
    if len(data64)>MAX_BODY: raise ValueError('Upload too large')
    content = base64.b64decode(data64, validate=True)
    if len(content)>12*1024*1024: raise ValueError('Upload must be smaller than 12 MB')
    origin = TEMPLATES/kind
    origin.mkdir(parents=True, exist_ok=True)
    if filename.lower().endswith('.zip'):
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            files = [e for e in zf.infolist() if not e.is_dir() and not e.filename.startswith('__MACOSX/')]
            if len(files)>80 or sum(e.file_size for e in files)>45*1024*1024: raise ValueError('ZIP contains too many or oversized files')
            for item in files:
                sub = safe_relative(item.filename)
                if item.external_attr >> 16 & 0o170000 == 0o120000:
                    raise ValueError('Symbolic links are not supported')
                destination = origin / sub
                destination.parent.mkdir(parents=True,exist_ok=True)
                destination.write_bytes(zf.read(item))
            # Overleaf often exports nested folders. Prefer root/main.tex and keep asset paths.
            if not (origin/'main.tex').exists():
                candidates = list(origin.rglob('main.tex'))
                if len(candidates)==1:
                    src = candidates[0]
                    nested_dir = src.parent
                    for f in nested_dir.iterdir():
                        if f.is_file(): shutil.copy2(f, origin/f.name)
    else:
        sub = safe_relative(filename)
        dest = origin / sub
        dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_bytes(content)
    return {'ok':True,'files':[str(x.relative_to(origin)) for x in origin.rglob('*') if x.is_file()][:100],
            'ready':template_source(kind) is not None}


class Handler(BaseHTTPRequestHandler):
    server_version = 'JobApply/0.1'

    def log_message(self, fmt, *args):
        if not self.path.startswith('/api/'):
            super().log_message(fmt,*args)

    def send_headers(self, code,ctype='application/json; charset=utf-8',length=None,attachment=None):
        self.send_response(code)
        self.send_header('Content-Type',ctype)
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('X-Frame-Options','SAMEORIGIN')
        self.send_header('Referrer-Policy','no-referrer')
        self.send_header('Content-Security-Policy',"default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self' data:; frame-src 'self'; connect-src 'self'; object-src 'none'")
        if attachment:
            self.send_header('Content-Disposition','attachment; filename="'+attachment.replace('"','')+'"')
        if length is not None: self.send_header('Content-Length',str(length))
        self.end_headers()

    def raw(self, data, ctype, filename=None):
        self.send_headers(200,ctype,len(data),filename)
        self.wfile.write(data)

    def json(self, obj, code=200):
        data = json.dumps(obj, ensure_ascii=False).encode('utf-8')
        self.send_headers(code,length=len(data))
        self.wfile.write(data)

    def error(self, msg, code=400):
        self.json({'ok':False,'message':str(msg)},code)

    def _get_query(self): return parse_qs(urlparse(self.path).query)

    def _single(self,q,key,default=''):
        return q.get(key,[default])[0]

    def do_GET(self):
        try:
            path = urlparse(self.path).path
            q = self._get_query()
            if path in ('/','/index.html'):
                content = (PUBLIC/'index.html').read_bytes()
                content = content.replace(b'{{CSRF_TOKEN}}',CSRF_TOKEN.encode('ascii'))
                return self.raw(content,'text/html; charset=utf-8')
            if path in ('/app.js','/style.css'):
                typ = 'application/javascript; charset=utf-8' if path.endswith('.js') else 'text/css; charset=utf-8'
                return self.raw((PUBLIC/path[1:]).read_bytes(),typ)
            if path == '/api/health':
                return self.json({'ok':True,'engine':'pdflatex' if shutil.which('pdflatex') else 'missing',
                                  'cv_template':(TEMPLATES/'cv'/'main.tex').exists(),
                                  'cv_missing_assets':missing_image_assets((TEMPLATES/'cv'/'main.tex').read_text(encoding='utf-8'),TEMPLATES/'cv') if (TEMPLATES/'cv'/'main.tex').exists() else [],
                                  'cover_template':template_source('cover-letter') is not None,
                                  'google_sheets':'not_connected', 'ai':'manual_chatgpt_handoff'})
            if path == '/api/applications': return self.json({'ok':True,'items':all_apps()})
            if path == '/api/application': return self.json({'ok':True,'item':read_manifest(self._single(q,'id'))})
            if path == '/api/document':
                kind = kind_dir(self._single(q,'kind'))
                file = folder_for(self._single(q,'id'))/kind/'main.tex'
                return self.json({'ok':True,'tex':file.read_text(encoding='utf-8') if file.exists() else ''})
            if path == '/api/diff':
                kind = kind_dir(self._single(q,'kind'))
                app_id = self._single(q,'id')
                old = template_source(kind)
                new = folder_for(app_id)/kind/'main.tex'
                if old is None or not new.is_file(): raise FileNotFoundError('Original and edited LaTeX must both exist')
                diff = difflib.unified_diff(old.read_text(encoding='utf-8').splitlines(), new.read_text(encoding='utf-8').splitlines(),
                                           fromfile='Original master template',tofile='This application',lineterm='')
                return self.json({'ok':True,'diff':'\n'.join(diff) or 'No changes from the original master template.'})
            if path == '/api/prompt-settings':
                kind = kind_dir(self._single(q,'kind'))
                file = PROMPTS/('cv-prompt.md' if kind=='cv' else 'cover-letter-prompt.md')
                return self.json({'ok':True,'prompt':file.read_text(encoding='utf-8')})
            if path == '/api/pdf' or path == '/api/download':
                kind = kind_dir(self._single(q,'kind'))
                typ = self._single(q,'format','pdf') if path=='/api/download' else 'pdf'
                if typ not in ('pdf','tex'): raise ValueError('Invalid download type')
                target = folder_for(self._single(q,'id'))/kind/('main.'+typ)
                if not target.exists(): raise FileNotFoundError('This document has not been generated')
                return self.raw(target.read_bytes(), 'application/pdf' if typ=='pdf' else 'text/plain; charset=utf-8',
                                ('CV' if kind=='cv' else 'Cover_Letter')+'.'+typ if path=='/api/download' else None)
            if path == '/api/tracker.csv':
                update_tracker()
                return self.raw(TRACKER.read_bytes(),'text/csv; charset=utf-8','job_applications.csv')
            self.error('Not found',404)
        except FileNotFoundError as e: self.error(e,404)
        except (ValueError,KeyError,UnicodeError) as e: self.error(e)
        except BrokenPipeError: pass
        except Exception as e: self.error('Server error: '+str(e),500)

    def do_POST(self):
        try:
            if self.headers.get('X-Job-Apply-Token') != CSRF_TOKEN:
                return self.error('Invalid request token',403)
            origin = self.headers.get('Origin','')
            if origin and origin not in ('http://127.0.0.1:'+str(PORT),'http://localhost:'+str(PORT)):
                return self.error('Cross-origin writes are not allowed',403)
            size = int(self.headers.get('Content-Length','0'))
            if size<0 or size>MAX_BODY: return self.error('Request too large',413)
            p = json.loads(self.rfile.read(size) or b'{}')
            path = urlparse(self.path).path
            routes = {'/api/create':create_application,'/api/save-document':save_source,'/api/compile':compile_pdf,
                      '/api/approve':approve,'/api/prepare':prepare,'/api/apply':apply,
                      '/api/edit':update_metadata,'/api/generate-prompt':create_prompt,'/api/upload-template':import_templates}
            if path == '/api/save-prompt':
                kind = kind_dir(p['kind'])
                prompt = p.get('prompt','')
                if not isinstance(prompt,str) or len(prompt)>60000: raise ValueError('Prompt too long')
                (PROMPTS/('cv-prompt.md' if kind=='cv' else 'cover-letter-prompt.md')).write_text(prompt, encoding='utf-8')
                return self.json({'ok':True})
            if path not in routes: return self.error('Not found',404)
            return self.json({'ok':True,'result':routes[path](p)})
        except FileNotFoundError as e: self.error(e,404)
        except (ValueError,KeyError,UnicodeError,json.JSONDecodeError,zipfile.BadZipFile) as e: self.error(e)
        except Exception as e: self.error('Server error: '+str(e),500)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--no-browser',action='store_true')
    parser.add_argument('--port',type=int,default=8765)
    args = parser.parse_args()
    global PORT
    PORT = args.port
    APPLICATIONS.mkdir(parents=True,exist_ok=True)
    TRACKER.parent.mkdir(parents=True,exist_ok=True)
    update_tracker()
    server = ThreadingHTTPServer(('127.0.0.1',PORT),Handler)
    url = 'http://127.0.0.1:'+str(PORT)
    print('Job Apply is running locally at '+url+' (Ctrl+C to stop)',flush=True)
    if not args.no_browser:
        threading.Timer(0.6,lambda:webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('Shutting down.')
    finally: server.server_close()

if __name__=='__main__':main()
