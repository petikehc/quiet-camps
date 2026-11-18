from pathlib import Path, PurePosixPath

from httpx import URL, Client


def download_csv(client: Client, url: str, dest_dir: Path) -> Path:
    filename = PurePosixPath(URL(url).path).name
    filepath = dest_dir / filename

    if filepath.is_file():
        return filepath

    temp_file = filepath.with_name(filepath.name + ".part")

    try:
        with client.stream("GET", url) as response, temp_file.open("wb") as f:
            response.raise_for_status()
            for chunk in response.iter_bytes():
                f.write(chunk)
    except BaseException:
        temp_file.unlink(missing_ok=True)
        raise

    temp_file.replace(filepath)

    return filepath
