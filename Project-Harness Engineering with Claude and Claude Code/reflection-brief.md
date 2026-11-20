# Reflection Brief — Harness Engineering Capstone

**Name:** Pal Kecskemeti
**Date:** 2026-11-20 (resubmission)

Replace each `→` with your answer. **Every answer cites at least one artifact from your own runs** — a run ID, file path, token count, claim outcome, or test count. Uncited answers do not pass. 3–6 sentences each unless noted. Paste short artifact snippets where they help.

**Environment**

- Model(s): Systems 1 and 2 ran live on 2026-11-20 through the course proxy; System 1's `summary.md` records `claude-haiku-4-5-20251001`. Run artifacts are copied to `evidence/system1/run_20261120_083822/` (run `20261120_083822`) and `evidence/system2/run_20261120-083949/` (run `20261120-083949`). An earlier System 2 run, `20261119-173134`, is in `evidence/system2/run_20261119-173134/`. System 4 ran offline from `fixtures/recorded_responses/shift_C_2026-04-30.json`. System 3 needs no model.
- OS / Python: Windows 11 host; commands run in WSL Debian with Python 3.13.5 using each system's existing `.venv` (the earlier Windows runs used Python 3.14.5, `evidence/system*/install.log`)
- Approx. API spend: System 1 estimated total **$0.1206** for 8 claims (`evidence/system1/run_20261120_083822/summary.md`); System 2 token usage is in `compression_api` of its `budget.json` (about 23.8k input tokens for the two compressions, plus the case-facts and eval calls). Total well under $1.

---

## Part 1 — Per-system

### System 1 — Agentic loop

1. **Loop control.** Quote the `stop_reason` sequence from one trace. Name the file and function that decides continue-vs-stop, and how.
   → Trace `evidence/system1/run_20261120_083822/traces/claim_04_neighbor_injury.jsonl` has this `stop_reason` sequence: turn 1 `tool_use` (`lookup_policy`), 2 `tool_use` (5x `record_claim_fact`), 3 `tool_use` (`classify_claim`, `assess_severity`), 4 `tool_use` (`route_to_adjuster`), 5 `end_turn`. `claims_intake/loop.py` `run()` continues iff `response.stop_reason == "tool_use"` (line 113), returns on `"end_turn"` (line 103), and raises `UnexpectedStopReason` for anything else (line 131). `evidence/system1/pytest.log` shows 30 passed.

2. **Anti-pattern.** Name one anti-pattern `test_antipatterns.py` checks for. What would break in your run if the loop used it?
   → `tests/test_antipatterns.py` has `test_no_integer_literal_iteration_cap_in_loop` (it also checks string-membership on text and claim-type branching; 30 passed, `evidence/system1/pytest.log`). In my run the claim_04 trace needed 5 turns and claim_03 needed 5 turns with one clarification (`summary.md`), so a cap like `for _ in range(3)` would have stopped claim_04 before `route_to_adjuster` on turn 4 and left it unrouted. Related, the loop's deterministic backstop fired for 5 claims (`escalations.jsonl`, reason "model ended its turn without a terminal action"). For example, `claim_01_kitchen_fire` ended with `end_turn` on turn 2 after only `lookup_policy` and `record_claim_fact`, and was escalated rather than lost.

3. **Tool design.** Pick two tools with overlapping inputs. How do the descriptions prevent misrouting? What did a structured tool error let the agent do that a generic string would not?
   → `claims_intake/tools.py` defines `classify_claim`, `assess_severity`, `route_to_adjuster`, `escalate_to_human`, `request_clarification`, `record_claim_fact` and `lookup_policy`. `route_to_adjuster` and `escalate_to_human` take overlapping claim inputs, so their descriptions state when each applies (routable vs needs-human) to prevent misrouting. In the run, claim_04, claim_05 and claim_08 reached `route_to_adjuster` (`queues/liability.jsonl`, `auto.jsonl`, `property_damage.jsonl`), and `claim_03_water_damage` used `request_clarification` once (`clarifications_asked = 1`). A structured escalation record lets a human act on a field: each line in `escalations.jsonl` carries `root_cause`, `case_facts` and `recommended_action`, which a generic string would not.

4. **Your numbers.** Quote the turn count and cost for one claim. How does it differ from the README sample, and why?
   → `claim_04_neighbor_injury` (liability, high severity, routed) took 5 turns, 17,465 input / 879 output tokens, and an estimated $0.0219 (`evidence/system1/run_20261120_083822/summary.md`). The whole 8-claim run cost $0.1206. Routed claims (04, 05, 08) used 5 turns and about $0.02 each, while claims that ended at turn 2 cost about $0.008. I found no README sample for System 1 in the local repo, so I cannot compare against one. Only 3 of the 7 claims expected to be `routed` actually routed in my run: claims 01, 02, 03 and 07 ended with `end_turn` without a terminal tool and were escalated by the backstop (claim_03 after one clarification). Claim_06 was escalated as expected, also via the backstop. Model behavior varies between runs, so these numbers will differ on a re-run.

### System 2 — Context strategy

5. **The reduction.** From `budget.json`: baseline tokens, assembled tokens, reduction %. Which section dominates the assembled context, and why keep it verbatim?
   → From `runs/20261120-083949/budget.json` (copy: `evidence/system2/run_20261120-083949/``budget.json`), the baseline was 38,708 tokens, the assembled context was 16,859 tokens, and the reduction was 56.45%, above the 50% target. My earlier run `20261119-173134` gave 16,822 tokens and 56.54%. The active segment dominates at 15,789 tokens because turns 29–48 are still live and decision-bearing, so `retail_context/assemble.py` keeps that segment byte-exact at the bottom boundary.

6. **Summarize vs preserve.** State the rule for what gets summarized vs kept byte-exact, citing your per-section token numbers.
   → The rule is: resolved issues are summarized, while the active payment-method issue is preserved byte-exact. Per-section numbers in `runs/20261120-083949/budget.json`: `case_facts: 204`, `resolved_refund: 413`, `resolved_subscription: 471`, `active: 15,789` (run `20261119-173134`: 204 / 423 / 424 / 15,789). The two resolved issues were compressed from 12,334 and 11,475 input tokens to 400 and 458 output tokens (`compression_api`). `tests/test_antipatterns.py::test_assembled_context_active_segment_byte_exact` guards the active segment: it skipped before a run existed in `solution/runs/` (28 passed, 2 skipped, `evidence/system2/pytest.log`) and passes with the run present (30 passed, `evidence/system2/pytest_after_run.log`).

7. **Facts block.** Compare `eval.jsonl` to `eval_control.jsonl`. Which question regressed, and what does that prove?
   → In `runs/20261120-083949/eval.jsonl` Q1–Q6 all passed (6/6, `evidence/system2/run_20261120-083949/`). In `eval_control.jsonl`, with the Case Facts block stripped, Q1 held but Q6 regressed (1 of 2 control questions failed): the model answered "I don't have access to the structured status token from the case record" instead of `payment_update_status: in_progress`. This reproduces the earlier run `20261119-173134`, where Q6 also failed, and proves the facts block carries load-bearing structured state that the summaries and raw turns do not reliably surface.

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
    → `evidence/system4/hot_state_size.txt`: `hot_state.json` is 643 bytes (re-run on 2026-11-20 under WSL; an earlier Windows run counted 658 because the em-dashes in the alerts were mis-encoded), against `HOT_STATE_BYTE_BUDGET = 5_120` in `state.py`; `write_atomic` raises if exceeded and writes via `os.replace`. The state is injected into every prompt on every shift indefinitely, so unbounded growth would eventually crowd out working context. A hard budget forces compaction now rather than failing later.

---

## Part 2 — Synthesis

*Graded on connecting two or more systems. Cite a named file/artifact from each.*

14. **Three layers.** Point to a file/artifact for each layer and justify.
    → Model: Claude calls via `claims_intake/client.py` (System 1); not exercised live. The recorded response `shift_C_2026-04-30.json` stood in for the model in System 4.
    → Harness: `claims_intake/loop.py` (stop_reason loop) and `.claude/skills/deploy-check/SKILL.md` (tool allowlist).
    → Orchestration: `shift_monitor/recovery.py` and `state.py`, which decide resume vs fresh and persist the hot state.

15. **Deterministic vs prompt.** Cite one behavior guaranteed in code (terminal tool, read-only allowlist, atomic write, byte budget) and one guided by prompt. When is each right?
    → Code-guaranteed: the 5,120-byte hot-state budget with atomic write (`state.py`; my file is 643 bytes) and the read-only allowlist in `deploy-check/SKILL.md`. Prompt-guided: the lot-quarantine recommendation in the System 4 summary (`evidence/system4/shift_output.txt`). Use code for invariants whose violation is costly or silent, and prompts for judgment that varies by input.

16. **Context, two faces.** Compare context management in System 2 (intra-session) and System 4 (cross-session) with cited numbers from both. Same principle, different mechanism — how?
    → System 2 manages intra-session context by compressing a 38,708-token transcript into a 16,859-token assembled context, a 56.45% reduction (`runs/20261120-083949/budget.json`; earlier run `20261119-173134`: 16,822 tokens, 56.54%). System 4 manages cross-session context by keeping `hot_state.json` at 643 bytes under the 5,120-byte cap (`evidence/system4/hot_state_size.txt`) and querying only the bounded `defects_since` slice instead of exposing the full 40-row warm store. Both systems keep durable facts in compact state and keep irrelevant history away from the model, but System 2 does it inside one long conversation (case-facts block plus summaries) while System 4 does it across repeated shift runs (hot tier plus SQL-filtered warm tier).

17. **Reliability you can't see in one run.** Name one behavior a test guarantees that a single successful run would not reveal. Why does it matter before shipping?
    → `test_antipatterns.py::test_assembled_context_active_segment_byte_exact` (System 2) guarantees byte-exact preservation of the active turns, which a glance at the 16,859-token `context.md` from run `20261120-083949` would not prove. It was skipped before any run existed in `solution/runs/` (28 passed, 2 skipped, `evidence/system2/pytest.log`) and passes after the run (30 passed, `evidence/system2/pytest_after_run.log`). System 1's backstop is a similar case: a single good run (claim_04) would not show that claims 01, 02 and 07 end without a terminal tool and still get escalated (`escalations.jsonl`).

18. **Blast radius.** Pick one system. What's the blast radius if it misbehaves, and what's the kill switch? Ground it in that system's tools, enforcement points, and state.
    → System 3: `deploy-check` is limited to Read/Grep/Glob and `git status|diff|log`, so a misbehaving fork cannot write or push; the blast radius is a wrong report. The enforcement point is `allowed-tools` in `SKILL.md`, and the kill switch is editing or deleting that file or not invoking the skill. No state is mutated. Validator `OK` (`evidence/system3/validator.txt`).

---

## Part 3 — Honest assessment

19. **What broke.** One thing that failed first try in your environment, and how you fixed it. (If nothing, what you checked to be sure.)
    → (1) My first venv install failed because I used a short 8.3 temp path and ran `pip install -e "<dir>[dev]"` from outside the project; I fixed it with the long path and by running `pip install -e ".[dev]"` inside each `solution/` (`install.log`). (2) An earlier `python -m retail_context.run --build` raised `FileNotFoundError: [WinError 206] The filename or extension is too long`, and with no `ANTHROPIC_API_KEY` Systems 1 and 2 could not run. On 2026-11-20 I re-ran everything in WSL with the key set: System 1 exits 0 (`evidence/system1/run.log`) and System 2 exits 0 with 6/6 eval passes (`evidence/system2/run.log`), and the skipped tests now pass. (3) In System 1, 4 of the 7 claims I expected to route did not: all were escalated by the deterministic backstop for ending without a terminal tool (`escalations.jsonl`), so the live run does not match the fixtures' `expected=routed` labels.

20. **What you'd change.** One architectural decision you'd make differently, grounded in what you observed.
    → I would not anchor System 4's query window to the wall clock. With fixtures dated April 2026 the offline run reports `new=0` while the recorded summary describes 5 defects (`evidence/system4/shift_output.txt`), so output and data disagree. Passing the shift's reference time explicitly would make the offline run reproducible.
