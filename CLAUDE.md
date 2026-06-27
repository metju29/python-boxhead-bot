# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# Boxhead Bot

## Tech Stack
- Language: Python 3.11+
- Environment: uv
- Browser automation: Playwright (screen capture via page.screenshot(), keyboard/mouse via page.keyboard/page.mouse)
- Computer vision: OpenCV (opencv-python)
- Testing: pytest + pytest-mock
- Linting/formatting: ruff

## Commands
- **Run:** `uv run python -m boxhead_bot` or `docker-compose run --rm bot` (Playwright runs headless in Docker)
- **Build:** `docker-compose build`
- **Test:** `docker-compose run --rm test` or `uv run pytest`
- **Single test:** `uv run pytest tests/test_detector.py::test_name -v`
- **Lint:** `uv run ruff check .`
- **Format:** `uv run ruff format .`

## Project Structure
```
src/
  boxhead_bot/
    capturer.py       # ScreenCapturer — Playwright page.screenshot() + ROI crop
    detector.py       # PlayerDetector, EnemyDetector, ObjectDetector
    decision.py       # DecisionEngine, MovementStrategy, ShootingStrategy
    controller.py     # InputController (page.keyboard), MouseController (page.mouse)
    runner.py         # BotRunner — main game loop
    __main__.py       # CLI entry point
tests/
  fixtures/           # static screenshots for testing
  test_capturer.py
  test_detector.py
  test_decision.py
  test_controller.py
Dockerfile
docker-compose.yml
pyproject.toml
```

## Code Conventions
- Naming: snake_case for functions/variables, PascalCase for classes
- File structure: one class family per file, grouped by pipeline layer
- Key patterns: Pipeline (Capture → Detect → Decide → Act), Strategy pattern for movement/shooting decisions

## Architecture Decisions
- Pipeline architecture: fixed sequence Capture → Detect → Decide → Act per frame
- Heuristic decision engine (IF/THEN rules) — no ML model in this phase
- Playwright replaces PyAutoGUI: headless browser captures game canvas (Ruffle/WebAssembly on `<canvas>`), controls input via page.keyboard/page.mouse — no window focus needed, works in Docker
- Docker runs the full bot headless (Playwright), not just tests
- Template matching + color segmentation for entity detection (no ML model needed)
- Emergency stop: KeyboardInterrupt + dedicated key combo via page.keyboard

## Development Concept
- **Primary:** TDD (Test-Driven Development)
- **Supplementary:** Clean Architecture / Hexagonal
- **SA note:** TDD fits because each pipeline stage has clear inputs/outputs testable with static fixture screenshots — write the test with a saved game screenshot before implementing the detector. Clean Architecture enforces layer separation (vision / decision / action), so DetectionEngine has no knowledge of InputController and DecisionEngine has no knowledge of OpenCV internals. Together they prevent regression when swapping detection algorithms and allow unit testing each layer in isolation.

## Claude Rules
- DO change: detector logic, heuristic rules in DecisionEngine, logging output, CLI flags, test fixtures
- ASK before changing: pipeline stage interfaces (method signatures of Capturer/Detector/Decision/Controller), project structure
- DO NOT change: emergency stop mechanism, public GitHub repo structure once published

## GitHub Setup (production-like workflow)

### Repository settings
- Squash merging only (no merge commits)
- Automatically delete head branches
- Branch protection on `main`: require PR before merging, 0 approvals (solo)

### Workflow — every change goes through Issue → branch → PR
1. Create Issue on GitHub
2. Create branch from Issue ("Create a branch" button)
3. `git fetch && git checkout branch-name`
4. Code + commit (Conventional Commits)
5. `git push origin branch-name`
6. Open PR → `closes #issue_number` in description
7. Wait for CodeRabbit review
8. Review diff → merge

### Required files (already created or to be created)
- `.github/workflows/ci.yml` — runs ruff + pytest on every PR to main
- `.github/dependabot.yml` — weekly dependency updates via PR
- `.github/ISSUE_TEMPLATE/feature.md` and `bug.md`
- `.github/pull_request_template.md`
- `.coderabbit.yaml` — AI code review (profile: chill)
- `.pre-commit-config.yaml` — ruff runs on every `git commit`

### CI pipeline (GitHub Actions)
Runs on every PR to main: `uv sync` → `ruff check` → `ruff format --check` → `pytest`

### Tech stack additions
- `structlog` — structured JSON logging, configured in `src/logger.py`
- `pre-commit` — local hook running ruff before every commit
