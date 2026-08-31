import re
import shutil
from datetime import datetime
from pathlib import Path

import cv2

DATA_YAML = Path("data/labeled/v39-pool-dedupe-fix-1659/data.yaml")
HASH_SIZE = 8
HAMMING_THRESHOLD = 3  # dHash bits (of HASH_SIZE * (HASH_SIZE - 1)) that may differ to flag as near-duplicate
REPORT_DIR = Path("reports") / DATA_YAML.parent.name / "train_valid_duplicates"

# Filenames follow "..._YYYYMMDD_HHMMSS..." across every game/export naming
# variant seen so far (raw captures, Roboflow re-exports with a "_png.rf.<id>"
# suffix, curated batches with an extra microsecond group). Only the
# date_time part is used — second-level precision is plenty for a >=1s
# time-delta diagnostic and keeps the regex robust to whatever trails it.
TIMESTAMP_RE = re.compile(r"(\d{8}_\d{6})")


def dhash(image_path: Path, hash_size: int = HASH_SIZE) -> int:
    img = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
    resized = cv2.resize(img, (hash_size + 1, hash_size), interpolation=cv2.INTER_AREA)
    diff = resized[:, 1:] > resized[:, :-1]
    value = 0
    for bit in diff.flatten():
        value = (value << 1) | int(bit)
    return value


def hamming(a: int, b: int) -> int:
    return bin(a ^ b).count("1")


def parse_timestamp(stem: str) -> datetime | None:
    match = TIMESTAMP_RE.search(stem)
    if not match:
        return None
    return datetime.strptime(match.group(1), "%Y%m%d_%H%M%S")


def load_hashes(base_dir: Path, split: str) -> dict[str, int]:
    images_dir = base_dir / split / "images"
    return {p.stem: dhash(p) for p in images_dir.glob("*.png")}


def save_preview(base_dir: Path, split: str, stem: str, out_path: Path) -> None:
    if out_path.exists():
        return
    img_path = base_dir / split / "images" / f"{stem}.png"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(img_path, out_path)


def main() -> None:
    base_dir = DATA_YAML.parent

    if REPORT_DIR.exists():
        shutil.rmtree(REPORT_DIR)
    previews_dir = REPORT_DIR / "previews"
    previews_dir.mkdir(parents=True)

    train_hashes = load_hashes(base_dir, "train")
    valid_hashes = load_hashes(base_dir, "valid")

    report_lines = [
        f"# Train/valid near-duplicates — {DATA_YAML.parent.name}",
        "",
        f"Hamming distance threshold: <= {HAMMING_THRESHOLD} (of {HASH_SIZE * (HASH_SIZE - 1)} bits)",
        "",
        "Flagged pairs are candidates for review, not confirmed duplicates — a busy scene sharing "
        "the same static arena background can hash as similar without being the same moment. "
        "Check both previews before removing anything.",
        "",
        "| valid image | train image | hamming distance | time delta (s) |",
        "|---|---|---|---|",
    ]
    total_flagged = 0

    for valid_stem in sorted(valid_hashes):
        valid_hash = valid_hashes[valid_stem]
        valid_ts = parse_timestamp(valid_stem)
        for train_stem, train_hash in train_hashes.items():
            distance = hamming(valid_hash, train_hash)
            if distance > HAMMING_THRESHOLD:
                continue
            train_ts = parse_timestamp(train_stem)
            if valid_ts and train_ts:
                delta = f"{abs((valid_ts - train_ts).total_seconds()):.1f}"
            else:
                delta = "n/a"
            save_preview(
                base_dir, "valid", valid_stem, previews_dir / f"{valid_stem}__valid.png"
            )
            save_preview(
                base_dir, "train", train_stem, previews_dir / f"{train_stem}__train.png"
            )
            report_lines.append(
                f"| {valid_stem}.png | {train_stem}.png | {distance} | {delta} |"
            )
            total_flagged += 1

    (REPORT_DIR / "report.md").write_text("\n".join(report_lines) + "\n")
    print(f"Flagged {total_flagged} candidate pairs.")
    print(f"Report: {REPORT_DIR / 'report.md'}")


if __name__ == "__main__":
    main()
