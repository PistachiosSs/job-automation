"""Job Apply configuration: a single config.json holds everything personal.

The master templates in templates/ stay public-safe placeholders. Personal
details live in config.json (git-ignored) and are stamped into the *working
copy* of each application when it is created, never into the masters.

Usage:
    from config import load_config, save_config, stamp_personal_fields
"""
import glob
import json
import os
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_FILE = ROOT / 'config.json'
EXAMPLE_FILE = ROOT / 'config.example.json'

DEFAULT_CONFIG = {
    'profile': {
        'full_name': 'Sample Candidate',
        'headline': "Master's Student in Informatics",
        'email': 'sample@example.com',
        'phone': '',
        'location': 'City, Country',
        'linkedin': '',
        'github': '',
        'portfolio': '',
        'photo': '',
        'target_field': 'Software Development',
    },
    'defaults': {
        'role_type': 'Werkstudent',
        'category': 'Software Developer',
        'availability': '20 hours/week',
        'start_date': 'Immediately',
    },
    'server': {
        'port': 8765,
        'open_browser': True,
        'pdflatex': '',
        'compile_timeout': 120,
    },
}

PROFILE_FIELDS = list(DEFAULT_CONFIG['profile'])
DEFAULT_FIELDS = list(DEFAULT_CONFIG['defaults'])
SERVER_FIELDS = list(DEFAULT_CONFIG['server'])

# LaTeX macro name -> profile key. Templates opt in by defining
# \newcommand{\ApplicantName}{...} etc.; macros that are absent are left alone.
PERSONAL_MACROS = {
    'ApplicantName': 'full_name',
    'ApplicantHeadline': 'headline',
    'ApplicantEmail': 'email',
    'ApplicantPhone': 'phone',
    'ApplicantLocation': 'location',
    'ApplicantLinkedIn': 'linkedin',
    'ApplicantGitHub': 'github',
    'ApplicantPortfolio': 'portfolio',
}
URL_KEYS = {'linkedin', 'github', 'portfolio'}

_ESCAPES = {'\\': r'\textbackslash{}', '&': r'\&', '%': r'\%', '$': r'\$', '#': r'\#',
            '_': r'\_', '{': r'\{', '}': r'\}', '~': r'\textasciitilde{}', '^': r'\textasciicircum{}'}
_ESCAPE_RE = re.compile('|'.join(re.escape(k) for k in _ESCAPES))


def latex_escape(text):
    """Escape plain text so it is safe inside a LaTeX macro body."""
    return _ESCAPE_RE.sub(lambda m: _ESCAPES[m.group(0)], str(text))


def latex_url(url):
    """URLs go into \\href; only characters that break the argument are removed."""
    return re.sub(r'[{}\\\s]', '', str(url))


def _merge(base, override):
    out = {}
    for section, defaults in base.items():
        out[section] = dict(defaults)
        incoming = override.get(section) if isinstance(override, dict) else None
        if isinstance(incoming, dict):
            for key in defaults:
                if key in incoming and incoming[key] is not None:
                    out[section][key] = incoming[key]
    return out


def load_config(path=None):
    """Return config merged over defaults. A missing or broken file yields defaults."""
    path = Path(path) if path else CONFIG_FILE
    data = {}
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        pass
    cfg = _merge(DEFAULT_CONFIG, data)
    try:
        cfg['server']['port'] = int(cfg['server']['port'])
    except (TypeError, ValueError):
        cfg['server']['port'] = DEFAULT_CONFIG['server']['port']
    try:
        cfg['server']['compile_timeout'] = max(10, int(cfg['server']['compile_timeout']))
    except (TypeError, ValueError):
        cfg['server']['compile_timeout'] = DEFAULT_CONFIG['server']['compile_timeout']
    cfg['server']['open_browser'] = bool(cfg['server']['open_browser'])
    return cfg


def save_config(cfg, path=None):
    """Validate, normalise and write config.json. Returns the saved config."""
    path = Path(path) if path else CONFIG_FILE
    clean = _merge(DEFAULT_CONFIG, cfg)
    for key in PROFILE_FIELDS:
        clean['profile'][key] = str(clean['profile'][key]).strip()[:300]
    for key in DEFAULT_FIELDS:
        clean['defaults'][key] = str(clean['defaults'][key]).strip()[:140]
    port = clean['server']['port']
    try:
        port = int(port)
    except (TypeError, ValueError):
        raise ValueError('Port must be a number')
    if not 1024 <= port <= 65535:
        raise ValueError('Port must be between 1024 and 65535')
    clean['server']['port'] = port
    clean['server']['open_browser'] = bool(clean['server']['open_browser'])
    clean['server']['pdflatex'] = str(clean['server']['pdflatex']).strip()
    try:
        clean['server']['compile_timeout'] = max(10, int(clean['server']['compile_timeout']))
    except (TypeError, ValueError):
        raise ValueError('Compile timeout must be a number of seconds')
    path.write_text(json.dumps(clean, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    return clean


def is_configured(cfg):
    """True once the user has replaced the placeholder identity."""
    p = cfg['profile']
    return p['full_name'] not in ('', DEFAULT_CONFIG['profile']['full_name']) and \
        p['email'] not in ('', DEFAULT_CONFIG['profile']['email'])


def _replace_macro(tex, macro, value):
    pattern = re.compile(r'^(\s*\\(?:re)?newcommand\{\\' + macro + r'\}\{).*(\}\s*(?:%.*)?)$', re.M)
    return pattern.sub(lambda m: m.group(1) + value + m.group(2), tex, count=1)


def stamp_personal_fields(tex, profile):
    """Fill \\newcommand{\\ApplicantX}{...} definitions from the profile."""
    for macro, key in PERSONAL_MACROS.items():
        value = profile.get(key, '')
        if value == '':
            continue  # keep whatever the template author put there
        rendered = latex_url(value) if key in URL_KEYS else latex_escape(value)
        tex = _replace_macro(tex, macro, rendered)
    return tex


def availability_sentence(availability, start_date):
    availability = str(availability or '').strip()
    start_date = str(start_date or '').strip()
    if availability and start_date:
        return 'I am available to start ' + start_date + ' and can work ' + availability + '.'
    if availability:
        return 'I can work ' + availability + '.'
    if start_date:
        return 'I am available to start ' + start_date + '.'
    return ''


def stamp_job_fields(tex, entry):
    """Fill job-specific macros (\\TargetCompany etc.) in a cover-letter working copy."""
    fields = {
        'TargetCompany': entry.get('company', ''),
        'TargetPosition': entry.get('job_title', ''),
        'AvailabilitySentence': availability_sentence(entry.get('availability'), entry.get('start_date')),
    }
    for macro, value in fields.items():
        if value and value not in ('Company not specified', 'Position not specified'):
            tex = _replace_macro(tex, macro, latex_escape(value))
    return tex


def find_pdflatex(configured=''):
    """Locate pdflatex on PATH or in the usual TeX Live / MiKTeX / MacTeX folders."""
    if configured:
        if Path(configured).is_file():
            return str(configured)
        found = shutil.which(configured)
        if found:
            return found
    found = shutil.which('pdflatex')
    if found:
        return found
    exe = 'pdflatex.exe' if sys.platform == 'win32' else 'pdflatex'
    candidates = []
    if sys.platform == 'win32':
        local = os.environ.get('LOCALAPPDATA', '')
        candidates += [
            os.path.join(local, 'Programs', 'MiKTeX', 'miktex', 'bin', 'x64'),
            os.path.join(local, 'Programs', 'MiKTeX', 'miktex', 'bin'),
            r'C:\Program Files\MiKTeX\miktex\bin\x64',
            r'C:\Program Files (x86)\MiKTeX\miktex\bin',
        ]
        candidates += sorted(glob.glob(r'C:\texlive\*\bin\windows'), reverse=True)
        candidates += sorted(glob.glob(r'C:\texlive\*\bin\win32'), reverse=True)
    elif sys.platform == 'darwin':
        candidates += ['/Library/TeX/texbin', '/usr/local/bin', '/opt/homebrew/bin']
    else:
        candidates += ['/usr/bin', '/usr/local/bin']
        candidates += sorted(glob.glob('/usr/local/texlive/*/bin/*'), reverse=True)
    for folder in candidates:
        path = os.path.join(folder, exe)
        if os.path.isfile(path):
            return path
    return None


def latex_install_hint():
    if sys.platform == 'win32':
        return ('pdflatex is not installed. Install MiKTeX (https://miktex.org/download) or TeX Live, '
                'then restart Job Apply. You can also set "server.pdflatex" in config.json to the full path.')
    if sys.platform == 'darwin':
        return 'pdflatex is not installed. Install BasicTeX or MacTeX (https://tug.org/mactex/) and restart Job Apply.'
    return 'pdflatex is not installed. Install TeX Live (e.g. sudo apt install texlive-latex-extra) and restart Job Apply.'
