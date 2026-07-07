"""Download a queue row's Asset URL(s) to local temp files so Postiz can
ingest them. um-assets style stores take an optional X-Token header."""
from pathlib import Path
from urllib.parse import urlparse

import requests


class AssetError(Exception):
    pass


def download_assets(urls: list, dest_dir, token: str = None) -> list:
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    headers = {"X-Token": token} if token else {}
    names = [Path(urlparse(u).path).name or "asset.bin" for u in urls]
    if len(set(names)) != len(names):
        raise AssetError(f"duplicate asset filenames in {names} — rename source files")
    paths = []
    for url, name in zip(urls, names):
        with requests.get(url, headers=headers, stream=True,
                          timeout=(10, 300)) as r:
            if r.status_code != 200:
                raise AssetError(f"GET {url} -> HTTP {r.status_code}")
            out = dest_dir / name
            with out.open("wb") as fh:
                for chunk in r.iter_content(chunk_size=1 << 20):
                    fh.write(chunk)
        if out.stat().st_size == 0:
            raise AssetError(f"GET {url} -> empty body")
        paths.append(out)
    return paths
