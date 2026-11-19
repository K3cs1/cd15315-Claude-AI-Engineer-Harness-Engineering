---
description: Conventions for co-located test files (*.test.ts / *.test.tsx) across the tree
paths:
  - "**/*.test.ts"
  - "**/*.test.tsx"
---

# Test file rules

Loads when editing any co-located `*.test.ts` or `*.test.tsx` file. These layer on top of the React rules (for tests under `src/components/` / `src/pages/`) and the API rules (for tests under `src/api/`). See `.claude/standards/testing.md` for the cross-cutting expectations.

## Structure

- One top-level `describe("<UnitName>", ...)` per file, named after the module under test (`describe("Cart", ...)` in `Cart.test.tsx`).
- Test names state behavior in plain language: `it("shows the empty state when there are no items")` — not `it("works")` or `it("test 1")`.
- Arrange / act / assert in that order, with a blank line between each phase. One behavior per `it`.

## Component tests (`*.test.tsx`)

- Query with Testing Library's accessible queries: `getByRole`, `getByLabelText`, `getByText`. `getByTestId` is a last resort and needs a comment explaining why no accessible query works.
- Simulate interaction with `userEvent` (awaited), not `fireEvent`.
- Snapshot tests (`toMatchSnapshot`, `toMatchInlineSnapshot`) are forbidden — assert on the specific user-visible output instead.

## API handler tests (`*.test.ts` under `src/api/`)

- Call the exported `handle(req)` directly with a request object and assert on the returned `{ status, body }`. Never start an HTTP server or use `supertest`.
- Assert expected failures with `await expect(handle(req)).rejects.toMatchObject({ status: 400, code: "EMPTY_ORDER" })` — check the `ApiError` `code`, not the message string.

## Forbidden in any test

- `setTimeout` / real-time waits. Use `vi.useFakeTimers()` or Testing Library's `findBy*` / `waitFor`.
- Mocking `@/db/*` modules (`vi.mock("@/db/orders")` etc.). Repository and handler tests hit the real PostgreSQL test instance.
- `.only` and `.skip` left in committed code.
