---
description: Review a pull request or diff against this repo's conventions and report categorized findings
argument-hint: <PR number, PR URL, diff range like main...HEAD, or file path>
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash(git diff:*)
  - Bash(git log:*)
  - Bash(git show:*)
  - Bash(git status:*)
  - Bash(gh pr view:*)
  - Bash(gh pr diff:*)
  - Bash(gh pr checks:*)
---

# /review — team PR review

You are reviewing the diff identified by `$ARGUMENTS` against this repository's conventions. Apply the path-scoped rules in `.claude/rules/` (they auto-load based on the files touched) and the shared standards in `.claude/standards/`.

## Phase 1 — Interview pattern

Ask clarifying questions BEFORE reporting findings whenever the author's intent is ambiguous. Without this step the reviewer commits to a confidently wrong verdict (e.g. "no test coverage" on a refactor whose behavior is already covered upstream) and the author has to argue it back. Ask first, then review with the answers.

Interview (ask 1-3 focused questions, then wait) when the diff shows any of these triggers:

- **Dependency changes** — `package.json` or `pyproject.toml` diffs: why is it added/bumped, and is a lighter or existing option unsuitable?
- **Public API response shape or DB column changes** — is this backward compatible, and is there a migration/rollout plan for existing clients and data?
- **Refactors with no test changes** — is existing coverage expected to catch regressions, and where does it live?
- **Multi-surface changes** — API + components + DB touched at once: which surface is the source of truth, and can they ship independently?

If none of these apply and intent is clear, skip the interview and go straight to Phase 2.

## Phase 2 — Review criteria

**Must report** (these block approval):

- **Bugs** — logic errors, missing `await`, race conditions, off-by-one errors, unhandled error paths.
- **Security** — raw SQL built from user input, missing authentication/authorization, secrets in code, `dangerouslySetInnerHTML` with unsanitized data.
- **Convention violations** caught by the path-scoped rules in `.claude/rules/` and `.claude/standards/` (e.g. returning `{ status: 404 }` instead of throwing `ApiError`, bypassing the repository layer).
- **Breaking changes** — response shape changes without a schema update, removed or renamed public fields.
- **Migration safety** — non-forward migrations, bad filename sequence, destructive changes without a plan, multi-statement writes outside `withTransaction`.

**Skip** (do not report; never block on these):

- Minor formatting — Prettier handles it.
- Naming bikeshedding when the existing name is clear and fine.
- Personal stylistic preferences not encoded in rules or standards.
- TODOs that already reference a tracked ticket.

When unsure whether something is must-report, ask in the interview phase rather than guessing.

## Phase 3 — Bundling: interacting vs. independent findings

**Interacting findings** overlap or share a single fix. Bundle them into ONE detailed message with all context, because the author must see them together — the fix changes the same lines. Example: a missing `await` and a missing transaction wrapper in the same function.

**Independent findings** touch separate functions or files and share no fix. Report them sequentially as discrete items, one at a time, so each piece of feedback is actionable on its own.

Heuristic: if fixing A changes the code that B references, they are interacting; otherwise they are independent.

## Phase 4 — Output format

For each finding, produce:

```
[severity] path/to/file.ts:line
finding: <one-sentence description>
fix: <one-sentence recommendation>
```

Severity is `bug` | `security` | `convention` | `breaking`. End with a one-line verdict: `approve`, `comment`, or `request-changes`.

## Examples

### Example 1 — independent findings

Input:

```
/review main...feature/order-lookup

--- a/src/api/orders/handler.ts
+++ b/src/api/orders/handler.ts
+export async function getOrder(req) {
+  const order = await orderRepo.findById(req.params.id);
+  if (!order) return { status: 404, body: { error: "not found" } };
+  return { status: 200, body: order };
+}
+
+export async function listRecent(req) {
+  const rows = await pool.query(`SELECT * FROM orders WHERE user_id = ${req.query.userId}`);
+  return { status: 200, body: rows };
+}
```

Output:

```
[convention] src/api/orders/handler.ts:3
finding: getOrder returns a `{ status: 404 }` body instead of throwing ApiError.
fix: Replace with `throw new ApiError(404, "order_not_found", "Order not found")`.

[convention] src/api/orders/handler.ts:8
finding: listRecent calls pool.query directly, bypassing the repository layer (and interpolating user input into SQL).
fix: Add a typed `listRecentByUser` function in src/db/orders.ts using parameterized queries and call that.

verdict: request-changes
```

The two findings are in separate functions with no shared fix, so they are reported separately.

### Example 2 — interacting findings

Input:

```
/review 482

--- a/src/api/orders/refund.ts
+++ b/src/api/orders/refund.ts
+export async function refundOrder(req) {
+  const order = orderRepo.findById(req.params.id);
+  paymentService.refund(order.paymentId, order.total);
+  pool.query("UPDATE orders SET status = 'refunded' WHERE id = $1", [order.id]);
+  return { status: 200, body: { id: order.id } };
+}
```

Output:

```
[bug] src/api/orders/refund.ts:2-5
finding: Three linked problems in refundOrder: (1) `findById`, `paymentService.refund`, and the status update are all missing `await`, so `order` is a Promise and errors are swallowed; (2) the DB update is not wrapped in `withTransaction`; (3) the payment is refunded before the DB write, so a DB failure leaves money refunded with the order still marked paid.
fix: Rewrite as `await withTransaction(async (tx) => { const order = await orderRepo.findById(id, tx); await orderRepo.markRefunded(order.id, tx); await paymentService.refund(order.paymentId, order.total); })` — awaiting everything, inside one transaction, with the DB write first so the payment call failing rolls it back.

verdict: request-changes
```

These are bundled into one finding because the fix changes the same lines.

## Notes

- This command is project-scoped (`.claude/commands/review.md`) so everyone on the team gets the same review. If you want to layer personal preferences (e.g. a stricter accessibility check on your own PRs), put a `~/.claude/commands/review-strict.md` in your home directory — it will not affect teammates.
- If a finding requires running code or modifying files to verify, ask the author to run a specific check rather than attempting it from the review session. This command's `allowed-tools` are read-only by design.
