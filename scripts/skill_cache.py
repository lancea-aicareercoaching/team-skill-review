"""Index completed static AI-skill scans for exact-source team-wide reuse.

This is not installation approval. Missing/errored/incomplete scans are not cached.
"""
import base64
import json
import os
from pathlib import Path
import re
import sys
import urllib.parse

from chat_scan import NAME_RE, SCANNER_COMMIT, github_api, validate_path

def main(folder):
    status = json.loads((Path(folder) / "result.json").read_text(encoding="utf-8"))
    if status.get("target_kind") != "ai_skill" or status.get("state") not in {"no_findings","needs_review"}:
        print("Nothing eligible to index")
        return
    url = urllib.parse.urlsplit(status.get("repository_url",""))
    parts = url.path.strip("/").split("/")
    commit = status.get("source_commit","")
    skill = status.get("skill_path","")
    scanner = status.get("scanner_commit","")
    if (url.scheme != "https" or url.netloc != "github.com" or len(parts) != 2 or
        any(not NAME_RE.fullmatch(p) or p in {".",".."} for p in parts) or
        not re.fullmatch("[0-9a-f]{40}",commit) or scanner != SCANNER_COMMIT):
        raise ValueError("Unverified source for skill cache")
    validate_path(skill, allow_root=True)
    segment = "_root" if skill == "." else skill
    key = f".scan-cache/skill-v1/{parts[0]}/{parts[1]}/{commit}/{scanner}/{segment}/entry.json"
    rid = status["request_id"]
    entry = {"repository_url":status["repository_url"],"source_commit":commit,"scanner_commit":scanner,
        "skill_path":skill,"request_id":rid,"state":status["state"],
        "result_path":f".scan-results/{rid}/result.json","report_path":f".scan-results/{rid}/report.json"}
    endpoint=f"/repos/{os.environ['GITHUB_REPOSITORY']}/contents/{key}"
    token=os.environ["GH_TOKEN"]
    try:
        prior=github_api(endpoint,token=token)
        if prior.get("type") == "file":
            print("Previously indexed exact skill version exists")
            return
    except ValueError as exc:
        if "HTTP 404" not in str(exc):
            raise
    github_api(endpoint,token=token,method="PUT",data={
        "message":f"Index reusable AI skill scan {rid}","branch":"main",
        "content":base64.b64encode((json.dumps(entry,indent=2)+"\n").encode()).decode()
    })
    print("Indexed completed skill scan")

if __name__=="__main__":
    main(sys.argv[1])
