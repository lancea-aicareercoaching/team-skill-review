# Teach Me: download, install, and test

## Review status

Reviewed source: https://github.com/doodledood/manifest-dev

Commit: `10fcc17a274432a871b39fd4b4ec516ea9bf10bb`

Source file: `claude-plugins/manifest-dev-tools/skills/teach-me/SKILL.md`

SkillSpector 2.12.0 static cloud scan: score 0/100, no findings, one file fully inspected, 100% configured coverage. AI analysis and dependency-content inspection were not enabled. No executable scripts were present. This is a bounded review for controlled testing, not a guarantee of safety or an owner-approved organization rollout.

Original report: [teach-me-cloud-2026-11-21.json](../reports/teach-me-cloud-2026-11-21.json).

The skill requests a running Markdown learning checklist. Use a separate practice file and fictional or non-sensitive material for tests. Permission to install it is not permission to edit business authorities or unrelated files.

## Files to download

Open `downloads/teach-me-10fcc17a.zip` in this repository and use GitHub's download button. Extract it to inspect its `teach-me/SKILL.md` and `teach-me/LICENSE`. Keep the full MIT notice when redistributing.

The skill file is an unchanged copy of the reviewed upstream version. Its Git blob SHA is `cd7957564fbcff050917e606123ca8c6a78e2673`. Package SHA-256 hashes are in `downloads/teach-me-10fcc17a.sha256.txt`.

The source folder is also available at [packages/teach-me](../packages/teach-me). Downloading the whole repository ZIP is not the same as downloading the skill package.

## ChatGPT: observed installation route

1. In an account/session that supports personal skills, invoke Skill Creator.
2. Supply the versioned source link or the downloaded skill package. Request installation of Teach Me while preserving its teaching instructions and MIT license.
3. Confirm that Teach Me appears in the account's skills and can be selected or loaded. Refresh the Skills page if needed.
4. Start a practice chat, explicitly select Teach Me, and run the tests below.

This route worked in the current user's account after installation in a separate chat. An earlier Work session could not complete installation because of environment write and connectivity restrictions. The installed teaching body was read and matched the upstream instructions. Installation moved the top-level `argument-hint` field under `metadata`; this is a packaging difference, so the original scan is not a byte-for-byte scan of the installed edition. Retain the original source version and record any further installer changes.

Skills availability and installation permissions may differ by account. Do not treat past success as proof of access for another account.

## Claude chat: documented route, not yet tested

1. Check Settings > Capabilities for code execution and file creation (or Create and edit files).
2. Open Customize > Skills, then the add/create control and Upload a skill.
3. Upload the ZIP containing the `teach-me` folder and enable the skill.
4. Confirm it loaded, then run the same practice tests below.

Check the current official instructions if labels differ: https://support.claude.com/en/articles/12512180-use-skills-in-claude

These instructions cover Claude chat. They do not establish Claude Code compatibility or account-wide/team sharing. Installing for yourself does not automatically install for teammates. Claude installation, activation, saved-file behavior, and functionality remain unverified in this project.

## Practice tests

Use non-sensitive practice material. Example request:

> Use Teach Me to help me understand this GitHub scan workflow. First check what I already understand, teach one gap at a time, and verify understanding before advancing. Save progress only to a separate practice checklist. Do not access or change business files. Tell me where the checklist is saved and whether it will remain available in another conversation.

Check and record:

- The installed skill was actually loaded; a similar generic answer alone does not establish activation.
- It asks for starting understanding before giving a long explanation.
- It explains a gap and asks a follow-up rather than accepting "okay" as proof of mastery.
- It recognizes that a red strict check may mean findings, not a crash.
- It recognizes that zero findings does not guarantee safety.
- It creates a separate Markdown checklist, reopens it, updates observed progress, and verifies readback.
- It identifies storage and cross-conversation limits honestly.

## Observed results and outstanding work

| Check | ChatGPT | Claude |
|---|---|---|
| Installation | Available and instructions loaded in this account | Not tested |
| Basic interactive teaching | Observed after installed instructions were loaded | Not tested |
| Understanding checks | Learner correctly identified review findings and clean-scan limits | Not tested |
| Explicitly requested checklist create/update/readback | Verified in this conversation's repository working copy | Not tested |
| Automatic checklist saving without an explicit request | Not tested | Not tested |
| Fresh-conversation recovery | Not tested | Not tested |
| Another team member's access | Deferred; not verified | Deferred; not verified |

The initial pre-installation conversation was a simulation and is not counted as installation evidence. The checklist test does not prove automatic saving or automatic reloading in future chats. See [learning checklist](../tests/teach-me-learning-checklist.md).

## Operating the scans

For Teach Me, use Actions > Scan Teach Me > Run workflow > main. Results appear under that run's Summary > Artifacts as `static-review-teach-me`. Artifacts expire after seven days; preserve evidence needed for review in the repository. The current workflow scans this fixed source version, not arbitrary GitHub links.

The package is prepared locally until its files are uploaded to the shared repository. Verify download from the repository before reporting distribution complete.
