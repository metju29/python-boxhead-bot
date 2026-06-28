from pathlib import Path

raw_dir = Path("tests/fixtures/raw")
count = 0

for file in raw_dir.iterdir():
    if file.is_file():
        try:
            file.unlink()
            count += 1
            print(f"Delete: {file.name}")
        except Exception as e:
            print(f"Error deleting {file.name}: {e}")
print(f"\nOperation completed. Number of deleted files: {count}")
