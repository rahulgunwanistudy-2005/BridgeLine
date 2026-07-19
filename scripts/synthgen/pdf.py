"""A tiny deterministic vector-PDF writer (no external dependencies, byte-stable).

Uses only the standard PDF Type1 fonts (Helvetica / Helvetica-Bold), so nothing is
embedded and output does not depend on system fonts. There are no timestamps or random
identifiers anywhere, so regenerating a document yields byte-identical output. The layout
engine is top-down (origin at the top-left, converted to PDF's bottom-left internally) and
paginates automatically.
"""

from __future__ import annotations

from dataclasses import dataclass, field

PAGE_WIDTH = 612.0   # US Letter
PAGE_HEIGHT = 792.0

# Approximate Helvetica advance widths (per 1000 em). Proportional enough for readable
# wrapping and column alignment; exactness is unnecessary for synthetic documents.
_WIDTHS: dict[str, int] = {
    " ": 278, "!": 278, '"': 355, "#": 556, "$": 556, "%": 889, "&": 667, "'": 191,
    "(": 333, ")": 333, "*": 389, "+": 584, ",": 278, "-": 333, ".": 278, "/": 278,
    "0": 556, "1": 556, "2": 556, "3": 556, "4": 556, "5": 556, "6": 556, "7": 556,
    "8": 556, "9": 556, ":": 278, ";": 278, "<": 584, "=": 584, ">": 584, "?": 556,
    "@": 1015, "A": 667, "B": 667, "C": 722, "D": 722, "E": 667, "F": 611, "G": 778,
    "H": 722, "I": 278, "J": 500, "K": 667, "L": 556, "M": 833, "N": 722, "O": 778,
    "P": 667, "Q": 778, "R": 722, "S": 667, "T": 611, "U": 722, "V": 667, "W": 944,
    "X": 667, "Y": 667, "Z": 611, "[": 278, "\\": 278, "]": 278, "^": 469, "_": 556,
    "`": 333, "a": 556, "b": 556, "c": 500, "d": 556, "e": 556, "f": 278, "g": 556,
    "h": 556, "i": 222, "j": 222, "k": 500, "l": 222, "m": 833, "n": 556, "o": 556,
    "p": 556, "q": 556, "r": 333, "s": 500, "t": 278, "u": 556, "v": 500, "w": 722,
    "x": 500, "y": 500, "z": 500, "{": 334, "|": 260, "}": 334, "~": 584,
}
_DEFAULT_WIDTH = 556


def text_width(text: str, size: float, *, bold: bool = False) -> float:
    """Approximate rendered width of text at a font size (bold is ~3% wider)."""

    units = sum(_WIDTHS.get(ch, _DEFAULT_WIDTH) for ch in text)
    width = units / 1000.0 * size
    return width * 1.03 if bold else width


def wrap_text(text: str, size: float, max_width: float, *, bold: bool = False) -> list[str]:
    """Greedy word-wrap into lines that fit max_width."""

    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if text_width(candidate, size, bold=bold) <= max_width or not current:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [""]


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


@dataclass
class _Page:
    ops: list[str] = field(default_factory=list)


class PDF:
    """Accumulate drawing operations across pages and serialize to bytes."""

    F_REGULAR = "F1"
    F_BOLD = "F2"

    def __init__(self) -> None:
        self._pages: list[_Page] = []
        self.new_page()

    def new_page(self) -> None:
        self._pages.append(_Page())

    @property
    def _page(self) -> _Page:
        return self._pages[-1]

    def text(self, x: float, y_top: float, s: str, size: float = 11, *,
             bold: bool = False, gray: float = 0.0) -> None:
        # Text is painted with the non-stroking (fill) color, which a prior filled rect
        # may have changed, so every text op sets its own gray (0=black, 1=white).
        font = self.F_BOLD if bold else self.F_REGULAR
        y = PAGE_HEIGHT - y_top
        self._page.ops.append(
            f"BT {gray:.3f} g /{font} {size:.2f} Tf {x:.2f} {y:.2f} Td ({_escape(s)}) Tj ET"
        )

    def line(self, x1: float, y1_top: float, x2: float, y2_top: float, width: float = 0.6) -> None:
        y1, y2 = PAGE_HEIGHT - y1_top, PAGE_HEIGHT - y2_top
        self._page.ops.append(
            f"{width:.2f} w {x1:.2f} {y1:.2f} m {x2:.2f} {y2:.2f} l S"
        )

    def rect(self, x: float, y_top: float, w: float, h: float, *,
             stroke: bool = True, fill_gray: float | None = None, line_width: float = 0.6) -> None:
        y = PAGE_HEIGHT - y_top - h
        ops = self._page.ops
        if fill_gray is not None:
            ops.append(f"{fill_gray:.3f} g {x:.2f} {y:.2f} {w:.2f} {h:.2f} re f")
        if stroke:
            ops.append(f"0 G {line_width:.2f} w {x:.2f} {y:.2f} {w:.2f} {h:.2f} re S")

    def build(self) -> bytes:
        objects: dict[int, bytes] = {}
        # 1 catalog, 2 pages, 3 font regular, 4 font bold, then page/content pairs.
        objects[1] = b"<< /Type /Catalog /Pages 2 0 R >>"
        objects[3] = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"
        objects[4] = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>"

        page_obj_numbers: list[int] = []
        next_obj = 5
        for page in self._pages:
            content = ("\n".join(page.ops)).encode("latin-1", "replace")
            content_num = next_obj
            page_num = next_obj + 1
            next_obj += 2
            objects[content_num] = (
                f"<< /Length {len(content)} >>\nstream\n".encode("latin-1")
                + content
                + b"\nendstream"
            )
            objects[page_num] = (
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {PAGE_WIDTH:.0f} {PAGE_HEIGHT:.0f}] "
                f"/Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> "
                f"/Contents {content_num} 0 R >>"
            ).encode("latin-1")
            page_obj_numbers.append(page_num)

        kids = " ".join(f"{n} 0 R" for n in page_obj_numbers)
        objects[2] = (
            f"<< /Type /Pages /Kids [{kids}] /Count {len(page_obj_numbers)} >>"
        ).encode("latin-1")

        max_obj = next_obj - 1
        pdf = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offsets: dict[int, int] = {}
        for number in range(1, max_obj + 1):
            offsets[number] = len(pdf)
            pdf.extend(f"{number} 0 obj\n".encode("latin-1"))
            pdf.extend(objects[number])
            pdf.extend(b"\nendobj\n")
        xref_pos = len(pdf)
        pdf.extend(f"xref\n0 {max_obj + 1}\n".encode("latin-1"))
        pdf.extend(b"0000000000 65535 f \n")
        for number in range(1, max_obj + 1):
            pdf.extend(f"{offsets[number]:010d} 00000 n \n".encode("latin-1"))
        pdf.extend(
            f"trailer\n<< /Size {max_obj + 1} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n".encode("latin-1")
        )
        return bytes(pdf)
