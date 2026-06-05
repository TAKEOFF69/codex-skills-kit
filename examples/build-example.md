# Example: build (via codex-prompt)

## What this demonstrates

A **Build** prompt generated for the fictional **Acme Notes** project (Next.js App Router web client + Node/TypeScript API + Postgres + an `acme` CLI). It shows the codex-prompt Build scaffold end to end: the Goal / Success means / Stop when spine, the control-field header block (Mode, Reasoning, Verification level), and the canonical Build phasing **A (data/SQL) → B (API) → C (UI)** with schemas pasted verbatim. It runs in **Hybrid** mode – the data and API phases are well-specified (Directive), while the share-token strategy carries one genuinely open decision surfaced as a Fork. It also shows the methodology's non-build-success proof rule: UI work closes only on an observable browser/curl check, not a green build.

## The generated prompt

```markdown
# Codex Build: Shareable read-only note links

Goal: add a "share read-only" feature so a note owner can mint a public, revocable link that renders the note read-only to anyone with the URL, no account required.

Success means:
  - Owner can mint and revoke a share token for any note they own; revocation is immediate.
  - `GET /share/:token` returns the note's title + rendered markdown (read-only) for a live token, 404 for a missing/revoked one.
  - The web client shows a "Share" control on a note that opens, copies, and revokes the link; the public `/s/[token]` page renders the note with no editor affordances.

Stop when: the three phases land, the new vitest specs pass, `pnpm build` is green, and the public share page renders a seeded note in a browser while a revoked token 404s.

> Mode: Hybrid (Directive on data + API; Investigative on the token-strategy Fork in Phase A, Step 1)
> Reasoning: high
> Depends on: none – greenfield feature on current `main`
> Verification level: local tests + browser pass

## Context

Acme Notes is an open-source, self-hostable markdown notes app: a Next.js (App Router) web client in `apps/web`, a Node/TypeScript API in `api`, Postgres for storage, and an `acme` import/export CLI in `packages/cli`. Notes today are private to their owner – there is no unauthenticated read path. This feature adds one: a per-note share token that grants read-only, account-free access via a public URL, with one-click revocation. Design spec lives at `docs/design/shareable-note-links.md`; read it before writing code.

Read `AGENTS.md` for project conventions (commit style, test commands, the "no deploy from a task" rule).

## Read these files FIRST

Data / schema:
  1. `db/migrations/` – existing migration naming + style
  2. `api/src/db/schema.ts` – Drizzle table defs (`notes` lives here)
  3. `api/src/notes/repository.ts` – how notes are read/written today

API:
  4. `api/src/notes/route.ts` – existing note route handlers + auth guard pattern
  5. `api/src/http/router.ts` – where routes are registered
  6. `api/src/auth/session.ts` – `requireOwner()` helper (the auth boundary you must NOT bypass for owner actions)

UI:
  7. `apps/web/src/lib/search.ts` – reference for the data-access + fetch-helper pattern the web client uses
  8. `apps/web/src/components/note/note-toolbar.tsx` – where the Share control mounts
  9. `apps/web/src/app/note/[id]/page.tsx` – authored-note render path to mirror for the public read-only page

Tests:
  10. `api/src/notes/route.test.ts` – vitest patterns for route specs

## Assumptions

- Tokens are unguessable, URL-safe, and stored hashed (treat the token like a bearer secret, never log the raw value).
- A note has at most one active share token at a time; re-sharing a note rotates the token (old link dies).
- Public read does not count toward any per-user rate limit tied to a session – it is anonymous traffic.

Fork – token storage shape (surfaced in Phase A, Step 1, decide before writing the migration): **(a)** a `share_token` text column + `share_revoked_at` timestamp directly on `notes`; **(b)** a separate `note_shares` table (note_id, token_hash, created_at, revoked_at) supporting future multi-link / audit. Default to **(b)** – it keeps `notes` clean, makes revocation a row update, and leaves room for per-link analytics without a second migration. Confirm before applying if (b) conflicts with anything in the repo you find while reading.

## Invariant

- Authored (owner) read/write paths and the `requireOwner()` auth boundary stay exactly as they are; the public path is purely additive.
- The existing `notes` columns and their `GET /notes/:id` JSON contract do not change shape.
- Markdown rendering on the public page uses the same renderer the authored page uses – no second, divergent sanitizer.

## Risk Gate

- Architectural fork on token storage (the Fork above) → if option (b) collides with repo reality, pause and report the two options with a recommendation; do not pick silently.
- Anything that would weaken `requireOwner()` or expose a write path on the public route → stop and report; the public surface is read-only by construction.
- Mechanical snags (a missing import, a test fixture to add, a migration-numbering nit) → fix-and-log, keep going; these are not halt conditions.

## Repo mismatch stop condition

If a cited file, export, table, or helper is missing or differently named (e.g. `requireOwner()` is actually `assertOwner()`, or `notes` uses a different ORM), stop and report the mismatch instead of inventing a shim.

## Not in scope

- Share-link expiry, password-protected links, or per-link view analytics (the `note_shares` shape leaves room; do not build them now).
- Email/social share affordances – the deliverable is copy-link + revoke only.
- The `acme` CLI (`packages/cli`) – no export/import changes this pass; touch on a report-only basis if you notice an interaction.

## Phase A: Data / schema

### Step 1: Decide the token shape (resolve the Fork), then write the migration

Resolve the storage Fork from Assumptions (default: separate `note_shares` table). Then add a migration following the `db/migrations/` naming style.

Target table (Drizzle, add to `api/src/db/schema.ts`):

\`\`\`ts
export const noteShares = pgTable("note_shares", {
  id: uuid("id").primaryKey().defaultRandom(),
  noteId: uuid("note_id")
    .notNull()
    .references(() => notes.id, { onDelete: "cascade" }),
  tokenHash: text("token_hash").notNull(),       // sha-256 of the raw token; raw is never stored
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
  revokedAt: timestamp("revoked_at", { withTimezone: true }),
}, (t) => ({
  tokenHashIdx: uniqueIndex("note_shares_token_hash_idx").on(t.tokenHash),
  noteActiveIdx: index("note_shares_note_active_idx").on(t.noteId, t.revokedAt),
}));
\`\`\`

"Active token for a note" = the row with `note_id = $1 AND revoked_at IS NULL`. Rotating = `UPDATE ... SET revoked_at = now()` on the active row, then INSERT a fresh one.

### Step 2: Repository helpers

In `api/src/notes/repository.ts`, add three functions next to the existing note accessors:

\`\`\`ts
createShare(noteId: string): Promise<{ token: string }>   // generates raw token, stores hash, rotates any active row
revokeShare(noteId: string): Promise<void>                // sets revoked_at on the active row
findNoteByShareToken(rawToken: string): Promise<Note | null> // hashes input, joins active row → note, null if revoked/missing
\`\`\`

Generate the raw token with `crypto.randomBytes(24).toString("base64url")`; store `createHash("sha256").update(raw).digest("hex")`. Return the raw token to the caller exactly once (mint time); never read it back.

## Phase B: API

### Step 1: Owner mutation routes (behind `requireOwner()`)

In `api/src/notes/route.ts`, register two owner-guarded handlers, matching the existing handler + guard pattern in that file:

- `POST /notes/:id/share` → `requireOwner` → `createShare(id)` → `201 { url }` where `url = ${PUBLIC_BASE_URL}/s/${token}`
- `DELETE /notes/:id/share` → `requireOwner` → `revokeShare(id)` → `204`

### Step 2: Public read route (no auth)

Register `GET /share/:token` in `api/src/http/router.ts` on the public, un-guarded path:

- Resolve via `findNoteByShareToken(token)`.
- Hit → `200 { title, markdown }` (markdown is the raw source; the web client renders it with the shared renderer).
- Miss/revoked → `404 { error: "not_found" }`. Return the same 404 for missing and revoked so a revoked token is indistinguishable from a never-existed one.

Add specs to `api/src/notes/route.test.ts`: mint → fetch (200) → revoke → fetch (404); and a random-token → 404.

## Phase C: UI

### Step 1: Share control on the authored note

In `apps/web/src/components/note/note-toolbar.tsx`, add a "Share" control that:

- calls `POST /notes/:id/share`, shows the returned URL, and offers Copy (writes to clipboard) + Revoke (`DELETE /notes/:id/share`).
- uses the existing fetch-helper + design-system primitives the toolbar already imports – no new colors, fonts, or one-off components.

### Step 2: Public read-only page

Add `apps/web/src/app/s/[token]/page.tsx` (App Router, Server Component):

- fetch `GET /share/:token` server-side; on 404 render `notFound()`.
- render title + markdown using the same renderer `apps/web/src/app/note/[id]/page.tsx` uses.
- render zero editor affordances: no toolbar, no save, no edit links. Mirror the authored read view's typography only.

## Constraints

- Read `docs/design/shareable-note-links.md` before writing code; build to the spec, not beyond it.
- Stay within the files listed under "Read these files FIRST" plus the new migration, `note_shares` schema, and `apps/web/src/app/s/[token]/page.tsx`. Report and pause if correctness needs a file outside this set.
- Keep the public route read-only by construction – no write handler shares its path prefix.
- Hash tokens at rest; never log or persist the raw token after mint.
- Do NOT use em dashes – en dashes for ranges and clauses.
- Do NOT add comments, docstrings, or types to code you did not change.
- Do NOT deploy. Commit and push only; verification is local tests + a local browser pass, never a deploy.

## Done when

- `pnpm test --filter api` passes, including the new mint → 200 → revoke → 404 spec and the random-token → 404 spec.
- `pnpm build` is green across `api` and `apps/web`.
- `pnpm typecheck` passes.
- Browser pass: with a seeded note and a freshly minted token, `/s/<token>` renders the note's title + markdown with no editor controls; after Revoke, the same URL renders the Next.js not-found page.

### Manual verification

\`\`\`bash
# token never leaks to logs or persists raw
rg -n "console\.log\(.*token" api/src apps/web/src
\`\`\`
Expected: zero results.

\`\`\`bash
# the public page exists and the routes are wired
rg -n "s/\[token\]|/notes/:id/share|/share/:token" apps/web/src api/src
\`\`\`
Expected: matches in 3 files – `apps/web/src/app/s/[token]/page.tsx`, `api/src/notes/route.ts`, `api/src/http/router.ts`.
```

## Why it's shaped this way

- **Phased A → B → C with verbatim schemas is the Build scaffold's core.** Each phase ships only what the next one needs to be deterministic: the Drizzle table and three repository signatures land before any handler references them, so Codex never has to guess a column name or a return shape mid-API-phase. Pasting the schema verbatim removes the single biggest source of cascade errors – a fabricated field.
- **It's Hybrid, not pure Directive, because exactly one decision is genuinely open.** Token storage (column-on-`notes` vs a `note_shares` table) is a real architectural Fork with downstream consequences, so it's surfaced as a labeled choice with a defaulted safest option (case b) rather than silently chosen. Everything else – the routes, the hashing, the render path – has one right answer and is Locked to exact specs, which is what keeps a multi-file feature from drifting.
- **The auth boundary is an explicit Invariant and a Risk Gate, not a hope.** `requireOwner()` and the existing `GET /notes/:id` contract are named as untouchable, and "weaken the auth boundary or expose a write path on the public route" is a hard halt. A security-sensitive surface (an unauthenticated read path) earns a true NEVER; routine snags stay skip-and-log so the work doesn't stall on a missing import.
- **UI work closes on an observable check, never on a green build.** Done-when requires a browser pass – the `/s/<token>` page rendering a seeded note read-only and a revoked token hitting the not-found page – because `pnpm build` passing proves the code compiles, not that the feature works. This is the methodology's non-negotiable proof rule for any UI deliverable.
- **The repo-mismatch stop condition and `rg` verification are the anti-fabrication guards.** Codex is told to halt on a renamed helper or a different ORM rather than invent a shim, and the closing `rg` checks assert concrete, repo-validated outcomes (no raw token in logs; the three wiring sites exist) instead of a vague "verified" – so completion is checkable, not asserted.
```