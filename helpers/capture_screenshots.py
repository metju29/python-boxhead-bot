import time
from datetime import datetime
from pathlib import Path

from playwright._impl._errors import TargetClosedError
from playwright.sync_api import sync_playwright

output_dir = Path("tests/fixtures/raw")
output_dir.mkdir(parents=True, exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, args=["--start-maximized"])
    try:
        page = browser.new_page(no_viewport=True)
        page.goto(
            "https://www.twoplayergames.org/game/boxhead-2play",
            wait_until="domcontentloaded",
        )
        while True:
            filename = (
                output_dir
                / f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            )
            page.screenshot(path=str(filename))
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopped by user (Ctrl+C).")
    except TargetClosedError:
        print("\nBrowser closed.")
    finally:
        browser.close()
