import random
import shutil
from pathlib import Path

import cv2

# Run this BEFORE split_train_valid.py, on the flat (pre-split) pool — same TRAIN_DIR convention.
# Keeps exactly one representative per near-duplicate cluster in the active pool (picked at random,
# not always the earliest — a burst's first frame isn't inherently better than the rest) and moves
# the rest to ARCHIVE_DIR instead of deleting them, so dataset
# stats (images-with-class counts) reflect real unique content — see project_game_mechanics_weapons-
# adjacent discussion: a single player_dead death produced bursts of 2-7 near-identical frames (corpse
# lingers on screen for seconds at 1 FPS), which inflated raw counts without adding real signal and
# made it impossible to tell how much unique data existed without this pass. split_train_valid.py's
# own duplicate-cluster exclusion stays in place as a safety net for anything that slips through, but
# after this step it should normally find nothing to exclude.
TRAIN_DIR = Path("data/labeled/v38-pool-1603/train")
ARCHIVE_DIR = Path("data/labeled/_duplicates_archive")
HASH_SIZE = 8
HAMMING_THRESHOLD = 3
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


def find_clusters(hashes: dict[str, int]) -> list[list[str]]:
    stems = list(hashes)
    parent = {s: s for s in stems}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for i in range(len(stems)):
        for j in range(i + 1, len(stems)):
            if hamming(hashes[stems[i]], hashes[stems[j]]) <= HAMMING_THRESHOLD:
                union(stems[i], stems[j])

    clusters: dict[str, list[str]] = {}
    for s in stems:
        clusters.setdefault(find(s), []).append(s)
    return list(clusters.values())


def archive_stem(images_dir: Path, labels_dir: Path, stem: str) -> None:
    (ARCHIVE_DIR / "images").mkdir(parents=True, exist_ok=True)
    (ARCHIVE_DIR / "labels").mkdir(parents=True, exist_ok=True)
    shutil.move(str(images_dir / f"{stem}.png"), ARCHIVE_DIR / "images" / f"{stem}.png")
    shutil.move(str(labels_dir / f"{stem}.txt"), ARCHIVE_DIR / "labels" / f"{stem}.txt")


def main() -> None:
    images_dir = TRAIN_DIR / "images"
    labels_dir = TRAIN_DIR / "labels"

    hashes = {p.stem: dhash(p) for p in images_dir.glob("*.png")}
    clusters = find_clusters(hashes)

    random.seed(SEED)
    multi_clusters = [c for c in clusters if len(c) > 1]
    archived = 0
    for cluster in multi_clusters:
        keeper = random.choice(cluster)
        extras = [s for s in cluster if s != keeper]
        for stem in extras:
            archive_stem(images_dir, labels_dir, stem)
            archived += 1

    remaining = len(list(images_dir.glob("*.png")))
    print(f"Total images before: {len(hashes)}")
    print(f"Duplicate clusters found: {len(multi_clusters)}")
    print(f"Archived (moved to {ARCHIVE_DIR}): {archived}")
    print(f"Remaining in pool: {remaining}")


if __name__ == "__main__":
    main()
