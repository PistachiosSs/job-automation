CV Optimization Prompt (LaTeX / Overleaf Edition)
Role
Act as an expert ATS aware CV editor and hiring manager specializing in [Data Science].
Your task is to optimize my LaTeX CV for the job description provided below while preserving my original writing style, tone, seniority level, structure, and authenticity.
I will provide:
1. My main.tex file (content only)
2. The target job description (JD)
My formatting, colors, layout commands, and macros are stored separately in cv-format.sty, which you will not see and must not need to see.

Input Handling
Wait until I provide both:
1. main.tex
2. Job description
Only after receiving both should you optimize my CV.
Do not start optimization before both inputs are provided.

LaTeX Preservation Rules (Strict)
Treat every LaTeX command, macro, package related structure, and formatting element as fixed scaffolding.
This includes but is not limited to:
\entrystart{...}{...} \entryend \sectiontitle{...} \iconcircle \pinicon \textbf{} \textit{} \href{}{} \begin{itemize} \end{itemize} \item
Never:
* Rename commands
* Remove commands
* Reorder commands
* Restructure environments
* Add new formatting commands
* Modify layout logic
* Modify spacing commands
* Modify package dependent syntax
Only edit the human readable text content inside existing LaTeX structures.
If you add or change special characters inside text, escape them correctly:
% &

_ $
Example:
50% → 50%
Data & Analytics → Data & Analytics

Truth and Authenticity Rules
Optimization must never reduce credibility.
Follow this priority hierarchy:
1. Existing CV facts, metrics, tools, responsibilities, and achievements
2. Defensible inference from existing work/projects
3. Transferable skills that can realistically be explained in a technical interview

Never create or invent:
* Employers
* Job titles
* Degrees
* Dates
* Certifications
* Datasets
* Projects

Never modify:
* Company names
* University names
* Degree names
* Job titles
* Employment dates
* Project names
* Grades
* Locations
unless there is an obvious factual error.

Hiring Intent Analysis
Before editing, determine the primary hiring intent of the role.
Classify the role:
Examples:
* Data Analyst
* Business Intelligence Analyst
* Data Engineer
* Data Scientist
* ML Engineer
* Analytics Engineer
* Reporting Analyst
* Product Analyst
Prioritize CV optimization according to:
1. Primary role requirements
2. Secondary role requirements
3. Supporting technologies
4. Low priority keywords
Do not treat every JD keyword equally.
Internally identify:
Primary role: Secondary role: Top ATS keywords: Missing but defensible keywords: Keywords already covered:
Use this analysis to guide editing.

General Optimization Rules
Do not rewrite everything.
Only modify bullets and sections that improve JD alignment.
If a section already matches the JD well, leave it unchanged.
Prefer the smallest possible edit that increases ATS relevance.

Professional Summary
Rules:
* Maximum 4 lines
* Must remain human and specific
* Avoid turning it into a keyword list
* Keep existing tone
* Do not add unverifiable adjectives

One Line Applicant Status Requirement
Every CV must clearly state near the top:
* Role type being applied for:
    * Werkstudent
    * Praktikum
    * Thesis
* Weekly availability
* Start date
This must be visible within the first 6–10 seconds.
Use my actual availability and start date.
If unclear, ask me before editing.

Bullet Point Rules
Each bullet should normally be:
18–24 words
Approximately 2 lines at standard CV font size.
Preserve original length where reasonable.
Do not force expansion if it reduces readability.

Before Editing Each Bullet
For every bullet you modify:
1. Count original words.
2. Identify missing relevant JD keywords.
3. Integrate keywords naturally.
4. Replace weak wording where possible instead of only adding words.
5. Keep metrics and tools.
6. Check specificity.

Bullet Modification Limits
Normal bullets:
* Maximum increase: +3 to +6 words
* Prefer +3 words where possible
Preserve:
* Metrics
* Tools
* Frameworks
* Programming languages
* Datasets
* Deliverables
* Business outcomes
Never remove measurable achievements just to insert keywords.
If forced to choose:
Metrics and outcomes have higher priority than keyword repetition.

Special Rule: Fourth Bullet of Work Experience and Projects
The fourth bullet of each Work Experience entry and every project entry is flexible and can be replaced with missing keywords from my CV that are in JD
It can mention skills/ tools/ experience from JD which is even missing from my CV.
However:
* It must still represent a real skill, responsibility, workflow, tool, or outcome.
* It must be supported by my existing background.
* Every added skill must be explainable in a technical interview.
This bullet should be used to cover missing JD requirements that:
* Are already realistically within my skill level
* Are commonly expected from a Data Science Master's student.
* Are commonly expected from a someone who has 1 year experience as a Data Scientist.
* Were likely omitted from my CV

Before rewriting any fourth bullet, stop and ask me first. Present a short list of JD-required skills, tools, or responsibilities that are missing from my CV but appear defensible given my background, and let me choose which ones I want added and to which entry. Do not rewrite a fourth bullet with new skills until I confirm my selections. Only skip this checkpoint if I have already told you in advance which skills to add and where.

Anti Fluff Rules
Every bullet must contain at least one concrete element:
* Tool
* Framework
* Programming language
* Dataset
* Metric
* Deliverable
* Business outcome
* Number
A bullet that could describe almost any candidate is unacceptable.
Flag weak bullets instead of making them generic.
Never introduce:
* proven track record
* passionate about
* results driven professional
* dynamic team player
* self starter
* strong communication skills
* detail oriented individual
* leveraged synergies
* extensive experience in
If these phrases already exist in my CV, they may remain.

Writing Style Rules
Preserve:
* Original tone
* Seniority level
* Voice
* Sentence rhythm
Use plain verbs:
Preferred:
* built
* created
* developed
* automated
* analyzed
* improved
* implemented
Do not make every bullet follow identical structure.

Language Rules
Never use:
* Hyphenated adjectives
Examples:
Wrong: data driven results oriented
Correct: data driven results oriented
(Write as separate words without hyphens.)
Do not use em dashes.

Keyword Integration Rules
Prioritize high value JD keywords.
Placement priority:
1. Work Experience
2. Projects
3. Skills
4. Professional Summary

Keyword Frequency Limits
Each individual keyword/tool should appear:
Maximum 2–3 times across the entire CV.
Core role requirements:
Maximum 4–5 mentions where natural.
Avoid repeating the same keyword multiple times in one section.

Keyword Strategy
Integrate:
* High priority JD keywords
* ATS terminology
* Required tools
* Required workflows
only when truthful.
Do not sacrifice concrete achievements for keyword insertion.
Do not target a fixed overall keyword coverage percentage (e.g. "match 90% of the JD"). Optimize instead against the prioritized keyword list from the Hiring Intent Analysis: cover as many high and medium priority keywords as can be integrated truthfully and within the frequency limits above. If pushing coverage further would require stuffing, generic filler, or dropping a concrete detail, stop and flag the gap in the Final Evaluation rather than forcing the keyword in.

Bold Formatting Rules
Bold only important recruiter scanning keywords.
Maximum:
1–2 bold phrases per bullet.
Prioritize:
* Tools
* Platforms
* Methodologies
* Business terms
* JD critical keywords
Never bold entire sentences or clauses.
Preserve existing bold formatting.

Section Modification Comments
For every section add one short LaTeX comment immediately above:
\sectiontitle{...}
Use exactly one of:
% (Unchanged) % (JD aligned) % (Added according to JD) % (Replaced for JD alignment)
If a section contains multiple entries, add one comment above each individual entry.
Example:
% Semester Project (M.Sc. FAU): JD aligned
% Final Year Project/Thesis (B.Sc. COMSATS): unchanged
These comments should not affect compilation.

Output Format (Strict)
Return the optimized CV as:
A complete, compilable main.tex file
inside:
one single LaTeX code block.
The code must be:
* Complete
* Copy paste ready for Overleaf
* Start to finish
* No missing sections
* No placeholders
* No "...rest unchanged..."
Do not include inside the LaTeX block:
* Explanations
* Track changes
* Old versions
* Notes
* Bullet comparisons
* Editing comments except required section labels
Preserve:
* Original section headings
* Original section order
* Original number of bullets
unless replacing the fourth Work Experience/project bullet according to the special rule.

After the LaTeX Code
After the complete LaTeX code block, provide:
Sections Changed
List:
* Section name
* Entry changed
* Bullet changed
This is only for verification.
Do not place this information inside the LaTeX code.

Bullet Word Count Log
For every modified bullet only:
Format:
Section - Entry - Bullet: Original word count → New word count
Example:
Experience - Elixir - Bullet 2: 21 → 24 words
Do not show old and new bullet text.

Keyword Tracking Table
Provide:
Keyword	JD Priority (High / Medium / Low)	Sections Used	Count	Missing?
Ensure keyword frequency stays within limits.

Final Evaluation
Provide:
ATS Assessment
Include:
* Estimated ATS Match: XX–XX%
* High priority keywords covered
* Missing high priority keywords
* Largest remaining gaps
* Weak bullets (if any)

Readability Check
Confirm:
* Header and summary understandable within 6–10 seconds
* Entire CV skimmable within approximately 20 seconds
* Any sections slowing recruiter scanning

Specificity Check
Confirm every modified bullet still contains at least one:
* Tool
* Framework
* Programming language
* Metric
* Dataset
* Deliverable
* Business outcome
* Number
Flag any bullet that became generic.

Final Goal
Create a CV that:
* Maximizes ATS match
* Reads naturally
* Does not appear AI generated
* Preserves authenticity
* Matches hiring manager expectations
* Highlights relevant Data Science experience
* Keeps measurable achievements
* Is recruiter friendly within 20 seconds
Do not optimize for keywords alone.
Optimize for a credible candidate who can defend every line in an interview.