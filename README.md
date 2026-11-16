# Job Apply — Local Application Studio (v0.2)

A small, local-only web app that turns one master LaTeX CV / cover letter into a tailored,
reviewed, tracked application per job. Runs on **Windows, macOS and Linux** with nothing but
Python 3 and a LaTeX distribution. No accounts, no API keys, nothing leaves your computer
unless you copy a prompt into ChatGPT yourself.

What it does:

- Keeps your master templates untouched and makes a **copy per application**.
- Stamps **your profile** (name, contact, links, photo) and the **job fields** (company, title,
  availability) into that copy automatically.
- Builds a complete **ChatGPT handoff prompt** (your rules + job description + current `main.tex`).
- Lets you paste the result back, **compile the PDF locally**, diff it against the master,
  approve each document, and mark the application *Prepared* and later *Applied*.
- Maintains `tracker/applications.csv` for import into a spreadsheet.

Not included (by design, see [docs/NEXT_STEPS.md](docs/NEXT_STEPS.md)): direct AI calls, Google Sheets sync.

## Quick start

### 1. Install the two prerequisites

| | Windows | macOS | Linux |
|---|---|---|---|
| Python 3.8+ | [python.org](https://www.python.org/downloads/) or `winget install Python.Python.3.13` | preinstalled / `brew install python` | `sudo apt install python3` |
| pdflatex | [MiKTeX](https://miktex.org/download) (`winget install MiKTeX.MiKTeX`) or TeX Live | [BasicTeX / MacTeX](https://tug.org/mactex/) | `sudo apt install texlive-latex-extra texlive-fonts-recommended` |

No `pip install` is needed — the app uses only the Python standard library.

> MiKTeX tip: run `initexmf --set-config-value "[MPM]AutoInstall=1"` once so missing LaTeX
> packages are installed automatically instead of showing a dialog during the first compile.

### 2. Get the code and run setup

```bash
git clone https://github.com/PistachiosSs/job-automation.git
cd job-automation
python setup.py          # guided wizard: your name, contact, links, defaults, port
```

`setup.py` checks Python and pdflatex, then writes **`config.json`** (git-ignored). Run
`python setup.py --check` any time to see the environment diagnostics, or
`python setup.py --yes` to create a config from `config.example.json` without prompts.

### 3. Start the app

| Windows | macOS | Linux / any shell |
|---|---|---|
| double-click `start.bat` or run `.\start.ps1` | double-click `start.command` | `./start.sh` |

All launchers run the setup wizard automatically if `config.json` is missing, then open
**http://127.0.0.1:8765**. Keep the window open while you use the app; `Ctrl+C` stops it.
Options: `--port 8766`, `--no-browser` (also settable in `config.json`).

## Using the app

1. **Profile & settings** — enter your details once. They are stamped into every new
   application copy; the master templates stay generic. Point *CV photo path* at a JPEG of
   yourself (or leave empty to keep the placeholder).
2. **Templates & prompts** — import your own LaTeX CV / cover letter (files or an Overleaf ZIP)
   or keep the bundled ones. Edit the tailoring instructions sent to ChatGPT.
3. **New application** — paste the job description, company and title (defaults for
   availability, start date and role type come from your profile), choose CV / cover letter.
4. **Document studio** — *Prepare ChatGPT prompt* → copy into ChatGPT → paste the returned
   `main.tex` back → *Save source* → *Compile PDF* → *Review changes* → *Approve*.
   The PDF download unlocks after approval.
5. *Mark as Prepared* once every requested document is approved. After you submit the
   application yourself, open **Application tracker** and *Mark Applied*. Export the CSV from there.

### Using your own templates

The app fills these macros if they exist in a template, and leaves everything else alone:

```latex
\newcommand{\ApplicantName}{...}      \newcommand{\ApplicantHeadline}{...}
\newcommand{\ApplicantEmail}{...}     \newcommand{\ApplicantPhone}{...}
\newcommand{\ApplicantLocation}{...}  \newcommand{\ApplicantLinkedIn}{...}
\newcommand{\ApplicantGitHub}{...}    \newcommand{\ApplicantPortfolio}{...}
% cover letters additionally:
\newcommand{\TargetCompany}{...}  \newcommand{\TargetPosition}{...}  \newcommand{\AvailabilitySentence}{...}
```

Add the block to your own `main.tex` (see [templates/cv/main.tex](templates/cv/main.tex) for the
`\applink{url}{label}` helper that shows a plain label when a URL is empty) and the profile
feature works for it too. Templates without the macros still work — nothing is stamped.

## Files and data

| Path | Purpose | In git? |
|---|---|---|
| `config.json` | your profile, defaults, port, pdflatex path | no |
| `config.example.json` | template for `config.json` | yes |
| `templates/cv/`, `templates/cover-letter/` | master LaTeX projects (generic placeholders) | yes |
| `prompts/*.md` | tailoring instructions for ChatGPT | yes |
| `applications/<date>-<company>-<id>/` | per-application copies, manifest, PDFs | no |
| `tracker/applications.csv` | spreadsheet-ready tracker | no |

If you import your real CV into `templates/`, remember it is tracked by git — keep the
repository private or add the file to `.gitignore` before committing.

## Tests

```bash
python -m unittest discover -s tests -p "*_test.py" -v   # unit tests (config, stamping, API, setup)
python tests/smoke_test.py                                # end-to-end: starts the server, compiles real PDFs when pdflatex exists
```

## Troubleshooting

- **"pdflatex is not installed"** — install a LaTeX distribution (table above) and restart; or
  set `server.pdflatex` in `config.json` / the Profile page to the full path of `pdflatex`.
- **First compile is slow or times out** — MiKTeX / TeX Live may be installing packages.
  Raise `server.compile_timeout` (seconds) and retry.
- **Compile error** — the app shows the relevant LaTeX lines. Missing images are reported
  before compilation starts.
- **Port already in use** — run `python app/server.py --port 8766` or change the port on the Profile page.
- **Browser cannot connect** — the server binds to `127.0.0.1` only; use that address, not a LAN IP.

## Security notes

The server listens on localhost only, requires a per-session token for every write, blocks
cross-origin requests, compiles with `-no-shell-escape` and never uploads anything. TeX is a
programmable format: only import templates you trust.
