---
description: Enforcement rules for Node.js API handlers under src/api/
paths:
  - "src/api/**/*"
---

# API handler rules

Loads when editing any file under `src/api/`. Layers on top of `.claude/standards/api.md`.

## Handler signature

- Every handler module exports `export async function handle(req: ApiRequest<TBody>): Promise<ApiResponse<TResponse>>`, typed with `ApiRequest` / `ApiResponse` from `@/api/_lib/types`.
- Declare `TBody` and `TResponse` as named interfaces in the same file (e.g. `OrderCreateBody`, `OrderCreateResponse`). No inline object types in the signature, no `any`.
- Return a plain `{ status, body }` object. Never touch a `res` object, call `res.send()`, or set headers from handler code.

## Validation

- The first statement of a handler that reads `req.body` is a `zod` parse against the matching schema from `@/api/_schemas/` (e.g. `orderCreateSchema.parse(req.body)`). Use the parsed value afterward — never read `req.body` again.
- New request shapes get a new schema file in `src/api/_schemas/`; do not define `z.object(...)` inline in a handler.

## Errors

- Expected failures throw `new ApiError(status, code, message)` imported from `@/api/_lib/error`. `code` is an `UPPER_SNAKE_CASE` string (e.g. `"EMPTY_ORDER"`) that clients can switch on.
- `throw new Error(...)` and `return { status: 4xx, ... }` for error cases are both forbidden in `src/api/` — route all expected errors through `ApiError`.

## Data access boundary

- Handlers talk to the database only through repository modules in `src/db/` (e.g. `ordersRepo` from `@/db/orders`).
- Never import `@/db/pool` or `@/db/tx` directly from a handler, and never write raw SQL in `src/api/`. If a handler needs a transaction, add a repository method that owns it.
- Handlers under `src/api/` must not import from `src/components/` or `src/pages/`.
