# Reflection Brief — Harness Engineering Capstone

**Name:** Pal Kecskemeti
**Date:** 2026-11-19

Replace each `→` with your answer. **Every answer cites at least one artifact from your own runs** — a run ID, file path, token count, claim outcome, or test count. Uncited answers do not pass. 3–6 sentences each unless noted. Paste short artifact snippets where they help.

**Environment**

- Model(s): Systems 1 and 2 not run live (no `ANTHROPIC_API_KEY`). System 4 ran offline from `fixtures/recorded_responses/shift_C_2026-04-30.json` (no model call). System 3 needs no model.
- OS / Python: Windows 11 / Python 3.14.5, one venv per system (`evidence/system*/install.log`, all installs exit 0)
- Approx. API spend: $0 (no live API calls made)

---

## Part 1 — Per-system

### System 1 — Agentic loop

1. **Loop control.** Quote the `stop_reason` sequence from one trace. Name the file and function that decides continue-vs-stop, and how.
   → **NOT ANSWERABLE YET:** no live trace (no API key; `evidence/system1/` has only `pytest.log`, 30 passed). From code: `claims_intake/loop.py` continues iff `response.stop_reason == "tool_use"` (line 113), returns on `"end_turn"` (line 103) and raises `UnexpectedStopReason` for anything else (line 131). The expected sequence is `tool_use ... tool_use, end_turn`; a real trace still needs to be quoted once a run exists.

2. **Anti-pattern.** Name one anti-pattern `test_antipatterns.py` checks for. What would break in your run if the loop used it?
   → `tests/test_antipatterns.py` has `test_no_integer_literal_iteration_cap_in_loop` (it also checks string-membership on text and claim-type branching; 30 passed, `evidence/system1/pytest.log`). A hard cap such as `for _ in range(5)` would cut off a claim that needs more tool turns mid-work. The failure impact in a real run is not observed, since no run was made.

3. **Tool design.** Pick two tools with overlapping inputs. How do the descriptions prevent misrouting? What did a structured tool error let the agent do that a generic string would not?
   → `claims_intake/tools.py` defines `classify_claim`, `assess_severity`, `route_to_adjuster`, `escalate_to_human`, `request_clarification`, `record_claim_fact` and `lookup_policy`. I did not analyze their descriptions or error payloads closely and have no run showing structured errors in use. **NOT ANSWERABLE YET:** needs a run and a closer read.

4. **Your numbers.** Quote the turn count and cost for one claim. How does it differ from the README sample, and why?
   → **NOT ANSWERABLE YET:** no turn count or cost exists because the system was not run (needs `ANTHROPIC_API_KEY`).

### System 2 — Context strategy

5. **The reduction.** From `budget.json`: baseline tokens, assembled tokens, reduction %. Which section dominates the assembled context, and why keep it verbatim?
   → **NOT ANSWERABLE YET:** `budget.json` was never produced. `python -m retail_context.run --build` computed a baseline of 47,144 tokens (`data/transcript_48turns.json`), then failed at the case-facts LLM call. The README's 50% reduction target is unverified here.

6. **Summarize vs preserve.** State the rule for what gets summarized vs kept byte-exact, citing your per-section token numbers.
   → **NOT ANSWERABLE YET:** no per-section token numbers. Code basis: `tests/test_antipatterns.py::test_assembled_context_active_segment_byte_exact` requires the active segment (turns 29-48) to be byte-exact. That test was SKIPPED in my run (`evidence/system2/pytest_after_build.txt`: 28 passed, 2 skipped) because no `runs/` artifact exists.

7. **Facts block.** Compare `eval.jsonl` to `eval_control.jsonl`. Which question regressed, and what does that prove?
   → **NOT ANSWERABLE YET:** `eval.jsonl` and `eval_control.jsonl` were not generated.

### System 3 — Claude Code config

8. **Path-scoped rules.** Quote the glob frontmatter from one rule file. Why is it better than a directory-level CLAUDE.md for cross-cutting conventions?
   → `.claude/rules/api.md` frontmatter: `paths:` with `- "src/api/**/*"`. The rule loads only when Claude touches matching files, so conventions for a cross-cutting area apply by file pattern rather than by directory. A directory CLAUDE.md cannot follow files spread across folders, and a root CLAUDE.md would load every convention into every task. Evidence: validator printed `OK`, exit 0 (`evidence/system3/validator.txt`); the tree lists `rules/api.md`, `react.md`, `tests.md` (`evidence/system3/claude_tree.txt`).

9. **Forked skill.** Quote the `context: fork` and `allowed-tools` lines. What does running forked + read-only buy you? What breaks without it?
   → `.claude/skills/deploy-check/SKILL.md`: `context: fork` and `allowed-tools: Read, Grep, Glob, Bash(git status:*), Bash(git diff:*), Bash(git log:*)`. The fork runs in an isolated sub-agent, so verbose checking output stays out of the main session and only a pass/fail summary returns. The read-only allowlist means a deploy check cannot edit files or run arbitrary shell. Without it, a check could modify the repo it validates and flood the main context. 35 passed (`evidence/system3/pytest.log`).

10. **Scope.** From the validator output: project-level vs user-level scope. Give one example of each from this config.
    → The validator (`ecommerce_team_config/claude_md.py`, `__main__.py:67`) requires `CLAUDE.md` to document both scopes and say user scope is not version-controlled; it printed only `OK`, so it does not print scope examples. Project-level example: `.claude/rules/api.md` and `.claude/skills/deploy-check/`, committed and shared with the team. User-level example: `~/.claude/` personal preferences, not shared. See `CLAUDE.md` in System 3's `solution/` for the documented examples.

### System 4 — Orchestration

11. **Push work down.** Defects the SQL query returned vs warm-tier total. Name the indexed query. Why does the model never see the full history?
    → The warm tier holds 40 defects (`SELECT COUNT(*)` on `data/warm.sqlite`, seeded from `fixtures/defects.json`). The shift-C run logged `run_shift done: shift=C new=0` (`evidence/system4/shift_output.txt`), so the query returned 0 rows: its window is anchored to the real clock (2026-11-19) while the fixtures are dated April 2026. The query is `defects_since` (`SELECT * FROM defects WHERE ts > ? ORDER BY ts DESC LIMIT ?`, limit 50), backed by `idx_defects_ts` in `warm.py`. The model only sees that bounded result plus the small hot state, never the history.

12. **Crash recovery.** The resume-vs-fresh decision and its staleness threshold (`recovery.py`). Why is a fresh start with an injected summary sometimes more reliable than resuming?
    → `recovery.py`: `decide()` returns `"fresh"` if there are no steps or the manifest is complete, `"resume"` if the last step is at most `STALE_RESUME_THRESHOLD_MINUTES = 30` old, otherwise `"fresh"`. I did not exercise a crash, so this is from code and the 33 passing tests (`evidence/system4/pytest.log`). A stale partial session may carry outdated tool results, so restarting with a summary of manifest findings gives a clean, bounded context.

13. **Small state.** Byte size of your `hot_state.json`. Why does the budget matter for a system run once per shift, indefinitely?
    → `evidence/system4/hot_state_size.txt`: `hot_state.json` is 658 bytes, against `HOT_STATE_BYTE_BUDGET = 5_120` in `state.py`; `write_atomic` raises if exceeded and writes via `os.replace`. The state is injected into every prompt on every shift indefinitely, so unbounded growth would eventually crowd out working context. A hard budget forces compaction now rather than failing later.

---

## Part 2 — Synthesis

*Graded on connecting two or more systems. Cite a named file/artifact from each.*

14. **Three layers.** Point to a file/artifact for each layer and justify.
    → Model: Claude calls via `claims_intake/client.py` (System 1); not exercised live. The recorded response `shift_C_2026-04-30.json` stood in for the model in System 4.
    → Harness: `claims_intake/loop.py` (stop_reason loop) and `.claude/skills/deploy-check/SKILL.md` (tool allowlist).
    → Orchestration: `shift_monitor/recovery.py` and `state.py`, which decide resume vs fresh and persist the hot state.

15. **Deterministic vs prompt.** Cite one behavior guaranteed in code (terminal tool, read-only allowlist, atomic write, byte budget) and one guided by prompt. When is each right?
    → Code-guaranteed: the 5,120-byte hot-state budget with atomic write (`state.py`; my file is 658 bytes) and the read-only allowlist in `deploy-check/SKILL.md`. Prompt-guided: the lot-quarantine recommendation in the System 4 summary (`evidence/system4/shift_output.txt`). Use code for invariants whose violation is costly or silent, and prompts for judgment that varies by input.

16. **Context, two faces.** Compare context management in System 2 (intra-session) and System 4 (cross-session) with cited numbers from both. Same principle, different mechanism — how?
    → **NOT ANSWERABLE YET:** needs System 2's assembled-token numbers. System 4 side: 658-byte hot state under a 5,120-byte cap and a 40-row warm store. System 2 side: only the 47,144-token baseline exists.

17. **Reliability you can't see in one run.** Name one behavior a test guarantees that a single successful run would not reveal. Why does it matter before shipping?
    → `test_antipatterns.py::test_assembled_context_active_segment_byte_exact` (System 2) guarantees byte-exact preservation of the active turns, which a single run's output would not prove. In my environment it SKIPPED for lack of run artifacts, so that guarantee is unverified here. Such tests matter before shipping because a regression would otherwise be silent.

18. **Blast radius.** Pick one system. What's the blast radius if it misbehaves, and what's the kill switch? Ground it in that system's tools, enforcement points, and state.
    → System 3: `deploy-check` is limited to Read/Grep/Glob and `git status|diff|log`, so a misbehaving fork cannot write or push; the blast radius is a wrong report. The enforcement point is `allowed-tools` in `SKILL.md`, and the kill switch is editing or deleting that file or not invoking the skill. No state is mutated. Validator `OK` (`evidence/system3/validator.txt`).

---

## Part 3 — Honest assessment

19. **What broke.** One thing that failed first try in your environment, and how you fixed it. (If nothing, what you checked to be sure.)
    → (1) My first venv install failed because I used a short 8.3 temp path and ran `pip install -e "<dir>[dev]"` from outside the project; I fixed it with the long path and by running `pip install -e ".[dev]"` inside each `solution/` (`install.log`). (2) `python -m retail_context.run --build` raised `FileNotFoundError: [WinError 206] The filename or extension is too long` partway through, after counting the 47,144-token baseline; I did not investigate it. (3) With no API key, Systems 1 and 2 could not run.

20. **What you'd change.** One architectural decision you'd make differently, grounded in what you observed.
    → I would not anchor System 4's query window to the wall clock. With fixtures dated April 2026 the offline run reports `new=0` while the recorded summary describes 5 defects (`evidence/system4/shift_output.txt`), so output and data disagree. Passing the shift's reference time explicitly would make the offline run reproducible.
