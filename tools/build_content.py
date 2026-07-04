from __future__ import annotations

import json
import posixpath
import re
import shutil
import sys
import zipfile
from io import BytesIO
from pathlib import Path
from typing import Iterable
from xml.etree import ElementTree as ET

import pdfplumber
from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
SITE_DIR = ROOT / "website"
SOURCE_DIR = ROOT / "02 成果"
DATA_DIR = SITE_DIR / "assets" / "data"
IMG_DIR = SITE_DIR / "assets" / "img"
PROJECT_IMG_DIR = IMG_DIR / "projects"

NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}

PROJECT_RANGES = [
    range(2, 6),
    range(6, 9),
    range(9, 12),
    range(12, 15),
    range(15, 19),
    range(19, 22),
    range(22, 25),
    range(25, 28),
    range(28, 30),
    range(30, 33),
    range(33, 35),
    range(35, 37),
    range(37, 39),
    range(39, 41),
    range(41, 43),
    range(43, 45),
]

FEATURED_INDEXES = {1, 2, 3, 4, 7, 16}


def find_source_file(pattern: str, suffix: str) -> Path:
    matches = [
        path
        for path in SOURCE_DIR.glob(pattern)
        if path.suffix.lower() == suffix and "2025" in path.name
    ]
    if not matches:
        raise FileNotFoundError(f"Could not find source file: {pattern}")
    return sorted(matches, key=lambda path: path.stat().st_mtime, reverse=True)[0]


def compact_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])", "", text)
    text = re.sub(r"\s+([，。；：！？、])", r"\1", text)
    text = re.sub(r"([（《“])\s+", r"\1", text)
    text = re.sub(r"\s+([）》”])", r"\1", text)
    text = text.replace(" : ", "：").replace(": ", "：")
    text = text.replace(" ;", "；").replace("; ", "；")
    return text


def clip_sentence(text: str, limit: int = 360) -> str:
    text = compact_text(text)
    if len(text) <= limit:
        return text
    clipped = text[:limit]
    last_stop = max(clipped.rfind(mark) for mark in "。！？；")
    if last_stop > limit * 0.55:
        return clipped[: last_stop + 1]
    return clipped.rstrip("，、；：") + "..."


def extract_project_text(pdf_path: Path) -> list[dict[str, str | None]]:
    projects: list[dict[str, str | None]] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page_index, page in enumerate(pdf.pages, start=1):
            text = compact_text(page.extract_text(x_tolerance=1, y_tolerance=3) or "")
            if "地点" not in text or "面积" not in text:
                continue

            title = compact_text(text.split("地点", 1)[0].strip(" -"))
            location_match = re.search(r"地点\s*[:：]\s*(.*?)\s*面积", text)
            area_match = re.search(r"面积\s*[:：]\s*([0-9,.\s]+(?:㎡|m2|m²)?)", text)
            location = compact_text(location_match.group(1)) if location_match else ""
            area = compact_text(area_match.group(1)) if area_match else None

            if area_match:
                summary_start = area_match.end()
            elif location_match:
                summary_start = location_match.end()
            else:
                summary_start = len(title)

            summary = text[summary_start:].strip()
            summary = re.sub(r"^㎡\s*", "", summary)
            summary = clip_sentence(summary)

            projects.append(
                {
                    "page": str(page_index),
                    "title": title,
                    "location": location,
                    "area": area or None,
                    "summary": summary,
                }
            )

    if len(projects) != 16:
        raise RuntimeError(f"Expected 16 projects, found {len(projects)}")
    return projects


def slide_media(zf: zipfile.ZipFile, slide_number: int) -> list[str]:
    slide = f"ppt/slides/slide{slide_number}.xml"
    rels_file = f"ppt/slides/_rels/slide{slide_number}.xml.rels"
    if slide not in zf.namelist() or rels_file not in zf.namelist():
        return []

    rel_root = ET.fromstring(zf.read(rels_file))
    rel_map: dict[str, str] = {}
    for rel in rel_root:
        rid = rel.attrib.get("Id")
        target = rel.attrib.get("Target")
        if rid and target and "media" in target:
            rel_map[rid] = posixpath.normpath(posixpath.join("ppt/slides", target))

    slide_root = ET.fromstring(zf.read(slide))
    media: list[str] = []
    for blip in slide_root.findall(".//a:blip", NS):
        embed = blip.attrib.get(f"{{{NS['r']}}}embed")
        target = rel_map.get(embed or "")
        if target and target not in media:
            media.append(target)
    return media


def resize_for_web(image: Image.Image, max_edge: int) -> Image.Image:
    image = image.copy()
    if image.mode in {"RGBA", "LA"}:
        background = Image.new("RGB", image.size, (245, 244, 240))
        background.paste(image, mask=image.getchannel("A"))
        image = background
    else:
        image = image.convert("RGB")

    width, height = image.size
    scale = min(1.0, max_edge / max(width, height))
    if scale < 1:
        image = image.resize((round(width * scale), round(height * scale)), Image.Resampling.LANCZOS)
    return image


def save_webp_variants(image: Image.Image, base_path: Path, alt: str) -> dict[str, str | int]:
    large = resize_for_web(image, 1900)
    small = resize_for_web(image, 900)
    large_path = base_path.with_name(base_path.name + "-lg.webp")
    small_path = base_path.with_name(base_path.name + "-sm.webp")
    large.save(large_path, "WEBP", quality=80, method=6)
    small.save(small_path, "WEBP", quality=76, method=6)
    return {
        "src": "./" + large_path.relative_to(SITE_DIR).as_posix(),
        "small": "./" + small_path.relative_to(SITE_DIR).as_posix(),
        "width": large.width,
        "height": large.height,
        "alt": alt,
    }


def media_to_image(zf: zipfile.ZipFile, media_path: str) -> Image.Image:
    with Image.open(BytesIO(zf.read(media_path))) as image:
        image.load()
        return image.copy()


def collect_range_media(zf: zipfile.ZipFile, slides: Iterable[int]) -> list[str]:
    media: list[str] = []
    for slide_number in slides:
        for item in slide_media(zf, slide_number):
            if item not in media:
                media.append(item)
    return media


def build_assets(pptx_path: Path, projects: list[dict[str, str | None]]) -> None:
    if PROJECT_IMG_DIR.exists():
        shutil.rmtree(PROJECT_IMG_DIR)
    PROJECT_IMG_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(pptx_path) as zf:
        hero_media = slide_media(zf, 1)[0]
        hero_image = media_to_image(zf, hero_media)
        save_webp_variants(hero_image, IMG_DIR / "hero", "半格设计研究室作品集封面模型图")

        for index, (project, slides) in enumerate(zip(projects, PROJECT_RANGES, strict=True), start=1):
            slug = f"p{index:02d}"
            project_dir = PROJECT_IMG_DIR / slug
            project_dir.mkdir(parents=True, exist_ok=True)

            images = []
            for image_index, media_path in enumerate(collect_range_media(zf, slides), start=1):
                image = media_to_image(zf, media_path)
                alt = f"{project['title']} 项目图片 {image_index}"
                images.append(save_webp_variants(image, project_dir / f"{slug}-{image_index:02d}", alt))

            project.update(
                {
                    "id": slug,
                    "featured": index in FEATURED_INDEXES,
                    "images": images,
                }
            )

    payload = {
        "brand": {
            "name": "半格设计研究室",
            "englishName": "HALF ARCHITECTS",
            "years": "2018-2025",
            "source": "半格建筑事务所作品集2025版",
        },
        "projects": projects,
    }
    (DATA_DIR / "projects.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    pdf_path = find_source_file("*2025*.pdf", ".pdf")
    pptx_path = find_source_file("*2025*.pptx", ".pptx")
    projects = extract_project_text(pdf_path)
    build_assets(pptx_path, projects)
    print(f"Built {len(projects)} projects from {pdf_path.name} and {pptx_path.name}")


if __name__ == "__main__":
    sys.exit(main())
