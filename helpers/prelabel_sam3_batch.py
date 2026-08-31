import json
import uuid
from pathlib import Path

import yaml
from ultralytics.models.sam import SAM3SemanticPredictor

BATCH_DIRS = [Path("data/raw/game_1/train")]
CHECKPOINT = "data/sam3.pt"
CLASSES_YAML = Path("data/labeled/v22-pool-1301/data.yaml")
CONF_THRESHOLD = 0.25
IMG_SIZE = 1024
DEVICE = "mps"
MODEL_VERSION = f"{Path(CHECKPOINT).stem}-sam3-prelabel"


def load_class_names(classes_yaml: Path) -> list[str]:
    return yaml.safe_load(classes_yaml.read_text())["names"]


def build_predictor(
    checkpoint: str, img_size: int, conf: float, device: str
) -> SAM3SemanticPredictor:
    overrides = {
        "conf": conf,
        "task": "segment",
        "mode": "predict",
        "model": checkpoint,
        "imgsz": img_size,
        "device": device,
        "save": False,
    }
    return SAM3SemanticPredictor(overrides=overrides)


def predict_boxes(
    predictor: SAM3SemanticPredictor, image_path: Path, class_names: list[str]
) -> tuple[list[tuple[int, float, float, float, float]], tuple[int, int]]:
    result = predictor(source=str(image_path), text=class_names)[0]
    height, width = result.orig_shape
    boxes = [
        (int(cls), xc, yc, w, h)
        for cls, (xc, yc, w, h) in zip(
            result.boxes.cls.tolist(), result.boxes.xywhn.tolist(), strict=True
        )
    ]
    return boxes, (width, height)


def to_ls_task(
    image_path: Path,
    batch_dir: Path,
    boxes: list[tuple[int, float, float, float, float]],
    class_names: list[str],
    model_version: str,
    width: int,
    height: int,
) -> dict:
    ls_result = []
    for cls, xc, yc, w, h in boxes:
        ls_result.append(
            {
                "id": uuid.uuid4().hex[:10],
                "type": "rectanglelabels",
                "value": {
                    "x": (xc - w / 2) * 100,
                    "y": (yc - h / 2) * 100,
                    "width": w * 100,
                    "height": h * 100,
                    "rotation": 0,
                    "rectanglelabels": [class_names[cls]],
                },
                "to_name": "image",
                "from_name": "label",
                "image_rotation": 0,
                "original_width": width,
                "original_height": height,
            }
        )
    return {
        "data": {
            "image": f"/data/local-files/?d={batch_dir.name}/images/{image_path.name}"
        },
        "predictions": [{"model_version": model_version, "result": ls_result}],
    }


def write_label_file(
    labels_dir: Path,
    image_path: Path,
    boxes: list[tuple[int, float, float, float, float]],
) -> None:
    lines = [f"{cls} {xc:.6f} {yc:.6f} {w:.6f} {h:.6f}" for cls, xc, yc, w, h in boxes]
    (labels_dir / image_path.with_suffix(".txt").name).write_text("\n".join(lines))


def process_batch(
    batch_dir: Path,
    predictor: SAM3SemanticPredictor,
    class_names: list[str],
    model_version: str,
) -> None:
    images_dir = batch_dir / "images"
    labels_dir = batch_dir / "labels"
    labels_dir.mkdir(parents=True, exist_ok=True)

    image_paths = sorted(images_dir.glob("*.png"))
    tasks = []
    for i, image_path in enumerate(image_paths, start=1):
        print(f"[{batch_dir.name}] [{i}/{len(image_paths)}] {image_path.name}")
        boxes, (width, height) = predict_boxes(predictor, image_path, class_names)
        write_label_file(labels_dir, image_path, boxes)
        tasks.append(
            to_ls_task(
                image_path, batch_dir, boxes, class_names, model_version, width, height
            )
        )

    (batch_dir / "classes.txt").write_text("\n".join(class_names))
    (batch_dir / "ls_tasks.json").write_text(json.dumps(tasks, indent=2))
    print(f"{batch_dir.name}: prelabeled {len(image_paths)} images.")


def main() -> None:
    class_names = load_class_names(CLASSES_YAML)
    predictor = build_predictor(CHECKPOINT, IMG_SIZE, CONF_THRESHOLD, DEVICE)

    for batch_dir in BATCH_DIRS:
        process_batch(batch_dir, predictor, class_names, MODEL_VERSION)

    print(f"Done. Prelabeled {len(BATCH_DIRS)} batch(es) with {CHECKPOINT}.")


if __name__ == "__main__":
    main()
