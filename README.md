# python-boxhead-bot

Automated bot for playing [Boxhead](https://www.twoplayergames.org/game/boxhead-2play) (a browser Flash/WebAssembly shooter) using Playwright, YOLOv11 and PPO reinforcement learning.

Implemented so far:

- **`ScreenCapturer`** — grabs game frames via `page.screenshot()`, with optional ROI cropping
- **`InputController`** — keyboard-only control (8-directional movement, shoot, weapon switch, pause, reset) via `page.keyboard`

## Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)
- Docker + Docker Compose (optional — used for headless runs and CI-consistent test runs)

## Installation

```bash
git clone <repo-url>
cd boxhead-bot
uv sync
uv run playwright install chromium
```

## Development

```bash
uv run pytest                                          # run tests
uv run pytest tests/test_controller.py::test_name -v   # run a single test
uv run ruff check .                                    # lint
uv run ruff format .                                   # format
```

Or via Docker:

```bash
docker-compose build
docker-compose run --rm test
```

## Helpers

Manual data-collection scripts, for playing the game while collecting raw screenshots into `data/raw/`:

```bash
uv run python helpers/capture_screenshots.py   # launches a browser, screenshots every 1s while you play; Ctrl+C to stop
uv run python helpers/clear_raw_screenshots.py # deletes all collected screenshots from data/raw/
```

## Project Structure

```text
src/boxhead_bot/
  capturer.py    # ScreenCapturer — Playwright page.screenshot() + ROI crop
  controller.py  # InputController — keyboard-only control via page.keyboard
helpers/         # manual data-collection scripts
docs/            # game-analysis.md and other reference notes
tests/           # pytest suite, with tests/fixtures/ for static screenshots
```

See `CLAUDE.md` for architecture decisions, tech stack, and coding conventions.

## Contributing

Commits follow [Conventional Commits](https://www.conventionalcommits.org/) (`feat`, `fix`, `docs`, `refactor`, `test`, `chore`). Every change goes through an Issue → branch → PR workflow.

A local pre-commit hook runs `ruff` on every commit. On each PR to `main`:

- **CI** (`.github/workflows/ci.yml`) — `uv sync`, `ruff check`, `ruff format --check`, `pytest`
- **CodeRabbit** — automated review (`.coderabbit.yaml`)
- Squash merging only, head branch deleted automatically after merge

[Dependabot](.github/dependabot.yml) opens weekly PRs for `pip` and GitHub Actions dependency updates.
