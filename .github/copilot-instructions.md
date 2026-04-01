# Copilot Coding Agent — Maestro Project Instructions

This project is managed by the **Maestro** orchestration system and uses **Squad** for multi-agent coordination.

## Before Starting Work

1. Read `backlog/README.md` for the project goals and success criteria.
2. Read `backlog/tasks/` for the discrete task list.
3. Read `STATUS.md` for current phase and blocking issues.
4. Read `FEEDBACK.md` for any human corrections or guidance.
5. If `.squad/team.md` exists, read it for the team roster and your role assignment.
6. If `.squad/routing.md` exists, check routing rules before starting.

## Work Conventions

- **Branch naming:** `maestro/{phase}-{kebab-case-slug}` (e.g., `maestro/planner-initial-plan`)
- **Commit messages:** Start with the phase: `[Planner]`, `[Coder]`, `[Tester]`, `[Reconciler]`
- **Status updates:** Update `STATUS.md` when you change the project's phase or objective.
- **Decisions:** If you make a significant architectural or data decision, log it in `.squad/decisions.md` (create it if missing).

## Phases

This project follows the Maestro lifecycle:
1. **Planner** — Survey existing files, define goals, write `PLAN.md`
2. **Squad Init** — Initialize the agent team based on the plan
3. **Coder** — Implement the plan (Squad routes to specialists)
4. **Tester** — Validate implementation, write tests
5. **Reconciler** — Compare dual-coder outputs (if applicable)
6. **Reviewer** — Critical review, fact-checking, final polish

## Data Constraints

- Prefer using data already in the repo (`data/`, `cache/`, CSV files).
- If external data is needed, document the source URL in `PLAN.md` and `requirements.txt`.
- Never hardcode API keys — use environment variables.
