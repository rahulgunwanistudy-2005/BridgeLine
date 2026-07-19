"""Generate the small, clean IEP PDF used by cx/01 before cc/02 fixtures land."""

from pathlib import Path

OUTPUT = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "synthetic"
    / "fixtures"
    / "samples"
    / "clean-sample-iep.pdf"
)

PAGES = (
    (
        "RIVERSIDE UNIFIED SCHOOL DISTRICT",
        "INDIVIDUALIZED EDUCATION PROGRAM (IEP)",
        "Student ID: RIV-204",
        "Eligibility: Specific learning disability",
        "School Year: 2026-2027",
        "Annual Review: May 10, 2027",
        "Triennial Reevaluation: 04/22/2029",
    ),
    (
        "ACCOMMODATIONS AND SERVICES",
        "Accommodation: Provide 50% extended time on classroom assessments.",
        "Applies to: All classes",
        "SERVICE MINUTES TABLE",
        "Service | Minutes | Frequency | Provider | Start | End",
        "Specialized academic instruction | 30 | 5x weekly | Special education teacher | 08/17/2026 | 05/28/2027",
    ),
    (
        "MEASURABLE ANNUAL GOAL",
        "Baseline: Currently identifies the main idea with 45% accuracy.",
        "Goal: Identify the main idea with 80% accuracy across three consecutive probes.",
        "Measure: Curriculum-based reading probe",
        "Progress cadence: Every two weeks",
        "Case manager signature: Jordan Lee   Date: 5/10/27",
    ),
)


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _stream(lines: tuple[str, ...]) -> bytes:
    commands = ["BT", "/F1 12 Tf", "54 738 Td", "16 TL"]
    for line in lines:
        commands.extend((f"({_escape(line)}) Tj", "T*"))
    commands.append("ET")
    return "\n".join(commands).encode("ascii")


def generate() -> None:
    """Write a valid three-page PDF with embedded text and a service table."""

    objects: dict[int, bytes] = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: b"<< /Type /Pages /Kids [3 0 R 5 0 R 7 0 R] /Count 3 >>",
        9: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    }
    for index, lines in enumerate(PAGES):
        page_number = 3 + index * 2
        content_number = page_number + 1
        content = _stream(lines)
        objects[page_number] = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 9 0 R >> >> /Contents {content_number} 0 R >>"
        ).encode("ascii")
        objects[content_number] = (
            f"<< /Length {len(content)} >>\nstream\n".encode("ascii")
            + content
            + b"\nendstream"
        )

    pdf = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for number in range(1, 10):
        offsets.append(len(pdf))
        pdf.extend(f"{number} 0 obj\n".encode("ascii"))
        pdf.extend(objects[number])
        pdf.extend(b"\nendobj\n")
    xref = len(pdf)
    pdf.extend(b"xref\n0 10\n0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.extend(
        f"trailer\n<< /Size 10 /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode(
            "ascii"
        )
    )
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_bytes(pdf)


if __name__ == "__main__":
    generate()
