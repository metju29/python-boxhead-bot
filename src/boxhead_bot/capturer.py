import cv2
import numpy as np
from playwright.sync_api import Page


class ScreenCapturer:
    def __init__(self, page: Page, roi: tuple | None = None):
        self._page = page
        self._roi = roi

    def capture(self) -> np.ndarray:
        png_bytes = self._page.screenshot()
        buf = np.frombuffer(png_bytes, dtype=np.uint8)
        try:
            frame = cv2.imdecode(buf, cv2.IMREAD_COLOR)
        except cv2.error as e:
            raise ValueError("Failed to decode screenshot bytes") from e
        if frame is None:
            raise ValueError("Failed to decode screenshot bytes")
        if self._roi is not None:
            croped_frame = frame[
                self._roi[1] : self._roi[1] + self._roi[3],
                self._roi[0] : self._roi[0] + self._roi[2],
            ]
            return croped_frame
        else:
            return frame
