import shutil
from pathlib import Path

import cv2
import yaml

DATA_YAML = Path("data/labeled/v38-pool-1603/data.yaml")
IOU_THRESHOLD = 0.7  # same-class pairs above this look like duplicate annotations, not two adjacent entities
REPORT_DIR = Path("reports") / DATA_YAML.parent.name / "overlapping_boxes"


def to_corners(
    xc: float, yc: float, w: float, h: float
) -> tuple[float, float, float, float]:
    return xc - w / 2, yc - h / 2, xc + w / 2, yc + h / 2


def iou(
    box_a: tuple[float, float, float, float], box_b: tuple[float, float, float, float]
) -> float:
    ax1, ay1, ax2, ay2 = box_a
    bx1, by1, bx2, by2 = box_b
    inter_w = max(0.0, min(ax2, bx2) - max(ax1, bx1))
    inter_h = max(0.0, min(ay2, by2) - max(ay1, by1))
    inter_area = inter_w * inter_h
    if inter_area == 0:
        return 0.0
    area_a = (ax2 - ax1) * (ay2 - ay1)
    area_b = (bx2 - bx1) * (by2 - by1)
    return inter_area / (area_a + area_b - inter_area)


def parse_label_file(label_path: Path) -> list[tuple[int, float, float, float, float]]:
    instances = []
    for line in label_path.read_text().splitlines():
        if not line.strip():
            continue
        cls, xc, yc, w, h = line.split()
        instances.append((int(cls), float(xc), float(yc), float(w), float(h)))
    return instances


def save_preview(
    base_dir: Path, split: str, stem: str, flagged_idx: tuple[int, int], out_path: Path
) -> None:
    img_path = base_dir / split / "images" / f"{stem}.png"
    label_path = base_dir / split / "labels" / f"{stem}.txt"
    img = cv2.imread(str(img_path))
    h, w = img.shape[:2]

    for i, line in enumerate(label_path.read_text().splitlines()):
        if not line.strip():
            continue
        cls, xc, yc, bw, bh = line.split()
        xc, yc, bw, bh = float(xc), float(yc), float(bw), float(bh)
        x1, y1 = int((xc - bw / 2) * w), int((yc - bh / 2) * h)
        x2, y2 = int((xc + bw / 2) * w), int((yc + bh / 2) * h)
        is_flagged = i in flagged_idx
        color = (0, 0, 255) if is_flagged else (0, 255, 0)
        thickness = 3 if is_flagged else 1
        cv2.rectangle(img, (x1, y1), (x2, y2), color, thickness)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_path), img)


def main() -> None:
    data = yaml.safe_load(DATA_YAML.read_text())
    class_names = data["names"]
    base_dir = DATA_YAML.parent

    if REPORT_DIR.exists():
        shutil.rmtree(REPORT_DIR)
    previews_dir = REPORT_DIR / "previews"
    previews_dir.mkdir(parents=True)

    report_lines = [
        f"# Overlapping same-class boxes — {DATA_YAML.parent.name}",
        "",
        f"IoU threshold: >= {IOU_THRESHOLD}",
        "",
        "| split | image | class | iou | preview |",
        "|---|---|---|---|---|",
    ]
    total_flagged = 0

    for split in ("train", "valid"):
        labels_dir = base_dir / split / "labels"
        if not labels_dir.exists():
            continue
        for label_file in sorted(labels_dir.glob("*.txt")):
            instances = parse_label_file(label_file)
            for i in range(len(instances)):
                for j in range(i + 1, len(instances)):
                    cls_i, *box_i = instances[i]
                    cls_j, *box_j = instances[j]
                    if cls_i != cls_j:
                        continue
                    overlap = iou(to_corners(*box_i), to_corners(*box_j))
                    if overlap < IOU_THRESHOLD:
                        continue
                    preview_name = f"{split}_{label_file.stem}_{i}_{j}.png"
                    save_preview(
                        base_dir,
                        split,
                        label_file.stem,
                        (i, j),
                        previews_dir / preview_name,
                    )
                    report_lines.append(
                        f"| {split} | {label_file.stem}.png | {class_names[cls_i]} | {overlap:.2f} | previews/{preview_name} |"
                    )
                    total_flagged += 1

    (REPORT_DIR / "report.md").write_text("\n".join(report_lines) + "\n")
    print(f"Flagged {total_flagged} overlapping pairs.")
    print(f"Report: {REPORT_DIR / 'report.md'}")


if __name__ == "__main__":
    main()
