"""Three invocation shapes.

thin     — prompt only.
rich     — hot state + new defects.
resumed  — prior partial findings + new defects since the last manifest step.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal

from .state import HotState

InvocationShape = Literal["thin", "rich", "resumed"]


@dataclass(frozen=True)
class Invocation:
    shape: InvocationShape
    prompt: str


def thin(prompt: str) -> Invocation:
    return Invocation(shape="thin", prompt=prompt)


def _truncate(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: limit - 3] + "..."


def rich(
    role: str, hot_state: HotState, new_defects: Sequence[Mapping[str, Any]]
) -> Invocation:
    lines = [
        f"You are the on-call {role} for Northridge Plant 3.",
        "",
        "## Current hot state",
        f"- recent_defect_hashes: {', '.join(hot_state.recent_defect_hashes) or '(none)'}",
        f"- current_shift_summary: {hot_state.current_shift_summary}",
        f"- active_alerts: {'; '.join(hot_state.active_alerts) or '(none)'}",
        f"- threshold_statuses: {json.dumps(hot_state.threshold_statuses, sort_keys=True)}",
        "",
        "## New defects since last shift",
    ]
    if new_defects:
        for d in new_defects:
            lines.append(
                f"- {d.get('id')} | {d.get('ts')} | shift {d.get('shift')} | "
                f"{d.get('component')} | {d.get('severity')} | "
                f"{_truncate(str(d.get('description', '')), 200)}"
            )
    else:
        lines.append("- (none)")
    lines += [
        "",
        "Respond with these sections: Summary, Findings, Recommended actions, "
        "and an Updated hot state proposal as a ```json block with keys "
        "current_shift_summary, active_alerts, threshold_statuses.",
    ]
    return Invocation(shape="rich", prompt="\n".join(lines))


def resumed(
    session_id: str,
    summary: str,
    latest_message: str,
    prior_steps: Sequence[Mapping[str, Any]],
    new_defects: Sequence[Mapping[str, Any]],
) -> Invocation:
    lines = [f"Resuming session {session_id}.", "", "## Prior partial findings"]
    if prior_steps:
        for step in prior_steps:
            payload = _truncate(json.dumps(step.get("payload"), default=str), 200)
            lines.append(f"- {step.get('name')}: {payload}")
    else:
        lines.append("- (none)")
    lines += ["", "## Prior summary", summary, "", "## New defects since last partial step"]
    if new_defects:
        for d in new_defects:
            lines.append(
                f"- {d.get('id')} | {d.get('ts')} | {d.get('component')} | "
                f"{d.get('severity')} | {_truncate(str(d.get('description', '')), 200)}"
            )
    else:
        lines.append("- (none)")
    lines += ["", "## Latest instruction", latest_message]
    return Invocation(shape="resumed", prompt="\n".join(lines))
