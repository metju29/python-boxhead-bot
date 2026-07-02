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
    buf = np.frombuffer(FIXTURE_PATH.read_bytes(), dtype=np.uint8)
    original_frame = cv2.imdecode(buf, cv2.IMREAD_COLOR)
    # x = self._roi[0], y = self._roi[1], w = self._roi[2], h = self._roi[3]
    expected_frame = original_frame[roi[1] : roi[1] + roi[3], roi[0] : roi[0] + roi[2]]
    capturer = ScreenCapturer(mock_page, roi)
    crop_frame = capturer.capture()
    assert np.array_equal(expected_frame, crop_frame)


def test_capture_raises_on_negative_roi_coords(mock_page):
    roi = (-100, 50, 800, 600)
    capturer = ScreenCapturer(mock_page, roi)
    with pytest.raises(ValueError):
        capturer.capture()


def test_capture_raises_on_non_positive_roi_size(mock_page):
    roi = (100, 50, 0, 600)
    capturer = ScreenCapturer(mock_page, roi)
    with pytest.raises(ValueError):
        capturer.capture()


def test_capture_raises_on_roi_out_of_bounds(mock_page):
    roi = (100, 100, 1920, 963)
    capturer = ScreenCapturer(mock_page, roi)
    with pytest.raises(ValueError):
        capturer.capture()
