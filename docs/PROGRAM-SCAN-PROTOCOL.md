# Program scan from chat

## Team-wide automation (program-v4)

The shared workflow applies to all authorized team members, not just a single operator. One submitted public software repository link resolves to a pinned source commit. A **normal scan** checks the immutable-source reusable index first at `.scan-cache/program-v4/<owner>/<repo>/<commit>.json`. Validate the indexed result/report/decision and matching run before reusing a verdict. **Fresh**, **rescan** or **from scratch** bypasses this cache and submits a new independent request. A status check for an existing request must not create another request.

GitHub Actions runs `prepare`, three parallel analyzer jobs (`codeql`, `osv`, and `embedded_skills`), then `aggregate` and `publish`. Aggregation records findings, incomplete coverage and deployment eligibility in `result.json`, `report.json` and `decision.md`. Publishing writes the report and eligible cache index without sending notifications.

**Fixed company scanner repository:** `lancea-aicareercoaching/team-skill-review` on `main`.

Use `.github/workflows/program-scan.yml` for **software programs**, without replacing the existing `chat-scan.yml` AI skill workflow.

1. Distinguish AI skills from software programs using the pinned source and the existing repository classification result. When a repository contains both, say which component will be checked. User may explicitly choose a program review; that request is not an installation instruction.
2. For a public GitHub software repository, submit one new `.program-requests/<unique-id>.json` file containing only `repository_url` (root) and optional `ref`. Submission triggers `Scan software program from chat`.
3. The worker resolves the requested ref to a 40-character commit. It checks out public source as data, without installing or starting the program. CodeQL attempts static analysis of supported Python and JS/TS source with `build-mode: none`; OSV-Scanner checks known dependency vulnerabilities. Both tool configurations and languages are bounded; this is **not** a complete software safety certification.
4. For software repositories, the same program job automatically discovers and analyzes up to 12 regular embedded `SKILL.md` files with pinned SkillSpector (static only). The combined result includes `embedded_skills.status`, `discovered_count`, `selected_count`, and per-file findings. More than 12 or a scanner failure means partial/incomplete coverage; no claim of comprehensive skill safety is permitted. This is not an instruction to execute or install any candidate skills.

5. On explicit follow-up, read `.scan-results/<id>/result.json` once and read the matching `report.json` published by the existing trusted publisher. Check the matching GitHub Actions run on delayed 404s. Never submit a duplicate because results are late.
6. `review_required` means automated checks completed without detected matches and any deployment still requires separate approval. `needs_review` indicates scanner findings. `incomplete` includes unavailable CodeQL licensing, scanner failures, unknown output format, or missing coverage. No automated report state means 'safe to install'.
7. Disclose that dedicated antivirus scanning is not included. The standard report is based on the configured automated static checks. Installation and candidate execution are outside the program scan.
8. Program scan evidence is recorded in `.scan-results/<request-id>/` automatically when the worker and publisher succeed. This **does not** copy, endorse, or approve the source repository for the company's distribution library. Only after an explicit per-repository approval and review of license and source SHA may an authorized user publish a versioned copy to the existing shared company library and verify readback.
9. If an analyzer does not run due to GitHub Code Security licensing restrictions or execution limits, report it as incomplete; don't alter paid settings or grant new permissions automatically.

## Static coverage and cache

Dedicated antivirus scanning is not included. Reuse only exact-source program-v4 reports with complete configured analyzer coverage and verified matching run and artifacts. Historical reports remain unchanged.

Verify the job set and the published result, report and decision against the exact request and immutable source. Reports with findings or coverage gaps block deployment eligibility. A clean static report leaves runtime behavior unverified and never authorizes installation or publication. Only AI-skill scans can lead to an installation offer.

**Default routing:** A repository-root link for a software program uses the combined program job without requiring the user to separately request SKILL.md checks; a direct link to an individual SKILL.md uses the AI-skill workflow. This is on-demand per link, not scheduled monitoring of repositories.
