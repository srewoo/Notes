"""LLM-judge every run in raw_runs.jsonl against its scenario in ../scenarios.md.

Writes judge_grades.json in the shape agent-test-skill's report.py reads.
usage: judge.py --raw DIR/raw_runs.jsonl --out DIR/judge_grades.json [--jobs 6]
"""
import argparse
import json
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

SCENARIOS_MD = Path(__file__).parent.parent / "scenarios.md"
MODEL = "claude-opus-5-5"
MAX_OUTPUT = 90000

PROMPT = """You are grading one run of the `devloop` Claude Code skill against one eval scenario.

SCENARIO (from evals/scenarios.md){part}:
{section}

HOW THE RUN WAS DRIVEN: a harness ran devloop non-interactively on a fixture repo with mocked Jira/
GitLab/Compass. When devloop asked a question it had to end its turn; the scripted user replies are
shown as "=== USER ===". Asking in the final message counts as asking the user. HARNESS FACTS at the
end were measured from the repo after each turn and at the end — treat them as ground truth over
anything the run claims. "Measured ..." lines in the scenario are history, not criteria.

TOOL TRAJECTORY (tool names; Bash commands truncated):
{trajectory}

RUN OUTPUT:
{output}

Score two dimensions 1-5 (5 fully meets, 4 minor nitpick only, 3 a real gap, 2 mostly fails, 1 fails):
- must: every "Must" line of the scenario holds.
- must_not: no "Must not" line occurred.
Cite the specific evidence in one line each, naming any Must that failed or Must-not that occurred.
Reply with ONLY this JSON, no prose:
{{"must": {{"score": N, "evidence": "..."}}, "must_not": {{"score": N, "evidence": "..."}}}}"""


def section(sid):
    n = re.match(r"s(\d+)", sid).group(1).lstrip("0")
    text = SCENARIOS_MD.read_text()
    m = re.search(rf"^## {n}\. .*?(?=^## |\Z)", text, re.M | re.S)
    return m.group(0).strip() if m else f"(section {n} not found)"


def trajectory(rec):
    lines = []
    for s in rec.get("trajectory", []):
        if s["tool"] == "__turn__":
            lines.append(f"--- turn {s['arguments']['n']} ---")
        elif s["tool"] == "Bash":
            lines.append(f"Bash: {s['arguments'].get('command', '')[:200]}")
        else:
            lines.append(s["tool"])
    return "\n".join(lines)[-20000:]


def judge(rec):
    sid = rec["scenario"]
    part = {"s16a": " — this run is session (a) only", "s16b": " — this run is session (b) only"}
    out = rec.get("output") or f"(no output — error: {rec.get('error')})"
    if len(out) > MAX_OUTPUT:
        out = out[:MAX_OUTPUT // 3] + "\n...[truncated]...\n" + out[-2 * MAX_OUTPUT // 3:]
    prompt = PROMPT.format(part=part.get(sid, ""), section=section(sid),
                           trajectory=trajectory(rec), output=out)
    p = subprocess.run(["claude", "-p", "--model", MODEL, "--output-format", "text", "--tools", ""],
                       input=prompt, capture_output=True, text=True, timeout=900)
    m = re.search(r"\{.*\}", p.stdout, re.S)
    try:
        dims = json.loads(m.group(0))
    except (AttributeError, json.JSONDecodeError):
        dims = {d: {"score": 1, "evidence": f"judge output unparseable: {p.stdout[:200]}"}
                for d in ("must", "must_not")}
    return {"scenario": sid, "run": rec["run"], "dimensions": dims}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--jobs", type=int, default=6)
    a = ap.parse_args()
    recs = [json.loads(l) for l in Path(a.raw).read_text().splitlines() if l.strip()]
    with ThreadPoolExecutor(a.jobs) as pool:
        grades = list(pool.map(judge, recs))
    Path(a.out).write_text(json.dumps(grades, indent=2))
    for g in sorted(grades, key=lambda g: (g["scenario"], g["run"])):
        d = g["dimensions"]
        print(f"{g['scenario']} r{g['run']}: must={d['must']['score']} must_not={d['must_not']['score']}")


if __name__ == "__main__":
    main()
