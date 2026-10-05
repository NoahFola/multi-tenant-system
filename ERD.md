# Multi-Tenant Workflow System: ERD

Firestore has no real foreign keys. "FK" means a stored ID that application code validates. Every tenant-owned document carries `tenant_id`, which enforces isolation.

## Diagram

```
Legend:  ||--o{  one-to-many     ||--o|  one-to-zero-or-one
         PK primary key         FK foreign key (app-enforced)   UK unique

┌─────────────────────────────────────────────────────────────────────────────┐
│                        IDENTITY & ACCESS                                    │
│                                                                             │
│  ┌──────────────┐  ||--o{  ┌──────────────────────────────────────────┐    │
│  │   TENANTS    │─────────>│                USERS                     │    │
│  │──────────────│          │──────────────────────────────────────────│    │
│  │ id        PK │          │ id              PK                       │    │
│  │ name         │          │ tenant_id       FK → TENANTS             │    │
│  │ status       │          │ role_id         FK → ROLES               │    │
│  │ created_at   │          │ email           UK                       │    │
│  └──────────────┘          │ password_hash                            │    │
│         │                  │ email_verified                           │    │
│         │ ||--o{           │ status                                   │    │
│         │                  │ created_at                               │    │
│         ▼                  └──────────────────────────────────────────┘    │
│  ┌──────────────┐                    │  │  │  │  │  │                      │
│  │    ROLES     │ <──────────────────┘  │  │  │  │  │  (role_id FK)        │
│  │──────────────│  ||--o{              │  │  │  │  │                      │
│  │ id        PK │                      │  │  │  │  │                      │
│  │ tenant_id FK │                      │  │  │  │  │                      │
│  │ name         │                      │  │  │  │  │                      │
│  │ permissions  │         ||--o{       │  │  │  │  │                      │
│  │ is_system    │     ┌───────────────-┘  │  │  │  │                      │
│  └──────────────┘     ▼                   │  │  │  │                      │
│                ┌──────────────┐           │  │  │  │                      │
│                │   SESSIONS   │           │  │  │  │                      │
│                │──────────────│           │  │  │  │                      │
│                │ id        PK │           │  │  │  │                      │
│                │ user_id   FK │           │  │  │  │                      │
│                │ tenant_id FK │           │  │  │  │                      │
│                │ refresh_token_hash       │  │  │  │                      │
│                │ family_id    │           │  │  │  │                      │
│                │ expires_at   │           │  │  │  │                      │
│                │ revoked_at   │           │  │  │  │                      │
│                └──────────────┘           │  │  │  │                      │
│                                 ||--o{   │  │  │  │                      │
│                         ┌────────────────┘  │  │  │                      │
│                         ▼                   │  │  │                      │
│                ┌─────────────────┐          │  │  │                      │
│                │  EMAIL_TOKENS   │          │  │  │                      │
│                │─────────────────│          │  │  │                      │
│                │ id           PK │          │  │  │                      │
│                │ user_id      FK │          │  │  │                      │
│                │ type            │          │  │  │                      │
│                │ token_hash      │          │  │  │                      │
│                │ expires_at      │          │  │  │                      │
│                │ used_at         │          │  │  │                      │
│                └─────────────────┘          │  │  │                      │
│                                   ||--o{   │  │  │                      │
│                           ┌────────────────┘  │  │                      │
│                           ▼                   │  │                      │
│                ┌─────────────────┐            │  │                      │
│                │   INVITATIONS   │            │  │                      │
│                │─────────────────│            │  │                      │
│                │ id           PK │            │  │                      │
│                │ tenant_id    FK │            │  │                      │
│                │ invited_by   FK │            │  │                      │
│                │ email           │            │  │                      │
│                │ role_id      FK │            │  │                      │
│                │ token_hash      │            │  │                      │
│                │ status          │            │  │                      │
│                │ expires_at      │            │  │                      │
│                └─────────────────┘            │  │                      │
└───────────────────────────────────────────────│──│──────────────────────┘
                                                │  │
┌───────────────────────────────────────────────│──│──────────────────────┐
│                     BUSINESS DATA             │  │                      │
│                                    ||--o{     │  │                      │
│  ┌──────────────┐  ||--o{  ┌───────┴──────────▼──┴──────────────────┐  │
│  │   PROJECTS   │─────────>│              WORKFLOWS                  │  │
│  │──────────────│          │─────────────────────────────────────────│  │
│  │ id        PK │          │ id              PK                      │  │
│  │ tenant_id FK │          │ tenant_id       FK → TENANTS            │  │
│  │ name         │          │ project_id      FK → PROJECTS           │  │
│  │ created_by FK│          │ submitted_by    FK → USERS              │  │
│  │ created_at   │          │ title                                   │  │
│  └──────────────┘          │ status                                  │  │
│       ▲                    │ version    (optimistic lock)            │  │
│       │ FK                 │ updated_at                              │  │
│    TENANTS                 └─────────────────────────────────────────┘  │
│                                       │           │                      │
│                            ||--o{     │           │  ||--o{              │
│                    ┌──────────────────┘           │                      │
│                    ▼                              │                      │
│         ┌────────────────────┐                   │                      │
│         │  WORKFLOW_HISTORY  │ <─── ||--o{ ── USERS (actor_id FK)       │
│         │────────────────────│                   │                      │
│         │ id              PK │                   │                      │
│         │ workflow_id     FK │                   │                      │
│         │ tenant_id       FK │                   │                      │
│         │ actor_id        FK │                   │                      │
│         │ from_status        │                   │                      │
│         │ to_status          │                   │                      │
│         │ idempotency_key UK │                   │                      │
│         │ at                 │                   │                      │
│         └────────────────────┘                   │                      │
└──────────────────────────────────────────────────│──────────────────────┘
                                                   │
┌──────────────────────────────────────────────────│──────────────────────┐
│                     EVENT PIPELINE               │ ||--o{               │
│                                        ||--o{    │                      │
│                         ┌─────────────────────────────────────────┐    │
│                         │            OUTBOX_EVENTS                 │    │
│                         │─────────────────────────────────────────│    │
│                         │ id              PK                       │    │
│                         │ tenant_id       FK                       │    │
│                         │ type                                     │    │
│                         │ aggregate_id    FK (workflow/etc.)       │    │
│                         │ payload                                  │    │
│                         │ status                                   │    │
│                         │ created_at                               │    │
│                         └─────────────────────────────────────────┘    │
│                                  │                    │                  │
│                       ||--o{     │                    │  ||--o{          │
│              ┌───────────────────┘                    │                  │
│              ▼                                        ▼                  │
│   ┌────────────────────┐              ┌───────────────────────────────┐ │
│   │  PROCESSED_EVENTS  │              │        NOTIFICATIONS          │ │
│   │────────────────────│              │───────────────────────────────│ │
│   │ id              PK │              │ id              PK            │ │
│   │ event_id        FK │              │ tenant_id       FK            │ │
│   │ consumer           │              │ user_id         FK → USERS    │ │
│   │ processed_at       │              │ event_id        FK            │ │
│   └────────────────────┘              │ status                        │ │
│                                       │ attempts                      │ │
│                                       │ last_error                    │ │
│                                       │ next_retry_at                 │ │
│                                       └───────────────────────────────┘ │
│                                                    │                     │
│                                          ||--o|    │                     │
│                                                    ▼                     │
│                                       ┌───────────────────────────────┐ │
│                                       │         DEAD_LETTERS          │ │
│                                       │───────────────────────────────│ │
│                                       │ id              PK            │ │
│                                       │ notification_id FK            │ │
│                                       │ tenant_id       FK            │ │
│                                       │ reason                        │ │
│                                       │ failed_at                     │ │
│                                       │ replayed_at                   │ │
│                                       └───────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                              AUDIT                                       │
│                                                                          │
│   TENANTS ──||--o{──> AUDIT_LOGS <──||--o{── USERS (actor_id FK)        │
│                                                                          │
│                ┌──────────────────────────────────────────┐             │
│                │               AUDIT_LOGS                 │             │
│                │──────────────────────────────────────────│             │
│                │ id              PK                        │             │
│                │ tenant_id       FK                        │             │
│                │ actor_id        FK → USERS                │             │
│                │ action                                    │             │
│                │ resource_type                             │             │
│                │ resource_id                               │             │
│                │ metadata                                  │             │
│                │ ip                                        │             │
│                │ at                                        │             │
│                └──────────────────────────────────────────┘             │
└─────────────────────────────────────────────────────────────────────────┘
```

## Collections

### Identity and access

#### TENANTS
| Field | Type | Key |
|---|---|---|
| id | string | PK |
| name | string | |
| status | string | |
| created_at | timestamp | |

#### USERS
| Field | Type | Key |
|---|---|---|
| id | string | PK |
| tenant_id | string | FK |
| role_id | string | FK |
| email | string | UK |
| password_hash | string | |
| email_verified | boolean | |
| status | string | |
| created_at | timestamp | |

#### ROLES
| Field | Type | Key |
|---|---|---|
| id | string | PK |
| tenant_id | string | FK |
| name | string | |
| permissions | array | |
| is_system | boolean | |

#### SESSIONS
| Field | Type | Key |
|---|---|---|
| id | string | PK |
| user_id | string | FK |
| tenant_id | string | FK |
| refresh_token_hash | string | |
| family_id | string | |
| expires_at | timestamp | |
| revoked_at | timestamp | |

#### EMAIL_TOKENS
| Field | Type | Key |
|---|---|---|
| id | string | PK |
| user_id | string | FK |
| type | string | |
| token_hash | string | |
| expires_at | timestamp | |
| used_at | timestamp | |

#### INVITATIONS
| Field | Type | Key |
|---|---|---|
| id | string | PK |
| tenant_id | string | FK |
| invited_by | string | FK |
| email | string | |
| role_id | string | FK |
| token_hash | string | |
| status | string | |
| expires_at | timestamp | |

### Business data

#### PROJECTS
| Field | Type | Key |
|---|---|---|
| id | string | PK |
| tenant_id | string | FK |
| name | string | |
| created_by | string | FK |
| created_at | timestamp | |

#### WORKFLOWS
| Field | Type | Key |
|---|---|---|
| id | string | PK |
| tenant_id | string | FK |
| project_id | string | FK |
| submitted_by | string | FK |
| title | string | |
| status | string | |
| version | int | |
| updated_at | timestamp | |

#### WORKFLOW_HISTORY
| Field | Type | Key |
|---|---|---|
| id | string | PK |
| workflow_id | string | FK |
| tenant_id | string | FK |
| actor_id | string | FK |
| from_status | string | |
| to_status | string | |
| idempotency_key | string | UK |
| at | timestamp | |

### Event pipeline

#### OUTBOX_EVENTS
| Field | Type | Key |
|---|---|---|
| id | string | PK |
| tenant_id | string | FK |
| type | string | |
| aggregate_id | string | FK |
| payload | map | |
| status | string | |
| created_at | timestamp | |

#### PROCESSED_EVENTS
| Field | Type | Key |
|---|---|---|
| id | string | PK |
| event_id | string | FK |
| consumer | string | |
| processed_at | timestamp | |

#### NOTIFICATIONS
| Field | Type | Key |
|---|---|---|
| id | string | PK |
| tenant_id | string | FK |
| user_id | string | FK |
| event_id | string | FK |
| status | string | |
| attempts | int | |
| last_error | string | |
| next_retry_at | timestamp | |

#### DEAD_LETTERS
| Field | Type | Key |
|---|---|---|
| id | string | PK |
| notification_id | string | FK |
| tenant_id | string | FK |
| reason | string | |
| failed_at | timestamp | |
| replayed_at | timestamp | |

### Audit

#### AUDIT_LOGS
| Field | Type | Key |
|---|---|---|
| id | string | PK |
| tenant_id | string | FK |
| actor_id | string | FK |
| action | string | |
| resource_type | string | |
| resource_id | string | |
| metadata | map | |
| ip | string | |
| at | timestamp | |

## Design notes

- **RBAC:** roles store a `permissions` array (for example `workflow:approve`), so permission checks are a lookup, not a join.
- **Sessions:** only a hash of the refresh token is stored. `family_id` lets you revoke the whole token chain if a stolen token is reused. `revoked_at` handles logout.
- **Email tokens:** verification and password-reset tokens are hashed, expire, and are single-use via `used_at`.
- **Concurrency:** `WORKFLOWS.version` is the guard. Approval runs as a transaction: update where `status = MANAGER_REVIEW` and `version = N`. The second concurrent write fails.
- **Idempotency:** `WORKFLOW_HISTORY.idempotency_key` (unique) makes retried requests a no-op. `PROCESSED_EVENTS` lets workers skip events they already handled.
- **Outbox:** the workflow update and its `OUTBOX_EVENTS` record are written in the same Firestore transaction, so an approval can never happen without its event.
- **Retries and recovery:** `NOTIFICATIONS.attempts` and `next_retry_at` drive retries. After the limit, the job moves to `DEAD_LETTERS`, where `replayed_at` tracks manual recovery.
- **Audit:** `AUDIT_LOGS` is append-only. Block update and delete in the service layer and in Firestore security rules.
- **Tenant isolation:** every collection except `TENANTS` has `tenant_id`. The repository layer injects it into every query from the JWT, never from the request body.
- **Subcollections:** `SESSIONS`, `WORKFLOW_HISTORY` and `DEAD_LETTERS` could be subcollections. They are kept flat for easier cross-document queries.
