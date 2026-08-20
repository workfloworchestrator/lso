# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

LSO (Lightweight Service Orchestrator, PyPI package `orchestrator-lso`) is a small FastAPI server that runs Ansible
playbooks and arbitrary executables on request, and reports results back to a caller-supplied callback URL. It is
typically driven by the Workflow Orchestrator, whose workflow steps sit in `awaiting_callback` until LSO POSTs back.

## Commands

```sh
uv sync --all-extras --dev && pre-commit install   # setup
uv run pytest                                      # all tests
uv run pytest test/routes/test_playbook.py::test_name   # one test
uv run pytest --cov-branch --cov=lso --cov-report=xml   # as CI runs it
uv run ruff format --respect-gitignore --check .   # formatting (CI check)
uv run ruff check --respect-gitignore .            # lint
uv run ty check .                                  # type check
uv run mkdocs serve                                # docs preview
python -m lso.app                                  # dev server on :44444
celery -A lso.worker worker --loglevel=info -Q $WORKER_QUEUE_NAME   # worker, when EXECUTOR=celery
bumpversion patch|minor|major                      # bumps 4 files, see .bumpversion.cfg
```

CI runs lint/type/tests on Python 3.12–3.14, plus a separate matrix against ansible-core 2.16, 2.19, and latest.

## Architecture

Request flow: `lso/routes/*` (validation + HTTP contract) → `lso/playbook.py` / `lso/execute.py` (dispatch) →
`lso/tasks.py` (the actual run + callback POST). `lso/app.py` mounts the three routers under `/api`.

**The executor is a runtime switch, not two code paths.** `settings.EXECUTOR` picks `threadpool` (default, in-process,
`lso/utils.py`) or `celery` (`lso/worker.py`). Both run the *same* functions in `lso/tasks.py` — the `@celery.task`
decorated functions are called directly by the thread pool. Change a task and you change both modes.

**Async jobs return a `job_id` immediately (201) and report later** by POSTing to the request's `callback` URL;
playbooks can also stream to a `progress` URL. `PlaybookFinishedHandler.reported` plus the crash safety net in
`run_playbook_proc_task` guarantee exactly one callback per job — a run that dies before finishing still POSTs a
`failed` status, so the orchestrator never orphans. Preserve that invariant when touching this path.

**`TESTING=true` makes the thread pool synchronous** (`future.result()` is awaited in `playbook.py`/`execute.py`), which
is why route tests can assert on side effects. It also flips `task_ignore_result`.

**Ansible is deliberately not a dependency.** LSO shells out to `ansible-playbook` / `ansible-inventory` on `PATH`
rather than importing Ansible, so deployers pick their own version; it is unpinned in the dev group for the same
reason. Inventory validation (`lso/routes/playbook.py`) runs `ansible-inventory --list` in a pinned environment with a
throwaway `HOME` and empty `ansible.cfg`, so the API accepts the same bodies on every machine. Its verdicts key off
*what Ansible parsed*, never off message wording, which differs between versions — keep it that way. A rejection
returns an `InventoryProblem` body: 422 for a bad inventory, 503 when the command is missing, 504 on timeout.

**Config** is one `pydantic-settings` singleton, `lso.config.settings`, read from env vars (see `.env.example`). The
`CELERY_REDIS_*` / `CELERY_BROKER_*` defaults in `lso/worker.py` exist to survive a Redis switch-over; the comments
there record why each one is needed. The `redis<6.5` pin in `pyproject.toml` is load-bearing — read its comment before
touching it.

## Conventions

- Ruff with a near-maximal rule set, line length 120, relative imports banned, docstrings required outside `test/`.
- Vale lints prose in `docs/` **and** in `lso/` docstrings (`.vale.ini`), so docstrings are held to a style guide.
- `develop` is the default branch; `main` is what the release/docs workflows watch.
