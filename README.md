# Job Apply — Local Application Studio (macOS, v0.1)

**Working local MVP:** A browser application that stores per-job copies of LaTeX templates, prepares a complete ChatGPT handoff prompt, supports editing and previewing LaTeX/PDF, requires independent document approvals, and maintains a local Prepared / Applied tracker.

**Not yet implemented:** automatic launch from the ChatGPT conversation, an AI connection inside the web app, direct Google Sheets write access, . Those features depend on an authorized, supported connector or further configuration. This package **does not use your ChatGPT subscription as an API key**.

## Included in this public repository

- `app/` — local Python HTTP server and browser interface.
- `templates/cv/` — LaTeX CV template, formatting style, and **generic placeholder photo**.
- `templates/cover-letter/cover_letter_master.tex` — reusable cover-letter LaTeX template.
- `prompts/` — editable CV and cover-letter prompt files.
- `tests/` — smoke and template detection tests.
- `start.sh` and `start.command` — local launchers for Unix/macOS.

Personal contact information and the user's original photograph have been replaced with public-safe placeholders. Replace them locally with your own details before applying for jobs. Never commit application history, `.env` files, API credentials, or private CVs.

## Launch on a Mac

1. Unzip the package on your Desktop so the folder is `~/Desktop/Job-Apply`.
2. Install **Python 3** if you do not already have it. The web server uses only Python standard-library modules; there is **no pip install**.
3. Install **MacTeX or BasicTeX** if you want PDF compilation. Confirm `pdflatex --version` works in Terminal.
4. Open `start.command` from Finder, or use Terminal:

```bash
cd ~/Desktop/Job-Apply
chmod +x start.command
./start.command
```

5. The browser should open **http://127.0.0.1:8765**. Keep the Terminal window running while you use the app. Press `Ctrl+C` to stop.

This service binds only to `127.0.0.1` and does not upload CVs or documents on its own. **Copying the handoff prompt into ChatGPT explicitly sends its included job/CV content to ChatGPT.** Only import LaTeX files you trust; TeX is a programmable document format.

## Use the app

1. Open **Templates & prompts**. Replace the bundled placeholder `photo.jpg` in CV assets with your own image, if desired. You can replace the bundled example cover-letter template and edit its prompt to suit your workflow.
2. Open **New application**. Paste the job description, enter the actual company/title/link and your real availability, and select CV, cover letter, or both.
3. The app creates `applications/<date>-<company>-<id>/` with separate editable working copies. The master remains unchanged.
4. Open **Document studio**, choose CV or cover letter, and click **Prepare ChatGPT prompt**. Copy it to ChatGPT and follow your prompt rules. When ChatGPT returns a full `main.tex`, paste it into the editor. The current CV prompt requests the job description before any tailoring; it also requires explicit approval for special fourth-bullet changes.
5. Click **Save source**, **Compile PDF**, and **Review changes**. Inspect the actual PDF in the right pane. **Approve** when ready. PDF download is enabled after approval.
6. After all selected documents are approved, select **Mark as Prepared**. This records a preparation timestamp but **does not claim an application was submitted**.
7. After submitting the application yourself, open **Application tracker** and click **Mark Applied**. Download the CSV to import into a Google Sheet.

## Files and data

- `templates/cv/` — immutable master CV *during application creation*; you can update its files from Templates & prompts.
- `templates/cover-letter/` — included master cover-letter project, replaceable from the portal.
- `prompts/` — separate editable plain-text instructions for CV and cover letter.
- `applications/<id>/cv/` and `applications/<id>/cover-letter/` — per-application `.tex`, auxiliary files and generated PDFs.
- `applications/<id>/manifest.json` — metadata including status, current job description and document approvals.
- `tracker/applications.csv` — automatically updated, UTF-8 CSV suitable for import into a new Google Sheet; remote Google Sheets synchronization is **not** connected yet.
- `.agents/skills/job-apply/SKILL.md` — draft agent skill contract for compatible local agents. This is **not** an installed ChatGPT `@job-apply` command.

## Limitations

- **ChatGPT launch:** a browser chat page cannot automatically start an arbitrary Desktop program. Start the local launcher first; a future custom ChatGPT app/MCP connector could expose supported actions with secure authorization.
- **ChatGPT AI:** there is no direct usage of the ChatGPT subscription from this localhost app. Tailoring is a deliberate copy/paste handoff, not one-click AI generation.
- **Google Sheets:** local CSV tracking works now; authenticating to Google and creating/updating a Sheet requires a later integration step.
- **LaTeX formatting:** layout commands are never automatically rewritten by this app, but AI-generated changes can still cause overflow or page-count changes. Inspect the compiled PDF.
- **Cover letter:** a generic master is included; tailor the content and prompt before sending applications.
- **CV template:** the included sample is for demonstration. Update the personal details and professional claims before use.

## Mac diagnostics

- If the Terminal says `pdflatex is not installed`, install MacTeX or BasicTeX and restart the Terminal. Check `/Library/TeX/texbin/pdflatex` if your PATH doesn't include it.
- If a compile fails, the app displays concise LaTeX errors. Missing images are detected in advance.
- If port 8765 is busy, close the old Job Apply process or run `python3 app/server.py --port 8766` and visit `http://127.0.0.1:8766`.
- To preserve all work, back up the entire `Job-Apply` folder. Do not discard `applications/` or `tracker/` when upgrading.
