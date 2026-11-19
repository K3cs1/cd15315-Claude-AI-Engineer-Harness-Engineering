"""Deterministic tool-output pruning for the verbose `lookup_order` response.

The "Tool Context Pruning" pattern: application-side filtering
of a verbose tool result so only the fields needed for the immediate decision survive
into context. For return/refund reasoning, exactly five fields matter — order identity,
when it was placed, what it cost, whether it shipped, and the return-window deadline.

Why each kept field is the only one that matters for return/refund reasoning:
  - order_id: identifies which order the return/refund applies to, so the agent
    acts on the right record and can cite it back to the customer.
  - order_date: the return window starts at placement, so the agent needs it to
    reason about how long ago the purchase happened.
  - order_total_usd: caps the refund amount; the agent cannot refund more than
    the customer paid.
  - fulfillment_status: decides routing — refund a delivered order via the
    return flow, versus cancel one that has not shipped.
  - return_eligible_until: the deadline itself; comparing it to today gives the
    eligible / not-eligible decision directly.

Implementation: deterministic field selection (no LLM call). The pruner has no
`anthropic` import — enforced by an AST audit.
"""
from __future__ import annotations

KEPT_FIELDS: tuple[str, ...] = (
    "order_id",
    "order_date",
    "order_total_usd",
    "fulfillment_status",
    "return_eligible_until",
)


class PrunerMissingFieldError(KeyError):
    """Raised when the raw tool response is missing one of the required kept fields."""


def prune_lookup_order(raw: dict) -> dict:
    missing = [f for f in KEPT_FIELDS if f not in raw]
    if missing:
        raise PrunerMissingFieldError(
            f"lookup_order response missing required fields: {', '.join(missing)}"
        )
    return {f: raw[f] for f in KEPT_FIELDS}
