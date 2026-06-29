from pathlib import Path

import numpy as np
import pytest

from boxhead_bot.capturer import ScreenCapturer

FIXTURE_PATH = (
    Path(__file__).parent / "fixtures" / "raw" / "screenshot_20260628_144112.png"
)


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
