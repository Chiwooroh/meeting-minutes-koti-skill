#!/usr/bin/env python
"""Build an official Korean meeting-minutes HWPX filename from a Markdown draft."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


INVALID_FILENAME_CHARS = r'<>:"/\|?*'


FIELD_ALIASES = {
    "project": ("과제명", "怨쇱젣紐"),
    "meeting": ("회의명", "뚯쓽紐"),
    "datetime": ("개최일시", "개최일시·장소", "媛쒖턀", "쇱떆"),
}


def normalize_label(value: str) -> str:
    return re.sub(r"\s+", "", value).strip().strip("?")


def parse_fields(markdown: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for raw_line in markdown.splitlines():
        line = raw_line.strip()
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) < 2:
            continue
        label = normalize_label(cells[0])
        value = cells[1].strip()
        if not value or set(value) <= {"-", ":"}:
            continue
        for key, aliases in FIELD_ALIASES.items():
            if key in fields:
                continue
            if any(alias in label for alias in aliases):
                fields[key] = value
                break
    return fields


def date_code(value: str, fallback: str | None = None) -> str:
    candidates = [value, fallback or ""]
    for candidate in candidates:
        match = re.search(r"20(\d{2})\D{0,4}(\d{1,2})\D{0,4}(\d{1,2})", candidate)
        if match:
            yy, mm, dd = match.groups()
            return f"{yy}{int(mm):02d}{int(dd):02d}"
        match = re.search(r"\b(\d{2})(\d{2})(\d{2})\b", candidate)
        if match:
            return "".join(match.groups())
    return "날짜확인"


def clean_title(value: str) -> str:
    title = value.strip()
    title = re.sub(r"\s+", " ", title)
    title = re.sub(r"^국토교통\s*R&D\s*내일의\s*리더\s*온보딩\s*프로그램\s*[-–]\s*", "온보딩 프로그램 ", title)
    title = title.replace(",", " ")
    for char in INVALID_FILENAME_CHARS:
        title = title.replace(char, " ")
    title = re.sub(r"\s+", " ", title).strip(" .-_")
    if title and not title.endswith("회의록"):
        title = f"{title} 회의록"
    return title or "회의록"


def official_filename(markdown_path: Path, folder_hint: str | None = None) -> str:
    text = markdown_path.read_text(encoding="utf-8-sig", errors="replace")
    fields = parse_fields(text)
    code = date_code(fields.get("datetime", ""), fallback=folder_hint)
    title = clean_title(fields.get("meeting", "회의록"))
    return f"{code} - {title}.hwpx"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Meeting-minutes Markdown draft")
    parser.add_argument("--directory", help="Directory to join with the generated filename")
    parser.add_argument("--folder-hint", help="Folder name or other text containing fallback date")
    args = parser.parse_args()

    input_path = Path(args.input)
    folder_hint = args.folder_hint or input_path.parent.name
    filename = official_filename(input_path, folder_hint=folder_hint)
    if args.directory:
        print(str(Path(args.directory) / filename))
    else:
        print(filename)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
