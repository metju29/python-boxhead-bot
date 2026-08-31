import collections
import re
import shutil
import time
from datetime import datetime
from pathlib import Path

import yaml
from ultralytics import YOLO

DATA_PATH = "data/labeled/v38-pool-1603/data.yaml"
BASE_MODEL = "models/yolo/pretrained/yolo11s.pt"
IMG_SIZE = 960
BATCH_SIZE = 4  # imgsz=960 needs this reduced to avoid OOM on M4 Pro; 640 can use 16
EPOCHS = 100
DEVICE = "mps"
MODEL_DIR = Path("models/yolo")
RESUME_FROM = None  # set to e.g. "runs/detect/train-X/weights/last.pt" to resume an interrupted run
KNOWN_LIMITATIONS_HEADER = "## Known limitations"


def next_model_path(variant: str, imgsz: int) -> Path:
    """Returns the subfolder for the next model version, e.g. models/yolo/boxhead_yolo11s_960_v3/
    — holds that version's weights, card, and copied diagnostic plots together."""
    prefix = f"boxhead_{variant}_{imgsz}"
    pattern = re.escape(prefix)
    versions = [
        int(match.group(1))
        for d in MODEL_DIR.glob(f"{prefix}_v*")
        if d.is_dir() and (match := re.fullmatch(rf"{pattern}_v(\d+)", d.name))
    ]
    return MODEL_DIR / f"{prefix}_v{max(versions, default=0) + 1}"


def dataset_stats(
    data_yaml_path: str,
) -> tuple[list[str], dict[int, tuple[int, int]], dict[str, int]]:
    """Returns (class_names, {class_id: (n_images, n_instances)}, {split: n_images}) across train+valid."""
    data_yaml_path = Path(data_yaml_path)
    data = yaml.safe_load(data_yaml_path.read_text())
    names = data["names"]

    img_count = collections.Counter()
    inst_count = collections.Counter()
    split_image_count: dict[str, int] = {}
    for split_dir in ("train", "valid"):
        labels_dir = data_yaml_path.parent / split_dir / "labels"
        label_files = list(labels_dir.glob("*.txt"))
        split_image_count[split_dir] = len(label_files)
        for label_file in label_files:
            seen = set()
            for line in label_file.read_text().splitlines():
                if not line.strip():
                    continue
                cls = int(line.split()[0])
                inst_count[cls] += 1
                seen.add(cls)
            for cls in seen:
                img_count[cls] += 1

    stats = {i: (img_count.get(i, 0), inst_count.get(i, 0)) for i in range(len(names))}
    return names, stats, split_image_count


def existing_known_limitations(card_path: Path) -> str | None:
    """Returns the previously written '## Known limitations' section body (if any), so
    regenerating a card doesn't wipe out hand-written notes."""
    if not card_path.exists():
        return None
    text = card_path.read_text()
    if KNOWN_LIMITATIONS_HEADER not in text:
        return None
    after = text.split(KNOWN_LIMITATIONS_HEADER, 1)[1]
    body = after.split("\n## ", 1)[0]
    return body.strip("\n")


def copy_diagnostic_plots(run_dir: Path, dest_dir: Path) -> list[str]:
    """Copies the Ultralytics-generated diagnostic plots for this run next to the model card,
    so they survive `runs/` being cleaned up later. Returns the filenames actually copied."""
    plot_names = [
        "confusion_matrix.png",
        "confusion_matrix_normalized.png",
        "BoxPR_curve.png",
        "BoxF1_curve.png",
        "results.png",
    ]
    copied = []
    for name in plot_names:
        src = run_dir / name
        if src.exists():
            shutil.copy(src, dest_dir / name)
            copied.append(name)
    return copied


def write_model_card(
    output_path: Path,
    data_path: str,
    base_model: str,
    imgsz: int,
    batch: int,
    epochs: int,
    metrics,
    train_hours: float,
    device: str,
    run_dir: Path,
    model_info: tuple[int, int, int, float] | None = None,
) -> None:
    """output_path is the model's subfolder (models/yolo/{model_name}/) — holds the .pt,
    the .md card written here, and copies of the run's diagnostic plots."""
    model_name = output_path.name
    names, stats, split_image_count = dataset_stats(data_path)
    metric_by_class = {
        cls_id: (p, r, ap50, ap)
        for cls_id, p, r, ap50, ap in zip(
            metrics.box.ap_class_index,
            metrics.box.p,
            metrics.box.r,
            metrics.box.ap50,
            metrics.box.ap,
            strict=True,
        )
    }

    card_path = output_path / f"{model_name}.md"
    arch_line = "- Architecture: n/a"
    if model_info is not None:
        n_layers, n_params, _n_gradients, flops = model_info
        arch_line = f"- Architecture: {n_layers} layers, {n_params:,} parameters, {flops:.1f} GFLOPs"

    copied_plots = copy_diagnostic_plots(run_dir, output_path)
    if "confusion_matrix.png" in copied_plots:
        confusion_line = "- Confusion matrix: `confusion_matrix.png` (`confusion_matrix_normalized.png` for per-class rates)"
    else:
        confusion_line = f"- Confusion matrix: not found in `{run_dir}`"

    lines = [
        f"# {model_name}",
        "",
        f"- Trained: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"- Base model: `{base_model}`",
        f"- Dataset: `{data_path}`",
        f"- Images: {split_image_count.get('train', 0)} train / {split_image_count.get('valid', 0)} valid "
        f"({sum(split_image_count.values())} total)",
        f"- imgsz={imgsz}, batch={batch}, epochs={epochs}",
        f"- Training time: {train_hours:.2f}h on {device}",
        arch_line,
        "",
        "## Overall validation metrics",
        f"- Precision: {metrics.results_dict['metrics/precision(B)']:.3f}",
        f"- Recall: {metrics.results_dict['metrics/recall(B)']:.3f}",
        f"- mAP50: {metrics.results_dict['metrics/mAP50(B)']:.3f}",
        f"- mAP50-95: {metrics.results_dict['metrics/mAP50-95(B)']:.3f}",
        confusion_line,
        "",
        "## Per-class dataset stats + validation metrics",
        "",
        "| class | images | instances | P | R | mAP50 | mAP50-95 |",
        "|---|---|---|---|---|---|---|",
    ]
    for cls_id, name in enumerate(names):
        n_images, n_instances = stats[cls_id]
        if cls_id in metric_by_class:
            p, r, ap50, ap = metric_by_class[cls_id]
            metrics_str = f"{p:.3f} | {r:.3f} | {ap50:.3f} | {ap:.3f}"
        else:
            metrics_str = "- | - | - | -"
        lines.append(f"| {name} | {n_images} | {n_instances} | {metrics_str} |")

    lines += ["", KNOWN_LIMITATIONS_HEADER, ""]
    preserved = existing_known_limitations(card_path)
    lines.append(preserved if preserved else "_(none noted yet)_")

    card_path.write_text("\n".join(lines) + "\n")
    print(f"Wrote model card to {card_path}")


if __name__ == "__main__":
    variant = Path(BASE_MODEL).stem
    train_start = time.time()

    if RESUME_FROM:
        model = YOLO(RESUME_FROM)
        model.train(resume=True)
    else:
        model = YOLO(BASE_MODEL)
        model.train(
            data=DATA_PATH,
            epochs=EPOCHS,
            imgsz=IMG_SIZE,
            batch=BATCH_SIZE,
            device=DEVICE,
        )

    train_hours = (time.time() - train_start) / 3600
    run_dir = Path(model.trainer.save_dir)
    model_info = model.info(verbose=True, imgsz=IMG_SIZE)

    output_path = next_model_path(variant, IMG_SIZE)
    output_path.mkdir(parents=True, exist_ok=True)
    weights_path = output_path / f"{output_path.name}.pt"
    shutil.copy(model.trainer.best, weights_path)
    print(f"Saved model to {weights_path}")

    metrics = model.val(data=DATA_PATH, device=DEVICE, verbose=False)
    write_model_card(
        output_path,
        DATA_PATH,
        BASE_MODEL,
        IMG_SIZE,
        BATCH_SIZE,
        EPOCHS,
        metrics,
        train_hours=train_hours,
        device=DEVICE,
        run_dir=run_dir,
        model_info=model_info,
    )
