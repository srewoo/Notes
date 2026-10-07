# reports-svc

Node 20, CommonJS, no dependencies. Service name in deploys: `reports-svc`
(helm chart `charts/reports-svc` in the `devops/helm-charts` GitLab project).

- Tests: `npm test` (node:test). Lint: `npm run lint`.
- One module per concern under `src/`; tests mirror it under `test/`.
- Standard: every user-facing action emits a usage event via `emitUsage()` in `src/usage.js`.
- Branch prefixes: `feature/`, `bugfix/`. The remote rejects `fix/`.
