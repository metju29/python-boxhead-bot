import random
import shutil
from pathlib import Path

import cv2

TRAIN_DIR = Path("data/labeled/v39-pool-dedupe-fix-1659/train")
VALID_DIR = Path("data/labeled/v39-pool-dedupe-fix-1659/valid")
# Classes still below the ~25-30 images-with-class threshold (see
# project_rare_class_split_threshold memory) are kept 100% in train so the
# already-scarce signal isn't split away. All classes have now crossed that
# threshold as of v19 — player_dead (the last holdout) reached 46 images.
PROTECTED_CLASSES = set()
# Burst-captured frames (game_4, 5 FPS) can be near-identical. A random split
# has no notion of that and will happily put one twin in train and the other
# in valid, inflating validation metrics with what's effectively memorized
# content (see find_train_valid_duplicates.py, which found 158 such pairs
# after a plain re-split reproduced the exact same partition — SEED is fixed,
# so re-splitting unchanged data changes nothing). Any stem with a
# near-duplicate anywhere in the pool is excluded from the valid draw here,
# the same way PROTECTED_CLASSES stems are.
HASH_SIZE = 8
HAMMING_THRESHOLD = 3
VALID_FRACTION = 0.2
SEED = 42


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


def find_duplicate_stems(images_dir: Path) -> set[str]:
    hashes = {p.stem: dhash(p) for p in images_dir.glob("*.png")}
    stems = list(hashes)
    duplicates = set()
    for i in range(len(stems)):
        for j in range(i + 1, len(stems)):
            if hamming(hashes[stems[i]], hashes[stems[j]]) <= HAMMING_THRESHOLD:
                duplicates.add(stems[i])
                duplicates.add(stems[j])
    return duplicates


if (VALID_DIR / "images").exists() and any((VALID_DIR / "images").iterdir()):
    raise SystemExit(
        f"{VALID_DIR}/images already contains files — this script isn't idempotent, "
        "re-running would draw an additional VALID_FRACTION on top of the existing split. "
        "Move the existing valid images/labels back into train (or reset from a fresh merge) first."
    )

normal_stems = list()
rare_stems = list()

duplicate_stems = find_duplicate_stems(TRAIN_DIR / "images")

txt_files_paths_list = (TRAIN_DIR / "labels").glob("*.txt")
for txt_file_path in txt_files_paths_list:
    txt_string = txt_file_path.read_text()
    is_rare = any(
        int(line.split()[0]) in PROTECTED_CLASSES for line in txt_string.splitlines()
    )
    if is_rare or txt_file_path.stem in duplicate_stems:
        rare_stems.append(txt_file_path.stem)
    else:
        normal_stems.append(txt_file_path.stem)

random.seed(SEED)
valid_count = int(len(normal_stems) * VALID_FRACTION)
valid_stems = random.sample(normal_stems, valid_count)

(VALID_DIR / "images").mkdir(parents=True, exist_ok=True)
(VALID_DIR / "labels").mkdir(parents=True, exist_ok=True)

for stem in valid_stems:
    image_path = TRAIN_DIR / "images" / f"{stem}.png"
    label_path = TRAIN_DIR / "labels" / f"{stem}.txt"
    shutil.move(image_path, VALID_DIR / "images")
    shutil.move(label_path, VALID_DIR / "labels")
print(f"Duplicate-cluster stems (forced to train): {len(duplicate_stems)}")
print(f"Rare steams: {len(rare_stems)}")
print(f"Valid steams: {len(valid_stems)}")
print(f"Train steams: {len(rare_stems) + (len(normal_stems) - valid_count)}")
