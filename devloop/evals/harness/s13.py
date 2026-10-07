"""Scenario 13: jirashastra-mcp at ff91465 (ENGX-1350), brief at Phase 4 done, Report section cut."""
import re
import subprocess
from pathlib import Path

SRC = Path.home() / "Development/Jirashastra-mcp"
KEY = "ENGX-1350"
COMPASS = "No consumers of the changed symbols outside jirashastra-mcp."
BASE = "ee1e29a3e4d428d719d79ae936524fa3756abb6e"
HEAD = "ff91465"
BRANCH = "feature/ENGX-1350-analytics-case-quality"
TICKET = Path(__file__).parent / "fixtures/ENGX-1350.md"


def sh(cmd, cwd):
    subprocess.run(cmd, cwd=cwd, shell=True, check=True, capture_output=True, text=True)


def setup(repo: Path):
    """APFS clone (copy-on-write, keeps node_modules), then pin origin/main to the brief's base."""
    subprocess.run(["cp", "-cR", str(SRC), str(repo)], check=True)
    origin = repo.parent / "origin.git"
    sh(f"git init -q --bare {origin}", repo.parent)
    sh("git clean -fdq -e node_modules -e .devloop && git reset -q --hard", repo)
    nohooks = "git -c core.hooksPath=/dev/null"  # the repo's pre-push hook blocks every push
    sh(f"{nohooks} push -q {origin} {BASE}:refs/heads/main && git remote set-url origin {origin}"
       f" && git fetch -q origin && {nohooks} checkout -q -B {BRANCH} {HEAD}", repo)
    b = repo / ".devloop/ENGX-1350/brief.md"
    text = b.read_text().split("\n## Report")[0]
    b.write_text(re.sub(r"Phase done: \d", "Phase done: 4", text) + "\n")
    for extra in ("eval-with.txt", "eval-without.txt"):
        (b.parent / extra).unlink(missing_ok=True)


def ticket():
    from fixtures import issue
    return issue("ENGX-1350", "JiraShastra analytics: stop false AI-behavior cases, add drill-down / "
                 "per-widget state checks, fix echo-kb help-doc retrieval", TICKET.read_text(),
                 itype="Task", updated="2026-09-23T18:16:11.032+0530", status="In Progress")
