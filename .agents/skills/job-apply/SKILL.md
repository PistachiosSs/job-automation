---
name: job-apply
description: Prepare per-job LaTeX CV and cover-letter content, with human review and Prepared/Applied tracking using a localhost web application.
---

# Job Apply skill — local project contract

This skill specification belongs to the local Desktop project. It does **not** automatically install an `@job-apply` invocation in ChatGPT. Custom ChatGPT app/MCP setup and permissions are needed for supported direct tool invocations. A plain skill file cannot start a separate browser on the user's macOS Desktop.

## Local application

- User launches `start.bat` (Windows), `start.command` (macOS) or `start.sh` from the project folder.
- Interface is `http://127.0.0.1:8765` (or the port in `config.json`) when the local server is running.
- All document artifacts, prompts, manifests, and CSV exports live under that project folder.
- Personal details come from `config.json`; the app stamps them into each application copy.

## Before tailoring

- Obtain both the job description and the complete local LaTeX `main.tex` source for the relevant document; ask for missing role type, availability and start date when the prompt requires them.
- Do not assume that a LaTeX document represents the current user; verify if names conflict.
- Read the actual instructions in `prompts/cv-prompt.md` or `prompts/cover-letter-prompt.md` and follow them as long as they don't require fabrication or unsafe edits.
- Existing CV content (employers, titles, dates, degrees, grades and claims) is authoritative unless the user confirms a correction. Do not infer personal qualifications from the job description.
- The supplied CV instructions require separate user consent before rewriting a fourth bullet with additional skills. Present a suggested list and wait for approval.

## Editing

- Preserve existing LaTeX commands, macro calls, section sequence and style files. Only change appropriate human-readable content.
- Respect the original writing tone and measured achievements. Escape LaTeX special characters.
- Tailor CV and cover letter separately; the cover letter must be consistent with the final approved CV.
- For each requested document, provide a **complete compilable `main.tex`**. Never replace sections with ellipses.
- Explain substantive changes and identify any missing high-priority requirements. A keyword match percentage is heuristic, not an authenticated ATS score.

## User approval & tracking

- A document must compile successfully and be reviewed by the user before approval.
- Approval is separate for CV and cover letter.
- Prepared means all requested documents are approved, not that the application was submitted.
- Applied means the user explicitly confirmed submitting the application. Never infer submission from a download.
- Avoid duplicate records for a single application ID.

## Integration reality

- The present browser app has a *manual ChatGPT handoff* (copy complete prompt into ChatGPT, paste complete LaTeX result back). This is the only implemented AI workflow.
- The Google Sheets deliverable is `tracker/applications.csv`, which can be imported into a newly created Sheet. No live Sheets MCP connection exists in this version.
- No Overleaf connection or Git access is needed; the original `main.tex` + `.sty` + image assets are copied locally.
