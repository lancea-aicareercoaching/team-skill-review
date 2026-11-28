# Skill Scanner releases

Use MAJOR.MINOR.PATCH for portable Skill Scanner packages. This version is separate from NVIDIA SkillSpector's version and the scanned skill's source commit. Earlier downloads were unversioned; no historical release numbers have been invented.

## Backend contextual evidence extension v1

- Preserve bounded detailed CodeQL, OSV and embedded SkillSpector evidence with truncation flags. No new scanners, cache changes or deployment exceptions.

## 0.14.0 — November 28, 2026

- Remove dedicated ClamAV scanning and signature freshness gates. Preserve CodeQL, OSV, SkillSpector, on-demand retrieval and explicit AI-skill deployment approval.
- Use program-v4 and skill-v3 caches; disclose antivirus scanning is not included.

## 0.12.0 — November 28, 2026

- Add pinned, isolated ClamAV file inspection to both GitHub scan paths. Publish signature versions, freshness, and explicit incomplete coverage.
- Use `program-v3` and `skill-v2` evidence indexes. Require complete, unexpired ClamAV evidence for reuse.
- Report scanner evidence and deployment eligibility. Eligible AI-skill deployment still requires separate approval.
- Remove the program workflow's completion issue and its issue-write permission. Keep the existing workflows and request paths.

## 0.2.1 — November 23, 2026

- Add a short installation offer after a positive review. Link the exact reviewed GitHub commit and skill folder, and carry over any installation conditions.
- Omit the offer for blocked, pending, or discovery results. Scanning never installs or activates the candidate.
- Release artifact: skill-scanner-v0.2.1.zip.

## 0.2.0 — November 22, 2026

- Investigate incomplete checks automatically, including relevant same-repository supporting files at the exact scanned commit, with explicit review bounds and provenance.
- Lead with Recommended to install or Do not install yet; distinguish evidence of risk from missing verification.
- Permit an evidence-based recommendation after a bounded parser limitation is understood through source review. Preserve original score, warnings, and incomplete coverage.
- Keep concise warning evidence, pinned source/report/run links, and installation conditions. Remove the generic installation-approval-pending ending.
- Do not rerun unchanged scans, execute candidate code, enable paid LLM providers, or install the candidate automatically.
- Release artifact: skill-scanner-v0.2.0.zip. Portable packaging does not update an installed account copy automatically.

## 0.1.0 — November 22, 2026

- First explicitly versioned package: skill-scanner-v0.1.0.zip.
- Short plain-language results with severity, rule, file/line, concise evidence, and links to source and report.
- Automatic read-only review of verified flagged source; original scanner findings and incomplete coverage remain unchanged.
- Existing repository/workflow routing and matching request IDs retained.
- Cloud request/result path previously verified live. Revised response instructions checked locally; portable download does not update an installed copy automatically. Claude connectivity remains unverified.

## Future updates

| Change | Example |
|---|---|
| Small correction or wording fix | 0.1.0 → 0.1.1 |
| Compatible new feature | 0.1.0 → 0.2.0 |
| First stable release | 1.0.0 |
| Incompatible change after stable release | 1.x.x → 2.0.0 |

Keep previously released versioned archives. Do not replace a versioned release with different bytes. When the underlying scanner is updated, document its version separately and retest before claiming unchanged compatibility.
