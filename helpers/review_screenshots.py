from pathlib import Path

import cv2

INPUT_DIR = Path("data/raw/dead_player_curated_5")
IMAGES_DIR = INPUT_DIR
LOG_FILE = INPUT_DIR / "screenshot_review_log.txt"

YES_KEYS = {32}  # space
NO_KEYS = {13, 10, ord("n")}  # enter, n
BACK_KEY = ord("b")
QUIT_KEY = ord("q")

image_paths = sorted(IMAGES_DIR.glob("*.png"))

reviewed = {}
if LOG_FILE.exists():
    for line in LOG_FILE.read_text().splitlines():
        if not line.strip():
            continue
        fname, flag = line.rsplit(",", 1)
        reviewed[fname] = flag

log_lines = [f"{fname},{flag}" for fname, flag in reviewed.items()]
todo = [p for p in image_paths if p.name not in reviewed]

print(f"{len(reviewed)} already reviewed, {len(todo)} left.")
print(
    "SPACE = interesting (yes) | ENTER/n = skip (no) | b = back one | q = save & quit"
)

cv2.namedWindow("review", cv2.WINDOW_NORMAL)

i = 0
while i < len(todo):
    image_path = todo[i]
    img = cv2.imread(str(image_path))
    done_count = len(reviewed)
    overlay = f"{done_count + 1}/{len(image_paths)}  {image_path.name}"
    cv2.putText(img, overlay, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
    cv2.imshow("review", img)
    key = cv2.waitKey(0) & 0xFF

    if key in YES_KEYS:
        flag = "yes"
    elif key in NO_KEYS:
        flag = "no"
    elif key == BACK_KEY:
        if log_lines:
            last = log_lines.pop()
            last_fname = last.rsplit(",", 1)[0]
            del reviewed[last_fname]
            LOG_FILE.write_text("\n".join(log_lines) + ("\n" if log_lines else ""))
            # Rebuild todo (the undone image may have been reviewed in a *previous* run, so it
            # was never in this session's todo list) and find where it landed, rather than just
            # decrementing i — that can go negative and wrap to the end via Python indexing.
            todo = [p for p in image_paths if p.name not in reviewed]
            i = next((idx for idx, p in enumerate(todo) if p.name == last_fname), 0)
            print(f"undid {last_fname}")
        continue
    elif key == QUIT_KEY:
        break
    else:
        continue  # ignore unknown key, redisplay same image

    reviewed[image_path.name] = flag
    log_lines.append(f"{image_path.name},{flag}")
    with LOG_FILE.open("a") as f:
        f.write(f"{image_path.name},{flag}\n")
    i += 1

cv2.destroyAllWindows()

yes_count = sum(1 for v in reviewed.values() if v == "yes")
print(
    f"Done for now. {len(reviewed)}/{len(image_paths)} reviewed, {yes_count} flagged yes."
)
print(f"Log: {LOG_FILE}")
