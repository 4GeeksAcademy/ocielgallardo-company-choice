# AUTH-088 — Unit Testing Plan (Authentication API)

## Goal

Protect the HealthCore authentication business logic with a pytest suite that covers every auth-related endpoint and helper. Tests assert **what the application decides**, not FastAPI HTTP serialization.

## Scope (AUTH-088 only)

In scope:

- Registration (`POST /users` → `create_user`)
- Login (`POST /auth/login` → `authenticate_user`)
- Current user (`GET /auth/me` + `get_current_user`)
- Forgot / reset / change password domain services
- JWT + password helpers in `services/app/core/security.py`

Out of scope for this ticket (deferred):

- API-042 backoffice endpoint suites (suppliers, incidents)
- FE-019 frontend Jest utilities

## How to run

```bash
# From repo root
uv sync
uv run pytest
uv run pytest --cov=services.app.core.security --cov=services.app.domain.user_service --cov=services.app.domain.password_reset_service --cov=services.app.core.deps --cov-report=term-missing
```

Dev dependencies (already added): `pytest`, `pytest-cov`, `httpx`.

Shared fixtures live in `tests/conftest.py` (temporary TinyDB + test `SECRET_KEY`).

Target: **≥ 70% coverage** on the auth modules listed above.

## Safety rule for tests

Never use the real TinyDB file `data/process/auth/auth.json`.  
Each test run must use an isolated temporary database (fixture) so production-like local users are never mutated.

---

## Test plan by endpoint / concern

Legend: **Happy** = valid input, expected success · **Edge** = boundary / unusual-but-valid · **Fail** = invalid input or denied path

### 1. Register — `create_user` / `POST /users`

| Type | Case | Why |
|------|------|-----|
| Happy | Valid email + password (≥8) creates user + profile; password stored hashed | Confirms core signup path |
| Edge | Password length exactly 8 | Boundary of `Field(min_length=8)` |
| Fail | Duplicate email → `ValueError` / 409 | Prevents account collision |
| Fail | Empty / too-short password rejected by model | Input rule, not HTTP plumbing |

### 2. Login — `authenticate_user` / `POST /auth/login`

| Type | Case | Why |
|------|------|-----|
| Happy | Correct email + password returns JWT whose `sub` is the user id | Token is usable |
| Edge | Existing user with `is_active=False` is rejected | Inactive accounts must not login |
| Fail | Wrong password → `InvalidCredentialsError` | Security |
| Fail | Unknown email → same error (no user leak) | Same message as wrong password |

### 3. Tokens — `create_access_token` / `decode_access_token`

| Type | Case | Why |
|------|------|-----|
| Happy | Encode then decode returns the same subject | Round-trip integrity |
| Edge | Token with `exp` in the past is rejected | Regression that blocked users for hours |
| Fail | Malformed / garbage string raises `JWTError` | Bad clients / attacks |
| Fail | Valid signature but missing `sub` raises `JWTError` | Incomplete payload |

### 4. Current user — `get_current_user` / `GET /auth/me`

| Type | Case | Why |
|------|------|-----|
| Happy | Valid Bearer token resolves to `UserPublic` | Session works |
| Edge | User exists but profile missing → `/me` returns `profile: null` | Partial data still usable |
| Fail | Expired / invalid token → 401 credentials exception | Guard protected routes |
| Fail | Token for deleted user id → 401 | Stale tokens after delete |

### 5. Forgot password — `forgot_password`

| Type | Case | Why |
|------|------|-----|
| Happy | Known email creates reset token (email send mocked) | Recovery starts |
| Edge | Unknown email still returns `{"message": "ok"}` | Anti-enumeration |
| Fail | Provider/config failure still returns `{"message": "ok"}` (logged server-side) | Client must not learn existence |

### 6. Reset password — `reset_password`

| Type | Case | Why |
|------|------|-----|
| Happy | Valid token + new password updates hash and deletes token | One-shot success |
| Edge | New reset for same user invalidates previous unused token | Single active token |
| Fail | Unknown / expired / already-used token → 400 | Prevents reuse |
| Fail *(AI-suggested)* | Corrupt `expires_at` (or naive datetime without timezone) treated as invalid, not 500 | Defensive parsing |

### 7. Change password — `change_password`

| Type | Case | Why |
|------|------|-----|
| Happy | Correct current password → new hash stored | Authenticated change works |
| Edge | New password length exactly 8 | Boundary |
| Fail | Wrong current password → 400 | Prevent takeover |
| Fail | User id not found → 400 | Consistency |

---

## AI-assisted case discovery

While reviewing `password_reset_service.reset_password`, an AI-assisted review flagged comparing `_now_utc()` (timezone-aware) with a stored `expires_at` that might be **naive** (no timezone). Plan: assert corrupt / naive expiry is rejected as invalid token (400), not an unhandled crash. Document any real bug found during implementation here:

- TODO: fill after first failing test run (if any).

## File layout (planned)

```
tests/
  conftest.py          # temp TinyDB + env fixtures
  test_security.py     # hash + JWT
  test_register.py     # create_user
  test_login.py        # authenticate_user
  test_token.py        # get_current_user / me helpers
  test_password_reset.py  # forgot / reset / change
TESTING.md             # this file
```

## Coverage results

TODO: paste `uv run pytest --cov` summary after the suite exists.

## Deferred extras

- **API-042**: suppliers + incidents suites (≥60% on those modules)
- **FE-019**: Jest for `extractDetail`, `getFieldErrors`, token helpers in `healthcoreClient.ts`
