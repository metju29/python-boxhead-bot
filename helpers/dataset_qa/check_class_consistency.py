import shutil
from pathlib import Path

import cv2
import yaml

DATA_YAML = Path("data/labeled/v39-pool-dedupe-fix-1659/data.yaml")
# Classes that must never co-occur in the same frame. There is exactly one
# player, so it can't be alive and dead at once. devil/devil_dead and
# zombie/zombie_dead are deliberately NOT listed here: multiple enemies can be
# on screen at once, so one lying dead while another is alive in the same
# frame is legitimate, not a labeling error.
EXCLUSIVE_PAIRS = [("player", "player_dead")]
REPORT_DIR = Path("reports") / DATA_YAML.parent.name / "class_consistency"


def classes_in_label_file(label_path: Path, class_names: list[str]) -> set[str]:
    classes = set()
    for line in label_path.read_text().splitlines():
        if not line.strip():
            continue
        cls_id = int(line.split()[0])
        classes.add(class_names[cls_id])
    return classes


def save_preview(
    base_dir: Path, split: str, stem: str, class_names: list[str], out_path: Path
) -> None:
    img_path = base_dir / split / "images" / f"{stem}.png"
    label_path = base_dir / split / "labels" / f"{stem}.txt"
    img = cv2.imread(str(img_path))
    h, w = img.shape[:2]

    for line in label_path.read_text().splitlines():
        if not line.strip():
            continue
        cls, xc, yc, bw, bh = line.split()
        cls, xc, yc, bw, bh = int(cls), float(xc), float(yc), float(bw), float(bh)
        x1, y1 = int((xc - bw / 2) * w), int((yc - bh / 2) * h)
        x2, y2 = int((xc + bw / 2) * w), int((yc + bh / 2) * h)
        cv2.rectangle(img, (x1, y1), (x2, y2), (0, 0, 255), 2)
        cv2.putText(
            img,
            class_names[cls],
            (x1, max(y1 - 8, 12)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 0, 255),
            2,
        )

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
        f"# Class consistency violations — {DATA_YAML.parent.name}",
        "",
        f"Exclusive pairs checked: {EXCLUSIVE_PAIRS}",
        "",
        "| split | image | conflicting classes | preview |",
        "|---|---|---|---|",
    ]
    total_flagged = 0

    for split in ("train", "valid"):
        labels_dir = base_dir / split / "labels"
        if not labels_dir.exists():
            continue
        for label_file in sorted(labels_dir.glob("*.txt")):
            present = classes_in_label_file(label_file, class_names)
            for cls_a, cls_b in EXCLUSIVE_PAIRS:
                if cls_a in present and cls_b in present:
                    preview_name = f"{split}_{label_file.stem}.png"
                    save_preview(
                        base_dir,
                        split,
                        label_file.stem,
                        class_names,
                        previews_dir / preview_name,
                    )
                    report_lines.append(
                        f"| {split} | {label_file.stem}.png | {cls_a} + {cls_b} | previews/{preview_name} |"
                    )
                    total_flagged += 1

    (REPORT_DIR / "report.md").write_text("\n".join(report_lines) + "\n")
    print(f"Flagged {total_flagged} frames with conflicting classes.")
    print(f"Report: {REPORT_DIR / 'report.md'}")


if __name__ == "__main__":
    main()
