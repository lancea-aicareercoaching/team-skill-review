"""Automatic bounded security triage, reporting and binary advisory verdict.

No candidate programs, skills, scripts, or install commands are executed.
Recommendations are evidence-limited; they never authorize installation.
"""
import collections
import json
import os
from pathlib import Path

def analyze(rid):
    folder = Path("program-results") / rid
    summary_file = folder / "result.json"
    report_file = folder / "report.json"
    result = json.loads(summary_file.read_text())
    report = json.loads(report_file.read_text())
    distinct_locations = set()
    codeql_examples = []
    severities = collections.Counter()
    for path in (sorted((folder / "sarif").rglob("*.sarif")) if (folder / "sarif").exists() and report.get("codeql",{}).get("status") == "success" else []):
        data = json.loads(path.read_text())
        for run in data.get("runs", []):
            rules = {r.get("id"): r for r in run.get("tool", {}).get("driver", {}).get("rules", [])}
            for issue in run.get("results", []):
                rule = issue.get("ruleId", "unknown")
                where = (issue.get("locations") or [{}])[0].get("physicalLocation", {})
                loc = where.get("artifactLocation", {}).get("uri", "")
                line = where.get("region", {}).get("startLine")
                fingerprint = (rule, loc, line)
                if fingerprint in distinct_locations:
                    continue
                distinct_locations.add(fingerprint)
                sev = str(issue.get("level") or rules.get(rule, {}).get("defaultConfiguration", {}).get("level") or "unknown")
                severities[sev] += 1
                metadata = rules.get(rule, {}).get("properties", {})
                raw_score = metadata.get("security-severity")
                try:
                    score = float(raw_score)
                    if not 0 <= score <= 10:
                        score = None
                except (TypeError, ValueError):
                    score = None
                codeql_examples.append({"rule":rule,"level":sev,"file":loc,"line":line,
                    "security_severity":score,
                    "message":str(issue.get("message",{}).get("text",""))[:500]})
    codeql_examples.sort(key=lambda x: (x['security_severity'] is None, -(x['security_severity'] or 0), x['rule'], x['file'], x['line'] or 0))
    vulnerabilities = collections.defaultdict(set)
    osv_evidence = []
    osv_file = folder / "osv.json"
    if osv_file.exists() and report.get("osv",{}).get("status") in ("success","findings"):
        osv = json.loads(osv_file.read_text())
        for group in osv.get("results", []):
            for package in group.get("packages", []):
                info = package.get("package", {})
                package_name = str(info.get("name") or info.get("package_name") or "unknown")
                for match in package.get("vulnerabilities", []):
                    vulnerabilities[str(match.get("id","unknown"))].add(package_name)
                    osv_evidence.append({"id":str(match.get("id","unknown")),
                        "package":package_name,"version":info.get("version"),
                        "ecosystem":info.get("ecosystem"),"inventory":group.get("source",{}),
                        "aliases":match.get("aliases",[]),"severity":match.get("severity",[]),
                        "affected":match.get("affected",[])})
    embedded = report.get("embedded_skills", {})
    embedded_hits = sum(x.get("findings") or 0 for x in embedded.get("results", []))
    complete = (report.get("codeql",{}).get("status") == "success"
        and report.get("codeql",{}).get("sarif_findings") is not None
        and report.get("osv",{}).get("status") in ("success","findings")
        and report.get("osv",{}).get("vulnerabilities") is not None
        and embedded.get("status") in ("complete","none_found"))
    unresolved = bool(report.get("codeql",{}).get("sarif_findings") or
        report.get("osv",{}).get("vulnerabilities") or embedded_hits)
    if not complete:
        verdict = "Do not install yet"
        reason = "At least one scanner or its evidence is incomplete."
    elif unresolved:
        verdict = "Do not install yet"
        reason = "Automated precaution: findings have not been adjudicated for actual exposure, severity, or false positives. This is not a final contextual assessment."
    else:
        verdict = "Recommended to install"
        reason = "Configured static checks completed without reported findings; runtime safety is not guaranteed."
    triage = {"codeql_unique_rule_locations":len(distinct_locations),
       "codeql_levels":dict(severities),"codeql_examples":codeql_examples[:15],
       "codeql_evidence":codeql_examples,
       "osv_evidence":osv_evidence,
       "osv_distinct_vulnerability_ids":len(vulnerabilities),
       "osv_examples":[{"id":key,"packages":sorted(vals)[:4]} for key,vals in list(sorted(vulnerabilities.items()))[:15]],
       "embedded_skill_findings":embedded_hits}
    result.update(recommendation=verdict,recommendation_reason=reason,
      recommendation_kind="automated_precaution", ai_investigation_complete=False,triage={
      "codeql_unique_rule_locations":len(distinct_locations),
      "osv_distinct_vulnerability_ids":len(vulnerabilities),"embedded_skill_findings":embedded_hits})
    report.update(recommendation=verdict,recommendation_reason=reason,triage=triage,
      recommendation_kind="automated_precaution", ai_investigation_complete=False,
      recommendation_scope="Advisory assessment of configured static checks only; never automatic installation or publication.")
    report_file.write_text(json.dumps(report,indent=2)+"\n")
    summary_file.write_text(json.dumps(result,indent=2)+"\n")
    markdown = (f"# {verdict}\n\n**Target:** {report.get('repository_url')} @ {report.get('source_commit')}\n\n"
       f"**Explanation:** {reason}\n\nCodeQL findings: {report.get('codeql',{}).get('sarif_findings')} "
       f"(distinct rule/locations: {len(distinct_locations)}). "
       f"OSV matches: {report.get('osv',{}).get('vulnerabilities')} "
       f"(distinct IDs: {len(vulnerabilities)}). "
       f"Embedded skill findings: {embedded_hits}; coverage: {embedded.get('status')}."
       "\n\nNo candidate was installed or activated. Distribution requires explicit approval.\n")
    (folder/"decision.md").write_text(markdown)
    if os.getenv("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"],"a") as f:
            f.write(markdown)
    print(verdict, reason)

if __name__=="__main__":
    analyze(os.environ["REQUEST_ID"])
