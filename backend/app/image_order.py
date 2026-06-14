from pathlib import Path
import re


def display_ordered_images(images: list[dict]) -> list[dict]:
    return sorted(images, key=image_order_key)


def image_order_key(image: dict) -> tuple:
    name = Path(image.get("local_path", "")).stem
    numbers = re.findall(r"\d+", name)
    numeric = int(numbers[-1]) if numbers else int(image.get("sort_order") or 0)
    return (numeric, image.get("local_path", ""))
