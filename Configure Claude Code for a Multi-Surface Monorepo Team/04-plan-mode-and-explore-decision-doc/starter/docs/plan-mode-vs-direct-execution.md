# Plan mode vs. direct execution — team decision guide

Choosing between Claude Code's **plan mode** (investigate and propose before changing anything) and **direct execution** (change code immediately) is the single biggest leverage point in how the team uses the harness day-to-day. The wrong mode at either extreme costs us: plan mode for trivial fixes is friction; direct execution for architectural changes burns context and produces rework.

> *Anchor talk: Knight-Webb, "SWE Is Becoming Plan and Review." The framing for this decision: pick the mode by the shape of the work, not its size.*

This doc walks four concrete decisions against our codebase: one plan-mode example, one direct-execution example, one Explore-subagent example, and one combined-workflow example.

---

## 1. Plan-mode example

**Task:** extract a shared `useCart(userId)` hook from the three components that each duplicate the cart-fetching pattern: `src/components/Cart/Cart.tsx`, `src/components/Checkout/Checkout.tsx`, and `src/components/MiniCart/MiniCart.tsx`.

**Why plan mode:** this hits every plan-mode criterion: a large-scale change, multiple valid approaches (a plain hook, a context provider, or a data-fetching library), an architectural decision (where cart state lives and who owns invalidation), and multi-file modification across three components plus a new hook module. The extraction target is a file that doesn't exist yet, so we name it in prose (a new hooks module for `useCart`) rather than by path.

Plan mode lets Claude read all three components, compare how each handles loading and error state, and propose one design for us to review before any file changes. Settling the hook's signature up front is what lets us prevent costly rework: if we discover after editing two components that the third needs a different return shape, we would redo the first two. This is the Knight-Webb principle: review the plan, not the diff.

---

## 2. Direct-execution example

**Task:** reject negative quantities in the order handler, in `src/api/orders/handler.ts`, by adding a `min: 0` style check to the quantity validation (the schema lives in `src/api/_schemas/orders.ts`, but the edit is one check).

**Why direct execution:** this is a simple, well-scoped change: one function, one check, no design choices. We can describe it in one sentence and already predict the patch, so a planning round trip would cost more than the change itself.

**The bar:** if you, the author, know what the diff looks like before invoking Claude, skip planning. Ask for the change, read the diff, run the tests. If you catch yourself unsure which function or file is involved, you are not past the bar; switch to plan mode.

---

## 3. Explore-subagent example

**Task:** find every place we call `processRefund` before we change its signature. Known candidates are `src/api/orders/refund.ts`, `src/api/billing/issue.ts`, and the definition in `src/services/payment.ts`.

**Why an Explore subagent:** discovery produces verbose output (grep hits, file excerpts, dead ends) that we will never need again once we have the answer. Delegating to an Explore subagent isolates verbose discovery output from the main conversation and returns only a summary, preserving main-session context for the actual change.

**Scratchpad pattern:** instruct the subagent to write its working notes to a scratchpad file such as `tmp/refund-callsites.md` (call site, caller function, argument shape). This scratchpad pattern means the inventory survives context compaction and can be re-read later by the main session or a fresh one, rather than living only in a chat summary.

---

## 4. Combined workflow — plan mode for investigation, then direct execution

**Task:** rename `ordersRepo.findById` to `ordersRepo.getById` in `src/db/orders.ts` to follow the team convention (`get*` for single-row reads, `find*` for multi-row).

**Why combine them:** the call-site list is unknown at the start. Static grep finds `src/api/orders/refund.ts` and `src/api/billing/issue.ts`, but dynamic lookups (method names built from strings) would be missed. That discovery is plan-mode work. Once the list is known, the rename is mechanical keystrokes, which is direct-execution work. This is combining plan mode for investigation with direct execution for implementation.

**Flow:**

1. **Plan mode investigates and proposes.** Claude searches for every call site, flags any dynamic lookups grep can't see, and proposes the full edit list.
2. **You approve the plan.** Check the list, especially the dynamic cases, and correct it if needed.
3. **Direct execution applies the rename and runs the tests.** No more planning; make the edits, run the suite, and confirm nothing still references `findById`.

---

## Quick reference

| Situation | Mode |
|-----------|------|
| Single function, fix is obvious, you can predict the diff | Direct execution |
| Multi-file refactor, API shape is debatable | Plan mode |
| Discovery / inventory across the codebase, you'll throw away the intermediate steps | Explore subagent |
| Investigation-then-mechanical-change | Plan mode → direct execution |
| Architectural decision (which database, which queue) | Plan mode, possibly with a fork to compare options |

When in doubt: plan mode is recoverable (you can switch to execution), but direct execution on a complex change is not. Default to plan when uncertain.
