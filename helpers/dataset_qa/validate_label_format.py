from pathlib import Path

import yaml

DATA_YAML = Path("data/labeled/v38-pool-1603/data.yaml")
REPORT_DIR = Path("reports") / DATA_YAML.parent.name / "label_format_violations"


def validate_line(line: str, num_classes: int) -> str | None:
    fields = line.split()
    if len(fields) != 5:
        return f"expected 5 fields, got {len(fields)}"
    try:
        cls = int(fields[0])
        xc, yc, w, h = (float(v) for v in fields[1:])
    except ValueError:
        return "non-numeric field"
    if not 0 <= cls < num_classes:
        return f"class index {cls} out of range [0, {num_classes - 1}]"
    if w <= 0 or h <= 0:
        return f"non-positive width/height (w={w}, h={h})"
    if not (
        0.0 <= xc <= 1.0 and 0.0 <= yc <= 1.0 and 0.0 <= w <= 1.0 and 0.0 <= h <= 1.0
    ):
        return f"coordinate outside [0, 1] (xc={xc}, yc={yc}, w={w}, h={h})"
    return None


def main() -> None:
    data = yaml.safe_load(DATA_YAML.read_text())
    num_classes = data["nc"]
    base_dir = DATA_YAML.parent

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_lines = [
        f"# Label format violations — {DATA_YAML.parent.name}",
        "",
        "| split | file | line | issue |",
        "|---|---|---|---|",
    ]
    total_violations = 0
    total_lines = 0

    for split in ("train", "valid"):
        labels_dir = base_dir / split / "labels"
        if not labels_dir.exists():
            continue
        for label_file in sorted(labels_dir.glob("*.txt")):
            for line_idx, line in enumerate(label_file.read_text().splitlines()):
                if not line.strip():
                    continue
                total_lines += 1
                issue = validate_line(line, num_classes)
                if issue:
                    report_lines.append(
                        f"| {split} | {label_file.name} | {line_idx} | {issue} |"
                    )
                    total_violations += 1

    (REPORT_DIR / "report.md").write_text("\n".join(report_lines) + "\n")
    print(f"Checked {total_lines} label lines, found {total_violations} violations.")
    print(f"Report: {REPORT_DIR / 'report.md'}")


if __name__ == "__main__":
    main()
