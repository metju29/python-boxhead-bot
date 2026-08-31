import json
import uuid
from pathlib import Path

import yaml
from ultralytics import YOLO

BATCH_DIRS = [Path("data/raw/dead_player_curated_5")]
MODEL_PATH = "models/yolo/boxhead_yolo11s_960_v2/boxhead_yolo11s_960_v2.pt"
CLASSES_YAML = Path("data/labeled/v38-pool-1603/data.yaml")
CONF_THRESHOLD = 0.25
DEVICE = "mps"
MODEL_VERSION = f"{Path(MODEL_PATH).stem}-prelabel"


def load_class_names(classes_yaml: Path) -> list[str]:
    return yaml.safe_load(classes_yaml.read_text())["names"]


def predict_boxes(
    model: YOLO, image_path: Path, conf: float
) -> tuple[list[tuple[int, float, float, float, float]], tuple[int, int]]:
    result = model.predict(image_path, device=DEVICE, conf=conf, verbose=False)[0]
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
    model: YOLO,
    class_names: list[str],
    conf: float,
    model_version: str,
) -> None:
    images_dir = batch_dir / "images"
    labels_dir = batch_dir / "labels"
    labels_dir.mkdir(parents=True, exist_ok=True)

    image_paths = sorted(images_dir.glob("*.png"))
    tasks = []
    for i, image_path in enumerate(image_paths, start=1):
        print(f"[{batch_dir.name}] [{i}/{len(image_paths)}] {image_path.name}")
        boxes, (width, height) = predict_boxes(model, image_path, conf)
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
    model = YOLO(MODEL_PATH)

    for batch_dir in BATCH_DIRS:
        process_batch(batch_dir, model, class_names, CONF_THRESHOLD, MODEL_VERSION)

    print(f"Done. Prelabeled {len(BATCH_DIRS)} batch(es) with {MODEL_PATH}.")


if __name__ == "__main__":
    main()
