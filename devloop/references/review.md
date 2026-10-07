# Review — blast radius & independent review

Read this during Phase 4b. The reviewer is a **separate headless Claude
session** (`claude -p`) on a **different model** from yours: a fresh context
alone still shares your model's blind spots. Its inputs are the diff, the repo
and the blast-radius file you write first.

## Step 1 — you write the blast radius

Invoke `mindtickle-engg:use-compass` and ask Compass for every caller/consumer
of each changed symbol, contract, config key, event and data shape — across
repos, not just this one. Cross-check in this repo with a local caller search.
Write `.devloop/<KEY>/blast-radius.md`:

```
| symbol/contract changed | impacted (repo:file:line) | source (compass/local) | covered by test? |
```

Compass unavailable → local search only, and the file's first line says
`Compass unavailable: cross-repo impact not checked`.

## Step 2 — start the reviewer session

**Snapshot the round first.** Copy every changed and new file (test and
non-test) into `.devloop/<KEY>/review-r<N>/`, keeping paths, and save
`git diff <base> --stat` beside it. The final-delta pass diffs against the last
snapshot, so without it nobody can tell which code the reviewer never saw.

Write the prompt below to `.devloop/<KEY>/review-prompt.md`, then run it from
the worktree **in the foreground** (Bash timeout 600000). **Never end your turn
while it runs:** in a headless session (`claude -p`, CI) ending the turn ends
the session and kills the reviewer. If it outlasts the timeout and moves to
the background, wait on it in this turn with Monitor (until the process exits)
before reading `review.md`:

```bash
claude -p "$(cat .devloop/<KEY>/review-prompt.md)" \
  --model <reviewer model> \
  --permission-mode dontAsk \
  --allowedTools "Read" "Grep" "Glob" "Bash(git status:*)" "Bash(git diff:*)" \
    "Bash(git log:*)" "Bash(<each test command>:*)" "Edit(<test glob>)" \
    "Skill(mindtickle-engg:use-compass)" "mcp__<enggx server>__*" \
  --output-format text > .devloop/<KEY>/review.md 2> .devloop/<KEY>/review.stderr
```

- **`<enggx server>`:** the EnggX server's name as its tools appear in this session —
  `mcp__<server>__explore_capabilities_tool` → `<server>` (e.g.
  `claude_ai_mindtickle_engineering` for the claude.ai connector). Not connected → drop
  that rule and the Compass skill rule; the reviewer uses local search only.
- **Reviewer model:** `claude-fable-5-1`; if you are Fable, `claude-opus-5-5`.
- **`<test glob>`:** the repo's test-file pattern (`**/*_test.go`,
  `**/*.test.ts`, `tests/**`); `Edit(path)` covers new files too. `dontAsk`
  denies every tool not listed, so the reviewer cannot edit source or run git
  writes.
- **Session can't start** (no `claude` CLI, or the call is refused — auto mode
  blocks nested `claude -p` unless the user allows `Bash(claude -p:*)`): fall
  back to one fresh-context subagent (the repo's `<repo>-code-reviewer`, else
  `general-purpose`) with the same prompt, and report
  `Review: subagent fallback — <reason>`. Never skip the review. A subagent's
  limits are only its prompt, so check them yourself: before it starts, save
  `git diff --stat`, `git stash list` and a copy of every non-test file you
  changed; afterwards compare. Any difference (edited source, a stash, a
  checkout) → restore files from your copy (leave any new stash for the user;
  `git stash` commands are outside the approved list), and report
  `fallback reviewer broke its limits: <what>`.

## The prompt (fill the `<…>`; nothing else)

```
Review a local change and test its blast radius. Work only in <worktree path>.
You may create or edit test files only; never edit non-test files, never run
git commands other than status/diff/log, never commit.

Change: <KEY> — <summary>. Base: <base ref>. Diff: `git diff <base>`.
Brief (ACs, Design table, change plan): <path to .devloop/<KEY>/brief.md>
Blast radius (written by the author): <path to .devloop/<KEY>/blast-radius.md>
Test commands: <from the brief>. Pre-existing failures: <path to baseline.txt>.

1. Review the diff against the brief and the repo's CLAUDE.md/AGENTS.md:
   correctness vs each AC, edge cases and error paths, the Design table
   actually implemented (no silent extra decisions), security at trust
   boundaries, conventions, dead code. Every finding cites file:line.
2. Check the blast radius, don't trust it. For each changed symbol, contract,
   config key, event and data shape, search for callers/consumers yourself
   (local search; Compass via the `mindtickle-engg:use-compass` skill for other
   repos if it is available). Every one missing from blast-radius.md goes
   under MISSED.
3. Unit-test the blast radius inside this repo: run the existing tests for
   every impacted module (not only the ones the author ran). For an impacted
   path whose behaviour the change can alter and that no test covers, add a
   focused unit test. Impacted code in other repos: list it, don't test it.
4. A failing test not in baseline.txt: say which change it points at. Don't
   fix non-test code.
5. Answer every row of CHECKS below. Each answer is a FINDINGS #, or
   "clear — <what you opened or ran>", or "n/a — <why it cannot apply>".
   A row answered "clear" without evidence counts as not checked.

Return exactly:
FINDINGS: | # | severity (blocker/major/minor) | file:line | issue | suggested fix |
CHECKS:
| # | check | answer |
| C1 | Real input shape: every test input standing for another component's output (parser, API/gRPC/DB response, LLM output, file) was produced by that component or copied from its real output — run the real producer on a sample and compare | |
| C2 | Copied strings: every heading, key, marker, enum value or regex that must match text another module emits — open the emitter and compare the exact string, suffixes and case included | |
| C3 | Closed sets: a new category, family, type, tag or state — including one the diff introduces only in prose, a prompt or a comment — is present in every enum, allowlist, switch, schema, prompt list or map that lists its siblings. Those lists often spell siblings differently from the prose: grep an existing sibling's prose name AND its slug, constant and enum forms ("Date range" → `date-range`, `DATE_RANGE`, `DateRange`) | |
| C4 | Stale results: name each cache, frozen plan, fingerprint or persisted artifact the changed code feeds, and its key. A key built only from input data does not change when code changes, so old results survive: the key needs a code-version part that this diff bumps | |
| C5 | Consumers: for every output whose size, order or shape changed, each consumer was opened and what it does to it (slice, parse, index, sort) still holds | |
| C6 | Tests that can fail: each new assertion fails when the code is wrong. A test that builds N items asserts all N; no default makes it trivially true; it does not assert a mock's own return; the input puts the triggering text where real input puts it | |
| C7 | Prose vs code: comments, docstrings, the brief and commit text describe what the code actually does | |
| C8 | One value, one path: logic that another package or sibling function also computes resolves it the same way | |
| C9 | Fail loudly: no default that hides a missing argument, no empty catch, no fail-open path without a log | |
| C10 | Out-of-diff wiring: every env var, Vault/helm value, flag or config the change needs is set in each environment it ships to | |
| C11 | Evidence kind: an AC that depends on LLM output or a live service is marked "needs live run" unless a real run was done | |
| C12 | Copies: every block, string, schema, fixture or predicate that appears twice or more in the diff (grep the added lines for each literal and each 3+ line block). Two copies with different wording — a description, a default, a test fixture — are a finding, and so is a new copy of an idiom the file already repeats | |
| C13 | Meaning changes: an existing field, param, return value or count whose meaning changes while its type does not. Name its readers (in this repo and returned to clients) and what each assumes; prefer a new field over redefining an old one | |
| C14 | Repo rules: every row of the brief's `## Repo rules`, plus any imperative line in CLAUDE.md/AGENTS.md the diff touches (test factories, file-size or monolith limits, placement, DI) — answer each met / not met with file:line. "The neighbouring code does it too" is not met | |
| C15 | Doc placement and casts: every doc comment the diff touches sits directly above the declaration it describes; no new `as never` / `as any` / `as unknown as` / `type: ignore` without a comment saying why | |
MISSED: | symbol/contract changed | impacted (repo:file:line) | how found | covered by test? |   ("none" if blast-radius.md was complete)
TESTS RUN: <commands + pass/fail counts copied from output>
TESTS ADDED: <file — what each asserts>
NOT CHECKED: <anything skipped and why>
```

## Acting on the result

- **Read `review.md`.** Empty, or missing the FINDINGS/CHECKS headings → the
  session failed (see `review.stderr`); rerun once, then fall back to the
  subagent (Step 2). Keep stderr out of `review.md`: CLI warnings would land in it.
- **A CHECKS row left blank or "clear" with no evidence** → start one more
  session whose prompt is the same header plus only those rows; still
  unanswered → list it under NOT CHECKED in the report.
- **MISSED not "none"** → add those rows to `blast-radius.md` and report
  `Blast radius: author missed <n>` — your own map was wrong there.
- **The reviewer's own tests are not trusted either.** For each test file it
  added or changed, answer C6 yourself and run the revert proof (SKILL.md Phase
  4) before keeping it. A test that passes with the change reverted is rewritten
  or deleted.
- **Verify before fixing.** Read each blocker/major at its file:line; a finding
  you can't reproduce or that contradicts the brief → note it as rejected, with
  why. Minor → report, don't fix.
- **Fix** confirmed blockers/majors (the run budget still applies), then redo
  Phase 4's Final run including the reviewer's new tests.
- **A blast-radius test failing** that isn't in `baseline.txt`: classify it with
  Phase 4's back-up/revert/restore steps — fails with your change reverted →
  pre-existing (report); passes reverted → yours (fix).
- **Re-review** only if fixes changed non-test code: one more session, same
  prompt and model — the **whole** prompt, every CHECKS row. Never send a
  re-review a shortened list ("re-answer C1, C2 and C6 only"): the fixes are
  new code, and the rows you drop are where it goes wrong. Two rounds max;
  anything still open goes in the report.

## Final-delta pass (after the last round)

Whatever you changed after the last snapshot was reviewed by nobody. Before the
report:

1. Diff it: `git diff --no-index .devloop/<KEY>/review-r<last>/ <each changed
   path>` for existing files, plus every file created since. Save it to
   `.devloop/<KEY>/final-delta.diff`.
2. Put that delta through SKILL.md's self-review list and answer every CHECKS
   row against it yourself, with evidence, in `.devloop/<KEY>/final-delta.md`.
3. Run the revert proof for every test the delta adds or changes.
4. A finding → fix it and repeat 1–3, within the run budget. This does not
   start a third reviewer session.
5. Report it: `final-delta pass: <n files>, <findings fixed / open>`.
- Cross-repo impact → Prerequisites / infra not done here, with the owning team.
