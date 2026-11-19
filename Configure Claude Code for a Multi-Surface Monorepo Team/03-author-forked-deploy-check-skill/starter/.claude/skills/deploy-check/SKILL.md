---
name: deploy-check
description: Read-only pre-deployment validation (clean tree, migrations, green CI) that returns a pass/fail summary
context: fork
argument-hint: "[target-branch] (defaults to main)"
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash(git status:*)
  - Bash(git diff:*)
  - Bash(git log:*)
  - Bash(git ls-files:*)
  - Bash(gh pr view:*)
  - Bash(gh pr checks:*)
---

# /deploy-check

Runs the team's pre-deployment validation checklist against the current working tree and the branch you're about to ship. Read-only by design — this skill never modifies files, never pushes, never deploys. It returns a single structured summary so the calling session can decide whether to proceed.

## Why this is a skill (not a CLAUDE.md addition)

A skill is **on-demand, forked and task-specific**: you only need it right before a deploy, and it produces verbose intermediate output (file enumeration, diff parsing, check traces) that has no value once the summary is known. CLAUDE.md is **always-loaded and universal**: conventions that must be present in every session (tests are co-located, throw `ApiError` for validation failures) belong there.

Putting deploy logic in CLAUDE.md would bloat every session's context and grow into a monolith. Rule of thumb: on-demand / forked / task-specific → skill; always-loaded / universal → CLAUDE.md.

## Why `context: fork`

The goal of `context: fork` is to keep verbose intermediate output **out of the main session**. A deploy check walks the working tree, inspects diffs and runs several enumeration passes; none of that matters to the calling conversation once we know whether to ship. Only the structured summary returns to the main conversation.

`context: fork` is a Claude Code product feature operating at the skill-invocation layer. It is conceptually analogous to the *Branching Reality* pattern: establish a shared starting point, then branch into an isolated exploration whose working output never flows back into the parent. Session-level forking (`fork_session`) applies the same pattern to a whole session.

## Checks

Run all three. Each check produces a pass-or-fail verdict; if any fails, the overall summary is **fail**.

### 1. Uncommitted changes

- **Detect:** run `git status --porcelain`.
- **Pass:** output is empty (clean working tree).
- **Fail:** any output. Surface the count of modified/untracked files in the verdict detail.

### 2. Migrations up-to-date with code

- **Detect:** `git diff --name-only <target>...HEAD`; for every new repository import or change under `src/db/`, confirm a matching `NNNN__*.sql` migration file was added in the same branch.
- **Pass:** every schema-affecting change has a migration in the branch (or there are none).
- **Fail:** a repository change has no migration. Name the repository module in the verdict detail.

### 3. CI checks green on the open PR

- **Detect:** `gh pr view --json statusCheckRollup` (or `gh pr checks`).
- **Pass:** all required checks report SUCCESS.
- **Fail:** any check is failing, pending or missing, or no PR exists. List the failing check names in the verdict detail.

## Output format

Return exactly this shape to the main session:

```
verdict: pass | fail
checks:
  - name: <check-name>
    status: pass | fail
    detail: <one line or empty>
```

Do not include the raw `git status`, raw diff hunks, or full check logs in the returned summary — those stay in the fork. If the author wants to investigate a failed check, they can re-invoke the skill targeting that single check or run the underlying command themselves.

## Personalization

This skill is project-scoped (`.claude/skills/deploy-check/`), so the whole team gets the same checks from version control. A teammate who wants a stricter personal variant, for example one that also fails when the diff exceeds 500 lines without a long enough PR description, can create a parallel skill at `~/.claude/skills/deploy-check-strict/` with a different name. That variant is not committed to the repo and does not affect teammates.

## What this skill deliberately does not do

- It never pushes, deploys, or runs migrations. The `allowed-tools` allowlist is read-only by construction; even if a future maintainer adds `Write` here, the team's `/review` command should catch the change.
- It does not run the test suite. Tests have their own pre-merge gate in CI; duplicating that here would slow every deploy check without adding signal.
- It does not check for secrets in code. That's the job of the `gitleaks` pre-commit hook, which fails the commit, not the deploy.
