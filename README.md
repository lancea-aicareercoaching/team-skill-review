\# Team Skill Review



A shared place to review selected GitHub skills, inspect security reports,

and download versions cleared for the intended AI environment.



\## Current status



The repository contains an initial local scanning demonstration.



\- Scanner: NVIDIA SkillSpector 2.12.0

\- Scan mode: static only, without AI analysis

\- Cloud scanning automation: not configured yet

\- Approved skill downloads: none yet

\- Skill installation and functionality testing: pending

\- Access from another team member's account: not independently verified



\## Candidate under review



Chief of Staff, with its Agent Protocol dependency.



Source repository:

https://github.com/alirezarezvani/claude-skills



Source version:

f8593c4941210a621a6629ce1da9e07897976d5f



| Component | Scan result | Inspection coverage |

|---|---|---|

| Chief of Staff | LOW, 6/100; scanner label SAFE | 100% within configured scope |

| Agent Protocol | LOW, 6/100; scanner label CAUTION | 50%, partial |



Both scans flagged instructions for saving decision records.

Agent Protocol also encountered a parser limitation and a missing

runtime decision-log reference.



The candidate remains UNDER REVIEW.

A scanner's SAFE label does not constitute installation approval.



\## Read the evidence



1\. Open REVIEW-STATUS.md for findings and outstanding requirements.

2\. Open reports/ for the original JSON scan reports.

3\. Check the source version before comparing or repeating results.



\## Workflow for new candidates



1\. Identify the exact skill, source version, and intended AI environment.

2\. Keep the downloaded candidate separate from active skills.

3\. Scan the candidate and identify required dependencies.

4\. Review findings, inspection coverage, and limitations.

5\. Record the review decision.

6\. For cleared candidates, prepare versioned downloads with source

&#x20;  attribution, license notices, and installation instructions.

7\. Test functionality in the intended AI environment.



Incomplete scans and unresolved findings must remain visible.



\## Using skills



Downloading files does not install a skill.



Follow the instructions supplied for each cleared candidate.

Compatibility with ChatGPT, Claude chat, or Claude Code must be tested

separately; it is not assumed.



\## Repository contents



\- README.md: team guide and current workflow status

\- REVIEW-STATUS.md: initial candidate review

\- reports/: saved security scan reports



\## Handling files



Keep this repository private.

Do not upload credentials, private business records, or client information.

Preserve applicable copyright and license notices when copying source files.



This repository does not replace the business knowledge base.

