import shutil
from pathlib import Path

import cv2
import yaml

DATA_YAML = Path("data/labeled/v38-pool-1603/data.yaml")
MEDIAN_RATIO = 5.0  # flag instances whose area is >Nx (or <1/Nx if FLAG_TOO_SMALL) the class median
MIN_INSTANCES = 10  # classes with fewer instances than this don't have a meaningful size distribution
# "Too small" is dominated by legitimate edge-of-screen truncation (a zombie half off-camera
# has a genuinely smaller box), not labeling errors — confirmed by inspection on v19-pool-1130
# (>95% of "too small" flags across ammo_pack/barrel/zombie/devil/fake_wall/explosion were
# edge-cropped, real objects). "Too large" is where the real bugs hide (see the grenade
# mislabeling incident). Off by default; flip to True for a deeper, noisier pass.
FLAG_TOO_SMALL = False
REPORT_DIR = Path("reports") / DATA_YAML.parent.name / "label_outliers"


def load_instances(
    data_yaml_path: Path,
) -> dict[int, list[tuple[str, str, int, float, float, float]]]:
    """Returns {class_id: [(split, stem, line_idx, xc, yc, area), ...]}."""
    base_dir = data_yaml_path.parent
    by_class: dict[int, list] = {}
    for split in ("train", "valid"):
        labels_dir = base_dir / split / "labels"
        for label_file in labels_dir.glob("*.txt"):
            for line_idx, line in enumerate(label_file.read_text().splitlines()):
                if not line.strip():
                    continue
                cls, xc, yc, w, h = line.split()
                cls, xc, yc, w, h = int(cls), float(xc), float(yc), float(w), float(h)
                by_class.setdefault(cls, []).append(
                    (split, label_file.stem, line_idx, xc, yc, w * h)
                )
    return by_class


def median_ratio_bounds(values: list[float], ratio: float) -> tuple[float, float]:
    sorted_vals = sorted(values)
    median = sorted_vals[len(sorted_vals) // 2]
    return median / ratio, median * ratio


def save_preview(
    data_yaml_path: Path,
    split: str,
    stem: str,
    flagged_line_idx: int,
    class_names: list[str],
    out_path: Path,
) -> None:
    base_dir = data_yaml_path.parent
    img_path = base_dir / split / "images" / f"{stem}.png"
    label_path = base_dir / split / "labels" / f"{stem}.txt"
    img = cv2.imread(str(img_path))
    h, w = img.shape[:2]

    for i, line in enumerate(label_path.read_text().splitlines()):
        if not line.strip():
            continue
        cls, xc, yc, bw, bh = line.split()
        cls, xc, yc, bw, bh = int(cls), float(xc), float(yc), float(bw), float(bh)
        x1, y1 = int((xc - bw / 2) * w), int((yc - bh / 2) * h)
        x2, y2 = int((xc + bw / 2) * w), int((yc + bh / 2) * h)
        is_flagged = i == flagged_line_idx
        color = (0, 0, 255) if is_flagged else (0, 255, 0)
        thickness = 3 if is_flagged else 1
        cv2.rectangle(img, (x1, y1), (x2, y2), color, thickness)
        if is_flagged:
            cv2.putText(
                img,
                class_names[cls],
                (x1, max(y1 - 8, 12)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                color,
                2,
            )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_path), img)


def main() -> None:
    data = yaml.safe_load(DATA_YAML.read_text())
    class_names = data["names"]

    if REPORT_DIR.exists():
        shutil.rmtree(REPORT_DIR)
    previews_dir = REPORT_DIR / "previews"
    previews_dir.mkdir(parents=True)

    by_class = load_instances(DATA_YAML)

    report_lines = [
        f"# Label size outliers — {DATA_YAML.parent.name}",
        "",
        f"Median ratio threshold: {MEDIAN_RATIO}x | min instances per class to analyze: {MIN_INSTANCES}",
        "",
        "Flagged instances are candidates for review, not confirmed errors — check the preview image before editing labels.",
        "",
    ]
    total_flagged = 0

    for cls_id in sorted(by_class):
        entries = by_class[cls_id]
        if len(entries) < MIN_INSTANCES:
            continue
        areas = [e[5] for e in entries]
        low, high = median_ratio_bounds(areas, MEDIAN_RATIO)
        if FLAG_TOO_SMALL:
            flagged = [e for e in entries if e[5] < low or e[5] > high]
        else:
            flagged = [e for e in entries if e[5] > high]
        if not flagged:
            continue

        name = class_names[cls_id]
        report_lines.append(
            f"## {name} ({len(flagged)} of {len(entries)} instances flagged)"
        )
        report_lines.append("")
        report_lines.append("| split | image | area | normal range | preview |")
        report_lines.append("|---|---|---|---|---|")
        for split, stem, line_idx, _xc, _yc, area in flagged:
            preview_name = f"{name}_{split}_{stem}_{line_idx}.png"
            save_preview(
                DATA_YAML,
                split,
                stem,
                line_idx,
                class_names,
                previews_dir / preview_name,
            )
            direction = "too small" if area < low else "too large"
            report_lines.append(
                f"| {split} | {stem}.png | {area:.5f} ({direction}) | {low:.5f}-{high:.5f} | previews/{preview_name} |"
            )
            total_flagged += 1
        report_lines.append("")

    (REPORT_DIR / "report.md").write_text("\n".join(report_lines) + "\n")
    print(f"Flagged {total_flagged} instances across {len(by_class)} classes.")
    print(f"Report: {REPORT_DIR / 'report.md'}")


if __name__ == "__main__":
    main()
