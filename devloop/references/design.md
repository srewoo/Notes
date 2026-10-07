# Design — architecture & infra decisions

Read this during Phase 2b. The goal is not a clever design; it is that every
decision the change forces is **written down, sourced, and either settled,
defaulted in the open, or asked** — never made silently.

## 1. Inventory (what exists — cite a source for every line)

| Area | What to find | Where to look |
|---|---|---|
| Runtime & deploy | where it runs, replicas/HPA, what is persistent vs ephemeral, restart behaviour | Helm charts / k8s manifests / Terraform — **including the deploy repo outside this checkout** (read it via the GitLab MCP, read-only); Dockerfile; repo infra docs |
| Data & state | datastores, key namespaces, TTLs, capacity limits, eviction policy | client modules, chart values, ADRs |
| Messaging | queues/topics/events actually enabled in prod | env/config schema + deployed values |
| Config & secrets | which values come from ConfigMap vs secret store (Vault etc.), how a new key is added and who can write it | env schema, vault/secret values files, populate scripts |
| External systems | every system the change calls; is a credential/app already provisioned | code search, secret values |
| Observability | what is actually on in prod (logs, metrics, traces) | logger/metrics modules + deployed flags |
| Standards | org + repo rules that constrain the design (e.g. "every action emits a usage event", file-size limits, bounded contexts, branch rules) | global and repo `CLAUDE.md` / `AGENTS.md`, ADR folder, CONTRIBUTING |
| Prior work | is the ask already (partly) built? | ADRs, grep for the feature's nouns, recent MRs |

**Finding the deploy repo:** take the service/deployment name from the
Dockerfile, CI deploy job or your memory notes for this repo, then search GitLab
scoped to your org's group for it (e.g. a helm-charts project with a folder of
that name). Not found → say so in the inventory; don't guess.

**When sources disagree**, trust in this order: values actually applied per
environment (the deploy repo's env values files) → manifests in this repo →
code defaults → docs and memory notes. Note every stale source you override.

**Standards include the user's global instructions** (`~/.claude/CLAUDE.md`)
as well as the repo's; a recommendation that deviates from either is an `ask`.

## 2. Decision checklist

For each row, decide whether the change forces a decision. Skip rows it
doesn't touch — don't invent decisions.

1. **Placement** — which package/service/bounded context owns this code. Check
   the brief's `## Repo rules` first: a rule such as "don't grow file X, split
   instead" or "one export per file" rules options out before you weigh them.
2. **Contract** — new/changed tool params, API, event, schema; backwards compat.
   A contract also changes when an existing field keeps its type but changes
   meaning (a `skippedCount` that now also counts a new kind of skip) — every
   reader of the old meaning is affected. Prefer a new field.
3. **Data & state** — store, durability across restarts, TTL, capacity, dedup/idempotency.
4. **Execution & failure** — sync vs async; timeouts; retries; what happens when the dependency is down; blast radius.
5. **Config & secrets** — source of each new value; who can change it; does "configurable without a code change" hold for the chosen source.
6. **Infra & deploy** — any manifest/values/secret change; which repo; who applies it.
7. **Rollout & rollback** — feature flag? reversible by config, or needs a revert/migration?
8. **Observability** — how success and failure are seen in prod, using what is actually enabled.
9. **Security** — trust boundaries, authn/authz, data exposure (tenant isolation, PII in logs).
10. **Cost** — LLM tokens, storage, calls per request, third-party quotas.
11. **Standards compliance** — does the recommendation satisfy every rule from the Standards inventory row?

## 3. Options and classification

For each forced decision give 2–3 options. Option A is "reuse what exists / no
new infra" whenever it can meet the ACs. Recommend one; the reason must cite an
AC/NFR and an inventory fact.

Classify every decision:

| Class | When | What you do |
|---|---|---|
| `settled` | the ticket, a review, an ADR or a repo standard decides it | cite the source; no question |
| `default` | one option is clearly best **and** cheap to reverse **and** changes no contract, data, infra, cost or standard | pick it; list it in the message so the user can override |
| `ask` | it changes a contract, data shape/durability, infra, cost, or crosses a team/repo boundary; **or** is hard to reverse; **or** two options are close; **or** the recommendation deviates from a standard | ask (below) |

A decision you'd put under "decisions I made myself" that fits the `ask` row is
an `ask`. Redefining what an existing field, count or status means is a
contract change even when no type changes — `ask`, never `default`.

## 4. Asking

- All `ask` decisions go in **one** AskUserQuestion call, up to 4 questions,
  ordered by how many ACs each blocks. More than 4 → ask the top 4, list the
  rest under Open questions, and ask them after the answers come back.
- Each question: recommended option first, labelled `(Recommended)`; each
  option's description states its trade-off in one line (what it costs, what
  breaks, how reversible). Use `preview` for side-by-side comparisons of
  config/contract shapes.
- In the same message, before the call, list the `default` decisions in one
  line each ("Defaulting: no retry — AC2 only forbids slowing the run; lost
  alert acceptable") so the user can override them in their answer.
- Prerequisites that block an AC (credential not provisioned, app not created,
  another team must merge a chart change) are asked **now**, as a question,
  not left for the report.

## 5. Record

Brief section:

```
## Design                     (Phase 2b; or "not needed — <reason>")
Inventory: <one line per area touched, each with source>
| # | Decision | Chosen | Class (settled/default/ask→answered) | Source / why | Reversible? |
Prerequisites: <what, owner, blocks which AC>
Infra changes: <in this repo (in the diff) | in other repos/systems (listed, not done)>
ADR suggested: <yes/no — yes for a new datastore/service, public contract, or cross-team infra>
```

Hard-to-reverse decisions → suggest `mindtickle-engg:adr` in the report; don't
write the ADR unless asked.
