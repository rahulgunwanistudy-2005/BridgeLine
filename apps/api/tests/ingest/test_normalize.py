"""Tests for typed normalization and image cleanup behavior."""

from io import BytesIO

import pytest
from PIL import Image, ImageDraw

from bridgeline.ingest.normalize import (
    EmptyDocumentError,
    EncryptedPDFError,
    OversizeUploadError,
    UnsupportedDocumentError,
    normalize_document,
    prepare_page_image,
)


def test_oversize_upload_is_rejected_before_parser_work() -> None:
    """The configured limit produces a friendly typed rejection."""

    with pytest.raises(OversizeUploadError, match="10 bytes"):
        normalize_document(b"%PDF-1.7 too large", filename="large.pdf", max_upload_bytes=10)


def test_unknown_file_type_is_a_typed_error() -> None:
    """Filename extensions alone never coerce arbitrary bytes into a parser."""

    with pytest.raises(UnsupportedDocumentError, match="supported"):
        normalize_document(b"not a document", filename="notes.pdf")


def test_zero_page_docx_is_rejected() -> None:
    """A DOCX containing no visible text or images is not a successful document."""

    from docx import Document

    stream = BytesIO()
    Document().save(stream)

    with pytest.raises(EmptyDocumentError, match="no readable pages"):
        normalize_document(stream.getvalue(), filename="empty.docx")


def test_encrypted_pdf_is_a_typed_friendly_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """A PDFium password failure never leaks through as a server error."""

    import pypdfium2 as pdfium

    def reject_password(_data: bytes) -> None:
        raise pdfium.PdfiumError("Incorrect password error")

    monkeypatch.setattr("bridgeline.ingest.normalize.pdfium.PdfDocument", reject_password)

    with pytest.raises(EncryptedPDFError, match="password-protected"):
        normalize_document(b"%PDF-1.7 encrypted", filename="locked.pdf")


def test_zero_page_pdf_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    """A valid PDF container with no pages cannot advance to OCR."""

    class ZeroPagePDF:
        def __len__(self) -> int:
            return 0

        def close(self) -> None:
            return None

    monkeypatch.setattr(
        "bridgeline.ingest.normalize.pdfium.PdfDocument",
        lambda _data: ZeroPagePDF(),
    )

    with pytest.raises(EmptyDocumentError, match="zero pages"):
        normalize_document(b"%PDF-1.7 empty", filename="empty.pdf")


def test_upside_down_page_is_rotated_before_ocr(monkeypatch: pytest.MonkeyPatch) -> None:
    """Orientation metadata from Tesseract is applied to an asymmetric page."""

    image = Image.new("RGB", (120, 80), "white")
    ImageDraw.Draw(image).rectangle((5, 5, 45, 20), fill="black")
    monkeypatch.setattr(
        "bridgeline.ingest.normalize.pytesseract.image_to_osd",
        lambda _image, output_type: {"rotate": 180},
    )

    prepared = prepare_page_image(image)

    assert prepared.crop((75, 55, 115, 75)).getbbox() is not None
    assert prepared.getpixel((110, 70)) != (255, 255, 255)
