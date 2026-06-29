from pathlib import Path

import cv2
import numpy as np
import pytest

from boxhead_bot.capturer import ScreenCapturer

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "raw" / "test_screenshot.png"


@pytest.fixture
def mock_page(mocker):
    page = mocker.Mock()
    page.screenshot.return_value = FIXTURE_PATH.read_bytes()
    return page


def test_capture_returns_numpy_array(mock_page):
    capturer = ScreenCapturer(mock_page)
    frame = capturer.capture()
    assert isinstance(frame, np.ndarray)


def test_capture_has_correct_shape(mock_page):
    capturer = ScreenCapturer(mock_page)
    frame = capturer.capture()
    assert frame.ndim == 3
    assert frame.shape[2] == 3


def test_screenshot_captured(mock_page):
    capturer = ScreenCapturer(mock_page)
    capturer.capture()
    mock_page.screenshot.assert_called_once()


def test_capture_raises_on_corrupt_bytes(mocker):
    page = mocker.Mock()
    page.screenshot.return_value = b""
    capturer = ScreenCapturer(page)
    with pytest.raises(ValueError):
        capturer.capture()


def test_capture_without_roi_returns_full_frame(mock_page):
    capturer = ScreenCapturer(mock_page)
    frame = capturer.capture()
    buf = np.frombuffer(FIXTURE_PATH.read_bytes(), dtype=np.uint8)
    original_frame = cv2.imdecode(buf, cv2.IMREAD_COLOR)
    assert frame.shape == original_frame.shape


def test_capture_with_roi_returns_cropped_frame(mock_page):
    roi = (100, 50, 800, 600)
    capturer = ScreenCapturer(mock_page, roi)
    crop_frame = capturer.capture()
    assert crop_frame.shape[0] == roi[3]
    assert crop_frame.shape[1] == roi[2]
