"""Visual box-tightness audit for one class: crops each labeled instance with context,
draws its box, and tiles everything into contact-sheet grids for fast scanning.

Different from find_label_outliers.py (which flags statistical size outliers vs the class
median) — this looks at *every* instance of one class to judge whether boxes hug the object
edges tightly, independent of size. Triggered when mAP50 is fine but mAP50-95 lags badly for
a class (boxhead_yolo11s_960_v2: shrapnel mAP50=0.898 vs mAP50-95=0.533, a 0.365 gap vs
0.06-0.14 for other classes) — that gap pattern points at loose/imprecise boxes, not missed
or misclassified detections.
"""

import math
import shutil
from pathlib import Path

import cv2
import yaml

DATA_YAML = Path("data/labeled/v39-pool-dedupe-fix-1659/data.yaml")
CLASS_NAME = "shrapnel"
CONTEXT_RATIO = 3.0  # crop side = max(box_w_px, box_h_px) * this, so the box occupies ~1/3 of the crop
THUMB_SIZE = 200  # px, square
GRID_COLS = 10
REPORT_DIR = Path("reports") / DATA_YAML.parent.name / f"box_tightness_{CLASS_NAME}"


def load_instances(
    data_yaml_path: Path, class_id: int
) -> list[tuple[str, str, int, float, float, float, float]]:
    """Returns [(split, stem, line_idx, xc, yc, w, h), ...] in YOLO-normalized coords."""
    base_dir = data_yaml_path.parent
    instances = []
    for split in ("train", "valid"):
        labels_dir = base_dir / split / "labels"
        for label_file in sorted(labels_dir.glob("*.txt")):
            for line_idx, line in enumerate(label_file.read_text().splitlines()):
                if not line.strip():
                    continue
                cls, xc, yc, w, h = line.split()
                if int(cls) != class_id:
                    continue
                instances.append(
                    (
                        split,
                        label_file.stem,
                        line_idx,
                        float(xc),
                        float(yc),
                        float(w),
                        float(h),
                    )
                )
    return instances


def make_thumbnail(
    data_yaml_path: Path,
    split: str,
    stem: str,
    xc: float,
    yc: float,
    bw: float,
    bh: float,
    same_image_boxes: list[tuple[float, float, float, float]],
) -> "cv2.Mat":
    """same_image_boxes: all same-class (xc, yc, w, h) in this image, including the current one —
    drawn in yellow so a neighbor that's actually labeled isn't mistaken for an unlabeled gap."""
    base_dir = data_yaml_path.parent
    img = cv2.imread(str(base_dir / split / "images" / f"{stem}.png"))
    img_h, img_w = img.shape[:2]

    box_w_px, box_h_px = bw * img_w, bh * img_h
    cx_px, cy_px = xc * img_w, yc * img_h
    side = max(box_w_px, box_h_px, 8) * CONTEXT_RATIO

    x1, y1 = int(cx_px - side / 2), int(cy_px - side / 2)
    x2, y2 = int(cx_px + side / 2), int(cy_px + side / 2)
    # Clamp to image bounds without distorting aspect ratio of the crop rectangle
    x1, y1 = max(x1, 0), max(y1, 0)
    x2, y2 = min(x2, img_w), min(y2, img_h)
    crop = img[y1:y2, x1:x2].copy()
    if crop.size == 0:
        crop = img.copy()
        x1, y1 = 0, 0

    for other_xc, other_yc, other_bw, other_bh in same_image_boxes:
        is_current = (other_xc, other_yc, other_bw, other_bh) == (xc, yc, bw, bh)
        ocx_px, ocy_px = other_xc * img_w, other_yc * img_h
        ow_px, oh_px = other_bw * img_w, other_bh * img_h
        bx1 = int((ocx_px - ow_px / 2) - x1)
        by1 = int((ocy_px - oh_px / 2) - y1)
        bx2 = int((ocx_px + ow_px / 2) - x1)
        by2 = int((ocy_px + oh_px / 2) - y1)
        color = (
            (0, 0, 255) if is_current else (0, 255, 255)
        )  # red = this instance, yellow = other labeled instances
        cv2.rectangle(crop, (bx1, by1), (bx2, by2), color, 1)

    return cv2.resize(crop, (THUMB_SIZE, THUMB_SIZE), interpolation=cv2.INTER_NEAREST)


def build_grids(thumbs: list["cv2.Mat"], cols: int, per_page: int) -> list["cv2.Mat"]:
    import numpy as np

    pages = []
    for page_start in range(0, len(thumbs), per_page):
        page_thumbs = thumbs[page_start : page_start + per_page]
        rows = math.ceil(len(page_thumbs) / cols)
        grid = np.zeros((rows * THUMB_SIZE, cols * THUMB_SIZE, 3), dtype=np.uint8)
        for i, thumb in enumerate(page_thumbs):
            r, c = divmod(i, cols)
            grid[
                r * THUMB_SIZE : (r + 1) * THUMB_SIZE,
                c * THUMB_SIZE : (c + 1) * THUMB_SIZE,
            ] = thumb
        pages.append(grid)
    return pages


def main() -> None:
    data = yaml.safe_load(DATA_YAML.read_text())
    class_id = data["names"].index(CLASS_NAME)

    instances = load_instances(DATA_YAML, class_id)
    print(f"{len(instances)} instances of '{CLASS_NAME}' found.")

    boxes_by_image: dict[tuple[str, str], list[tuple[float, float, float, float]]] = {}
    for split, stem, _line_idx, xc, yc, bw, bh in instances:
        boxes_by_image.setdefault((split, stem), []).append((xc, yc, bw, bh))

    if REPORT_DIR.exists():
        shutil.rmtree(REPORT_DIR)
    previews_dir = REPORT_DIR / "previews"
    previews_dir.mkdir(parents=True)

    thumbs = []
    report_lines = [
        f"# Box tightness audit — {CLASS_NAME} ({DATA_YAML.parent.name})",
        "",
        f"{len(instances)} instances. Each thumbnail is a {CONTEXT_RATIO}x-context crop, {THUMB_SIZE}px. "
        "Red = this instance's box, yellow = other labeled instances of the same class visible in this crop.",
        "",
        "| # | split | image | line |",
        "|---|---|---|---|",
    ]
    for idx, (split, stem, line_idx, xc, yc, bw, bh) in enumerate(instances):
        thumb = make_thumbnail(
            DATA_YAML, split, stem, xc, yc, bw, bh, boxes_by_image[(split, stem)]
        )
        thumbs.append(thumb)
        cv2.imwrite(
            str(previews_dir / f"{idx:03d}_{split}_{stem}_{line_idx}.png"), thumb
        )
        report_lines.append(f"| {idx} | {split} | {stem}.png | {line_idx} |")

    per_page = GRID_COLS * GRID_COLS  # square-ish pages, e.g. 10x10 = 100
    grids = build_grids(thumbs, GRID_COLS, per_page)
    for page_num, grid in enumerate(grids):
        grid_path = REPORT_DIR / f"grid_{page_num:02d}.png"
        cv2.imwrite(str(grid_path), grid)
        print(
            f"Wrote {grid_path} ({min(per_page, len(thumbs) - page_num * per_page)} thumbnails)"
        )

    (REPORT_DIR / "report.md").write_text("\n".join(report_lines) + "\n")
    print(f"Report: {REPORT_DIR / 'report.md'}")


if __name__ == "__main__":
    main()
