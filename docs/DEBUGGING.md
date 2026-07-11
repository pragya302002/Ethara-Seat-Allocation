# Debugging Notes

Real issues found and fixed during this build, each caught by actually
running the code against a real local Postgres instance rather than
assuming correctness. Kept here in technical detail; the summary table
version is in `AI_PROMPTS.md`.

---

### 1. Missing `email-validator` dependency

**Symptom:** `ImportError: email-validator is not installed` the first
time the FastAPI app was imported, tracing back to Pydantic's `EmailStr`
type used in `schemas/auth.py`.

**Root cause:** Pydantic 2.x's `EmailStr` requires `email-validator` as a
runtime dependency but doesn't pull it in automatically unless you install
`pydantic[email]` explicitly — a plain `pip install pydantic` leaves it
missing.

**Fix:** Added `email-validator==2.2.0` to `requirements.txt`.

---

### 2. Seat undersupply in seed data

**Symptom:** Seed script completed without error, but only seated 3,120
employees when the intent was ~4,400 (88% of 5,000).

**Root cause:** `SEATS_PER_ZONE = 65` × 48 zones = 3,120 total seats —
fewer than the number of employees the fill-rate math wanted to seat. The
seed script's `min(fill_count, len(seats), len(active_employees))` guard
is correct defensive code (it prevents a crash from oversampling), but it
silently capped the actual seating percentage below what was intended,
and nothing in the output made that obvious until the numbers were
cross-checked.

**Fix:** Increased `SEATS_PER_ZONE` to 115 (5,520 total seats — ~10% more
than headcount, matching a real office's vacancy buffer). Re-ran and
confirmed via direct SQL that `occupied seats == active seat_allocations`
and the ratio matched the intended 88%.

**Lesson applied:** don't trust a script that "completed successfully" —
cross-check the actual output numbers against what was intended.

---

### 3. `asyncio.gather()` on a shared SQLAlchemy `AsyncSession`

**Symptom (caught before shipping, not in production):**
`sqlalchemy.exc.InvalidRequestError: This session is provisioning a new
connection; concurrent operations are not permitted`.

**Root cause:** `DashboardService.summary()` initially tried to run its 7
aggregate queries concurrently via `asyncio.gather()` to reduce total
latency. A single SQLAlchemy `AsyncSession` wraps one underlying database
connection and cannot execute multiple statements concurrently on it —
each `await self.db.execute(...)` needs the previous one to fully finish.

**Fix:** Rewrote to sequential `await` calls. True per-query concurrency
would require a separate session (and thus a separate pooled connection)
per query — for a single dashboard load, the added connection-pool
pressure isn't clearly a better trade than one sequential round-trip
chain, so sequential was kept deliberately, not just as a quick patch.

---

### 4. Synchronous Anthropic client blocking the async event loop

**Symptom (caught before shipping):** none observed directly (would have
manifested as request latency spikes / reduced throughput under
concurrent load in production, not a hard crash), but confirmed as a real
architectural problem on inspection.

**Root cause:** `AIAssistantService` initially instantiated
`anthropic.Anthropic` (the synchronous client) inside an `async def`
service method running under FastAPI's async event loop. A synchronous
network call inside an async function blocks the *entire* event loop for
its duration — meaning every other concurrent request to the API (not
just AI Assistant requests) would stall while waiting on Claude's
response.

**Fix:** Switched to `anthropic.AsyncAnthropic` and `await`ed both API
calls. Confirmed the async client is available in the installed SDK
version before making the change.

---

### 5. Wrong Claude model string

**Symptom:** would have caused every AI Assistant request to fail with a
"model not found" error once a real `ANTHROPIC_API_KEY` was configured.

**Root cause:** The first draft of `ai_assistant_service.py` used
`claude-sonnet-4-6` — a model string that was actually a leftover from an
unrelated context (a template for building Claude-powered artifacts in
the assistant's own tooling), not a real, current Anthropic model
identifier for backend API use.

**Fix:** Corrected to `claude-sonnet-5`, verified against the assistant's
own accurate knowledge of currently-available Anthropic models rather
than assumed from a stale/miscontextualized template.

**Not yet live-tested:** no `ANTHROPIC_API_KEY` was available in the
development sandbox, so the actual Claude round-trip (tool-use → backend
query execution → summarized answer) is structurally correct and the
no-key fallback path is confirmed working, but the live model call itself
needs verification once a real key is set in the deployed environment.

---

### 6. Google Fonts fetch failure at build time

**Symptom:** `next build` failed with `Failed to fetch 'Inter' from Google
Fonts` / `403` errors.

**Root cause:** the development sandbox's network egress allowlist
doesn't include `fonts.googleapis.com`, so `next/font/google`'s build-time
font-fetching step failed.

**Fix:** Rather than treating this as a sandbox-only quirk to work around,
removed the Google Fonts dependency entirely in favor of a system font
stack (`-apple-system, BlinkMacSystemFont, 'Segoe UI', ...`) declared via
plain CSS custom properties. This is a legitimate simplification
independent of the sandbox issue — it removes a build-time network
dependency that could just as easily flake in a real CI/CD pipeline (e.g.
Vercel's build step, if Google Fonts has an outage), and system fonts
render instantly with no extra network round-trip for end users.

---

### 7. Test suite: reserved-TLD email validation

**Symptom:** `test_login_success` and similar tests failed with `422`
instead of the expected `200`/`401`.

**Root cause:** Test fixtures used email addresses like
`test.admin@test.local`. Pydantic's `EmailStr` validator (via
`email-validator`) rejects RFC 2606 reserved TLDs (`.test`, `.example`,
`.invalid`, `.localhost`) by default as "special-use" domains — the exact
same validation behavior that correctly rejects malformed real-world
emails in production was also (correctly) rejecting test fixture emails
that happened to use a reserved TLD.

**Fix:** Changed all test fixture emails to a non-reserved domain
(`@etharatest-qa.com`), matching the pattern already used successfully in
`seed.py` (`@etharatest.com`).

---

### 8. Test suite: async event loop mismatch

**Symptom:** `RuntimeError: Task ... got Future ... attached to a
different loop` on several async tests, non-deterministically.

**Root cause:** `pytest-asyncio`'s default behavior creates a new event
loop per test function, but the application's SQLAlchemy `engine` (and
its connection pool) is a module-level singleton created once at import
time, bound to whichever event loop was active on first use. When a later
test ran under a *different* function-scoped loop but reused a pooled
`asyncpg` connection created under an earlier loop, asyncpg correctly
refused to operate on it.

**Fix:** Two changes together: (1) set
`asyncio_default_fixture_loop_scope = session` in `pytest.ini` so async
fixtures share one loop for the whole test session; (2) added an autouse
fixture that calls `await engine.dispose()` after every test, forcing a
fresh connection under the current loop rather than reusing a
potentially stale pooled one.

---

### 9. Test suite: shared session corrupted by interleaved HTTP calls

**Symptom:** Two tests failed with a `RuntimeError` surfacing during
`db_session.commit()`, with a stack trace showing SQLAlchemy attempting
to roll back a connection mid-failure.

**Root cause:** These two tests used the long-lived `db_session` fixture
to insert a second test entity (a second employee, a second seat) *after*
already making a real HTTP call through the `AsyncClient` (which
internally opens its own separate session via `get_db` for that request).
Interleaving direct writes on the fixture's session with real HTTP
request/response cycles left the fixture's underlying connection's
transaction state inconsistent in practice, even though each session was
technically a separate connection from the pool.

**Fix:** For the specific inserts that needed to happen *between* HTTP
calls within a test, used a fresh, short-lived
`async with AsyncSessionLocal() as tmp_session:` block instead of
reusing the long-lived fixture session — commit and close immediately,
with no interleaving.
