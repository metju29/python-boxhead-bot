from pathlib import Path
from unittest.mock import Mock

import numpy as np
import pytest
import torch
from pytest_mock import MockerFixture

from boxhead_bot.detector import Detection, YOLODetector


@pytest.fixture
def mock_yolo_cls(mocker: MockerFixture) -> Mock:
    result = mocker.Mock()
    result.boxes.xyxy = torch.zeros((0, 4))
    result.boxes.conf = torch.zeros(0)
    result.boxes.cls = torch.zeros(0)
    result.names = {0: "player", 1: "zombie"}

    mock_cls = mocker.patch("boxhead_bot.detector.YOLO")
    mock_cls.return_value.return_value = [result]
    return mock_cls


@pytest.fixture
def frame() -> np.ndarray:
    return np.zeros((963, 1920, 3), dtype=np.uint8)


@pytest.fixture
def detector(mock_yolo_cls: Mock) -> YOLODetector:
    return YOLODetector(Path("fake.pt"))


def test_detect_returns_empty_list_when_no_objects(
    frame: np.ndarray, detector: YOLODetector
) -> None:
    assert detector.detect(frame) == []


def test_detect_returns_detection_for_single_object(
    mock_yolo_cls: Mock, frame: np.ndarray, detector: YOLODetector
) -> None:
    result = mock_yolo_cls.return_value.return_value[0]
    result.boxes.xyxy = torch.tensor([[10.0, 20.0, 50.0, 80.0]])
    result.boxes.conf = torch.tensor([0.75])
    result.boxes.cls = torch.tensor([1.0])

    detections = detector.detect(frame)

    assert detections == [
        Detection(class_name="zombie", bbox=(10.0, 20.0, 50.0, 80.0), confidence=0.75)
    ]


def test_init_loads_model_from_weights_path(mock_yolo_cls: Mock) -> None:
    weights_path = Path("weights/model.pt")
    YOLODetector(weights_path)

    mock_yolo_cls.assert_called_once_with(weights_path)
