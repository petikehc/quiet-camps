import csv
from pathlib import Path


def detect_encoding(path: Path) -> str:
    data = path.read_bytes()
    try:
        data.decode("utf-8-sig")
    except UnicodeDecodeError:
        encoding = "cp1252"
    else:
        encoding = "utf-8-sig"
    return encoding


def read_header(path: Path) -> tuple[str, ...]:
    encoding = detect_encoding(path)
    with path.open(encoding=encoding, newline="") as f:
        reader = csv.reader(f)
        first_line = next(reader)
        return tuple(first_line)
