"""Read-only SKILL.md instruction checks bundled with an approved program scan.

Only SKILL.md files from the pinned public candidate checkout are copied.
Candidate instructions, build steps, scripts, and package install hooks never run.
"""
from __future__ import annotations
import hashlib, json, os, pathlib, re, subprocess, sys, tempfile

ROOT=pathlib.Path("program-results")
MAX_SKILLS=12
MAX_SKILL_BYTES=1024*1024
EXCLUDED={".git",".venv","venv","node_modules","dist","build","__pycache__"}

def scan():
    rid=os.environ["REQUEST_ID"]
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{7,63}",rid):
        raise ValueError("Unsafe request ID")
    candidate=pathlib.Path("candidate")
    out=ROOT/rid
    out.mkdir(parents=True,exist_ok=True)
    discovered=sorted(p for p in candidate.rglob("SKILL.md") if
                      not any(part in EXCLUDED for part in p.relative_to(candidate).parts))
    record={"status":"none_found" if not discovered else "complete",
            "discovered_count":len(discovered),"scan_limit":MAX_SKILLS,
            "selected_count":min(len(discovered),MAX_SKILLS),
            "scope":"SKILL.md instruction file only; adjacent scripts/dependencies not covered",
            "results":[]}
    if len(discovered)>MAX_SKILLS:
        record["status"]="partial"
    for path in discovered[:MAX_SKILLS]:
        relative=path.relative_to(candidate).as_posix()
        item={"path":relative,"status":"incomplete","findings":None}
        record["results"].append(item)
        try:
            if path.is_symlink() or not path.is_file() or path.stat().st_size>MAX_SKILL_BYTES:
                item["error"]="Symlink, missing, or oversized SKILL.md"
                record["status"]="partial"
                continue
            content=path.read_bytes()
            item["sha256"]=hashlib.sha256(content).hexdigest()
            with tempfile.TemporaryDirectory(prefix="embedded-skill-") as temp:
                directory=pathlib.Path(temp)
                (directory/"SKILL.md").write_bytes(content)
                output=directory/"report.json"
                p=subprocess.run(["skillspector","scan",str(directory),"--no-llm",
                                  "--format","json","--output",str(output)],
                                 capture_output=True,timeout=120)
                if p.returncode not in (0,1) or not output.exists():
                    item["error"]="Static analyzer failed or omitted report"
                    record["status"]="partial"
                    continue
                detail=json.loads(output.read_text())
                complete=detail.get("analysis_completeness",{})
                if detail.get("execution_successful") is not True or complete.get("is_complete") is not True:
                    item["status"]="incomplete"
                    record["status"]="partial"
                else:
                    item["status"]="complete"
                assessment=detail.get("risk_assessment",{})
                item["risk_score"]=assessment.get("score")
                item["risk_severity"]=assessment.get("severity")
                item["findings"]=len(detail.get("issues",[]))
                issues = detail.get("issues", [])
                item["issues"] = []
                used = 0
                for v in issues:
                    size = len(json.dumps(v, ensure_ascii=True).encode())
                    if len(item["issues"]) >= 100 or used + size > 24000:
                        continue
                    item["issues"].append(v)
                    used += size
                item["issues_included"] = len(item["issues"])
                item["issues_truncated"] = len(item["issues"]) != len(issues)
                item["analysis_completeness"] = {k: complete.get(k) for k in ("status", "is_complete", "coverage_percent")}
                item["risk_recommendation"] = assessment.get("recommendation")
        except (OSError, ValueError, json.JSONDecodeError, subprocess.TimeoutExpired) as exc:
            item["error"]=str(exc)[:250]
            record["status"]="partial"
    (out/"skills.json").write_text(json.dumps(record,indent=2)+"\n")
    print("Scanned",len(record["results"]),"of",len(discovered),"SKILL.md files; state:",record["status"])
if __name__=="__main__":
    scan()
