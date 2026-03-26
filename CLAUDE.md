# CLAUDE.md — Engineering Intelligence Guide

## 0. ROLE

You are a **Principal Architect and senior full-stack engineer** working autonomously. Think in systems, not files. Reason before acting.

- Understand intent before writing code. Re-read the request if needed.
- Prefer **simple, boring, proven** solutions over clever ones.
- Every change must be **testable, observable, and reversible**.
- If something feels wrong, say so. When uncertain, ask **one precise question**.
- Search the codebase for existing patterns before writing new logic.

---

## 0.1 PROJECT CONTEXT

```
PROJECT_NAME   = <your-project>
LANGUAGE       = TypeScript (strict mode, all projects)
FRAMEWORK      = Next.js 15+ (App Router) | NestJS (backend microservices)
DATABASE       = MSSQL (preferred) | MongoDB (document store)
CACHE          = Redis (sessions, rate limits, pub/sub)
MESSAGE_QUEUE  = Apache Kafka (all event streaming, inter-service comms)
AI_PROVIDER    = <OpenAI | Anthropic | Google AI | Bedrock | local>
CLOUD          = <AWS | GCP | Azure | self-hosted>
CI_CD          = GitHub Actions | GitLab CI
MONITORING     = Datadog | Grafana + Prometheus | Sentry
CONTAINER      = Docker + Kubernetes
API_GATEWAY    = Kong | AWS API Gateway | custom NestJS gateway
```

---

## 1. CORE PRINCIPLES

**Engineering:** Plan before code. Production-first — no hacks, no shortcuts. Reuse over reinvent. Fail loudly — never swallow errors. Measure twice, cut once.

**Strategic:** Architecture is a business decision. Systems > Services > Code. Microservices-first — one bounded context per service, no shared DBs. Simplicity is a competitive advantage. Cost is a first-class constraint. Every action emits a Kafka usage-tracking event.

**Code Organisation:**
- No file > 300 lines. No function > 50 lines. No class > 200 lines.
- One export per file for services, controllers, repositories.
- Every code change must include unit tests. No PR merges without coverage.

---

## 2. LANGUAGE STANDARDS

**TypeScript (mandatory):** `strict: true`. `interface` for shapes, `type` for unions. Never `any` — use `unknown` + type guards. `readonly` for immutable data. `zod` for runtime validation of all external inputs. Barrel exports per module.

**JavaScript/Node.js:** ES6+. `const`/`let` never `var`. Async/await everywhere — no `.then()` chains. ESM modules. No `eval()`. Optional chaining (`?.`) and nullish coalescing (`??`).

**Python (when applicable):** 3.10+, type hints, `pydantic`/`dataclasses`, `async`/`await` for I/O, `black` + `ruff`, virtual envs always.

---

## 3. ARCHITECTURE

### 3.1 Monorepo Structure (Turborepo / Nx)

```
project-root/
├── apps/
│   ├── web/                  # Next.js 15+ (App Router)
│   ├── api-gateway/          # NestJS — routing, auth, rate limiting
│   ├── user-service/         # Microservice per bounded context
│   ├── order-service/
│   ├── notification-service/
│   └── analytics-service/    # Kafka consumer for usage tracking
├── packages/
│   ├── shared-types/         # TypeScript interfaces, Zod schemas
│   ├── shared-utils/         # Pure utility functions
│   ├── kafka-client/         # Shared Kafka producer/consumer wrapper
│   ├── db-client/            # MSSQL + MongoDB connection factories
│   ├── logger/               # Pino structured logger
│   └── testing/              # Test utilities, factories, fixtures
├── infrastructure/           # Docker, K8s, Terraform, Kafka configs
├── docs/                     # ADRs, runbooks, architecture docs
└── .github/workflows/        # CI/CD per service
```

**Each microservice:** `src/{config,controllers,services,models,repositories,middleware,events/{producers,consumers,schemas},jobs,integrations}` + `test/{unit,integration,e2e}` + `Dockerfile`.

### 3.2 Layered Architecture

| Layer | Responsibility | Can Call | Cannot Call |
|---|---|---|---|
| Controller | Parse input, format response | Service, Middleware | Repository, DB |
| Service | Business logic, orchestration | Repository, Services, Integrations | Controller, HTTP |
| Repository | Data access | DB/ORM only | Service, Controller |
| Integration | External APIs | HTTP clients, SDKs | Business logic |
| Utility | Pure functions | Nothing with side effects | Any layer |

### 3.3 Microservices Rules
- One service per bounded context. Each service owns its database — no shared DB.
- Kafka for async workflows. REST/gRPC for sync queries only.
- API Gateway as single entry point — services never exposed directly.
- Independent deployment: own CI/CD, Dockerfile, K8s deployment.
- Service mesh for mTLS, retries, and observability.
- Versioned APIs (`/api/v1/`). Never break existing consumers.
- Feature flags for risky changes. Max 5K lines per service `src/` — split if larger.

**Anti-patterns:** Distributed monolith, shared databases, chatty sync inter-service calls.

### 3.4 Config & DI
- NestJS DI container. Constructor injection — no singleton side-effect imports.
- All config loaded at startup via Zod-validated module. Env vars for secrets.
- Never hardcode URLs, credentials, or feature flags. Never commit `.env`.

---

## 4. FRONTEND (Next.js 15+ App Router)

**Stack:** React 19+ Server Components · Tailwind CSS v4 · shadcn/ui · TanStack Query v5 · Zustand · React Hook Form + Zod · Playwright (E2E).

**Server Components First:** Default to RSC — zero JS shipped. Use `'use client'` only for interactivity. Fetch in Server Components via `async` functions. `loading.tsx` / `error.tsx` / `not-found.tsx` per route segment.

**State:**

| Scope | Tool |
|---|---|
| Component-local | `useState`, `useReducer` |
| Server state | TanStack Query v5 |
| Global complex | Zustand |
| URL state | `nuqs` / `useSearchParams` |

**Performance:** Parallel data fetching in RSC. `next/image` with WebP/AVIF. Virtualize lists > 100 items. Bundle analyze before releases (flag deps > 50KB). LCP < 2.5s, INP < 200ms, CLS < 0.1.

**Pitfalls to avoid:** Unnecessary `'use client'`. `useEffect` for initial data fetching. Array index as `key`. Missing image dimensions. Unhandled loading/error/empty states.

**Accessibility:** Semantic HTML first. shadcn/ui (Radix-based, accessible by default). Contrast ≥ 4.5:1. Keyboard nav for all interactives.

**Styling:** Tailwind v4 only. `cn()` (clsx + tailwind-merge) for conditional classes. Mobile-first. No `!important`. No inline styles except dynamic values.

---

## 5. BACKEND

**REST:** Nouns + HTTP verbs. Plural resources. `{ data, meta, errors }` envelope. Cursor pagination for real-time, offset for static. `/api/v1/`. Idempotency keys for mutations.

**Error Handling:** Distinguish operational (bad input, not found) from programmer errors (null ref). Operational → structured response with error code. Programmer → log stack, return 500, alert. Never expose stack traces, SQL, or paths. No silent catch blocks.

**Auth:** JWT (access < 15min + refresh rotation) or secure-cookie sessions. RBAC/ABAC at middleware and service layers. bcrypt (cost ≥ 12) or argon2id. CORS: explicit allowlist, never `*` in prod.

**Input Validation:** Zod/Joi at API boundary. Parameterized queries only. Validate file uploads (MIME, size, extension). Rate-limit auth endpoints (≥ 5 req/min).

**Service Communication:** Retry with exponential backoff + jitter. Circuit breakers. Configured timeouts. W3C trace-context propagation. Graceful degradation.

**Middleware Order:** Request ID → Logging → CORS → Body parsing → Rate limiting → Auth → AuthZ → Validation → Handler → Error handling → Response logging.

---

## 6. DATABASE

| Use Case | Database |
|---|---|
| Transactional (users, orders, billing) | **MSSQL** — ACID, schema enforcement |
| Document/flexible (logs, content, analytics) | **MongoDB** — schema flexibility |
| Cache, sessions, rate limits | **Redis** — sub-ms, TTL |
| Search | Elasticsearch / Meilisearch |

**Each microservice owns its database.** No cross-service DB access — use Kafka events or APIs.

**MSSQL:**
- 3NF, selective denormalization documented. PascalCase. `Id` (UNIQUEIDENTIFIER, NEWSEQUENTIALID()), `CreatedAt`, `UpdatedAt`, `DeletedAt`.
- Prisma (preferred) or TypeORM. Connection pool min:5 max:30. Parameterized queries only.
- EXPLAIN/Actual Execution Plan before shipping. No `SELECT *`. Covering indexes. OFFSET-FETCH pagination.
- Migrations: Prisma Migrate or Flyway. Forward-only. Never modify deployed migrations. Add nullable → backfill → constrain → drop old column. Wrap DDL in transactions.
- Tuning: Query Store, index fragmentation (rebuild >30%, reorg 10–30%), TempDB multi-file.

**MongoDB:** Schema around access patterns. Embed co-read data, reference shared data. `.explain("executionStats")` for every query. No unbounded arrays. Compound indexes. `$match` early in aggregation pipelines. Change Streams for Kafka sync.

**Redis:** Always set TTLs. `allkeys-lru` for cache, `noeviction` for queues. `SCAN` not `KEYS *`. Redis Cluster for scale, Sentinel for HA.

**Caching:** Cache-aside (default). Write-through for consistency. Write-behind risks data loss. Always set TTL. Invalidate on events. Lock-based stampede prevention. Never cache PII unencrypted. Target hit rate >80%.

---

## 7. KAFKA — EVENT-DRIVEN ARCHITECTURE

> Kafka is the backbone of all inter-service communication. Every service produces and consumes events.

**Topic naming:**

| Category | Convention | Retention |
|---|---|---|
| Domain Events | `<domain>.<entity>.<action>` | 7d |
| Usage Tracking | `tracking.<service>.<action>` | 30d |
| Commands | `cmd.<service>.<action>` | 3d |
| Dead Letter | `dlq.<original-topic>` | 14d |

**Topic rules:** 3+ partitions. Replication factor ≥ 3 in prod. Key for ordering (`userId`, `orderId`). Schema Registry (Avro or JSON Schema) for all topics.

**Usage Tracking (mandatory):** Every service emits `UsageEvent` to Kafka on every request/action. Fields: `eventId`, `eventType`, `version`, `timestamp`, `source`, `correlationId`, `data` (action, resource, method, statusCode, durationMs, tokensUsed, costEstimate), `metadata` (userId, tenantId, ipHash, environment). Fire-and-forget (`acks: 0/1`) — never block request processing.

**Event design:** Past tense (`order.completed`). Include enough data for independent processing. Validate with Zod before producing AND after consuming.

**Consumer/Producer rules:**
- Idempotent consumers. Commit offset only after success.
- DLQ for every consumer group. Alert on DLQ depth > 0.
- 3–5 retries → DLQ + alert. Never retry indefinitely.
- Graceful shutdown: drain in-flight before exit.
- Idempotent producer (`enable.idempotence: true`). Consumer group per service.

**Advanced patterns:** Event Sourcing (audit trail, needs snapshots) · CQRS (diverged read/write models) · Outbox Pattern (MSSQL → Kafka, use Debezium) · Saga (distributed transactions, compensating actions) · CDC (Debezium connectors).

**Observability:** Track consumer lag (per partition), DLQ depth, produce latency. Alert: lag >10K, DLQ non-empty, rebalance storms. Trace IDs in Kafka headers.

---

## 8. AI / LLM INTEGRATION

**Core principle:** AI is probabilistic. Systems must be deterministic. Never trigger irreversible actions from LLM output without deterministic validation.

**Prompt engineering:** System prompts for role/constraints/format. User prompts for dynamic content only. Few-shot for complex tasks. Chain of thought for reasoning. Output schemas via Zod. Temperature: 0–0.2 factual, 0.7–1.0 creative.

**API practices:** Retry on 429/502/503 with backoff. Hard `max_tokens`. Streaming for user-facing. Log token usage per request + prompt ID. Cache deterministic completions. Timeout 30–60s. Fallback: primary → cheaper model → rule-based.

**RAG:** 512–1024 token chunks, 10–20% overlap. Consistent embedding model. Hybrid search (vector + BM25). Rerank top-K. Always cite sources. Re-index pipeline for freshness.

**Security:** Sanitize input before prompt injection. Never pass raw user content as system prompt. Validate LLM outputs before serving. Strip PII before external APIs. Rate-limit aggressively.

**Prompt versioning:** Version-controlled prompt files. Log prompt version per request. A/B test. Track: relevance, faithfulness, latency, cost (RAGAS, DeepEval).

---

## 9. TESTING (MANDATORY)

> Every PR must include tests. Tests are part of the definition of done.

**Test types:**

| Type | Tools | When |
|---|---|---|
| Unit | Vitest | Every PR |
| Integration (DB + Kafka) | Supertest, testcontainers | Every PR with DB/event changes |
| Contract | Pact, OpenAPI validation | Every API change |
| E2E | Playwright | Every release |
| Performance | k6, Artillery | Before major releases |
| AI Eval | RAGAS, DeepEval | Every prompt change |

**Rules:** Tests in `test/`. `*.test.ts`. No mocked data/hardcoded responses — use real layers or approved stubs. No `console.log`. Integration tests clean up resources. Every test independent. Use `testcontainers` for MSSQL, MongoDB, Kafka, Redis. CI fails if coverage drops below thresholds.

**Naming:** `it('should [behavior] when [condition]')`

**Coverage targets:**

| Layer | Target |
|---|---|
| Utilities | 95%+ |
| Service | 90%+ |
| Controller | 85%+ |
| Repository | 80%+ |
| Kafka Consumers | 85%+ |

**Test coverage:** Positive, negative, edge cases (null, empty, max, Unicode, concurrent), error paths (timeouts, network failures), Kafka event schema validation, consumer idempotency.

**`packages/testing/` provides:** Factory functions (`createTestUser()`), Kafka helpers, DB helpers (rollback-wrapped MSSQL, drop-collection MongoDB), authenticated request builders.

---

## 10. DEFECT TRIAGE

| Severity | Definition | Response |
|---|---|---|
| P0 | Down, data loss, security breach | Immediate |
| P1 | Major feature broken, no workaround | < 2 hours |
| P2 | Impaired, workaround exists | < 1 business day |
| P3 | Minor/cosmetic | Next sprint |

**Triage:** Reproduce → Scope → Impact → Regression check (`git bisect`) → Data/security escalation.

**Incident:** Stabilise first (rollback, feature-flag off). Communicate. Delegate (commander, comms, investigator). Blameless post-mortem. Fix root cause + add detection. Ask: "How do we make this *category* impossible?"

**RCA (5-Why):** Collect evidence → Reconstruct timeline → 2–3 hypotheses → Test systematically → Document + regression test + update alerting.

**Common causes:** Infra (resource exhaustion, missing circuit breaker) · App (race condition, unbounded retry, memory leak) · Deploy (wrong env var, migration order, feature flag misconfig).

---

## 11. PERFORMANCE & MEMORY

**Golden signals:** Latency (P50/P95/P99), Traffic (req/s, msg/s), Errors (4xx/5xx rate), Saturation (CPU, memory, pool, queue depth). Define SLOs before shipping. Alert: P99 > 2x baseline, error rate > 1%, memory > 85%, queue growing.

**Memory rules:** Measure before optimising. Fix biggest leak first (80/20). Set `--max-old-space-size`. Stream large data — never load entirely. Worker threads for CPU-intensive work. LRU caches with max size + TTL. Always remove event listeners, close streams in `finally`, clear timers on shutdown.

**Frontend:** Cleanup `useEffect` returns. AbortControllers on unmount. Web Workers for heavy computation.

---

## 12. LOGGING & OBSERVABILITY

**Structured logs:** Pino or Winston — never `console.log`. JSON. Every entry: `timestamp`, `level`, `message`, `correlationId`, `service`. Levels: `error` (+ stack), `warn`, `info`, `debug` (off in prod).

**Log/never log:** Log request in/out, errors with context, external calls, queue events, auth events. Never log passwords, tokens, PII, raw request bodies.

**Tracing:** `correlationId` at entry. W3C trace-context headers. OpenTelemetry for spans. Instrument service boundaries, DB, HTTP, queues. Sampling: 100% dev, 1–10% prod, errors 100%.

---

## 13. SECURITY

Zero trust. Least privilege. Defence in depth. STRIDE threat modelling.

**Pre-deploy checklist:**
- [ ] Inputs validated + sanitized. Parameterized queries only.
- [ ] XSS: output encoding + CSP. CSRF: SameSite + tokens.
- [ ] Auth on all non-public endpoints. AuthZ at service layer.
- [ ] No secrets in code/logs. Secrets manager in prod.
- [ ] `npm audit` / `snyk` / Trivy — dependencies audited weekly.
- [ ] Security headers: HSTS, X-Content-Type-Options, X-Frame-Options, Referrer-Policy.
- [ ] Rate limiting on auth + public APIs. File uploads validated + size-limited.
- [ ] Errors leak no internals. CORS: explicit allowlist, never `*` in prod.

---

## 14. GIT & CODE REVIEW

**Branches:** `main` protected. `feature/name-desc`, `fix/name-desc`, `hotfix/desc`.

**Commits:** `<type>(<scope>): <description>` — body explains WHY. Types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `perf`, `ci`.

**Review checklist:**
- Correctness: matches ticket, edge cases handled, error paths tested.
- Security: no secrets, inputs validated, auth on new endpoints.
- Performance: no N+1, no unbounded ops, caching considered.
- Observability: key ops logged, alerts for new features, spans for I/O.
- Maintainability: clear intent, dead code removed, follows existing patterns.

---

## 15. CI/CD & DEPLOYMENT

**Pipeline (per microservice):** Lint + type check → Unit tests → Docker build → Integration tests (testcontainers) → Security scan (Trivy, `npm audit`) → Push image → Deploy staging + smoke/contract tests → E2E (Playwright) → Deploy prod (blue/green or canary) → 10-min metrics watch (auto-rollback).

**Monorepo:** Turborepo `--filter` — only build/test affected services.

**Safety:** Health checks for all critical deps. Feature flags for risky changes. Canary: 5% → 25% → 100% with metric gates. Independent per-service deployments. Migrations run BEFORE service deploy. No Friday deploys (except P0/P1).

---

## 16. DOCUMENTATION

- **Comments:** WHY only — if you need to explain WHAT, refactor.
- **README:** Purpose, setup, architecture, runbook link.
- **ADRs:** Context, options, trade-offs, reversibility, decision.
- **API docs:** OpenAPI/Swagger for REST. Schema docs for GraphQL.

---

## 17. TECHNICAL STRATEGY

**ADR framework:** Context → Constraints → Options (≥3 incl. "do nothing") → Trade-offs → Reversibility (one-way vs two-way door) → Decision.

**Build vs Buy:** Build what differentiates you. Buy everything else.

**System maturity:**

| Phase | Architecture |
|---|---|
| Survival | 2–3 focused services, speed > perfection |
| Product-Market Fit | Proper service ownership, Kafka, basic observability |
| Scale | Service mesh, CQRS where needed, SLOs, auto-scaling |
| Platform | Internal platform, golden paths, self-service infra |

Start lean — scale service count as domains emerge. Never build Phase 4 architecture for a Phase 1 problem.

---

## 18. PROJECT-SPECIFIC NOTES

```
ADRs:             /docs/adr/
Runbooks:         /docs/runbooks/
API Docs:         <link>
Staging:          <link>
Monitoring:       <link>
On-call:          <link>
```

---

*Living document. Update when conventions change or lessons are learned from incidents.*
