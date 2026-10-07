"""Scenario 17: jirashastra-mcp at 0e2bd79 (QB-8371 as raised for review, before Bito), brief at Phase 4 done."""
import subprocess
from pathlib import Path

SRC = Path.home() / "Development/Jirashastra-mcp"
KEY = "QB-8371"
BASE = "61c1c7c"
HEAD = "0e2bd79"
BRANCH = "feature/QB-8371-generation-readiness-gate"
FIXTURES = Path(__file__).parent / "fixtures"
COMPASS = "No consumers of the changed symbols outside jirashastra-mcp."


def sh(cmd, cwd):
    subprocess.run(cmd, cwd=cwd, shell=True, check=True, capture_output=True, text=True)


def setup(repo: Path):
    """APFS clone, pin origin/main to the base, check out the MR head, plant the Phase-4 brief."""
    subprocess.run(["cp", "-cR", str(SRC), str(repo)], check=True)
    # The source keeps this branch checked out in a worktree; a copy of that metadata makes
    # `checkout -B` refuse, and nested worktrees poison scoped vitest runs.
    sh("rm -rf .git/worktrees .claude/worktrees && git worktree prune", repo)
    origin = repo.parent / "origin.git"
    sh(f"git init -q --bare {origin}", repo.parent)
    sh("git clean -fdq -e node_modules -e .devloop && git reset -q --hard", repo)
    nohooks = "git -c core.hooksPath=/dev/null"  # the repo's pre-push hook blocks every push
    sh(f"{nohooks} push -q {origin} {BASE}:refs/heads/main && git remote set-url origin {origin}"
       f" && git fetch -q origin && {nohooks} checkout -q -B {BRANCH} {HEAD}", repo)
    d = repo / f".devloop/{KEY}"
    d.mkdir(parents=True, exist_ok=True)
    (d / "brief.md").write_text((FIXTURES / f"{KEY}-brief.md").read_text())


def ticket():
    from fixtures import issue
    return issue(KEY, "Jirashastra should not generate test cases or scope if there is no usable info",
                 (FIXTURES / f"{KEY}.md").read_text(), itype="Task",
                 updated="2026-09-25T12:30:36.157+0530", status="To Do")
