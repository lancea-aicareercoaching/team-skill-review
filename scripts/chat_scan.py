"""Bounded public-GitHub skill scan worker. Candidate instructions never execute."""
from __future__ import annotations
import base64
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request

MAX_REQUEST = 4096
MAX_RESPONSE = 4 * 1024 * 1024
MAX_BLOB = 1024 * 1024
MAX_FILES = 150
MAX_TOTAL = 10 * 1024 * 1024
SCANNER_COMMIT = "a09091e0ebf6c96ff327457529d7b0d372125884"
ID_RE = re.compile(r"[a-z0-9][a-z0-9-]{7,63}")
NAME_RE = re.compile(r"[A-Za-z0-9_.-]{1,100}")

def request_id(path):
    p = PurePosixPath(path)
    if p.parent != PurePosixPath(".scan-requests") or p.suffix != ".json" or not ID_RE.fullmatch(p.stem):
        raise ValueError("Request must be .scan-requests/<unique-lowercase-id>.json")
    return p.stem

def validate_request(data):
    if not isinstance(data, dict) or set(data) - {"repository_url", "ref", "skill_path"}:
        raise ValueError("Only repository_url, ref, and skill_path are accepted")
    url = data.get("repository_url")
    if not isinstance(url, str):
        raise ValueError("repository_url is required")
    u = urllib.parse.urlsplit(url)
    if u.scheme != "https" or u.netloc != "github.com" or u.query or u.fragment:
        raise ValueError("Use a public https://github.com/owner/repo URL without credentials or query")
    parts = u.path.strip("/").split("/")
    if len(parts) != 2:
        raise ValueError("Use the repository root URL; provide the skill folder separately")
    owner, repo = parts
    if repo.endswith(".git"):
        repo = repo[:-4]
    if any(not NAME_RE.fullmatch(x) or x in {".", ".."} for x in (owner, repo)):
        raise ValueError("Invalid GitHub owner or repository")
    ref = data.get("ref", "HEAD")
    if not isinstance(ref, str) or not 1 <= len(ref) <= 200 or any(ord(c) < 32 for c in ref):
        raise ValueError("Invalid version/ref")
    folder = data.get("skill_path")
    if folder is not None:
        if not isinstance(folder, str) or len(folder) > 500:
            raise ValueError("Invalid skill_path")
        validate_path(folder, allow_root=True)
    return {"repository_url": f"https://github.com/{owner}/{repo}", "repository": f"{owner}/{repo}", "ref": ref, "skill_path": folder}

def validate_path(value, allow_root=False):
    if allow_root and value == ".":
        return
    if not value or value.startswith("/") or "\\" in value or ":" in value or any(ord(c) < 32 for c in value):
        raise ValueError("Unsafe file path")
    if any(x in {"", ".", "..", ".git"} for x in value.split("/")):
        raise ValueError("Unsafe file path")

def read_bounded(response, limit):
    content = response.read(limit + 1)
    if len(content) > limit:
        raise ValueError("GitHub response exceeds configured size limit")
    return content

def github_api(endpoint, token=None, method="GET", data=None):
    # endpoint is constructed from validated repo/ref/blob identifiers, never a user URL.
    if not endpoint.startswith("/repos/") or any(ord(c) < 32 for c in endpoint):
        raise ValueError("Invalid API endpoint")
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "team-skill-review", "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    payload = None if data is None else json.dumps(data).encode()
    req = urllib.request.Request("https://api.github.com" + endpoint, headers=headers, data=payload, method=method)
    # GitHub API repo/blob/commit endpoints should not redirect to another host.
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None
    try:
        with urllib.request.build_opener(NoRedirect()).open(req, timeout=30) as response:
            return json.loads(read_bounded(response, MAX_RESPONSE))
    except urllib.error.HTTPError as exc:
        raise ValueError(f"GitHub API HTTP {exc.code}; check repository visibility, ref, permissions, or rate limit") from None

def source_tree(request, api=github_api):
    repo = request["repository"]
    # The caller provides only public-source access; validate public visibility before acquisition.
    commit = api(f"/repos/{repo}/commits/{urllib.parse.quote(request['ref'], safe='')}")
    sha = commit["sha"]
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise ValueError("Unexpected source commit")
    tree_sha = commit["commit"]["tree"]["sha"]
    if not re.fullmatch(r"[0-9a-f]{40}", tree_sha):
        raise ValueError("Unexpected source tree")
    tree = api(f"/repos/{repo}/git/trees/{tree_sha}?recursive=1")
    if tree.get("truncated"):
        raise ValueError("Repository tree is truncated; cannot claim complete skill discovery")
    entries = tree.get("tree")
    if not isinstance(entries, list) or len(entries) > 20000:
        raise ValueError("Repository exceeds discovery limit")
    skills = []
    for e in entries:
        if e.get("type") == "blob" and e.get("mode") in {"100644", "100755"} and PurePosixPath(e["path"]).name == "SKILL.md":
            folder = str(PurePosixPath(e["path"]).parent)
            validate_path(folder, allow_root=True)
            skills.append(folder)
    return sha, entries, sorted(set(skills))

def repository_kind(entries, skills):
    """Classify broad repository shape; not a security verdict."""
    paths = {e.get("path", "") for e in entries if e.get("type") == "blob"}
    program_markers = {"pyproject.toml", "setup.py", "package.json", "Cargo.toml",
                       "go.mod", "pom.xml", "requirements.txt", "Dockerfile",
                       "compose.yml", "docker-compose.yml"}
    has_program = bool(paths & program_markers)
    if has_program and skills:
        return "software_program_with_skills"
    if has_program:
        return "software_program"
    if skills:
        return "ai_skill"
    return "undetermined"


def select_skill(requested, skills):
    if not skills:
        raise ValueError("No regular SKILL.md files found; this is not a general repository audit")
    if requested is None:
        return skills[0] if len(skills) == 1 else None
    if requested not in skills:
        raise ValueError("Selected folder does not contain a discovered regular SKILL.md")
    return requested

def materialize(repo, entries, folder, target, api=github_api):
    prefix = "" if folder == "." else folder + "/"
    selected = [e for e in entries if e["path"].startswith(prefix) and e.get("type") in {"blob", "commit"}]
    if not selected or len(selected) > MAX_FILES:
        raise ValueError("Selected skill exceeds file-count limit")
    total = sum(e.get("size", 0) for e in selected)
    if total > MAX_TOTAL:
        raise ValueError("Selected skill exceeds byte limit")
    manifest = []
    target.mkdir(parents=True, exist_ok=False)
    for e in selected:
        rel = e["path"][len(prefix):]
        validate_path(rel)
        if e.get("type") != "blob" or e.get("mode") not in {"100644", "100755"}:
            raise ValueError("Selected skill contains a symlink or submodule; not supported")
        size = e.get("size")
        if not isinstance(size, int) or size < 0 or size > MAX_BLOB:
            raise ValueError("Selected file exceeds scan acquisition limit")
        sha = e["sha"]
        if not re.fullmatch(r"[0-9a-f]{40}", sha):
            raise ValueError("Unexpected blob identifier")
        blob = api(f"/repos/{repo}/git/blobs/{sha}")
        if blob.get("encoding") != "base64":
            raise ValueError("Unsupported GitHub blob encoding")
        data = base64.b64decode(blob["content"], validate=False)
        if len(data) != size or len(data) > MAX_BLOB:
            raise ValueError("Blob size mismatch")
        actual = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
        if actual != sha:
            raise ValueError("Blob integrity mismatch")
        output = target.joinpath(*PurePosixPath(rel).parts)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(data)
        manifest.append({"path": rel, "bytes": len(data), "git_blob": sha, "sha256": hashlib.sha256(data).hexdigest()})
    return manifest

def classify(report, exit_code):
    complete = report.get("analysis_completeness", {})
    if report.get("execution_successful") is not True or exit_code not in (0, 1):
        return "scan_error"
    if complete.get("is_complete") is not True:
        return "incomplete"
    assessment = report.get("risk_assessment", {})
    if report.get("issues") or report.get("suppressed_count", 0) or assessment.get("recommendation") != "SAFE":
        return "needs_review"
    if exit_code != 0:
        return "needs_review"
    return "no_findings"

def run_request(request_path, output_root=Path("chat-results"), api=github_api, scanner="skillspector"):
    rid = request_id(request_path)
    out = output_root / rid
    out.mkdir(parents=True, exist_ok=True)
    result = {"schema_version": 1, "request_id": rid, "state": "scan_error",
              "scan_mode": "static_only", "approval": "not_granted",
              "scanner_commit": SCANNER_COMMIT,
              "run_url": os.getenv("GITHUB_SERVER_URL", "https://github.com") + "/" + os.getenv("GITHUB_REPOSITORY", "lancea-aicareercoaching/team-skill-review") + "/actions/runs/" + os.getenv("GITHUB_RUN_ID", "local"),
              "limitations": ["Not a whole-repository security audit.", "Candidate code and instructions are not activated.", "External dependencies and AI semantic analysis are not requested.", "No installation or rollout approval is granted."]}
    try:
        raw = Path(request_path).read_bytes()
        if len(raw) > MAX_REQUEST:
            raise ValueError("Request exceeds size limit")
        request = validate_request(json.loads(raw))
        result.update({k: request[k] for k in ("repository_url", "ref")})
        source_api = api
        read_token = os.getenv("SOURCE_READ_TOKEN")
        if api is github_api and read_token:
            def source_api(endpoint):
                return github_api(endpoint, token=read_token)
        visibility = source_api(f"/repos/{request['repository']}")
        if visibility.get("private") is not False:
            raise ValueError("Only public candidate repositories are supported")
        sha, entries, skills = source_tree(request, source_api)
        result["source_commit"] = sha
        kind = repository_kind(entries, skills)
        result["repository_kind"] = kind
        result["skill_count"] = len(skills)
        if kind in {"software_program", "software_program_with_skills"} and request["skill_path"] is None:
            # Do not silently substitute a SKILL.md scan for a program security audit.
            result.update(state="needs_target_selection", target_kind="software_program",
                          skills=skills[:30], choices_truncated=len(skills) > 30,
                          explanation="This repository contains software. An AI skill scan would not audit the full application. Choose a specific skill_path to scan just that skill, or use a separately approved program security workflow.")
            selected = None
        elif not skills:
            result.update(state="program_review_required", target_kind="software_program",
                          explanation="No regular SKILL.md was found; the current SkillSpector workflow cannot audit the full program.")
            selected = None
        else:
            selected = select_skill(request["skill_path"], skills)
            if selected is None:
                result.update(state="needs_selection", target_kind="ai_skill",
                              skills=skills[:30], skill_count=len(skills), choices_truncated=len(skills) > 30)
        if selected is not None:
            result["target_kind"] = "ai_skill"
            result["skill_path"] = selected
            with tempfile.TemporaryDirectory(prefix="skill-review-") as temp:
                folder = Path(temp) / "candidate"
                result["files"] = materialize(request["repository"], entries, selected, folder, source_api)
                report_path = (out / "report.json").resolve()
                scanner_env = {k: v for k, v in os.environ.items() if k not in
                               {"SOURCE_READ_TOKEN", "GH_TOKEN", "GITHUB_TOKEN"}}
                proc = subprocess.run([scanner, "scan", str(folder), "--no-llm", "--fail-on-findings",
                                       "--fail-on-incomplete", "--format", "json", "--output", str(report_path)],
                                      capture_output=True, timeout=600, env=scanner_env)
                result["scanner_exit_code"] = proc.returncode
                if not report_path.is_file() or report_path.stat().st_size > 2 * MAX_RESPONSE:
                    raise ValueError("Scanner did not produce a bounded report")
                report = json.loads(report_path.read_text(encoding="utf-8"))
                # Keep a bounded JSON evidence file that the chat connector can fetch directly.
                result["state"] = classify(report, proc.returncode)
                result["risk_assessment"] = report.get("risk_assessment")
                result["inspection"] = {k: report.get("analysis_completeness", {}).get(k) for k in
                                        ("status", "coverage_percent", "is_complete", "total_components", "fully_inspected_files", "partially_inspected_files")}
                result["finding_count"] = len(report.get("issues", []))
                result["report_path"] = f".scan-results/{rid}/report.json"
                result["scanner_version"] = report.get("metadata", {}).get("skillspector_version")
    except (ValueError, KeyError, TypeError, OSError, subprocess.SubprocessError) as exc:
        result["state"] = "scan_error"
        result["error"] = str(exc)[:1200]
    (out / "result.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return result

def select_changed_request():
    sha = os.environ["GITHUB_SHA"]
    raw = subprocess.check_output(["git", "diff-tree", "--no-commit-id", "--name-only", "--diff-filter=A", "-r", sha], text=True)
    paths = [p for p in raw.splitlines() if p.startswith(".scan-requests/") and p.endswith(".json")]
    if len(paths) != 1:
        raise ValueError("Create exactly one new request file per commit; use a new id for each scan")
    rid = request_id(paths[0])
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as f:
        f.write(f"request_path={paths[0]}\nrequest_id={rid}\n")
    return paths[0]

def publish(folder, api=github_api):
    # Fresh runner: do not load candidate code. Write only this request's two JSON files.
    rid = Path(folder).name
    if not ID_RE.fullmatch(rid):
        raise ValueError("Invalid result identifier")
    repo = os.environ["GITHUB_REPOSITORY"]
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
        raise ValueError("Invalid destination")
    token = os.environ["GH_TOKEN"]
    status = json.loads((Path(folder) / "result.json").read_text(encoding="utf-8"))
    if status.get("request_id") != rid:
        raise ValueError("Result does not match request")
    for name in ("report.json", "decision.md", "result.json"):
        file = Path(folder) / name
        if not file.exists():
            continue
        if file.is_symlink() or not file.is_file() or file.stat().st_size > 2 * MAX_RESPONSE:
            raise ValueError("Unsafe result artifact")
        content = file.read_bytes()
        if name.endswith(".json"):
            json.loads(content)
        elif name == "decision.md":
            if len(content) > 16384:
                raise ValueError("Decision note too large")
            content.decode("utf-8")
        endpoint = f"/repos/{repo}/contents/.scan-results/{rid}/{name}"
        # Create only. Existing results must not silently be overwritten.
        api(endpoint, token=token, method="PUT", data={"message": f"Record scan {rid}: {name}", "branch": "main",
                                                     "content": base64.b64encode(content).decode()})
    if status.get("target_kind") == "software_program":
        try:
            publish_program_cache(status, api=api)
        except (ValueError, OSError) as exc:
            print(f"Warning: scan result published but reusable index was not saved: {exc}", file=sys.stderr)



def publish_program_cache(status, api=github_api):
    """Register completed immutable-source result for reuse by all team members.
    Fresh scans still publish their own reports; cache aliases never overwrite reviews.
    """
    if status.get("target_kind") != "software_program" or status.get("pipeline_version") != "program-v2":
        return
    if status.get("recommendation") not in {"Recommended to install", "Do not install yet"}:
        return
    source = status.get("repository_url", "")
    parsed = urllib.parse.urlsplit(source)
    parts = parsed.path.strip("/").split("/")
    commit = status.get("source_commit", "")
    if parsed.scheme != "https" or parsed.netloc != "github.com" or len(parts) != 2 or any(
        not NAME_RE.fullmatch(p) or p in {".", ".."} for p in parts
    ) or not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("Cannot cache an unverified program source")
    key = f".scan-cache/program-v2/{parts[0]}/{parts[1]}/{commit}.json"
    entry = {"repository_url": source, "source_commit": commit, "pipeline_version": "program-v2",
             "request_id": status["request_id"], "recommendation": status["recommendation"],
             "result_path": f".scan-results/{status['request_id']}/result.json",
             "report_path": f".scan-results/{status['request_id']}/report.json"}
    destination = os.environ["GITHUB_REPOSITORY"]
    endpoint = f"/repos/{destination}/contents/{key}"
    payload = {"message": f"Index reusable program scan {status['request_id']}",
               "branch": "main", "content": base64.b64encode(
                   (json.dumps(entry, indent=2) + "\n").encode()).decode()}
    # A previously completed identical source/pipeline has a valid reusable entry.
    # Never replace it automatically. "Fresh" scans remain separate immutable results.
    try:
        existing = api(endpoint, token=os.environ["GH_TOKEN"])
        if existing.get("type") == "file":
            print(f"Reusable program scan index exists: {key}")
            return
    except ValueError as exc:
        if "HTTP 404" not in str(exc):
            raise
    api(endpoint, token=os.environ["GH_TOKEN"], method="PUT", data=payload)
    print(f"Saved reusable scan index: {key}")

if __name__ == "__main__":
    if sys.argv[1] == "select":
        select_changed_request()
    elif sys.argv[1] == "scan":
        run_request(sys.argv[2])
    elif sys.argv[1] == "publish":
        publish(sys.argv[2])
    else:
        raise SystemExit("Expected select, scan, or publish")
