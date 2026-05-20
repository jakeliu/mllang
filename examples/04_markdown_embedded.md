# Refactor authentication module to JWT

We're switching from session-based auth to JWT tokens. Preserve all user DB
intact. No breaking API changes. Migration must complete in under 10 minutes
of downtime window.

## Acceptance criteria

- Existing sessions auto-migrate without re-login prompt
- All API endpoints return same response shape
- Rollback plan documented before deploy
- Token signing key rotation policy in place

```mllang
V:0.1.r1; I:auth-jwt-migration-001;
G:{task=refactor_auth, from=sessions, to=jwt, deadline=2026-06-15};
S:{users_table=preserve, api_compat=hard, downtime_budget_s=600};
D:[migration_plan, rollback_plan, no_breaking_api, RS256_24h_expiry];
R:[downtime_overrun, token_leak, session_migration_failure];
N:@K -> implement;
H:test=pass;
P:0.85;
EN: Auth refactor sessions→JWT, preserve users DB, no breaking API.
```

## Notes

Token signing key rotation policy: RS256 with 24h expiry. Refresh tokens
rotate every 30 days. Existing session cookies serve as bridge tokens for
first 7 days post-migration.

---

# Second example — debugging task in same file

Different chapter of same project. Each fenced `mllang` block is a separate
packet that the agent parses independently.

## Symptom

User reports 401 errors on `/login` after migration deploy.

```mllang
V:0.1.r1; I:auth-jwt-debug-401;
G:{task=diagnose, scope=login_endpoint, parent=auth-jwt-migration-001};
S:{symptom="401 returned for valid credentials", env=production, since="deploy 14:32"};
D:[check_jwt_secret_rotation, check_clock_drift_between_nodes];
E:["server.log:14:33:21", "metrics_dashboard.png"];
U:[?secret_actually_rotated_at_deploy];
R:[partial_outage_continues];
N:@C -> verify_root_cause;
H:test=pass | escalate@H;
P:0.71;
EN: Diagnose post-deploy 401s — likely JWT secret rotation race or clock drift.
```

Human reads prose. Agents parse the fenced blocks. Same file, two task contexts,
zero ambiguity.
