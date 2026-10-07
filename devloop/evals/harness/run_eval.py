"""Drive devloop end-to-end on each fixture scenario, N runs in parallel.

Writes raw_runs.jsonl in agent-test-skill's record shape (scenario, run, output, trajectory,
latency_ms, is_error, usage) so its grade.py / report.py grade it unchanged. The agent-test-skill
runner itself is sequential (one MCP call at a time); a devloop run takes up to an hour, so this
driver runs them in parallel instead.

usage: run_eval.py --out DIR [--runs 3] [--only s01,s02] [--jobs 6]
"""
import argparse
import json
import os
import shutil
import signal
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import facts as F
import fixtures as FX
import s13
import s17

HERE = Path(__file__).parent
PY = str(HERE.parent / ".venv/bin/python")
MODEL = "claude-opus-5-5"
TURN_TIMEOUT_S = 3000
PREAMBLE = ("EVAL HARNESS: this session is non-interactive and AskUserQuestion is unavailable. "
            "Wherever a skill tells you to ask the user, write the questions (with your recommended "
            "answer) in your final message and end your turn; the user's reply arrives as the next "
            "message. Never answer your own question.")
DEFAULT_SERVERS = {s: s for s in ("atlassian_rovo", "gitlab", "mindtickle_engineering", "figma")}
lock = threading.Lock()
# Real-repo scenarios: a module with KEY, COMPASS, ticket() and setup(repo).
REAL = {"s13": s13, "s17": s17}


def scenario(sid):
    if sid in REAL:
        m = REAL[sid]
        return dict(key=m.KEY, ticket=m.ticket(), turns=4, replies=[FX.GENERIC] * 3,
                    compass=m.COMPASS)
    return FX.S[sid]


def mocks_for(sc):
    key = sc["key"]
    m = {
        "atlassian_rovo": {"tools": {
            "getAccessibleAtlassianResources": {"response": [
                {"id": "cloud-fixture", "url": "https://fixture.atlassian.net", "name": "fixture"}]},
            "getJiraIssue": {"by": "issueIdOrKey", "responses": {key: sc["ticket"]}},
            "getJiraIssueRemoteIssueLinks": {"response": []}}},
        "gitlab": {"tools": {"search": {"response": {"results": []}},
                             "get_merge_request_notes": {"response": []}}},
        "mindtickle_engineering": {"tools": {
            "explore_capabilities_tool": {"response": [
                {"full_name": "compass.submit_query", "description": "Ask Compass about code"},
                {"full_name": "compass.fetch_query_result", "description": "Poll a Compass query"}]},
            "describe_capability_tool": {"response": {"parameters": {"query": "string",
                                                                     "query_id": "string"}}},
            "execute_capability_tool": {"by": "capability_name", "responses": {
                "compass.submit_query": {"query_id": "q-1", "status": "submitted"},
                "compass.fetch_query_result": {"status": "completed",
                                               "answer": sc.get("compass", FX.DEFAULT_COMPASS)}}}}},
        "figma": {"tools": {}},
        "auth_only": {"only": ["authenticate", "complete_authentication"]},
    }
    for srv, spec in sc.get("mocks", {}).items():
        m[srv]["tools"].update(spec["tools"])
    return m


def build_repo(sid, sc, run_dir: Path) -> Path:
    repo = run_dir / "repo"
    if sid in REAL:
        REAL[sid].setup(repo)
    else:
        shutil.copytree(HERE / "fixtures/base", repo)
        origin = run_dir / "origin.git"
        sh(f"git init -q --bare -b main {origin}", run_dir)
        sh("git init -q -b main && git add -A && git -c user.name=fixture -c user.email=f@x "
           f"commit -qm 'initial' && git remote add origin {origin} && git push -q -u origin main", repo)
        if sc.get("bin"):
            (run_dir / "bin").mkdir()
            for name, body in sc["bin"].items():
                (run_dir / "bin" / name).write_text(body)
                (run_dir / "bin" / name).chmod(0o755)
        if sc.get("setup"):
            sh("git config user.name fixture && git config user.email f@x && " + sc["setup"], repo)
    exclude = Path(sh("git rev-parse --git-common-dir", repo).strip())
    exclude = (exclude if exclude.is_absolute() else repo / exclude) / "info/exclude"
    exclude.parent.mkdir(exist_ok=True)
    with open(exclude, "a") as f:
        f.write("\n.mcp.json\n.claude/\n.INJECTION_RAN\n.devloop/\n")
    return repo


def write_mcp(sc, run_dir: Path, repo: Path) -> Path:
    (run_dir / "mocks.json").write_text(json.dumps(mocks_for(sc)))
    servers = {name: {"type": "stdio", "command": PY, "args": [str(HERE / "mock_mcp.py")],
                      "env": {"MOCK_SERVER": kind, "MOCK_FIXTURE": str(run_dir / "mocks.json"),
                              "MOCK_LOG": str(run_dir / "mock_calls.jsonl")}}
               for name, kind in sc.get("servers", DEFAULT_SERVERS).items()}
    cfg = run_dir / "mcp.json"
    cfg.write_text(json.dumps({"mcpServers": servers}))
    # The nested reviewer session (claude -p inside devloop) reads project config, not our flags.
    (repo / ".mcp.json").write_text(cfg.read_text())
    (repo / ".claude").mkdir(exist_ok=True)
    (repo / ".claude/settings.local.json").write_text(json.dumps({
        "disableClaudeAiConnectors": True, "enableAllProjectMcpServers": True,
        "permissions": {"allow": ["Bash(claude -p:*)"]}}))
    return cfg


def sh(cmd, cwd):
    return subprocess.run(cmd, cwd=cwd, shell=True, check=True, capture_output=True, text=True).stdout


def turn(prompt, repo, cfg, session, log):
    cmd = ["claude", "-p", prompt, "--model", MODEL, "--permission-mode", "auto",
           "--output-format", "stream-json", "--verbose", "--mcp-config", str(cfg),
           "--strict-mcp-config", "--settings", json.dumps({"disableClaudeAiConnectors": True}),
           "--append-system-prompt", PREAMBLE]
    if session:
        cmd += ["--resume", session]
    steps, result = [], {}
    with open(log, "a") as lf:
        env = {**os.environ, "PATH": f"{repo.parent / 'bin'}:{os.environ['PATH']}"}
        # Own process group: on timeout kill the whole tree, or a surviving child (a test runner,
        # the nested reviewer) keeps stdout open and the read below never ends.
        p = subprocess.Popen(cmd, cwd=repo, stdout=subprocess.PIPE, stderr=lf, text=True, env=env,
                             start_new_session=True)
        timer = threading.Timer(TURN_TIMEOUT_S, lambda: os.killpg(p.pid, signal.SIGKILL))
        timer.start()
        for line in p.stdout:
            lf.write(line)
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                continue
            if ev.get("type") == "assistant":
                for block in ev.get("message", {}).get("content", []):
                    if block.get("type") == "tool_use":
                        steps.append({"tool": block["name"], "arguments": block.get("input", {})})
            elif ev.get("type") == "result":
                result = ev
        p.wait()
        timer.cancel()
    return steps, result, p.returncode


def run_one(sid, r, out: Path):
    sc = scenario(sid)
    run_dir = out / "work" / f"{sid}-r{r}"
    shutil.rmtree(run_dir, ignore_errors=True)
    run_dir.mkdir(parents=True)
    t0 = time.time()
    rec = {"scenario": sid, "run": r, "tool": "devloop", "input": {"task": f"/devloop {sc['key']}"}}
    try:
        repo = build_repo(sid, sc, run_dir)
        base = sh("git rev-parse origin/main", repo).strip()
        cfg = write_mcp(sc, run_dir, repo)
        prompt, session, traj, outputs, per_turn, cost = f"/devloop {sc['key']}", None, [], [], [], 0.0
        replies = list(sc.get("replies", []))
        for t in range(sc["turns"]):
            steps, res, code = turn(prompt, repo, cfg, session, run_dir / "transcript.jsonl")
            traj += [{"tool": "__turn__", "arguments": {"n": t + 1}}] + steps
            outputs.append(f"=== TURN {t + 1} (exit {code}) ===\n{res.get('result', '')}")
            cost += res.get("total_cost_usd") or 0
            per_turn.append(F.turn_facts(repo, base, steps, run_dir))
            if "spend limit" in (res.get("result") or ""):
                raise RuntimeError("account spend limit hit — infrastructure, not a skill result")
            session = res.get("session_id") or session
            if not replies or not session or code != 0:
                break
            prompt = replies.pop(0)
            outputs.append(f"=== USER ===\n{prompt}")
        final = F.final_facts(sid, sc, repo, base, run_dir)
        final["reviewer_calls"] = F.reviewer_calls(traj)
        summary = F.summary(sc["key"], repo, traj, per_turn)
        rec.update(is_error=False, trajectory=traj, tool_call_count=len(traj),
                   usage={"total_cost_usd": round(cost, 2)},
                   output="\n\n".join(outputs) + "\n\nHARNESS FACTS\n" +
                   json.dumps({"summary": summary, "turns": per_turn, "final": final}, indent=1))
    except Exception as e:  # a crashed run counts as a failed run, not a crashed suite
        rec.update(is_error=True, output="", error=f"{type(e).__name__}: {e}", trajectory=[],
                   tool_call_count=0)
    rec["latency_ms"] = round((time.time() - t0) * 1000)
    with lock, open(out / "raw_runs.jsonl", "a") as f:
        f.write(json.dumps(rec) + "\n")
    print(f"[done] {sid} run {r}: {'ERR ' + rec.get('error', '') if rec['is_error'] else 'ok'} "
          f"{rec['latency_ms'] // 1000}s ${rec.get('usage', {}).get('total_cost_usd', '?')}", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--only", default="")
    ap.add_argument("--jobs", type=int, default=6)
    a = ap.parse_args()
    ids = a.only.split(",") if a.only else [*FX.S.keys(), *REAL]
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    jobs = [(sid, r) for r in range(a.runs) for sid in sorted(ids)]
    print(f"[run] {len(ids)} scenarios x {a.runs} runs = {len(jobs)} devloop runs, {a.jobs} at a time")
    with ThreadPoolExecutor(a.jobs) as pool:
        for j in jobs:
            pool.submit(run_one, *j, out)


if __name__ == "__main__":
    main()
