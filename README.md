# Team Skill Review

Shared security reports, review status, and instructions for selected GitHub skills.

## Current status

- Scanner: NVIDIA SkillSpector 2.12.0, pinned to a recorded source revision.
- Mode: static analysis only (`--no-llm`); AI analysis is disabled.
- Cloud scanning: verified through GitHub Actions, including downloadable reports.
- Upload action: updated to v7.0.0; the Node.js 20 warning was absent in run #2.
- Teach Me: source reviewed for controlled testing; cloud static scan found no issues with complete configured coverage. A source package and installation guide are prepared; organization rollout is not approved.
- Teach Me ChatGPT installation, basic interactive teaching, and explicitly requested checklist create/update/readback: observed in the current account. Automatic saving and fresh-conversation recovery are not verified.
- Claude functionality: not yet tested. Chief of Staff remains under review.
- Access from another team member's account: not independently verified.

## Scan a skill from chat

The chat-to-cloud connection has been verified in ChatGPT: a request created in conversation triggered GitHub Actions, and its matching Teach Me report was retrieved in that conversation. The first live scan reported 0 findings with complete configured static inspection.

Ask the assistant: **Scan this GitHub skill: [link].** The assistant needs a GitHub connection with file creation and read access to this repository. Follow [the chat scan protocol](docs/CHAT-SCAN-PROTOCOL.md) for request submission, result retrieval, and interpretation. A reusable installed chat skill is still pending; this documentation does not install one. Claude connectivity is not yet tested.

The new workflow accepts public repository URLs and an optional skill folder and version. Multiple discovered skills require a selection. It is a skill scan, not a whole-repository audit. JSON results are retained in `.scan-results/<request-id>/` and can be retrieved directly through the GitHub connection.

## Teach Me download and installation

See [Teach Me: download, install, and test](docs/TEACH-ME-GUIDE.md) for the recorded source version, source download, MIT license, ChatGPT route, proposed Claude route, and exact test limits.

The recorded [learning checklist](tests/teach-me-learning-checklist.md) contains observed learner answers and storage-test results. The [Teach Me cloud report](reports/teach-me-cloud-2026-11-21.json) is retained in this repository in addition to expiring workflow artifacts.

## Run a cloud scan from your browser

1. Sign into a GitHub account with write access to this private repository.
2. Open [Actions](https://github.com/lancea-aicareercoaching/team-skill-review/actions).
3. Select **Scan selected skills** in the left sidebar.
4. Click **Run workflow**, select **main**, and click the green **Run workflow** button.
5. Open the new run and wait for both jobs to finish.
6. Select **Summary**, then scroll to **Artifacts**.
7. Download `static-review-chief-of-staff` and `static-review-agent-protocol`.
8. Extract each ZIP into a separate folder. Each contains `report.json` and `provenance.txt` when scanning and upload complete.

Your computer does not need to stay on after GitHub accepts the run. No local Python or PowerShell is required to start these cloud scans.

To test updated workflow code, start a new run from **main**. Re-running an older run uses that run's earlier workflow revision.

### Scope and usage

**Scan selected skills** scans Chief of Staff and Agent Protocol at their fixed source commit below. **Scan Teach Me** scans Teach Me at commit `10fcc17a274432a871b39fd4b4ec516ea9bf10bb`; download its artifact named `static-review-teach-me`. These two older workflows remain fixed examples. The new **Scan skill from chat** workflow accepts new public repository targets. No workflow activates skills or automatically approves downloads.

Runs use the repository owner's GitHub Actions allowance. Each of the two jobs has a 20-minute timeout. Check included compute and artifact-storage usage before repeated runs; do not enable paid usage without the agreed business approval.

## Understand red results

The workflow uses `--fail-on-findings` and `--fail-on-incomplete`.

- **Exit code 1:** the scan may have completed, but findings or incomplete inspection failed the strict checks. Inspect the report.
- **Exit code 2 or an installation/download error:** investigate the execution problem; do not treat it as a completed security review.
- A successful upload step means the artifact was uploaded, not that the skill passed review.
- A green run or a scanner label of SAFE is not proof of safety or installation approval.

In `report.json`, check `execution_successful`, `risk_assessment`, `issues`, and `analysis_completeness`. Confirm the source and scanner revisions in `provenance.txt`.

The report-preservation step runs even when scan checks fail. If a failure occurs before report creation, an artifact may contain provenance only, or no artifact may exist. Verify that `report.json` is present and valid.

## Report retention

Workflow artifacts are retained for **7 days**, subject to repository policies. Download and preserve reports and provenance needed for the review before expiry. Save later runs under distinct names or folders so earlier evidence is retained.

The `reports/` folder holds the original local scan reports plus the explicitly retained Teach Me cloud report. Other cloud-run artifacts are separate and are not automatically committed to this repository.

## Candidate under review

- Source: https://github.com/alirezarezvani/claude-skills
- Source commit: `f8593c4941210a621a6629ce1da9e07897976d5f`
- Candidate: `c-level-advisor/skills/chief-of-staff`
- Dependency: `c-level-advisor/skills/agent-protocol`
- Scanner commit: `a09091e0ebf6c96ff327457529d7b0d372125884`

| Component | Result from reviewed reports | Static inspection coverage |
|---|---|---|
| Chief of Staff | LOW, 6/100; scanner label SAFE; one MEDIUM finding | 100% within configured scope |
| Agent Protocol | LOW, 6/100; scanner label CAUTION; one MEDIUM finding | 50%, partial |

Both scans flagged decision-file persistence. Reviewed excerpts describe saved decision records. Agent Protocol also encountered a tool-misuse parser limitation and a missing runtime decision-log reference. Other advisor components and runtime behavior have not been verified.

**Status: UNDER REVIEW. Not approved for installation or team use.**

Local and first-run cloud reports were reviewed. Run #2 verified the updated upload action and artifact availability; its report contents have not been separately reviewed.

## Review a new candidate

1. Identify the exact skill, source version, intended AI environment, and dependencies.
2. Keep downloaded candidates separate from active skills.
3. Configure the selected source and scope, then scan before activation.
4. Record findings, incomplete checks, and manual review conclusions.
5. Resolve or explicitly disposition findings and record the review decision.
6. For cleared candidates, prepare versioned downloads with attribution, license notices, and installation instructions.
7. Test functionality in the intended environment and record what was actually verified.

Use the new chat scan protocol to submit a different public skill without editing workflow code. The original manual workflows remain available for their fixed candidates.

## Use reviewed skills

Downloading files does not install a skill. Follow each cleared candidate's environment-specific instructions. Compatibility with ChatGPT, Claude chat, and Claude Code must be tested separately.

The request-file connection now lets an authorized assistant submit a scan and retrieve its results. It has been verified in ChatGPT. Each assistant/account still needs suitable GitHub tools and access; a skill alone does not grant those permissions. Claude remains unverified.

## Repository contents

- `README.md`: browser instructions and current workflow status.
- `REVIEW-STATUS.md`: initial candidate review and outstanding requirements.
- `reports/`: local JSON reports and the retained Teach Me cloud report.
- `docs/TEACH-ME-GUIDE.md`: download, installation, and test instructions.
- `downloads/`: versioned Teach Me source ZIP and checksums.
- `packages/teach-me/`: unchanged upstream skill and MIT license.
- `tests/`: observed learning progress and checklist-storage test.
- `.github/workflows/chat-scan.yml`: request-triggered cloud skill scanner and result publisher.
- `scripts/chat_scan.py`: bounded source acquisition, scan handling, and JSON publication.
- `docs/CHAT-SCAN-PROTOCOL.md`: assistant procedure and connection requirements.
- `.scan-requests/` and `.scan-results/`: correlated requests and retained evidence.
- `.github/workflows/scan-skills.yml`: manually triggered cloud scanner.
- `.github/workflows/scan-teach-me.yml`: manually triggered Teach Me scanner.

## Handling files

Keep this repository private. Do not upload credentials, private business records, or client information. Preserve copyright and license notices when redistributing source files. This repository does not replace the business knowledge base.
