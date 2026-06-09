# Codex Audit: API access-control sweep

Goal: produce a read-only PASS/FAIL audit of Acme Notes API access-control checks.

Success means:
  - Every listed route has a PASS or FAIL row with file evidence.
  - Every FAIL names the exploit path and missing check.
  - No source files are edited.

Stop when: the report is written, HEAD is re-anchored, and `git status` confirms read-only behavior.

> Mode: Investigative
> Reasoning: high
> Verification level: code read

## Context
The API resolves a session cookie to a user ID and then checks note ownership. This pass verifies that every route reaches the correct check.

## Read these files FIRST
1. `api/src/auth/session.ts` – session resolution
2. `api/src/auth/authorize.ts` – ownership helper
3. `api/src/notes/route.ts` – route handlers

## Assumptions
The server-side session is the only trusted caller identity.

## Invariant
Read-only audit. No source, test, config, or migration file is modified.

## Risk Gate
This is non-destructive; if structure differs, audit the real enforcement point and continue.

## Repo mismatch stop condition
If the API is not under `api/src/notes`, report the real route structure before scoring.

## Not in scope
CSRF, rate limiting, input validation, and frontend-only checks.

## Output format
Write a table with route, check reached, Verdict, Evidence, and Exploit / why-safe. Verdict is PASS or FAIL only.

## Anchor HEAD
Capture `git rev-parse HEAD` at start and end. If HEAD changed, re-check every finding.

## Constraints
- DO NOT edit files.
- Internal sources first.
- Cite only lines actually read.

## Done when
- Report has HEAD_START and HEAD_END.
- Every route has PASS or FAIL.
- `git status --porcelain` shows no source edits.
