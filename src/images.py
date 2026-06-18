"""Task 4 - Images.

Apply image resolution and the sensitivity-based suppression rule:
- sensitivity True  -> image suppressed (set to None), the editorial guardrail.
- otherwise         -> keep the source image if it is a valid http(s) URL.
"""

from __future__ import annotations


def _valid_image(url) -> bool:
    return isinstance(url, str) and url.startswith(("http://", "https://"))


def resolve_images(edition: dict) -> dict:
    """Walk every story; suppress sensitive images, drop invalid URLs."""
    for section in edition.get("sections", []):
        for story in section.get("stories", []):
            if story.get("sensitivity"):
                story["image"] = None
            elif not _valid_image(story.get("image")):
                story["image"] = None
    return edition


if __name__ == "__main__":
    import json
    from pathlib import Path

    edition = json.loads(Path("data/fixtures/edition_sample.json").read_text())
    resolve_images(edition)

    stories = [st for s in edition["sections"] for st in s["stories"]]
    sensitive_with_image = [st["id"] for st in stories if st["sensitivity"] and st["image"]]
    assert not sensitive_with_image, f"sensitive stories kept images: {sensitive_with_image}"

    with_img = sum(1 for st in stories if st["image"])
    without_img = sum(1 for st in stories if not st["image"])
    print(f"OK: images suppressed for all sensitive stories")
    print(f"with image: {with_img}, without image: {without_img}")
