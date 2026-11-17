import csv
from collections import Counter, defaultdict
from collections.abc import Iterable
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


def group_by_header(paths: Iterable[Path]) -> dict[tuple[str, ...], list[str]]:
    """Header -> the names of the files that have it, in first-seen order."""
    groups: defaultdict[tuple[str, ...], list[str]] = defaultdict(list)
    for path in paths:
        header = read_header(path)
        groups[header].append(path.name)
    return dict(groups)


def value_shapes(values: Iterable[str]) -> Counter[str]:
    """Count the shape of each value: every digit becomes "9", everything else stays."""
    shapes: list[str] = []
    for value in values:
        shape: list[str] = []
        for char in value:
            if char.isdigit():
                shape.append("9")
            else:
                shape.append(char)

        shapes.append("".join(shape))

    return Counter(shapes)
