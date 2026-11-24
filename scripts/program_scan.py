"""Trusted chat program-scan request validation and report assembly.
Never imports, installs, builds, or launches candidate code.
"""
import json, os, pathlib, re, subprocess, sys, urllib.parse, urllib.request

ROOT=pathlib.Path("program-results")
ID=re.compile(r"[a-z0-9][a-z0-9-]{7,63}$")
PART=re.compile(r"[A-Za-z0-9_.-]{1,100}$")
def request_file():
    changed=subprocess.check_output(["git","diff-tree","--no-commit-id","--name-only","--diff-filter=A","-r",os.environ["GITHUB_SHA"]],text=True).splitlines()
    matched=[p for p in changed if p.startswith(".program-requests/") and p.endswith(".json")]
    if len(matched)!=1: raise ValueError("Exactly one new program request file required")
    path=pathlib.PurePosixPath(matched[0])
    if path.parent!=pathlib.PurePosixPath(".program-requests") or not ID.fullmatch(path.stem):
        raise ValueError("Invalid request ID")
    return matched[0],path.stem

def validate():
    path,rid=request_file()
    if pathlib.Path(path).stat().st_size>4096: raise ValueError("Request too large")
    request=json.loads(pathlib.Path(path).read_text())
    if not isinstance(request,dict) or set(request)-{"repository_url","ref"}: raise ValueError("Only repository_url and ref allowed")
    url=urllib.parse.urlsplit(request.get("repository_url",""))
    parts=url.path.strip("/").split("/")
    if url.scheme!="https" or url.netloc!="github.com" or url.username or url.password or url.query or url.fragment or len(parts)!=2:
        raise ValueError("Supply a public GitHub repository root URL")
    owner,name=parts
    if not PART.fullmatch(owner) or not PART.fullmatch(name) or owner in {".",".."} or name in {".",".."}:
        raise ValueError("Invalid repository")
    ref=request.get("ref","HEAD")
    if not isinstance(ref,str) or not 1<=len(ref)<=200 or any(ord(c)<32 for c in ref): raise ValueError("Invalid ref")
    repository=f"{owner}/{name}"
    headers={"Accept":"application/vnd.github+json","User-Agent":"team-skill-review","X-GitHub-Api-Version":"2022-11-28"}
    token=os.environ.get("SOURCE_READ_TOKEN")
    if token: headers["Authorization"]="Bearer "+token
    meta=json.load(urllib.request.urlopen(urllib.request.Request("https://api.github.com/repos/"+repository,headers=headers),timeout=30))
    if meta.get("private") is not False: raise ValueError("Only public repositories")
    commit_url="https://api.github.com/repos/"+repository+"/commits/"+urllib.parse.quote(ref,safe="")
    commit=json.load(urllib.request.urlopen(urllib.request.Request(commit_url,headers=headers),timeout=30))
    sha=commit["sha"]
    if not re.fullmatch("[0-9a-f]{40}",sha): raise ValueError("Unverified commit")
    out=os.environ["GITHUB_OUTPUT"]
    with open(out,"a") as f:
        for key,value in {"request_id":rid,"repository":repository,"source_commit":sha}.items():f.write(key+"="+value+"\n")
    ROOT.joinpath(rid).mkdir(parents=True,exist_ok=True)
    ROOT.joinpath(rid,"request.json").write_text(json.dumps({"request_id":rid,"repository_url":"https://github.com/"+repository,"source_commit":sha,"pipeline_version":"program-v2"},indent=2))
    print("Validated program request",rid,"at",sha)

def summarize():
    rid=os.environ["REQUEST_ID"]
    if not ID.fullmatch(rid):raise ValueError("Bad request ID")
    folder=ROOT/rid
    req=json.loads((folder/"request.json").read_text())
    codeql=os.environ.get("CODEQL_STATUS","unknown")
    osv=os.environ.get("OSV_STATUS","unknown")
    report={"schema_version":2,"target_kind":"software_program","request_id":rid,**req,
            "scan_mode":"static_code_and_dependency","codeql":{"status":codeql,"sarif_findings":None},
            "osv":{"status":osv,"vulnerabilities":None},
            "limitations":["Not a full security guarantee","No candidate application installation, startup, tests, or build was authorized",
                           "Only supported CodeQL languages and OSV-recognized package inventories are covered",
                           "External runtime services, secrets handling, and dynamic behavior are not verified"],
            "review_required":True,"publication_approved":False}
    sarifdir=folder/"sarif"
    sarifs=list(sarifdir.rglob("*.sarif")) if sarifdir.exists() else []
    if codeql=="success" and sarifs:
        count=0
        for file in sarifs:
            data=json.loads(file.read_text())
            for run in data.get("runs",[]):count+=len(run.get("results",[]))
        report["codeql"]["sarif_findings"]=count
    else:
        report["codeql"]["status"]="incomplete"
    osvfile=folder/"osv.json"
    if osv in {"success","findings"} and osvfile.is_file():
        data=json.loads(osvfile.read_text())
        sources=data.get("results",[])
        if not isinstance(sources,list) or not sources:
            report["osv"]["status"]="incomplete"
            report["osv"]["explanation"]="No recognized dependency inventory was reported."
        else:
            report["osv"]["sources_checked"]=len(sources)
            report["osv"]["vulnerabilities"]=sum(len(p.get("vulnerabilities",[])) for source in sources for p in source.get("packages",[]))
            report["osv"]["status"]=osv
    else:
        report["osv"]["status"]="incomplete"
    embedded_file=folder/"skills.json"
    embedded_status=os.environ.get("EMBEDDED_STATUS","unknown")
    if embedded_status=="success" and embedded_file.is_file():
        embedded=json.loads(embedded_file.read_text())
        if embedded.get("status") not in {"complete","partial","none_found"} or not isinstance(embedded.get("results"),list):
            embedded={"status":"incomplete","results":[],"error":"Invalid embedded-skill report"}
    else:
        embedded={"status":"incomplete","results":[],"error":"Embedded skill scan did not complete"}
    report["embedded_skills"]=embedded
    has_skill_findings=any((item.get("findings") or 0)>0 or (item.get("risk_severity") or "").upper() in {"MEDIUM","HIGH","CRITICAL"} for item in embedded.get("results",[]))
    if report["codeql"]["status"]=="incomplete" or report["osv"]["status"]=="incomplete" or embedded["status"] in {"partial","incomplete"}:
        state="incomplete"
    elif report["codeql"]["sarif_findings"] or report["osv"]["vulnerabilities"] or has_skill_findings:
        state="needs_review"
    else:
        state="review_required"
    report["state"]=state
    summary={key:report[key] for key in ["schema_version","target_kind","request_id","repository_url","source_commit","scan_mode","state","codeql","osv","review_required","publication_approved"]}
    summary["embedded_skills"]={"status":embedded.get("status"),"discovered_count":embedded.get("discovered_count"),"selected_count":embedded.get("selected_count"),"findings":sum(v.get("findings") or 0 for v in embedded.get("results",[]))}
    summary["pipeline_version"]="program-v2"
    summary["report_path"]=f".scan-results/{rid}/report.json"
    summary["run_url"]=os.getenv("GITHUB_SERVER_URL","https://github.com")+"/"+os.getenv("GITHUB_REPOSITORY","lancea-aicareercoaching/team-skill-review")+"/actions/runs/"+os.getenv("GITHUB_RUN_ID","")
    (folder/"result.json").write_text(json.dumps(summary,indent=2)+"\n")
    (folder/"report.json").write_text(json.dumps(report,indent=2)+"\n")
    print("Report state:",state)
if __name__=="__main__":
    if sys.argv[1]=="validate":validate()
    elif sys.argv[1]=="summarize":summarize()
    else:raise ValueError("Unknown command")
