# E-Commerce Platform — Shared Claude Code Conventions

This file is the **project-level** entry point for the e-commerce monorepo. Every teammate's Claude session loads it automatically.

## Scope: what belongs here vs. elsewhere

| Scope | Location | Shared with team? | What belongs here |
|---|---|---|---|
| **Project-level** | `./CLAUDE.md`, `.claude/` (rules, standards, commands, skills, `settings.json`) | Yes — committed to git, reviewed in PRs | Team conventions: coding standards, path-scoped rules, `/review` and `/deploy-check` workflows |
| **User-level** | `~/.claude/CLAUDE.md`, `~/.claude/settings.json` | **No** — lives in your home directory and is **not shared** with teammates via version control | Personal preferences only, e.g. your preferred commit message style, editor preference, or shell aliases |
| **Directory-level** | `CLAUDE.md` inside a subdirectory (e.g. `src/api/CLAUDE.md`) | Yes — committed alongside the code it describes | Context that only matters when working inside that subtree |

Team intent: anything a teammate's Claude session must do the same way as yours belongs at project or directory level, so it is versioned and reviewed like code. If a rule only reflects how *you* like to work, keep it at user level — it stays local and never overrides the team baseline for anyone else.

## Shared standards (modular via @-imports)

The actual conventions live in focused files so this entry point stays scannable:

@.claude/standards/frontend.md
@.claude/standards/api.md
@.claude/standards/database.md
@.claude/standards/testing.md

Path-scoped rules in [.claude/rules/](.claude/rules/) layer on top of these standards and activate only when Claude is editing matching files (React components, API handlers, test files).

## Repository layout

```
src/components/   React components (functional + hooks)
src/pages/        Top-level routes
src/api/          Node.js API handlers
src/db/           PostgreSQL repository-pattern modules
```

Tests are co-located: `Foo.tsx` lives next to `Foo.test.tsx`.

## Troubleshooting

If a CLAUDE.md instruction isn't being followed, run `/memory` to see exactly which CLAUDE.md, rules, and imported files actually loaded for the current session.

## Team workflows

- `/review <pr-ref>` — codified PR review checklist. (You will author this in Exercise 2.)
- `/deploy-check` — read-only pre-deployment validation. (You will author this in Exercise 3.)

For decisions about when to use plan mode vs. direct execution on this codebase, you will produce a team decision doc in Exercise 4.
