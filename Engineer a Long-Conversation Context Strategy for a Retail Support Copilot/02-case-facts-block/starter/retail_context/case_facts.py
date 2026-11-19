"""Case-facts extraction into a persistent block at the top of context.

Extraction is LLM-driven: one Claude call against the full transcript that returns
strict JSON for the 12 required fields. This is commonly called a *scratchpad* — same
concept, different word: a dense structured block that survives compression and is
placed at the top boundary of context so the model can recover transactional facts
without scanning thousands of tokens of narrative.

Missing-field behavior raises `CaseFactExtractionError` listing the gaps — silent
null-fill is forbidden.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from retail_context.client import complete_with_system, get_model
from retail_context.transcript import Transcript

# The 12-field contract for the case-facts block. Order matters: to_markdown()
# renders in this order, and each name is the exact JSON key the extraction
# prompt requires the LLM to return.
REQUIRED_FIELDS: tuple[str, ...] = (
    "customer_id",
    "refund_order_id",
    "refund_amount_usd",
    "refund_status",
    "subscription_id",
    "subscription_plan",
    "subscription_cancel_reason",
    "subscription_status",
    "active_payment_method_last4",
    "new_payment_method_last4",
    "payment_update_failure_code",
    "payment_update_status",
)


@dataclass
class CaseFacts:
    customer_id: str
    refund_order_id: str
    refund_amount_usd: float
    refund_status: str
    subscription_id: str
    subscription_plan: str
    subscription_cancel_reason: str
    subscription_status: str
    active_payment_method_last4: str
    new_payment_method_last4: str
    payment_update_failure_code: str
    payment_update_status: str

    def to_markdown(self) -> str:
        return "\n".join(
            [
                "# Case Facts",
                "",
                "**Customer**",
                f"- customer_id: {self.customer_id}",
                "",
                "**Refund (resolved)**",
                f"- refund_order_id: {self.refund_order_id}",
                f"- refund_amount_usd: {self.refund_amount_usd:.2f}",
                f"- refund_status: {self.refund_status}",
                "",
                "**Subscription (resolved)**",
                f"- subscription_id: {self.subscription_id}",
                f"- subscription_plan: {self.subscription_plan}",
                f"- subscription_cancel_reason: {self.subscription_cancel_reason}",
                f"- subscription_status: {self.subscription_status}",
                "",
                "**Payment update (active)**",
                f"- active_payment_method_last4: {self.active_payment_method_last4}",
                f"- new_payment_method_last4: {self.new_payment_method_last4}",
                f"- payment_update_failure_code: {self.payment_update_failure_code}",
                f"- payment_update_status: {self.payment_update_status}",
            ]
        )


class CaseFactExtractionError(ValueError):
    def __init__(self, missing: list[str], raw: dict[str, Any]):
        super().__init__(f"case-facts extraction missing required fields: {missing}")
        self.missing = missing
        self.raw = raw


_SYSTEM_PROMPT = """You extract transactional case facts from a customer-support transcript.

Return EXACTLY one JSON object and nothing else: no prose, no markdown, no code fences.

The object MUST contain exactly these 12 keys, in this order:
customer_id, refund_order_id, refund_amount_usd, refund_status,
subscription_id, subscription_plan, subscription_cancel_reason, subscription_status,
active_payment_method_last4, new_payment_method_last4,
payment_update_failure_code, payment_update_status

Rules:
- Every key is required. If the transcript does not state a value, set it to null.
  NEVER guess, infer, or invent a value.
- Use the LATEST state stated in the transcript for each field (e.g. the final status of
  each issue), not an earlier or superseded value.
- Identifiers (customer_id, refund_order_id, subscription_id) are copied verbatim,
  e.g. "CUST-88421", "ORD-77310", "SUB-22119".
- refund_amount_usd is a JSON number (e.g. 22.14), not a string, with no currency symbol.
- *_last4 fields are 4-digit strings (keep leading zeros), e.g. "4242".
- Status tokens and codes (refund_status, subscription_status, subscription_cancel_reason,
  payment_update_status, payment_update_failure_code) are preserved verbatim as they appear
  in the transcript or tool output, in snake_case / original casing
  (e.g. "processed", "in_progress", "AVS_MISMATCH"). Do not paraphrase into natural language.
- subscription_plan is the plan name as written in the transcript.
"""


def _parse_json(raw: str) -> dict[str, Any]:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]
        if raw.rstrip().endswith("```"):
            raw = raw.rsplit("```", 1)[0]
    return json.loads(raw)


def extract(
    transcript: Transcript,
    *,
    model: str | None = None,
    log_path: Path | None = None,
) -> CaseFacts:
    user = f"Transcript:\n\n{transcript.full_text}"
    target_model = model or get_model()
    text, in_tok, out_tok = complete_with_system(
        _SYSTEM_PROMPT, user, model=target_model, max_tokens=2048
    )
    parsed = _parse_json(text)

    if log_path is not None:
        log_path = Path(log_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(
            json.dumps(
                {
                    "model": target_model,
                    "input_tokens": in_tok,
                    "output_tokens": out_tok,
                    "parsed": parsed,
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    missing = [f for f in REQUIRED_FIELDS if parsed.get(f) is None or parsed.get(f) == ""]
    if missing:
        raise CaseFactExtractionError(missing=missing, raw=parsed)

    values: dict[str, Any] = {f: str(parsed[f]) for f in REQUIRED_FIELDS}
    values["refund_amount_usd"] = float(parsed["refund_amount_usd"])
    return CaseFacts(**values)


def to_dict(facts: CaseFacts) -> dict[str, Any]:
    return asdict(facts)
