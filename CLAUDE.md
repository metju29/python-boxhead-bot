# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# Boxhead Bot

## Tech Stack
- Language: Python 3.11+
- Environment: uv
- Browser automation: Playwright (screen capture via page.screenshot(), keyboard/mouse via page.keyboard/page.mouse)
- Computer vision: OpenCV (opencv-python) + Ultralytics YOLOv11 (entity detection)
- ML / RL: PyTorch, Stable-Baselines3, Gymnasium
- Data labeling: Roboflow (external, cloud) — exports dataset in YOLO format
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
    detector.py       # YOLODetector — YOLOv11 inference → List[Detection]
    game_state.py     # GameState dataclass — structured output from detector
    env.py            # BoxheadEnv — Gymnasium wrapper around Playwright game
    controller.py     # InputController (page.keyboard), MouseController (page.mouse)
    runner.py         # BotRunner — runs trained RL policy in game loop
    __main__.py       # CLI entry point
data/
  raw/                # collected game screenshots (unlabeled)
  labeled/            # Roboflow export in YOLO format (images + labels)
models/
  yolo/               # trained YOLOv11 weights (.pt files)
  rl/                 # saved RL policy checkpoints
training/
  train_yolo.py       # YOLO training script (Ultralytics API)
  train_rl.py         # RL training script (Stable-Baselines3 PPO/DQN)
  evaluate_rl.py      # evaluate trained policy, log metrics
tests/
  fixtures/           # static screenshots for testing
  test_capturer.py
  test_detector.py
  test_game_state.py
  test_env.py
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
- **Detection:** YOLOv11 (Ultralytics) replaces template matching — trained on labeled game screenshots, outputs `List[Detection]` with class, bbox, confidence
- **Decision:** RL agent (PPO via Stable-Baselines3) replaces IF/THEN heuristics — trained inside `BoxheadEnv` (Gymnasium), loaded as frozen policy at runtime
- **GameState dataclass** is the contract between Detect and Decide layers — detector fills it, env/policy reads it; neither knows how the other works
- Playwright replaces PyAutoGUI: headless browser captures game canvas (Ruffle/WebAssembly on `<canvas>`), controls input via page.keyboard/page.mouse — no window focus needed, works in Docker
- Docker runs the full bot headless (Playwright), not just tests
- Training runs locally or on GPU machine, not in Docker bot container — models are saved to `models/` and loaded at runtime
- Emergency stop: KeyboardInterrupt + dedicated key combo via page.keyboard

## ML Pipeline

### Phase 1 — Computer Vision (YOLO)
1. Collect raw screenshots with `helpers/capture_screenshots.py` while playing manually
2. Upload to Roboflow → label entities: `player`, `enemy`, `weapon`, `health_pack`
3. Export dataset in YOLOv11 format → `data/labeled/`
4. Train: `uv run python training/train_yolo.py` → saves weights to `models/yolo/`
5. Integrate into `detector.py` — `YOLODetector.detect(frame) -> List[Detection]`

### Phase 2 — Reinforcement Learning (PPO)
1. Implement `BoxheadEnv(gymnasium.Env)` in `env.py`:
   - `observation_space`: GameState as flat numpy array (positions, counts, distances)
   - `action_space`: Discrete(8) — 4 movement directions × 2 (shoot / don't shoot)
   - `reward`: +score_delta (primary — game objective is max score), -death, +survival_tick
   - `step()`: sends action via InputController, captures frame, runs YOLODetector, returns next obs + reward
2. Train: `uv run python training/train_rl.py` → saves policy to `models/rl/`
3. Evaluate: `uv run python training/evaluate_rl.py`
4. BotRunner loads frozen policy → `policy.predict(obs)` → action → controller

### Phase 3 (optional) — End-to-end from pixels
- CNN feature extractor + PPO directly on raw game frame (no separate YOLO step)
- Requires GPU and significantly more training time

## Development Concept
- **Primary:** TDD (Test-Driven Development)
- **Supplementary:** Clean Architecture / Hexagonal
- **SA note:** TDD fits because each pipeline stage has clear inputs/outputs testable with static fixture screenshots — write the test with a saved game screenshot before implementing the detector. Clean Architecture enforces layer separation (vision / decision / action), so `YOLODetector` has no knowledge of `InputController` and the RL policy has no knowledge of OpenCV internals. `GameState` is the stable contract between layers — it can be constructed from real detector output or from a fixture dict in tests, so swapping YOLO for a future model doesn't break decision tests. Training scripts (`training/`) are intentionally outside `src/` — they are one-off tools, not part of the runtime pipeline.

## Claude Rules
- DO change: YOLO training config, reward function in `BoxheadEnv`, logging output, CLI flags, test fixtures, `GameState` fields
- ASK before changing: pipeline stage interfaces (method signatures of Capturer/Detector/Env/Controller), `GameState` schema once RL training has started (breaks trained policy), project directory structure
- DO NOT change: emergency stop mechanism, public GitHub repo structure once published, `models/` directory contents (trained weights)

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
- `torch` — PyTorch (CPU for inference, GPU for training)
- `ultralytics` — YOLOv11 training + inference API
- `stable-baselines3` — PPO/DQN RL algorithms
- `gymnasium` — standard RL environment interface
- `numpy` — observation/action arrays
