# Example: pr-series (via codex-prompt)

## What this demonstrates

A **PR-series** prompt for migrating the Acme Notes API from REST to typed RPC, split across five numbered PRs. It shows the methodology's signature PR-series moves: a numbered PR overview table with explicit merge order, hard per-PR boundaries ("touches / doesn't touch"), the data → types → API → routes → cleanup ordering that keeps early PRs zero-user-impact, and a skip-and-continue commit protocol so one tripped risk gate never strands the rest of the series. It runs in **Directive** mode because the PR boundaries are pre-decided, and ships one prompt for one PR (PR 3 of 5) rather than one mega-prompt for all five.

## The generated prompt

```markdown
# Codex PR-series: Acme Notes REST → typed RPC (PR 3 of 5 – server handlers)

Goal: replace the hand-rolled REST handlers under `api/src/notes/` with typed RPC procedures registered on the new router, so every notes operation flows through the shared RPC contract instead of ad-hoc Express routes.

Success means:
  - All five notes operations (list, get, create, update, delete) exist as RPC procedures on `notesRouter` with input/output validated by the Zod contracts shipped in PR 2.
  - The legacy REST handlers in `api/src/notes/route.ts` still respond identically (untouched) – this PR adds the RPC path beside them, it does not remove them.
  - `pnpm --filter api test` and `pnpm --filter api typecheck` both pass.

Stop when: the five RPC procedures are registered, the new procedure tests are green, and the legacy REST suite is still green.

> Mode: Directive
> Reasoning: high
> Depends on: PR 1 (rpc runtime + base router merged), PR 2 (Zod contracts merged)
> Verification level: local tests

## Context
We are migrating the Acme Notes API from REST to a typed RPC layer over five PRs (overview table below). The contract types and the empty router skeleton already landed in PRs 1–2. This PR fills `notesRouter` with the five notes procedures, each delegating to the existing service functions in `api/src/notes/service.ts` so business logic is reused, not rewritten. The web client and the `acme` CLI continue calling the old REST endpoints until PR 4 flips them; this PR is therefore zero-user-impact.

Read `AGENTS.md` for project conventions and `CONTRIBUTING.md` for the PR checklist.

## PR Overview

| PR | Title | Status | Depends on |
|----|-------|--------|------------|
| 1  | RPC runtime + base router + CI wiring | done | – |
| 2  | Zod contracts for notes (input/output schemas) | done | PR 1 |
| 3  | Server handlers → RPC procedures (this PR) | this | PR 2 |
| 4  | Migrate web client + `acme` CLI callers to RPC | pending | PR 3 |
| 5  | Remove legacy REST handlers + add 410 redirects | pending | PR 4 |

Merge order is strict and matches the dependency column: each PR is reviewable and revertable on its own, and no PR after PR 4 has user-visible impact until PR 4 itself merges.

## Read these files FIRST
1. `api/src/rpc/router.ts` – base router + `procedure` builder (PR 1)
2. `api/src/rpc/contracts/notes.ts` – Zod input/output schemas (PR 2)
3. `api/src/notes/service.ts` – business logic to delegate into
4. `api/src/notes/route.ts` – legacy REST handlers (reference only, untouched)
5. `api/src/notes/__tests__/route.test.ts` – legacy REST suite (the safety net)
6. `api/src/rpc/__tests__/router.test.ts` – RPC test harness pattern to mirror

## Assumptions
- The `procedure` builder from PR 1 accepts `.input(schema).output(schema).handler(fn)` and is already exported from `api/src/rpc/router.ts`. Confirm the exact builder surface before writing procedures; if it differs, adapt the call shape and report the delta.
- The service functions in `api/src/notes/service.ts` are pure of HTTP concerns (no `req`/`res`) and can be called directly from a procedure handler. If any service function still reaches into Express request objects, stop and surface it as a labeled choice – wrapping vs. refactoring the service is a PR-4 decision, not this one.
- Auth context (the authenticated user id) is available on the RPC `ctx` the same way PR 1's base router exposes it. Mirror how `router.ts` threads `ctx`.

## Invariant
- The legacy REST endpoints under `api/src/notes/route.ts` keep responding byte-for-byte as they do today. This PR is additive: RPC procedures land alongside REST, not in place of it.
- `service.ts` business logic is reused unchanged. No behavior moves into the procedure layer.
- No client (web or CLI) is repointed in this PR.

## Risk Gate
Halt and surface for user input only on: (a) a service function that cannot be called without an Express `req`/`res` (architectural fork – wrap vs. refactor is PR 4's call); (b) an auth/ownership check that lives in `route.ts` rather than `service.ts`, meaning the RPC path would silently skip it (privilege boundary). Everything else – a missing helper, a contract field that needs a tweak, a flaky test – is skip-and-log + continue, not a session halt.

## Repo mismatch stop condition
If `api/src/rpc/contracts/notes.ts` is missing any of the five operation schemas, or the `procedure` builder is not exported from `api/src/rpc/router.ts`, or `service.ts` does not expose a function per operation, stop and report the mismatch instead of inventing the missing piece. That gap means PR 1 or PR 2 did not land as assumed.

## Not in scope
- `apps/web/src/lib/api-client.ts` and `packages/cli/src/export.ts` – the callers. They migrate in PR 4; touch only on a report-only basis.
- Deleting or modifying `api/src/notes/route.ts` – that is PR 5.
- Any change to the Zod contracts in `contracts/notes.ts` beyond a reported, confirmed gap.

## Task 1: Register the five notes procedures
File: `api/src/rpc/routers/notes.ts` (new file)

Build `notesRouter` with one procedure per operation, each wired to its PR-2 contract and delegating to the matching `service.ts` function. Mirror the builder and `ctx` usage from `api/src/rpc/__tests__/router.test.ts`. Sketch (adapt to the verified builder surface):

\`\`\`ts
import { router, procedure } from "../router";
import * as contracts from "../contracts/notes";
import * as service from "../../notes/service";

export const notesRouter = router({
  list: procedure
    .input(contracts.listInput)
    .output(contracts.listOutput)
    .handler(({ input, ctx }) => service.listNotes(ctx.userId, input)),
  get: procedure
    .input(contracts.getInput)
    .output(contracts.noteOutput)
    .handler(({ input, ctx }) => service.getNote(ctx.userId, input.id)),
  create: procedure
    .input(contracts.createInput)
    .output(contracts.noteOutput)
    .handler(({ input, ctx }) => service.createNote(ctx.userId, input)),
  update: procedure
    .input(contracts.updateInput)
    .output(contracts.noteOutput)
    .handler(({ input, ctx }) => service.updateNote(ctx.userId, input)),
  delete: procedure
    .input(contracts.deleteInput)
    .output(contracts.deleteOutput)
    .handler(({ input, ctx }) => service.deleteNote(ctx.userId, input.id)),
});
\`\`\`

## Task 2: Mount the notes router on the base router
File: `api/src/rpc/router.ts`

Register `notesRouter` under the `notes` namespace on the app's root RPC router, beside whatever PR 1 mounted. Add the import and the namespace entry only – do not restructure the existing router composition.

## Task 3: Procedure tests
File: `api/src/rpc/routers/__tests__/notes.test.ts` (new file)

One vitest test per procedure, mirroring the harness in `api/src/rpc/__tests__/router.test.ts`:
- A happy-path call per operation asserting the output matches the contract.
- One input-validation test (e.g. `create` with a missing title) asserting the Zod input rejects before the handler runs.
- One ownership test on `get` (or `delete`) asserting a note owned by another user is not returned – this proves the auth check survived the move from REST to RPC.

## Commit protocol
Tasks are ordered but independent at the commit level. A risk gate trip on one task = skip that task, log why, and continue with the next; do not halt the whole PR. Reserve a session halt for the two Risk-Gate conditions above (Express-coupled service, or an auth check that lives only in `route.ts`). Commit per task with a message that names the task; leave the working tree clean before reporting done.

## Constraints
- This PR ONLY adds the RPC path for notes – DO NOT modify `route.ts`, the web client, or the CLI.
- Zero user-visible impact: no route, URL, or response that any current client hits changes.
- Reuse `service.ts`; no business logic is rewritten in the procedure layer.
- Stay within the listed files. If correctness needs an out-of-scope file (e.g. a shared `ctx` type), report and pause.
- DO NOT use em dashes – en dashes for ranges and clauses.
- Surface any ambiguity as a labeled choice with the safest option defaulted.
- DO NOT deploy. Commit + push only; verification is local tests, never a deploy.

## Done when
- `notesRouter` exposes all five procedures and is mounted on the root router.
- `pnpm --filter api test` passes, including the new `notes.test.ts` and the untouched legacy `route.test.ts`.
- `pnpm --filter api typecheck` passes.
- The legacy REST endpoints still respond as before (legacy suite green is the proof).

### Manual verification
\`\`\`bash
rg -n "notesRouter" api/src/rpc
\`\`\`
Expected: definition in `routers/notes.ts` + the mount in `router.ts`, and nothing in `api/src/notes/route.ts` (legacy handlers untouched).

\`\`\`bash
rg -n "service\\." api/src/rpc/routers/notes.ts
\`\`\`
Expected: five delegations, one per operation – business logic reused, not reimplemented.
```

## Why it's shaped this way

- **Directive mode, because the PR boundaries are pre-decided.** A REST → RPC migration has a known target shape, so the PR-series default is Directive: the prompt ships the exact procedure registrations and mount points rather than asking Codex to design the layering. The five-PR split itself is the planning artifact; each prompt just executes its slice.
- **One prompt per PR – this one is PR 3 of 5.** The skill's PR-series rule is "one prompt per PR," so the overview table sets the whole series for context while the body scopes hard to PR 3. Shipping all five PRs in one prompt would blur the boundaries the numbering exists to enforce and make any single failure expensive to isolate.
- **Data → types → API → routes → cleanup keeps early PRs zero-impact.** The merge order (runtime/contracts → server handlers → client callers → REST removal) means PRs 1–3 add the RPC path beside the live REST path and change nothing a user can hit. The user-visible flip is deferred to PR 4, and the irreversible deletion to PR 5, so the risky work is last and individually revertable.
- **The invariant is the legacy REST suite staying green.** Because this PR is additive, the safety net is concrete and runnable: the untouched `route.test.ts` proves the old path still works while the new `notes.test.ts` proves the new one does. That is why the Done-when leans on local tests and an `rg` check that `route.ts` was never touched.
- **Skip-and-continue commit protocol, narrow risk gate.** The risk gate halts only for the two genuinely architectural/privilege decisions (Express-coupled service, auth check stranded in `route.ts`); every mechanical hiccup is skip-and-log. This is the methodology's guard against the past incident where a mid-series risk gate worded as a session-stop stranded the remaining commits – ordered work should degrade gracefully, not all-or-nothing.
```
