"""Dependency-free PDF writer for professional multi-page briefs.

Why this exists instead of a library
------------------------------------
The API image (``requirements-api.txt``) has no PDF toolchain and the target
Python is externally managed, so adding ``reportlab``/``weasyprint`` at this
stage is a governed change with a system-dependency and supply-chain review.
This module produces the one document shape the Territory Opportunity Brief
needs - A4, single text column, headings, wrapped paragraphs, bullet lists and
simple key/value or grid tables - using only the 14 standard PDF base fonts
(no embedded font files) and the standard Helvetica AFM metrics for accurate
line breaking. Output opens in Preview, Acrobat, Chrome and ``pdftotext``.

If the brief later needs charts or rich typography, replace the renderer in
``territory_brief_render.py`` with a library-backed one; the generator output
in ``territory_brief.py`` is deliberately independent of this writer.
"""

from __future__ import annotations

import io
import zlib
from dataclasses import dataclass, field

# --- Helvetica AFM advance widths (units per 1000 em) --------------------------
# Adobe Core-14 metrics. Index = Latin-1 code point. Exact for the printable
# ASCII range (32-126); the Latin-1 supplement uses the AFM values where Adobe
# defines them and a sane default (556/'n' width) elsewhere. Line breaking only
# needs to be tight, not pixel-perfect, and every glyph the brief emits is in
# the exact range.
_HELV = [
    278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278,
    278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278,
    278, 278, 355, 556, 556, 889, 667, 191, 333, 333, 389, 584, 278, 333, 278, 278,
    556, 556, 556, 556, 556, 556, 556, 556, 556, 556, 278, 278, 584, 584, 584, 556,
    1015, 667, 667, 722, 722, 667, 611, 778, 722, 278, 500, 667, 556, 833, 722, 778,
    667, 778, 722, 667, 611, 722, 667, 944, 667, 667, 611, 278, 278, 278, 469, 556,
    333, 556, 556, 500, 556, 556, 278, 556, 556, 222, 222, 500, 222, 833, 556, 556,
    556, 556, 333, 500, 278, 556, 500, 722, 500, 500, 500, 334, 260, 334, 584, 556,
    556, 556, 222, 556, 333, 1000, 556, 556, 333, 1000, 667, 333, 1000, 556, 611, 556,
    556, 222, 222, 333, 333, 350, 556, 1000, 333, 1000, 500, 333, 944, 556, 500, 667,
    278, 333, 556, 556, 556, 556, 260, 556, 333, 737, 370, 556, 584, 333, 737, 333,
    400, 584, 333, 333, 333, 556, 537, 278, 333, 333, 365, 556, 834, 834, 834, 611,
    667, 667, 667, 667, 667, 667, 1000, 722, 667, 667, 667, 667, 278, 278, 278, 278,
    722, 722, 778, 778, 778, 778, 778, 584, 778, 722, 722, 722, 722, 667, 667, 611,
    556, 556, 556, 556, 556, 556, 889, 500, 556, 556, 556, 556, 278, 278, 278, 278,
    556, 556, 556, 556, 556, 556, 556, 584, 611, 556, 556, 556, 556, 500, 556, 500,
]
# Helvetica-Bold advance widths.
_HELVB = [
    278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278,
    278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278,
    278, 333, 474, 556, 556, 889, 722, 238, 333, 333, 389, 584, 278, 333, 278, 278,
    556, 556, 556, 556, 556, 556, 556, 556, 556, 556, 333, 333, 584, 584, 584, 611,
    975, 722, 722, 722, 722, 667, 611, 778, 722, 278, 556, 722, 611, 833, 722, 778,
    667, 778, 722, 667, 611, 722, 667, 944, 667, 667, 611, 333, 278, 333, 584, 556,
    333, 556, 611, 556, 611, 556, 333, 611, 611, 278, 278, 556, 278, 889, 611, 611,
    611, 611, 389, 556, 333, 611, 556, 778, 556, 556, 500, 389, 280, 389, 584, 556,
    556, 556, 278, 556, 500, 1000, 556, 556, 333, 1000, 667, 333, 1000, 556, 611, 556,
    556, 278, 278, 500, 500, 350, 556, 1000, 333, 1000, 556, 333, 944, 556, 500, 667,
    278, 333, 556, 556, 556, 556, 280, 556, 333, 737, 370, 556, 584, 333, 737, 333,
    400, 584, 333, 333, 333, 611, 556, 278, 333, 333, 365, 556, 834, 834, 834, 611,
    722, 722, 722, 722, 722, 722, 1000, 722, 667, 667, 667, 667, 278, 278, 278, 278,
    722, 722, 778, 778, 778, 778, 778, 584, 778, 722, 722, 722, 722, 667, 667, 611,
    556, 556, 556, 556, 556, 556, 889, 556, 556, 556, 556, 556, 278, 278, 278, 278,
    611, 611, 611, 611, 611, 611, 611, 584, 611, 611, 611, 611, 611, 556, 611, 556,
]
_HELVO = _HELV  # Oblique shares Helvetica advance widths.

_FONTS = {
    "H": ("Helvetica", _HELV),
    "B": ("Helvetica-Bold", _HELVB),
    "I": ("Helvetica-Oblique", _HELVO),
}

PAGE_W = 595.276  # A4 width in PostScript points (210mm)
PAGE_H = 841.890  # A4 height in points (297mm)


def text_width(s: str, font: str, size: float) -> float:
    table = _FONTS[font][1]
    total = 0
    for ch in s:
        cp = ord(ch)
        total += table[cp] if cp < 256 else 556
    return total * size / 1000.0


def _pdf_escape(s: str) -> str:
    return s.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")


def _sanitize(s: str) -> str:
    """Coerce to Latin-1 so every code point has a metric and encodes cleanly."""
    replacements = {
        "‘": "'", "’": "'", "“": '"', "”": '"',
        "–": "-", "—": "-", "…": "...", "•": "-",
        " ": " ", "→": "->", "≤": "<=", "≥": ">=",
        "·": "-", "﻿": "",
    }
    for bad, good in replacements.items():
        s = s.replace(bad, good)
    return s.encode("latin-1", "replace").decode("latin-1")


def wrap_text(s: str, font: str, size: float, max_width: float) -> list[str]:
    """Greedy word wrap; hard-splits any single token longer than ``max_width``."""
    s = _sanitize(s)
    out: list[str] = []
    for raw_line in s.split("\n"):
        words = raw_line.split(" ")
        current = ""
        for word in words:
            candidate = word if not current else f"{current} {word}"
            if text_width(candidate, font, size) <= max_width or not current:
                if text_width(candidate, font, size) <= max_width:
                    current = candidate
                    continue
                # single oversized token: hard split
                if current:
                    out.append(current)
                    current = ""
                chunk = ""
                for ch in word:
                    if text_width(chunk + ch, font, size) <= max_width or not chunk:
                        chunk += ch
                    else:
                        out.append(chunk)
                        chunk = ch
                current = chunk
            else:
                out.append(current)
                current = word
        out.append(current)
    return out


@dataclass
class _Op:
    kind: str
    payload: dict = field(default_factory=dict)


class PdfBuilder:
    """Flowing-text page builder. Coordinates are in points from the top-left.

    Usage: create, add content with ``heading``/``paragraph``/``bullets``/
    ``key_values``/``table``/``spacer``/``rule``/``page_break``, then ``build()``
    for the PDF bytes. Pagination, margins and page numbers are automatic.
    """

    def __init__(
        self,
        *,
        title: str,
        margin_left: float = 56,
        margin_right: float = 56,
        margin_top: float = 64,
        margin_bottom: float = 64,
        footer: str | None = None,
    ) -> None:
        self.title = _sanitize(title)
        self.ml = margin_left
        self.mr = margin_right
        self.mt = margin_top
        self.mb = margin_bottom
        self.footer = _sanitize(footer) if footer else None
        self.content_w = PAGE_W - margin_left - margin_right
        self._pages: list[list[str]] = []
        self._cur: list[str] = []
        self._y = PAGE_H - margin_top
        self._page_started = False

    # -- low-level ------------------------------------------------------------
    def _ensure_page(self) -> None:
        if not self._page_started:
            self._cur = []
            self._y = PAGE_H - self.mt
            self._page_started = True

    def _new_page(self) -> None:
        if self._page_started:
            self._pages.append(self._cur)
        self._cur = []
        self._y = PAGE_H - self.mt
        self._page_started = True

    def _space_left(self) -> float:
        return self._y - self.mb

    def _need(self, height: float) -> None:
        self._ensure_page()
        if height > self._space_left():
            self._new_page()

    def _draw_line(self, x: float, y: float, s: str, font: str, size: float) -> None:
        self._cur.append(
            f"BT /{font} {size:.2f} Tf 1 0 0 1 {x:.2f} {y:.2f} Tm ({_pdf_escape(s)}) Tj ET"
        )

    def _text_block(
        self,
        s: str,
        *,
        font: str = "H",
        size: float = 10.5,
        leading: float = 14.5,
        indent: float = 0.0,
        space_after: float = 6.0,
        color: tuple[float, float, float] | None = None,
    ) -> None:
        lines = wrap_text(s, font, size, self.content_w - indent)
        for ln in lines:
            self._need(leading)
            if color:
                self._cur.append(f"{color[0]:.3f} {color[1]:.3f} {color[2]:.3f} rg")
            self._draw_line(self.ml + indent, self._y - size, ln, font, size)
            if color:
                self._cur.append("0 0 0 rg")
            self._y -= leading
        self._y -= space_after

    # -- public content API -------------------------------------------------
    def title_block(self, subtitle: str, meta_lines: list[str]) -> None:
        self._ensure_page()
        self._need(120)
        self._y -= 40
        self._text_block(self.title, font="B", size=22, leading=27, space_after=6)
        self._text_block(_sanitize(subtitle), font="H", size=12.5, leading=17,
                         space_after=14, color=(0.30, 0.30, 0.30))
        self.rule()
        for line in meta_lines:
            self._text_block(_sanitize(line), font="H", size=10, leading=14, space_after=2,
                             color=(0.25, 0.25, 0.25))
        self._y -= 10
        self.rule()
        self._y -= 6

    def heading(self, s: str, level: int = 1) -> None:
        sizes = {1: 15.5, 2: 12.5}
        size = sizes.get(level, 12.5)
        self._need(size + 20)
        self._y -= 10 if level == 1 else 6
        self._text_block(_sanitize(s), font="B", size=size, leading=size + 4,
                         space_after=5 if level == 1 else 3)

    def paragraph(self, s: str, *, italic: bool = False, muted: bool = False) -> None:
        self._text_block(
            s,
            font="I" if italic else "H",
            size=10.5,
            leading=14.5,
            space_after=7,
            color=(0.33, 0.33, 0.33) if muted else None,
        )

    def spacer(self, h: float = 8.0) -> None:
        self._ensure_page()
        self._y -= h

    def rule(self) -> None:
        self._ensure_page()
        self._need(8)
        self._cur.append(
            f"0.75 w 0.80 0.80 0.80 RG {self.ml:.2f} {self._y:.2f} m "
            f"{PAGE_W - self.mr:.2f} {self._y:.2f} l S 0 0 0 RG"
        )
        self._y -= 10

    def bullets(self, items: list[str], *, ordered: bool = False) -> None:
        for i, item in enumerate(items, start=1):
            marker = f"{i}." if ordered else "-"
            marker_w = text_width(marker + " ", "H", 10.5)
            lines = wrap_text(_sanitize(item), "H", 10.5, self.content_w - marker_w - 6)
            for j, ln in enumerate(lines):
                self._need(14.5)
                if j == 0:
                    self._draw_line(self.ml + 4, self._y - 10.5, marker, "H", 10.5)
                self._draw_line(self.ml + 4 + marker_w + 2, self._y - 10.5, ln, "H", 10.5)
                self._y -= 14.5
            self._y -= 3
        self._y -= 4

    def key_values(self, pairs: list[tuple[str, str]]) -> None:
        label_w = max((text_width(_sanitize(k), "B", 10) for k, _ in pairs), default=90)
        label_w = min(label_w + 14, self.content_w * 0.42)
        for k, v in pairs:
            v_lines = wrap_text(_sanitize(v), "H", 10, self.content_w - label_w)
            block_h = max(len(v_lines), 1) * 13.5 + 3
            self._need(block_h)
            top = self._y
            self._draw_line(self.ml, top - 10, _sanitize(k), "B", 10)
            for i, ln in enumerate(v_lines):
                self._draw_line(self.ml + label_w, top - 10 - i * 13.5, ln, "H", 10)
            self._y = top - block_h

    def table(self, headers: list[str], rows: list[list[str]], *, widths: list[float] | None = None) -> None:
        """Simple grid table. ``widths`` are relative weights; default equal."""
        n = len(headers)
        if widths is None:
            widths = [1.0] * n
        total = sum(widths)
        col_w = [self.content_w * w / total for w in widths]
        pad = 4.0
        size = 9.0
        lead = 12.0

        def render_row(cells: list[str], *, bold: bool, shade: bool) -> None:
            wrapped = [
                wrap_text(_sanitize(str(c)), "B" if bold else "H", size, col_w[i] - 2 * pad)
                for i, c in enumerate(cells)
            ]
            row_h = max((len(w) for w in wrapped), default=1) * lead + 2 * pad
            self._need(row_h + (16 if bold else 0))
            top = self._y
            if shade:
                self._cur.append(
                    f"0.94 0.94 0.94 rg {self.ml:.2f} {top - row_h:.2f} "
                    f"{self.content_w:.2f} {row_h:.2f} re f 0 0 0 rg"
                )
            x = self.ml
            for i, cell_lines in enumerate(wrapped):
                for j, ln in enumerate(cell_lines):
                    self._draw_line(x + pad, top - pad - size - j * lead, ln,
                                    "B" if bold else "H", size)
                x += col_w[i]
            # horizontal separator
            self._cur.append(
                f"0.5 w 0.82 0.82 0.82 RG {self.ml:.2f} {top - row_h:.2f} m "
                f"{self.ml + self.content_w:.2f} {top - row_h:.2f} l S 0 0 0 RG"
            )
            self._y = top - row_h

        self._need(60)
        render_row(headers, bold=True, shade=True)
        for r in rows:
            render_row([str(c) for c in r], bold=False, shade=False)
        self._y -= 8

    def page_break(self) -> None:
        self._new_page()

    # -- assembly ---------------------------------------------------------
    def build(self) -> bytes:
        if self._page_started:
            self._pages.append(self._cur)
        pages = self._pages or [[]]
        total = len(pages)

        objects: list[bytes] = []

        def add(obj: bytes) -> int:
            objects.append(obj)
            return len(objects)  # 1-based object number

        font_obj_nums = {}
        for key, (name, _w) in _FONTS.items():
            num = add(
                f"<< /Type /Font /Subtype /Type1 /BaseFont /{name} "
                f"/Encoding /WinAnsiEncoding >>".encode("latin-1")
            )
            font_obj_nums[key] = num

        # Reserve Pages object number.
        pages_obj_num = len(objects) + 1
        objects.append(b"")  # placeholder, filled later

        kids: list[int] = []
        for idx, ops in enumerate(pages, start=1):
            stream_parts = list(ops)
            # footer + page number
            footer_bits = []
            if self.footer:
                footer_bits.append(self.footer)
            footer_bits.append(f"Page {idx} of {total}")
            footer_line = "    |    ".join(footer_bits)
            fy = self.mb - 24
            stream_parts.append(
                f"BT /H 8.00 Tf 0.45 0.45 0.45 rg 1 0 0 1 {self.ml:.2f} {fy:.2f} Tm "
                f"({_pdf_escape(_sanitize(footer_line))}) Tj ET 0 0 0 rg"
            )
            content = ("\n".join(stream_parts)).encode("latin-1", "replace")
            compressed = zlib.compress(content)
            stream_obj = (
                b"<< /Length " + str(len(compressed)).encode() +
                b" /Filter /FlateDecode >>\nstream\n" + compressed + b"\nendstream"
            )
            content_num = add(stream_obj)
            resources = (
                "<< /Font << " +
                " ".join(f"/{k} {font_obj_nums[k]} 0 R" for k in _FONTS) +
                " >> >>"
            )
            page_obj = (
                f"<< /Type /Page /Parent {pages_obj_num} 0 R "
                f"/MediaBox [0 0 {PAGE_W:.3f} {PAGE_H:.3f}] "
                f"/Resources {resources} /Contents {content_num} 0 R >>"
            ).encode("latin-1")
            page_num = add(page_obj)
            kids.append(page_num)

        objects[pages_obj_num - 1] = (
            f"<< /Type /Pages /Count {total} /Kids [" +
            " ".join(f"{k} 0 R" for k in kids) + "] >>"
        ).encode("latin-1")

        info_num = add(
            f"<< /Title ({_pdf_escape(self.title)}) /Producer (CareGist brief writer) >>".encode("latin-1")
        )
        catalog_num = add(f"<< /Type /Catalog /Pages {pages_obj_num} 0 R >>".encode("latin-1"))

        # Serialize with xref.
        buf = io.BytesIO()
        buf.write(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offsets = [0] * (len(objects) + 1)
        for i, obj in enumerate(objects, start=1):
            offsets[i] = buf.tell()
            buf.write(f"{i} 0 obj\n".encode())
            buf.write(obj)
            buf.write(b"\nendobj\n")
        xref_pos = buf.tell()
        buf.write(f"xref\n0 {len(objects) + 1}\n".encode())
        buf.write(b"0000000000 65535 f \n")
        for i in range(1, len(objects) + 1):
            buf.write(f"{offsets[i]:010d} 00000 n \n".encode())
        buf.write(
            f"trailer\n<< /Size {len(objects) + 1} /Root {catalog_num} 0 R "
            f"/Info {info_num} 0 R >>\nstartxref\n{xref_pos}\n%%EOF".encode()
        )
        return buf.getvalue()
