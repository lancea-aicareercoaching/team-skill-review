"""Automatic bounded security triage, reporting and deployment eligibility.

No candidate programs, skills, scripts, or install commands are executed.
Recommendations are evidence-limited; they never authorize installation.
"""
import collections
import hashlib
import json
import os
from pathlib import Path

def severity_band(row):
    raw = row.get("security_severity")
    if raw is None:
        raw = (row.get("database_specific") or {}).get("severity")
    if isinstance(raw, str) and raw.lower() in {"critical", "high", "medium", "low"}:
        return raw.lower()
    try:
        score = float(raw)
        if 0 <= score <= 10:
            return "critical" if score >= 9 else "high" if score >= 7 else "medium" if score >= 4 else "low"
    except (ValueError, TypeError):
        pass
    return "unknown"

def paginated_records(folder, rid, commit, kind, records, budget=120000):
    priority = {"critical": 0, "high": 1, "unknown": 2, "medium": 3, "low": 4}
    rows = sorted(records, key=lambda row: priority[severity_band(row)])
    pages = []
    batch = []
    used = 0
    def flush():
        if not batch:
            return
        number = len(pages) + 1
        name = f"evidence-{kind}-{number:06d}.json"
        data = {"schema_version": 2, "request_id": rid, "source_commit": commit,
                "analyzer": kind, "page": number, "records": batch}
        payload = (json.dumps(data, ensure_ascii=True, separators=(",", ":")) + "\n").encode()
        if len(payload) > 900000:
            raise ValueError("Individual evidence page exceeds safe publication size")
        (folder / name).write_bytes(payload)
        pages.append({"path": name, "page": number, "count": len(batch),
                      "sha256": hashlib.sha256(payload).hexdigest()})
    for row in rows:
        row = dict(row, severity_band=severity_band(row))
        size = len(json.dumps(row, ensure_ascii=True, separators=(",", ":")).encode()) + 1
        if batch and used + size > budget:
            flush()
            batch = []
            used = 0
        batch.append(row)
        used += size
    flush()
    return {"total_records": len(rows), "included_records": sum(p["count"] for p in pages),
            "truncated": False, "pages": pages,
            "severity_counts": dict(collections.Counter(severity_band(row) for row in rows))}

def codeql_detail(issue, rule):
    properties = rule.get("properties", {})
    return {"rule": issue.get("ruleId"), "level": issue.get("level") or rule.get("defaultConfiguration", {}).get("level"),
            "security_severity": properties.get("security-severity"), "precision": properties.get("precision"),
            "help_uri": rule.get("helpUri"), "tags": properties.get("tags"),
            "message": str(issue.get("message", {}).get("text", ""))[:2000],
            "locations": (issue.get("locations") or [])[:5],
            "location_count": len(issue.get("locations") or []),
            "has_code_flow": bool(issue.get("codeFlows"))}

def osv_detail(match, package, group):
    affected = []
    for a in match.get("affected", [])[:30]:
        affected.append({"package": a.get("package"), "ranges": a.get("ranges", [])[:30],
                         "ranges_truncated": len(a.get("ranges", [])) > 30,
                         "versions": a.get("versions", [])[:50],
                         "versions_truncated": len(a.get("versions", [])) > 50})
    return {"id": match.get("id"), "aliases": match.get("aliases", [])[:30],
            "package": package.get("package"), "inventory": group.get("source"),
            "dependency_groups": package.get("dependency_groups"),
            "summary": str(match.get("summary", ""))[:1500], "severity": match.get("severity"),
            "database_specific": match.get("database_specific"), "withdrawn": match.get("withdrawn"),
            "affected": affected, "affected_truncated": len(match.get("affected", [])) > 30,
            "references": match.get("references", [])[:15]}

def analyze(rid):
    folder = Path("program-results") / rid
    summary_file = folder / "result.json"
    report_file = folder / "report.json"
    result = json.loads(summary_file.read_text())
    report = json.loads(report_file.read_text())
    distinct_locations = set()
    codeql_examples = []
    codeql_details = []
    osv_details = []
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
                codeql_details.append(codeql_detail(issue, rules.get(rule, {})))
                fingerprint = (rule, loc, line)
                if fingerprint in distinct_locations:
                    continue
                distinct_locations.add(fingerprint)
                sev = str(issue.get("level") or rules.get(rule, {}).get("defaultConfiguration", {}).get("level") or "unknown")
                severities[sev] += 1
                if len(codeql_examples) < 15:
                    codeql_examples.append({"rule":rule,"level":sev,"file":loc,"line":line,
                      "message":str(issue.get("message",{}).get("text",""))[:220]})
    vulnerabilities = collections.defaultdict(set)
    osv_file = folder / "osv.json"
    if osv_file.exists() and report.get("osv",{}).get("status") in ("success","findings"):
        osv = json.loads(osv_file.read_text())
        for group in osv.get("results", []):
            for package in group.get("packages", []):
                info = package.get("package", {})
                package_name = str(info.get("name") or info.get("package_name") or "unknown")
                for match in package.get("vulnerabilities", []):
                    vulnerabilities[str(match.get("id","unknown"))].add(package_name)
                    osv_details.append(osv_detail(match, package, group))
    embedded = report.get("embedded_skills", {})
    embedded_hits = sum(x.get("findings") or 0 for x in embedded.get("results", []))
    if report["state"] == "incomplete":
        advisory = "Scan coverage incomplete"
        reason = "One or more configured checks had missing, failed, or limited evidence."
    elif report["state"] == "needs_review":
        advisory = "Findings require review"
        reason = "The configured checks reported unresolved findings. See the analyzer results below."
    else:
        advisory = "No findings in completed static checks"
        reason = "Configured checks completed without reported findings. Runtime behavior remains unverified."
    eligibility = "eligible_for_approval" if report["state"] == "review_required" else "blocked"
    triage = {"codeql_unique_rule_locations":len(distinct_locations),
       "codeql_levels":dict(severities),"codeql_examples":codeql_examples,
       "osv_distinct_vulnerability_ids":len(vulnerabilities),
       "osv_examples":[{"id":key,"packages":sorted(vals)[:4]} for key,vals in list(sorted(vulnerabilities.items()))[:15]],
       "embedded_skill_findings":embedded_hits}
    result.update(advisory=advisory,advisory_reason=reason,deployment_eligibility=eligibility,triage={
      "codeql_unique_rule_locations":len(distinct_locations),
      "osv_distinct_vulnerability_ids":len(vulnerabilities),"embedded_skill_findings":embedded_hits})
    report["contextual_evidence"] = {"schema_version": 2,
        "request_id": rid, "source_commit": report["source_commit"],
        "codeql": paginated_records(folder, rid, report["source_commit"], "codeql", codeql_details),
        "osv": paginated_records(folder, rid, report["source_commit"], "osv", osv_details),
        "limitations": ["Scanner-reported evidence, not a determination of exploitability.",
                        "Missing severity, affected ranges or dependency groups remain unknown.",
                        "Truncated evidence does not establish clearance.",
                        "Dependency declarations do not establish installed runtime versions."]}
    result["contextual_evidence_version"] = 2
    report.update(advisory=advisory,advisory_reason=reason,deployment_eligibility=eligibility,triage=triage,
      advisory_scope="Advisory assessment of configured static checks only; never automatic installation or publication.")
    report_file.write_text(json.dumps(report,indent=2)+"\n")
    summary_file.write_text(json.dumps(result,indent=2)+"\n")
    markdown = (f"# {advisory}\n\n**Target:** {report.get('repository_url')} @ {report.get('source_commit')}\n\n"
       f"**Explanation:** {reason}\n\nCodeQL findings: {report.get('codeql',{}).get('sarif_findings')} "
       f"(distinct rule/locations: {len(distinct_locations)}). "
       f"OSV matches: {report.get('osv',{}).get('vulnerabilities')} "
       f"(distinct IDs: {len(vulnerabilities)}). "
       f"Embedded skill findings: {embedded_hits}; coverage: {embedded.get('status')}.\n\n"
       "Dedicated antivirus scanning is not included.\n\n"
       f"Deployment eligibility: {eligibility.replace('_', ' ')}."
       "\n\nNo candidate was installed or activated. Distribution requires explicit approval.\n")
    (folder/"decision.md").write_text(markdown)
    if os.getenv("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"],"a") as f:
            f.write(markdown)
    print(advisory, reason)

if __name__=="__main__":
    analyze(os.environ["REQUEST_ID"])
