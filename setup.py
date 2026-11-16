#!/usr/bin/env python3
"""First-time setup for Job Apply.

    python setup.py            interactive wizard: profile, defaults, server
    python setup.py --check    only print the environment diagnostics
    python setup.py --yes      non-interactive: write config.json from the
                               existing file or config.example.json

Everything you enter is stored in config.json (git-ignored). The master
templates are left untouched; your details are stamped into each application
copy when it is created.
"""
import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'app'))
import config as cfgmod  # noqa: E402

LABELS = {
    'full_name': 'Full name',
    'headline': 'Headline under your name (e.g. "M.Sc. Student in Computer Science")',
    'email': 'Email address',
    'phone': 'Phone number',
    'location': 'Location (City, Country)',
    'linkedin': 'LinkedIn URL (optional)',
    'github': 'GitHub URL (optional)',
    'portfolio': 'Portfolio URL (optional)',
    'photo': 'Path to your CV photo (JPEG, optional - leave empty for the placeholder)',
    'target_field': 'Field you apply in (used in the ChatGPT prompt, e.g. "Data Science")',
    'role_type': 'Default application type (Werkstudent / Praktikum / Thesis / Full-time)',
    'category': 'Default position category',
    'availability': 'Default weekly availability (e.g. "20 hours/week")',
    'start_date': 'Default start date (e.g. "Immediately")',
    'port': 'Local port for the web app',
}


def check_environment(cfg):
    ok = True
    print('Environment check')
    print('  Python      : ' + sys.version.split()[0] + ' at ' + sys.executable)
    if sys.version_info < (3, 8):
        print('  !! Python 3.8 or newer is required')
        ok = False
    tex = cfgmod.find_pdflatex(cfg['server'].get('pdflatex', ''))
    print('  pdflatex    : ' + (tex if tex else 'NOT FOUND - ' + cfgmod.latex_install_hint()))
    cv = ROOT / 'templates' / 'cv' / 'main.tex'
    cover = ROOT / 'templates' / 'cover-letter'
    has_cover = any((cover / n).is_file() for n in ('main.tex', 'cover_letter_master.tex'))
    print('  CV template : ' + ('found' if cv.is_file() else 'missing templates/cv/main.tex'))
    print('  Cover letter: ' + ('found' if has_cover else 'missing (optional)'))
    photo = ROOT / 'templates' / 'cv' / 'photo.jpg'
    print('  CV photo    : ' + ('placeholder present' if photo.is_file() else 'missing templates/cv/photo.jpg'))
    print('  config.json : ' + ('present' if cfgmod.CONFIG_FILE.is_file() else 'not created yet'))
    return ok and tex is not None


def ask(label, current):
    shown = ' [' + str(current) + ']' if current not in ('', None) else ''
    try:
        answer = input('  ' + label + shown + ': ').strip()
    except EOFError:
        return current
    if answer == '-':
        return ''
    return answer if answer else current


def wizard(cfg):
    print('\nProfile (press Enter to keep the value in brackets, "-" to clear it)')
    for key in cfgmod.PROFILE_FIELDS:
        cfg['profile'][key] = ask(LABELS[key], cfg['profile'][key])
    print('\nDefaults for new applications')
    for key in cfgmod.DEFAULT_FIELDS:
        cfg['defaults'][key] = ask(LABELS[key], cfg['defaults'][key])
    print('\nServer')
    cfg['server']['port'] = ask(LABELS['port'], cfg['server']['port'])
    return cfg


def validate_photo(cfg):
    photo = cfg['profile'].get('photo', '')
    if not photo:
        return
    path = Path(photo).expanduser()
    if not path.is_absolute():
        path = ROOT / path
    if not path.is_file():
        print('  !! Photo not found: ' + str(path) + ' (the placeholder will be used until you fix the path)')
    elif path.suffix.lower() not in ('.jpg', '.jpeg'):
        print('  !! The CV template expects a JPEG; convert ' + path.name + ' to .jpg')


def main(argv=None):
    parser = argparse.ArgumentParser(description='Set up Job Apply')
    parser.add_argument('--check', action='store_true', help='only run the environment check')
    parser.add_argument('--yes', action='store_true', help='write config.json without prompting')
    args = parser.parse_args(argv)

    if cfgmod.CONFIG_FILE.is_file():
        cfg = cfgmod.load_config()
    elif cfgmod.EXAMPLE_FILE.is_file():
        cfg = cfgmod.load_config(cfgmod.EXAMPLE_FILE)
    else:
        cfg = cfgmod.load_config()

    healthy = check_environment(cfg)
    if args.check:
        return 0 if healthy else 1

    if not args.yes:
        cfg = wizard(cfg)
    try:
        cfg = cfgmod.save_config(cfg)
    except ValueError as e:
        print('Could not save config.json: ' + str(e))
        return 1
    validate_photo(cfg)
    print('\nSaved ' + str(cfgmod.CONFIG_FILE))
    if not cfgmod.is_configured(cfg):
        print('Note: the profile still uses the sample name/email. Edit config.json or use the Profile page later.')
    print('Next: run start.bat (Windows), ./start.sh (macOS/Linux) or "python app/server.py"'
          ' and open http://127.0.0.1:' + str(cfg['server']['port']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
