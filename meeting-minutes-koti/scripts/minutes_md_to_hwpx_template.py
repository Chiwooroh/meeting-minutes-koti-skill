#!/usr/bin/env python
"""Fill a HWPX meeting-minutes template from a minutes Markdown file.

This keeps the user's HWPX table layout, but writes the minutes body into the
real "meeting content" table cell and relaxes negative character spacing so
long Korean text is not squeezed to fit the cell.
"""

from __future__ import annotations

import argparse
import copy
import re
import shutil
import tempfile
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from lxml import etree


HP_NS = "http://www.hancom.co.kr/hwpml/2011/paragraph"
HH_NS = "http://www.hancom.co.kr/hwpml/2011/head"
NS = {"hp": HP_NS, "hh": HH_NS}

FIELDS = {
    "project": "\uacfc\uc81c\uba85",
    "meeting": "\ud68c\uc758\uba85",
    "datetime": "\uac1c\ucd5c\uc77c\uc2dc",
    "place": "\uc7a5\uc18c",
    "attendees": "\ucc38\uc11d\uc778\uc6d0",
    "purpose": "\ud68c\uc758\ubaa9\uc801",
}

FIELD_ALIASES = {
    "project": ["\uacfc\uc81c\uba85", "\uacfc \uc81c \uba85", "\uacfc  \uc81c  \uba85"],
    "meeting": ["\ud68c\uc758\uba85", "\ud68c \uc758 \uba85", "\ud68c  \uc758  \uba85"],
    "datetime": ["\uac1c\ucd5c\uc77c\uc2dc", "\uc77c\uc2dc", "\uac1c\ucd5c\uc77c\uc2dc\u00b7\uc7a5\uc18c"],
    "place": ["\uc7a5\uc18c"],
    "attendees": ["\ucc38\uc11d\uc778\uc6d0", "\ucc38 \uc11d \uc778 \uc6d0"],
    "purpose": ["\ud68c\uc758\ubaa9\uc801", "\ud68c \uc758 \ubaa9 \uc801"],
}

TEMPLATE_LABELS = {
    "project": "\uacfc  \uc81c  \uba85",
    "meeting": "\ud68c  \uc758  \uba85",
    "datetime": "\uc77c\uc2dc",
    "place": "\uc7a5\uc18c",
    "attendees": "\ucc38 \uc11d \uc778 \uc6d0",
    "purpose": "\ud68c \uc758 \ubaa9 \uc801",
    "content": "\ud68c \uc758 \ub0b4 \uc6a9",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create HWPX meeting minutes from Markdown.")
    parser.add_argument("--template", required=True, help="HWPX template path.")
    parser.add_argument("--style-reference", help="Optional HWPX whose paragraph/table formatting should be preserved.")
    parser.add_argument("--input", required=True, help="Minutes Markdown path.")
    parser.add_argument("--output", required=True, help="Output HWPX path.")
    return parser.parse_args()


def normalize_label(text: str) -> str:
    return re.sub(r"\s+", "", text.strip())


def canonical_field(label: str) -> str | None:
    compact = normalize_label(label)
    for field, aliases in FIELD_ALIASES.items():
        if compact in {normalize_label(alias) for alias in aliases}:
            return field
    return None


def parse_minutes(markdown: str) -> tuple[dict[str, str], list[str]]:
    fields = {key: "" for key in FIELDS}
    for line in markdown.splitlines():
        if not line.startswith("|"):
            continue
        cols = [part.strip() for part in line.strip().strip("|").split("|")]
        if len(cols) < 2 or re.fullmatch(r"[-:\s]+", cols[0]) or cols[0] == "\uad6c\ubd84":
            continue
        field = canonical_field(cols[0])
        if field:
            fields[field] = cols[1]

    content = ""
    content_patterns = [
        r"##\s*\ud68c\uc758\s*\ub0b4\uc6a9\s*(.*?)(?=\n##\s*\uacf5\uc9c0|\n##\s*\ud655\uc778|\Z)",
        r"##\s*\?뚯쓽\s*\?댁슜\s*(.*?)(?=\n##\s*怨듭|\n##\s*\?뺤씤|\Z)",
    ]
    for pattern in content_patterns:
        match = re.search(pattern, markdown, re.S)
        if match:
            content = match.group(1).strip()
            break

    check_match = re.search(r"##\s*\ud655\uc778\s*\ud544\uc694\s*\uc0ac\ud56d\s*(.*?)(?=\n## |\Z)", markdown, re.S)
    if check_match:
        check_text = check_match.group(1).strip()
        if check_text and check_text != "- \uc5c6\uc74c":
            content = f"{content}\n\n\u25a1 \ud655\uc778 \ud544\uc694 \uc0ac\ud56d\n{check_text}".strip()

    return fields, [line.rstrip() for line in content.splitlines() if line.strip()]


def cell_text(cell) -> str:
    return "".join(t.text or "" for t in cell.xpath(".//hp:t", namespaces=NS))


def find_cells(root):
    return root.xpath("//hp:tbl//hp:tc", namespaces=NS)


def find_cell_after_label(root, label: str):
    cells = find_cells(root)
    wanted = normalize_label(label)
    for index, cell in enumerate(cells):
        if normalize_label(cell_text(cell)) == wanted and index + 1 < len(cells):
            return cells[index + 1]
    raise SystemExit(f"Could not find label in HWPX template: {label}")


def clear_extra_controls(paragraph) -> None:
    for elem in paragraph.xpath(".//hp:lineBreak | .//hp:hyphen | .//hp:nbSpace", namespaces=NS):
        parent = elem.getparent()
        if parent is not None:
            parent.remove(elem)


def set_paragraph_text(paragraph, text: str) -> None:
    clear_extra_controls(paragraph)
    texts = paragraph.xpath(".//hp:t", namespaces=NS)
    if not texts:
        run = paragraph.find(".//hp:run", namespaces=NS)
        if run is None:
            run = etree.SubElement(paragraph, f"{{{HP_NS}}}run", charPrIDRef="9")
        texts = [etree.SubElement(run, f"{{{HP_NS}}}t")]
    texts[0].text = text
    for item in texts[1:]:
        item.text = ""


def remove_paragraph(paragraph) -> None:
    parent = paragraph.getparent()
    if parent is not None:
        parent.remove(paragraph)


def ensure_paragraph_has_single_run(paragraph) -> None:
    runs = paragraph.xpath("./hp:run", namespaces=NS)
    if not runs:
        etree.SubElement(paragraph, f"{{{HP_NS}}}run")
        return
    for run in runs[1:]:
        paragraph.remove(run)


def find_style_by_name(header_root, name: str):
    for style in header_root.xpath("//hh:style", namespaces=NS):
        if style.get("name") == name:
            return style
    return None


def apply_paragraph_role_style(paragraph, text: str, header_root) -> None:
    stripped = text.lstrip()
    style_name = None
    if stripped.startswith("\u25a1") or stripped.startswith("\u2751"):
        style_name = "\u2751 \ub124\ubaa8"
    elif stripped.startswith("-"):
        style_name = "- \ud558\uc774\ud508"

    if style_name is None:
        return

    style = find_style_by_name(header_root, style_name)
    if style is None:
        return
    paragraph.set("styleIDRef", style.get("id"))
    if style.get("paraPrIDRef"):
        paragraph.set("paraPrIDRef", style.get("paraPrIDRef"))
    char_ref = style.get("charPrIDRef")
    if char_ref:
        for run in paragraph.xpath(".//hp:run", namespaces=NS):
            run.set("charPrIDRef", char_ref)


def write_single_cell(root, label: str, value: str) -> None:
    target = find_cell_after_label(root, label)
    paragraphs = target.xpath(".//hp:p", namespaces=NS)
    if not paragraphs:
        raise SystemExit(f"Cell after {label} has no paragraph.")
    set_paragraph_text(paragraphs[0], value)
    for paragraph in paragraphs[1:]:
        remove_paragraph(paragraph)


def write_content_cell(root, header_root, content_lines: list[str]) -> list:
    target = find_cell_after_label(root, TEMPLATE_LABELS["content"])
    paragraphs = target.xpath(".//hp:p", namespaces=NS)
    if not paragraphs:
        raise SystemExit("Meeting-content cell has no paragraph.")

    reusable = paragraphs
    while len(reusable) < len(content_lines):
        clone = copy.deepcopy(reusable[-1])
        parent = reusable[-1].getparent()
        parent.insert(parent.index(reusable[-1]) + 1, clone)
        reusable.append(clone)

    for paragraph, line in zip(reusable, content_lines):
        ensure_paragraph_has_single_run(paragraph)
        set_paragraph_text(paragraph, line)
        apply_paragraph_role_style(paragraph, line, header_root)

    for paragraph in reusable[len(content_lines) :]:
        remove_paragraph(paragraph)

    return reusable[: len(content_lines)]


def set_table_cells_top_aligned(root) -> None:
    """Keep generated table text aligned to the top of each cell."""

    for sub_list in root.xpath("//hp:tbl//hp:tc/hp:subList", namespaces=NS):
        sub_list.set("vertAlign", "TOP")


def content_row_height(content_lines: list[str]) -> int:
    """Estimate a content-row height from generated text length."""

    estimated_visual_lines = 0
    for line in content_lines:
        estimated_visual_lines += max(1, (len(line) + 41) // 42)
    return max(3335, estimated_visual_lines * 1250 + 1200)


def resize_table_to_content(root, content_lines: list[str]) -> None:
    """Resize the generated table height based on the actual minutes content."""

    target = find_cell_after_label(root, TEMPLATE_LABELS["content"])
    row = target.getparent()
    if row is None:
        return

    height = content_row_height(content_lines)

    for cell in row.xpath("./hp:tc", namespaces=NS):
        cell_size = cell.find("./hp:cellSz", namespaces=NS)
        if cell_size is not None:
            cell_size.set("height", str(height))

    table = row.getparent()
    if table is None:
        return
    table_size = table.find("./hp:sz", namespaces=NS)
    if table_size is None:
        return

    row_heights: dict[str, int] = {}
    for cell in table.xpath("./hp:tr/hp:tc", namespaces=NS):
        addr = cell.find("./hp:cellAddr", namespaces=NS)
        cell_size = cell.find("./hp:cellSz", namespaces=NS)
        if addr is None or cell_size is None:
            continue
        row_addr = addr.get("rowAddr", "")
        cell_height = int(cell_size.get("height", "0"))
        row_heights[row_addr] = max(row_heights.get(row_addr, 0), cell_height)
    if row_heights:
        table_size.set("height", str(sum(row_heights.values())))


def create_kopub_dotum_body_char_pr(header_root) -> str:
    """Create a dedicated KoPub Dotum charPr with normal spacing.

    The source template mixes KoPub Dotum and KoPub Batang charPr entries inside
    the content cell, and some entries have negative spacing. A new charPr avoids
    mutating shared template styles and gives Hancom Office a clear body style.
    """

    char_properties = header_root.xpath("//hh:charProperties", namespaces=NS)[0]
    source = header_root.xpath('//hh:charPr[@id="4"]', namespaces=NS)[0]
    next_id = str(max(int(item.get("id")) for item in header_root.xpath("//hh:charPr", namespaces=NS)) + 1)
    char_pr = copy.deepcopy(source)
    char_pr.set("id", next_id)
    char_pr.set("height", "1100")
    char_pr.set("useFontSpace", "0")
    char_pr.set("useKerning", "0")

    font_ref = char_pr.find("./hh:fontRef", namespaces=NS)
    if font_ref is not None:
        for key in list(font_ref.attrib):
            font_ref.set(key, "3")  # KoPub돋움체 Medium in the supplied template.

    ratio = char_pr.find("./hh:ratio", namespaces=NS)
    if ratio is not None:
        for key in list(ratio.attrib):
            ratio.set(key, "100")

    spacing = char_pr.find("./hh:spacing", namespaces=NS)
    if spacing is not None:
        for key in list(spacing.attrib):
            spacing.set(key, "0")

    char_properties.append(char_pr)
    char_properties.set("itemCnt", str(int(char_properties.get("itemCnt", "0")) + 1))
    return next_id


def apply_body_char_pr(paragraphs: list, char_pr_id: str) -> None:
    for paragraph in paragraphs:
        for run in paragraph.xpath(".//hp:run", namespaces=NS):
            run.set("charPrIDRef", char_pr_id)


def create_non_condensed_para_pr_map(header_root, paragraphs: list) -> dict[str, str]:
    """Clone paragraph styles used by the content cell with condense disabled."""

    para_properties = header_root.xpath("//hh:paraProperties", namespaces=NS)[0]
    existing = header_root.xpath("//hh:paraPr", namespaces=NS)
    next_id = max(int(item.get("id")) for item in existing) + 1
    mapping: dict[str, str] = {}
    used_refs: list[str] = []

    for paragraph in paragraphs:
        ref = paragraph.get("paraPrIDRef")
        if ref and ref not in used_refs:
            used_refs.append(ref)

    for ref in used_refs:
        source_items = header_root.xpath(f'//hh:paraPr[@id="{ref}"]', namespaces=NS)
        if not source_items:
            continue
        new_id = str(next_id)
        next_id += 1
        para_pr = copy.deepcopy(source_items[0])
        para_pr.set("id", new_id)
        para_pr.set("condense", "0")
        break_setting = para_pr.find("./hh:breakSetting", namespaces=NS)
        if break_setting is not None:
            break_setting.set("lineWrap", "BREAK")
        para_properties.append(para_pr)
        mapping[ref] = new_id

    para_properties.set("itemCnt", str(len(header_root.xpath("//hh:paraPr", namespaces=NS))))
    return mapping


def apply_para_pr_map(paragraphs: list, mapping: dict[str, str]) -> None:
    for paragraph in paragraphs:
        ref = paragraph.get("paraPrIDRef")
        if ref in mapping:
            paragraph.set("paraPrIDRef", mapping[ref])


def normalize_hyphen_style(header_root, char_pr_id: str, para_pr_map: dict[str, str]) -> None:
    """Point the '- hyphen' style at non-condensed KoPub Dotum properties."""

    for style in header_root.xpath("//hh:style", namespaces=NS):
        if style.get("name") != "- \ud558\uc774\ud508":
            continue
        style.set("charPrIDRef", char_pr_id)
        para_ref = style.get("paraPrIDRef")
        if para_ref in para_pr_map:
            style.set("paraPrIDRef", para_pr_map[para_ref])


def force_all_spacing_zero(header_root) -> None:
    """Set every HWPX charPr spacing value to 0 in the output document."""

    for spacing in header_root.xpath("//hh:charPr/hh:spacing", namespaces=NS):
        for key in list(spacing.attrib):
            spacing.set(key, "0")


def force_all_text_condense_zero(header_root) -> None:
    """Disable paragraph text condensation used to squeeze lines."""

    for para_pr in header_root.xpath("//hh:paraPr", namespaces=NS):
        para_pr.set("condense", "0")


def force_all_line_spacing_160(header_root) -> None:
    """Set every HWPX paragraph line spacing value to 160%."""

    for line_spacing in header_root.xpath("//hh:paraPr//hh:lineSpacing", namespaces=NS):
        line_spacing.set("type", "PERCENT")
        line_spacing.set("value", "160")
        line_spacing.set("unit", "HWPUNIT")


def fill_xml(
    section_bytes: bytes,
    header_bytes: bytes,
    fields: dict[str, str],
    content_lines: list[str],
    preserve_reference_formatting: bool = False,
) -> tuple[bytes, bytes]:
    parser = etree.XMLParser(remove_blank_text=False)
    section_root = etree.fromstring(section_bytes, parser)
    header_root = etree.fromstring(header_bytes, parser)

    for field in ["project", "meeting", "datetime", "place", "attendees", "purpose"]:
        write_single_cell(section_root, TEMPLATE_LABELS[field], fields[field])
    content_paragraphs = write_content_cell(section_root, header_root, content_lines)
    set_table_cells_top_aligned(section_root)
    resize_table_to_content(section_root, content_lines)
    force_all_spacing_zero(header_root)
    force_all_text_condense_zero(header_root)
    force_all_line_spacing_160(header_root)

    section_out = etree.tostring(section_root, encoding="UTF-8", xml_declaration=True, standalone=True)
    header_out = etree.tostring(header_root, encoding="UTF-8", xml_declaration=True, standalone=True)
    return section_out, header_out


def copy_zip_with_replacement(template: Path, output: Path, section_xml: bytes, header_xml: bytes) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        tmp_output = Path(tmp) / output.name
        with ZipFile(template, "r") as zin, ZipFile(tmp_output, "w", ZIP_DEFLATED) as zout:
            for info in zin.infolist():
                data = zin.read(info.filename)
                if info.filename == "Contents/section0.xml":
                    data = section_xml
                elif info.filename == "Contents/header.xml":
                    data = header_xml
                zout.writestr(info, data)
        shutil.copyfile(tmp_output, output)


def main() -> None:
    args = parse_args()
    template = Path(args.template).expanduser().resolve()
    style_reference = Path(args.style_reference).expanduser().resolve() if args.style_reference else template
    input_path = Path(args.input).expanduser().resolve()
    output = Path(args.output).expanduser().resolve()
    fields, content_lines = parse_minutes(input_path.read_text(encoding="utf-8"))

    with ZipFile(style_reference) as zf:
        section_xml = zf.read("Contents/section0.xml")
        header_xml = zf.read("Contents/header.xml")
    filled_section, filled_header = fill_xml(
        section_xml,
        header_xml,
        fields,
        content_lines,
        preserve_reference_formatting=bool(args.style_reference),
    )
    copy_zip_with_replacement(style_reference, output, filled_section, filled_header)
    print(f"Wrote HWPX: {output}")


if __name__ == "__main__":
    main()
