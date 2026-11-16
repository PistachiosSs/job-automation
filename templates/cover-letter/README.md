# Master cover letter template

**Template file:** `cover_letter_master.tex`

The local portal detects this file automatically when it starts; no upload or rename is needed. New applications that include a cover letter receive a separate working copy named `main.tex`, along with the template assets. The master remains unchanged. If `main.tex` is also present in this template folder, it takes precedence for compatibility with imported Overleaf projects.

After updating the portal code, restart it with `start.command` and refresh the browser. Existing application documents remain unchanged; select **Cover letter** when creating a new application to use the detected master.

This is the immutable, general master for the job-application workflow. Make a separate copy for each job before editing. It is designed to compile with MacTeX/Overleaf (pdfLaTeX), needs no custom `.sty` file, and follows the simple, left-aligned visual style of the reference cover letters.

## Tailoring contract for the application tool

1. Start from a new copy of `cover_letter_master.tex`. Do **not** modify the master.
2. Replace the six job-specific fields (`TargetPosition`, `TargetCompany`, `LetterDate`, `RoleMotivation`, `RoleContribution`, `AvailabilitySentence`).
3. Use the **actual job description** to tailor motivation and relevant evidence. For Unity/XR/3D roles, foreground the TRUST project and Blender/Unity workflow. For software roles, foreground engineering, prior DevOps/frontend work and collaboration. Adapt the emphasis without inventing achievements or technology experience.
4. Preserve truthful, reusable core details: Master's studies in International Software Systems Science, Bachelor's in Computer Science, student-assistant work at the University of Bamberg Gamification Chair on TRUST, Unity/Blender contributions, 4+ years of Blender, earlier DevOps and frontend experience.
5. Do not claim the AR Master's thesis is completed or in progress without checking its current status; the general master intentionally omits it. Avoid changing degree title or dates without verification.
6. If the job specifically asks for availability, use the `AvailabilitySentence` macro. At the time this template was created, the applicant stated availability to start immediately for up to 20 hours/week; re-check before sending later applications.
7. Check company name, position title, company-specific details, relevance of each paragraph, spelling, and one-page PDF output before sending.
8. Save outputs separately, for example `applications/<company>/<role>/cover_letter.tex` and `cover_letter.pdf`.

## Editing example

```latex
\newcommand{\TargetPosition}{Working Student - XR Development}
\newcommand{\TargetCompany}{Example GmbH}
\newcommand{\RoleMotivation}{Your work on ... appeals to me because ... .}
\newcommand{\RoleContribution}{For this role, my experience with ... would help me ... .}
\newcommand{\AvailabilitySentence}{I can start immediately and work up to 20 hours per week.}
```

The four supplied PDF letters served as **writing and minimalist layout references**, not as exact LaTeX source files. If an original cover-letter `.tex` design is supplied later, the reusable content can be placed in it without changing its visual style.
