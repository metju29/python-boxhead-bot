import time
from datetime import datetime
from pathlib import Path

from playwright._impl._errors import TargetClosedError
from playwright.sync_api import sync_playwright

output_dir = Path("data/raw/game_6")
output_dir.mkdir(parents=True, exist_ok=True)
CAPTURE_INTERVAL = (
    1  # 1 FPS — for a player_dead-focused session. Unlike mine/shrapnel/explosion
)
# bursts, a death pose lingers on screen for seconds until Retry, so a high capture rate here just
# produces many near-identical frames of the same death that get excluded as duplicates anyway (see
# split_train_valid.py's duplicate-cluster exclusion — player_dead already sits at ~89% duplicate
# rate in the existing pool). 1 FPS still reliably catches every death (it lingers far longer than
# 1s) while prioritizing distinct deaths over redundant frames of the same one.
#
# NOTE: this used to crop via page.screenshot(clip=...) with ROI converted to CSS pixels. Dropped
# after the game canvas was observed jumping from centered to the top-left corner shortly after the
# capture loop started — suspected cause: Playwright's clip implementation can briefly override the
# page's device metrics (emulated viewport) to produce the crop, which fires a resize event that
# Ruffle's stage-scaling logic reacts to by re-laying-out the movie. Screenshotting the canvas element
# directly uses a different code path (element bounding box, no viewport override) and should avoid
# triggering that. Not yet confirmed live — verify the game stays put after a minute or two of capture.

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, args=["--start-maximized"])
    try:
        page = browser.new_page(no_viewport=True)
        page.goto(
            "https://www.twoplayergames.org/game/boxhead-2play",
            wait_until="domcontentloaded",
        )

        # The game renders inside an iframe (twoplayergames.org/gameframe/boxhead-2play), not the
        # top-level page — a plain page.locator("canvas") never finds it no matter how long you wait.
        canvas = page.frame_locator('iframe[src*="gameframe"]').locator("canvas").first
        print(
            "Waiting for the game canvas to appear — click through the ad/menu now..."
        )
        canvas.wait_for(state="visible", timeout=0)
        print("Canvas found, starting capture.")

        while True:
            filename = (
                output_dir
                / f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.png"
            )
            canvas.screenshot(path=str(filename))
            time.sleep(CAPTURE_INTERVAL)
    except KeyboardInterrupt:
        print("\nStopped by user (Ctrl+C).")
    except TargetClosedError:
        print("\nBrowser closed.")
    finally:
        browser.close()
