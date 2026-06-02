from pathlib import Path
import re
import shutil
import subprocess
from typing import Any

import yaml

from .config import get_settings


def parse_count(value: Any) -> int:
    text = str(value or "").strip()
    if not text:
        return 0
    if "万" in text:
        try:
            return int(float(text.replace("万", "")) * 10000)
        except ValueError:
            return 0
    digits = re.findall(r"\d+", text)
    return int(digits[0]) if digits else 0


def note_key_from_url(url: str) -> str:
    match = re.search(r"/(?:search_result|explore)/([^?/#]+)", url)
    if match:
        return match.group(1)
    return re.sub(r"\W+", "_", url).strip("_")[:80]


def natural_image_key(path: Path) -> tuple:
    numbers = re.findall(r"\d+", path.stem)
    numeric = int(numbers[-1]) if numbers else 0
    return (numeric, path.name)


class OpenCLIError(RuntimeError):
    pass


class OpenCLIClient:
    def __init__(self):
        self.settings = get_settings()

    def check_available(self) -> dict:
        resolved = shutil.which(self.settings.opencli_bin) if "/" not in self.settings.opencli_bin else self.settings.opencli_bin
        if not resolved or not Path(resolved).exists():
            return {
                "ok": False,
                "message": "opencli 不在 PATH 中。请在 .env 设置 OPENCLI_BIN=/完整路径/opencli，或修复 shell PATH。",
                "bin": self.settings.opencli_bin,
            }
        return {"ok": True, "message": "opencli 可用", "bin": resolved}

    def run(self, args: list[str], timeout: int = 120) -> str:
        availability = self.check_available()
        if not availability["ok"]:
            raise OpenCLIError(availability["message"])
        result = subprocess.run(
            [self.settings.opencli_bin, *args],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode != 0:
            raise OpenCLIError((result.stderr or result.stdout).strip() or "opencli 执行失败")
        return result.stdout

    def search(self, keyword: str, limit: int) -> list[dict]:
        output = self.run(["xiaohongshu", "search", keyword, "--limit", str(limit)])
        data = yaml.safe_load(output) or []
        if not isinstance(data, list):
            return []
        notes = []
        for item in data:
            if not isinstance(item, dict):
                continue
            url = str(item.get("url", ""))
            notes.append(
                {
                    "note_key": note_key_from_url(url),
                    "keyword": keyword,
                    "title": item.get("title", ""),
                    "author": item.get("author", ""),
                    "likes": parse_count(item.get("likes")),
                    "url": url,
                    "status": "pending_detail",
                    "error_message": "",
                }
            )
        return notes

    def note_detail(self, url: str) -> dict:
        output = self.run(["xiaohongshu", "note", url])
        data = yaml.safe_load(output) or []
        detail: dict[str, Any] = {}
        if not isinstance(data, list):
            return detail
        for item in data:
            if not isinstance(item, dict):
                continue
            field = item.get("field")
            value = item.get("value", "")
            if field in {"title", "author", "content"}:
                detail[field] = str(value or "")
            elif field in {"likes", "collects", "comments"}:
                detail[field] = parse_count(value)
            elif field == "tags":
                detail["tags"] = str(value or "")
        return detail

    def download_images(self, url: str, note_key: str) -> list[dict]:
        output_dir = self.settings.images_dir
        self.run(["xiaohongshu", "download", url, "--output", str(output_dir)], timeout=180)
        note_dir = output_dir / note_key
        files = sorted(note_dir.glob("*"), key=natural_image_key)
        images = []
        for index, path in enumerate(files, start=1):
            if path.is_file() and path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}:
                images.append(
                    {
                        "local_path": str(path.relative_to(self.settings.database_path.parent.parent)),
                        "sort_order": index,
                        "file_size": path.stat().st_size,
                    }
                )
        return images
