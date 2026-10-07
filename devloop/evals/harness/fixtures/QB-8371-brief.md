# QB-8371 — Jirashastra should not generate test cases or scope if there is no usable info
Fetched: 2026-09-25T12:40+05:30   Jira updated: 2026-09-25T12:30:36.157+0530   Phase done: 4
Worktree: .claude/worktrees/QB-8371   Branch: feature/QB-8371-generation-readiness-gate (from origin/main 61c1c7c)

## Acceptance criteria        (source: description "Acceptance criteria" section)
AC1 Summary-only story (no desc/ACs/links), no additionalContext → generate_test_cases returns INSUFFICIENT_CONTEXT with whatToAdd; no LLM, no gatherContext.
AC2 Same story + real additionalContext (PRD text) → generates normally.
AC3 Well-specified story with empty case-index + flow-graph → generates; response has readiness 'thin' + contextGaps.
AC4 No "As a… I want…" format but real description + ACs → ready.
AC5 force: true bypasses the gate; bypass logged.
AC6 epic_pipeline proceed skips insufficient children with a reason, processes the rest.
AC7 generate_test_plan and run_full_pipeline apply the same gate.
AC8 Warn-only mode via env flag attaches verdict without blocking.
AC9 Fix assess_story mode=validate description (it does call an LLM).

## Review constraints
Review: none found (checked: comments (0), issuelinks (0), remote links/MRs (0), no linked docs).

## Conflicts
None. Ticket text says "insufficient = below floor AND no ACs AND no additionalContext"; implemented as additionalContext counting toward the signal (so "n/a" doesn't unlock) — same observable result for AC1/AC2.

## Code map
- packages/story-validator/src/rule-validator.ts:15 runRuleValidation — reuse C03/C06 results (pattern: pure rule fn + test in packages/story-validator/test/rule-validator.test.ts).
- packages/extraction/src/extraction.service.ts:73 EXTERNAL_SECTION_HEADING — linked-doc section of enrichedContent (ancestors excluded by design, QB-8324).
- apps/mcp-server/src/tools/tool-handlers.ts:2811 generate_test_cases runSync (after extractForTenant, before cache probe); :3612 executeStream; :3548 response build (contextGaps already there).
- tool-handlers.ts:1826 generate_test_plan runSync after extraction.
- tool-handlers.ts:7697 run_full_pipeline step 1.
- tool-handlers.ts:1102 errorResult (text-only), pattern for env flags: pageScanDefault :1958.
- tool-handlers-merged.ts:161 assess_story description (AC9); tool-docs.ts:18 same doc.
- packages/epic-processing/src/epic-processing.service.ts:146 runChild (AC6).
- Usage event: main.ts:621 already emits mcp.tool.<name>.error per failed call.

## Design
Inventory: runtime qac-svc-jshamcp (memory note); env flags read via process.env (pageScanDefault tool-handlers.ts:1958); Kafka per-call usage in main.ts:621, off by default in prod (memory); errors are text-only errorResult (tool-handlers.ts:1102); standards: bounded contexts via barrel, @Inject, tests on every change, <300 lines/file.
| # | Decision | Chosen | Class | Source / why | Reversible? |
| D1 | Placement | pure scorer + mode resolver in @jirashastra/story-validator; thin gate wrapper apps/mcp-server/src/tools/generation-readiness-gate.ts | settled+default | ticket Approach 1; wrapper avoids story-validator→extraction dep | yes |
| D2 | Contract: force param | `force` on generate_test_cases, generate_test_plan, run_full_pipeline | settled | AC5 | yes |
| D3 | Contract: blocked result | errorResult text `INSUFFICIENT_CONTEXT: …` + whatToAdd bullets | default | repo errors are text-only | yes |
| D4 | Contract: readiness on generate response | additive `readiness: {verdict, storySignalChars, acCount, whatToAdd}` | settled | AC3/AC8 | yes |
| D5 | Config | GENERATION_READINESS_MODE=off|warn|block, Vault-only (user 2026-09-25, PAGE_SCAN_ENABLED precedent); unset/empty→warn silently, invalid→warn+log | settled(flag)+default(name) | AC8, ticket "ship warn-only first" | yes, env |
| D6 | Observability | structured log `generation_readiness` only, no new Kafka event | ask→answered: log only | user 2026-09-25 | yes |
| D7 | Thin rule | ≥2 empty/failed among case-index, flow-graph, app-knowledge, knowledge-base | ask→answered: ≥2 | user 2026-09-25 | yes |
| D8 | Insufficient floor | substantive chars (own desc (epic context cut) + ACs + subtasks + epic children + docs linked on the issue itself + additionalContext; placeholders, URLs, link cards, media stripped; comments and API-contract blocks excluded) <150 AND 0 ACs | default | C06 uses 150; calibrate in warn phase | yes |
| D9 | Epic skip | optional `skippedReason` on EpicStoryResult, counted in skippedCount, block mode only | default | ticket "skipped with a reason, like epic-plan-registry" | yes |
Prerequisites: devops-helm-charts values-mt-bots.yaml env.vault[] entry + Vault key; see report. Not needed for warn (empty=warn).
Infra changes: none in this diff.
ADR suggested: no

## Change plan
- packages/story-validator/src/generation-readiness.ts (new): pure assessGenerationReadiness — AC1–4.
- packages/story-validator/src/index.ts: export — AC1–4.
- apps/mcp-server/src/tools/generation-readiness-gate.ts (new): mode env, force, log, blocked result — AC1,5,8.
- apps/mcp-server/src/tools/tool-handlers.ts: call gate at 4 sites, add force param, readiness on response — AC1,2,3,5,7.
- apps/mcp-server/src/tools/tool-handlers-merged.ts + tool-docs.ts: validate description — AC9.
- packages/epic-processing (service + package.json + package-lock.json 1 line): skip insufficient child — AC6.
- packages/extraction/src/extraction.service.ts + index.ts: linkedDocsText beside selfScopedContent (one path for gate + epic) — AC2.
- .env.example: GENERATION_READINESS_MODE documented — AC8.

## Test commands (from package.json scripts)
- typecheck: npx nx typecheck @jirashastra/mcp-server | @jirashastra/epic-processing (story-validator has no typecheck target)
- lint: npx eslint <files> (no per-package lint targets; eslint.config.mjs at root)
- unit: npx vitest run packages/story-validator | packages/epic-processing ; (cd apps/mcp-server && npx vitest run)

## Not doing
- Per-case "low-confidence" marking (in Approach prose, not an AC) — readiness field on response covers it.
- Offline calibration replay on ~100 prod generations — needs prod data; happens during warn-only phase.
- generate_regression_impact (ticket: out of scope).
- api-gateway gatherContext (apps/api-gateway/src/api/api.service.ts:125) — not listed in ticket.

## Open questions
(see gate)
