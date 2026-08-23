from __future__ import annotations

from datetime import datetime
from textwrap import wrap


def _escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _lines(title: str, sections: list[tuple[str, str]]) -> list[str]:
    output = [title, f"Generated: {datetime.utcnow().isoformat()} UTC", ""]
    for heading, body in sections:
        output.extend([heading, "-" * min(len(heading), 72)])
        for paragraph in str(body or "").splitlines() or [""]:
            output.extend(wrap(paragraph, width=92) or [""])
        output.append("")
    return output


def make_text_pdf(title: str, sections: list[tuple[str, str]]) -> bytes:
    """Create a compact single-font PDF without external binary deps."""
    text_lines = _lines(title, sections)
    pages = [text_lines[i:i + 48] for i in range(0, len(text_lines), 48)] or [[]]
    objects: list[bytes] = []

    def add(obj: bytes) -> int:
        objects.append(obj)
        return len(objects)

    catalog_id = add(b"<< /Type /Catalog /Pages 2 0 R >>")
    pages_id = add(b"")
    font_id = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>")
    page_ids = []

    for page in pages:
        content = ["BT", "/F1 10 Tf", "50 780 Td", "14 TL"]
        for line in page:
            content.append(f"({_escape(line)}) Tj")
            content.append("T*")
        content.append("ET")
        stream = "\n".join(content).encode("latin-1", "replace")
        content_id = add(b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream")
        page_id = add(
            f"<< /Type /Page /Parent {pages_id} 0 R /MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 {font_id} 0 R >> >> /Contents {content_id} 0 R >>".encode()
        )
        page_ids.append(page_id)

    objects[pages_id - 1] = (
        f"<< /Type /Pages /Kids [{' '.join(f'{page_id} 0 R' for page_id in page_ids)}] "
        f"/Count {len(page_ids)} >>".encode()
    )

    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{index} 0 obj\n".encode())
        pdf.extend(obj)
        pdf.extend(b"\nendobj\n")
    xref_at = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode())
    pdf.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root {catalog_id} 0 R >>\n"
        f"startxref\n{xref_at}\n%%EOF\n".encode()
    )
    return bytes(pdf)
