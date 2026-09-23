from dataclasses import dataclass
from pathlib import Path

import numpy as np
from ultralytics import YOLO


@dataclass(frozen=True)
class Detection:
    class_name: str
    bbox: tuple[float, float, float, float]
    confidence: float


class YOLODetector:
    def __init__(self, weights_path: Path) -> None:
        self._model = YOLO(weights_path)

    def detect(self, frame: np.ndarray) -> list[Detection]:
        results = self._model(frame)
        result = results[0]
        boxes = result.boxes.xyxy.tolist()
        confidences = result.boxes.conf.tolist()
        class_ids = result.boxes.cls.tolist()
        detections = []
        for box, confidence, class_id in zip(
            boxes, confidences, class_ids, strict=True
        ):
            detections.append(
                Detection(
                    bbox=tuple(box),
                    confidence=confidence,
                    class_name=result.names[int(class_id)],
                )
            )
        return detections
