#!/usr/bin/env python
"""Extract readable meeting notice context from .eml files."""

from __future__ import annotations

import argparse
from email import policy
from email.parser import BytesParser
from email.header import decode_header, make_header
from pathlib import Path
from html.parser import HTMLParser


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if text:
            self.parts.append(text)

    def text(self) -> str:
        return "\n".join(self.parts)


def decode_value(value: str | None) -> str:
    if not value:
        return ""
    return str(make_header(decode_header(value)))


def message_body(message) -> str:
    plain_parts: list[str] = []
    html_parts: list[str] = []
    for part in message.walk():
        content_type = part.get_content_type()
        disposition = (part.get_content_disposition() or "").lower()
        if disposition == "attachment":
            continue
        if content_type == "text/plain":
            plain_parts.append(part.get_content())
        elif content_type == "text/html":
            extractor = TextExtractor()
            extractor.feed(part.get_content())
            html_parts.append(extractor.text())
    body = "\n\n".join(item.strip() for item in plain_parts if item.strip())
    if body:
        return body
    return "\n\n".join(item.strip() for item in html_parts if item.strip())


def parse_eml(path: Path) -> str:
    with path.open("rb") as file:
        message = BytesParser(policy=policy.default).parse(file)
    attachments = []
    for part in message.walk():
        if part.get_content_disposition() == "attachment":
            filename = decode_value(part.get_filename())
            if filename:
                attachments.append(filename)

    lines = [
        f"## {path.name}",
        "",
        f"- 제목: {decode_value(message.get('subject'))}",
        f"- 발신자: {decode_value(message.get('from'))}",
        f"- 수신자: {decode_value(message.get('to'))}",
        f"- 참조: {decode_value(message.get('cc'))}",
        f"- 발송일: {decode_value(message.get('date'))}",
        f"- 첨부: {', '.join(attachments) if attachments else '없음'}",
        "",
        "### 본문",
        "",
        message_body(message).strip() or "[본문 없음]",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract Markdown context from .eml files.")
    parser.add_argument("eml", nargs="+", help=".eml file paths")
    parser.add_argument("--out", required=True, help="Output Markdown path")
    args = parser.parse_args()

    paths = [Path(item).expanduser().resolve() for item in args.eml]
    output = Path(args.out).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    chunks = ["# 회의 공지 메일 참고 정보", ""]
    for path in paths:
        if not path.exists():
            raise SystemExit(f"EML file not found: {path}")
        chunks.append(parse_eml(path))
    output.write_text("\n".join(chunks).rstrip() + "\n", encoding="utf-8")
    print(f"Wrote notice context: {output}")


if __name__ == "__main__":
    main()
