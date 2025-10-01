# Repository Guidelines

## Project Structure & Module Organization
Core runtime code lives in `src/`, with `main.py` orchestrating startup and dependency wiring. Configuration helpers (`config.py`), command routing, and the two-stage filter are grouped within that package; avoid creating parallel modules outside `src/` unless absolutely necessary. Tests reside in `tests/` and mirror source modules one-to-one. Persistent artifacts such as Telegram sessions and cached data should stay in `data/`, while runtime logs write to `logs/`. Docker assets (`Dockerfile`, `docker-compose.yml`) support containerized deployments.

## Build, Test, and Development Commands
Set up a local environment with `python -m venv venv && source venv/bin/activate` followed by `pip install -r requirements.txt`. Launch the bot via `python main.py` for local runs or `docker-compose up -d` for the recommended container setup. Use `python run_tests.py` to execute the full regression suite; individual checks can be run (e.g., `python tests/test_two_stage.py`) when iterating on a feature.

## Coding Style & Naming Conventions
Follow the existing Python style: 4-space indentation, explicit type hints, and descriptive docstrings. Keep modules and files in snake_case, classes in PascalCase, and async coroutine names ending with verbs (e.g., `analyze_message`). When expanding configuration or source maps, prefer declarative data structures and keep JSON payloads parseable. Log messages should remain structured and, when user-facing, stay in Russian to match the bot’s responses.

## Testing Guidelines
Unit tests rely on the built-in `unittest` runner. Place new cases under `tests/`, prefix files with `test_`, and mirror the target module path. Ensure new logic has deterministic coverage; mock network calls and external APIs. Before opening a PR, run `python run_tests.py` and confirm a clean exit status.

## Commit & Pull Request Guidelines
Commit titles use the `type: summary` convention already present (`feat:`, `fix:`, `refactor:`). Keep messages concise and scoped to a single change. Pull requests should describe intent, outline manual testing, and link relevant issues. Include screenshots or log excerpts when touching user-visible flows. Flag configuration changes and breaking migrations explicitly so reviewers can double-check deployment steps.

## Security & Configuration Tips
Never commit secrets from `.env` or session files (`fact_checker_bot.session`). When sharing logs, redact API tokens and chat IDs. Coordinate changes to `sources.json` or `src/sources_config.py` with stakeholders, as they directly influence fact-checking coverage.
