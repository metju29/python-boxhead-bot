import cv2
import numpy as np


class ScreenCapturer:
    def __init__(self, page):
        self._page = page

    def capture(self):
        png_bytes = self._page.screenshot()
        buf = np.frombuffer(png_bytes, dtype=np.uint8)
        frame = cv2.imdecode(buf, cv2.IMREAD_COLOR)
        return frame
