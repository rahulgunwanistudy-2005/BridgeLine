"""Render a ground-truth IEPRecord into a realistic district IEP form (PDF + HTML).

The PDF is a real text-layer document (good OCR — the "clean" demo path) rendered with the
byte-stable vector writer in ``pdf.py``. The HTML is the same content styled as a genuine
district form for on-screen viewing. Both derive from the same record, so they never
disagree, and both are clearly marked as synthetic demo data.
"""

from __future__ import annotations

import html as html_lib
from typing import Any

from synthgen.constants import DISTRICT_NAME, SCHOOL_NAME
from synthgen.district import STUDENTS
from synthgen.pdf import PDF, wrap_text

_LEFT = 54.0
_RIGHT = 558.0
_WIDTH = _RIGHT - _LEFT
_TOP = 54.0
_BOTTOM = 748.0
_LINE = 14.0

_NAMES = {s["student_ref"]: s for s in STUDENTS}

_SCOPE_LABEL = {"all": "all classes", "subject": "specific subject", "context": "specific context"}


def _display_name(student_ref: str) -> str:
    return _NAMES.get(student_ref, {}).get("display_name", student_ref)


def _scope(applies_to: list[str]) -> str:
    return ", ".join(_SCOPE_LABEL.get(a, a) for a in applies_to)


class _FormRenderer:
    def __init__(self, record: dict[str, Any]) -> None:
        self.record = record
        self.pdf = PDF()
        self.y = _TOP

    # ── layout helpers ────────────────────────────────────────────────
    def _ensure(self, needed: float) -> None:
        if self.y + needed > _BOTTOM:
            self.pdf.new_page()
            self.y = _TOP

    def _gap(self, amount: float) -> None:
        self.y += amount

    def _heading(self, title: str) -> None:
        self._ensure(_LINE * 2)
        self.pdf.rect(_LEFT, self.y, _WIDTH, _LINE + 4, fill_gray=0.88, stroke=False)
        self.pdf.text(_LEFT + 4, self.y + _LINE - 1, title, 11, bold=True)
        self.y += _LINE + 10

    def _wrapped(self, text: str, size: float = 10.5, x: float = _LEFT, width: float | None = None,
                 bold: bool = False) -> None:
        width = width or (_RIGHT - x)
        for line in wrap_text(text, size, width, bold=bold):
            self._ensure(_LINE)
            self.pdf.text(x, self.y + size, line, size, bold=bold)
            self.y += _LINE

    def _label_value(self, label: str, value: str, label_w: float = 112) -> None:
        self._ensure(_LINE)
        self.pdf.text(_LEFT + 8, self.y + 10, label, 10, bold=True)
        for i, line in enumerate(wrap_text(value, 10, _RIGHT - (_LEFT + 8 + label_w))):
            if i:
                self._ensure(_LINE)
            self.pdf.text(_LEFT + 8 + label_w, self.y + 10, line, 10)
            self.y += _LINE

    # ── sections ──────────────────────────────────────────────────────
    def _header(self) -> None:
        self.pdf.text(_LEFT, self.y + 14, DISTRICT_NAME, 15, bold=True)
        self.y += 20
        self.pdf.text(_LEFT, self.y + 12, "Individualized Education Program (IEP)", 12, bold=True)
        self.y += 18
        self.pdf.rect(_LEFT, self.y, _WIDTH, 16, fill_gray=0.15, stroke=False)
        self.pdf.text(_LEFT + 4, self.y + 12,
                      "CONFIDENTIAL - SYNTHETIC DEMO DATA - NOT A REAL STUDENT", 9.5,
                      bold=True, gray=1.0)
        self.y += 26

    def _student_info(self) -> None:
        r = self.record
        d = r["dates"]
        self._heading("Student Information")
        box_top = self.y
        info_w = 140
        self._label_value("Student:", _display_name(r["student_ref"]), info_w)
        self._label_value("Student ID:", r["student_ref"], info_w)
        self._label_value("School:", SCHOOL_NAME, info_w)
        self._label_value("School Year:", r["school_year"], info_w)
        self._label_value("Eligibility:", r["disability_category"], info_w)
        self._label_value("Annual Review:", d["annual_review"] or "Not stated", info_w)
        self._label_value("Triennial Reevaluation:", d["triennial_reeval"] or "Not stated", info_w)
        self._label_value("Last Progress Report:", d["last_progress_report"] or "Not stated", info_w)
        self.pdf.rect(_LEFT, box_top - 4, _WIDTH, self.y - box_top + 4)
        self.y += 10

    def _present_levels(self) -> None:
        self._heading("Present Levels of Performance")
        baselines = [g["baseline"] for g in self.record["goals"]]
        summary = "Present levels are summarized from the student's current baselines: " + \
            " ".join(baselines)
        self._wrapped(summary)
        self.y += 6

    def _goals(self) -> None:
        self._heading("Measurable Annual Goals")
        for i, g in enumerate(self.record["goals"], start=1):
            self._ensure(_LINE * 4)
            self.pdf.text(_LEFT, self.y + 11, f"Goal {i}", 10.5, bold=True)
            self.y += _LINE
            self._wrapped(g["text"], 10, x=_LEFT + 8, width=_WIDTH - 8)
            self._label_value("Baseline:", g["baseline"])
            self._label_value("Target:", g["target"])
            self._label_value("Measure:", g["measure"])
            self._label_value("Progress cadence:", g["progress_cadence"])
            self.y += 6

    def _accommodations(self) -> None:
        self._heading("Accommodations")
        for a in self.record["accommodations"]:
            self._ensure(_LINE * 2)
            self.pdf.text(_LEFT + 4, self.y + 10, "-", 10, bold=True)
            text = f"{a['text']}  (applies to: {_scope(a['applies_to'])})"
            self._wrapped(text, 10, x=_LEFT + 16, width=_RIGHT - (_LEFT + 16))

    def _services(self) -> None:
        self._heading("Special Education and Related Services")
        cols = [("Service", 168), ("Min/wk", 52), ("Frequency", 128), ("Provider", 156)]
        x0 = _LEFT
        # header row
        self._ensure(_LINE * 2)
        self.pdf.rect(x0, self.y, _WIDTH, _LINE + 2, fill_gray=0.9, stroke=False)
        cx = x0
        for name, w in cols:
            self.pdf.text(cx + 3, self.y + 11, name, 9.5, bold=True)
            cx += w
        self.y += _LINE + 2
        for s in self.record["services"]:
            provider = s["provider_role"]
            values = [s["type"], str(s["minutes_per_week"]), s["frequency"], provider]
            # compute wrapped lines per cell to size the row
            wrapped = [wrap_text(v, 9.5, w - 6) for v, (_, w) in zip(values, cols)]
            rows = max(len(w) for w in wrapped)
            row_h = rows * (_LINE - 2) + 4
            self._ensure(row_h)
            cx = x0
            for lines, (_, w) in zip(wrapped, cols):
                for j, line in enumerate(lines):
                    self.pdf.text(cx + 3, self.y + 10 + j * (_LINE - 2), line, 9.5,
                                  bold=(provider == "Unassigned" and lines is wrapped[3]))
                self.pdf.line(cx, self.y - 2, cx, self.y + row_h - 2)
                cx += w
            self.pdf.line(x0 + _WIDTH, self.y - 2, x0 + _WIDTH, self.y + row_h - 2)
            self.pdf.line(x0, self.y + row_h - 2, x0 + _WIDTH, self.y + row_h - 2)
            self.y += row_h

    def _signatures(self) -> None:
        self.y += 12
        self._heading("Signatures")
        self._wrapped("This synthetic IEP is provided for demonstration only.", 9.5)
        self.y += 8
        for role in ("Case Manager: Ms. Jordan Lee", "Parent/Guardian: (synthetic)",
                     "LEA Representative: (synthetic)"):
            self._ensure(_LINE * 2)
            self.pdf.line(_LEFT, self.y + 12, _LEFT + 240, self.y + 12)
            self.pdf.text(_LEFT, self.y + 22, role, 9.5)
            self.pdf.line(_LEFT + 300, self.y + 12, _RIGHT, self.y + 12)
            self.pdf.text(_LEFT + 300, self.y + 22, "Date", 9.5)
            self.y += 30

    def render(self) -> bytes:
        self._header()
        self._student_info()
        self._present_levels()
        self._goals()
        self._accommodations()
        self._services()
        self._signatures()
        return self.pdf.build()


def render_pdf(record: dict[str, Any]) -> bytes:
    return _FormRenderer(record).render()


def render_two_column_pdf(record: dict[str, Any]) -> bytes:
    """A two-column layout variant of the same record (harder to parse; for scan 5)."""

    pdf = PDF()
    # Full-width header.
    pdf.text(_LEFT, _TOP + 14, DISTRICT_NAME, 14, bold=True)
    pdf.text(_LEFT, _TOP + 30, "Individualized Education Program (IEP) - Alternate Layout", 10, bold=True)
    pdf.rect(_LEFT, _TOP + 36, _WIDTH, 15, fill_gray=0.15, stroke=False)
    pdf.text(_LEFT + 4, _TOP + 47, "CONFIDENTIAL - SYNTHETIC DEMO DATA - NOT A REAL STUDENT",
             9, bold=True, gray=1.0)
    r = record
    d = r["dates"]
    pdf.text(_LEFT, _TOP + 66, f"{_display_name(r['student_ref'])}  ({r['student_ref']})  -  "
             f"{r['disability_category']}  -  SY {r['school_year']}", 9.5, bold=True)
    pdf.text(_LEFT, _TOP + 80,
             f"Annual review {d['annual_review'] or 'Not stated'}   "
             f"Triennial {d['triennial_reeval'] or 'Not stated'}   "
             f"Last progress {d['last_progress_report'] or 'Not stated'}", 9)

    mid = 300.0
    gutter = 18.0
    left_x, right_x = _LEFT, mid + gutter
    left_w, right_w = mid - _LEFT, _RIGHT - (mid + gutter)
    size = 8.5
    lh = 11.0

    def column(x: float, width: float, blocks: list[tuple[str, bool]], start_y: float) -> None:
        y = start_y
        for text, bold in blocks:
            if not text:
                y += lh * 0.5
                continue
            for line in wrap_text(text, size, width, bold=bold):
                pdf.text(x, y, line, size, bold=bold)
                y += lh

    body_top = _TOP + 100
    left_blocks: list[tuple[str, bool]] = [("MEASURABLE ANNUAL GOALS", True), ("", False)]
    for i, g in enumerate(r["goals"], start=1):
        left_blocks += [(f"Goal {i}: {g['text']}", True),
                        (f"Baseline: {g['baseline']}", False),
                        (f"Target: {g['target']}", False),
                        (f"Measure: {g['measure']} | Cadence: {g['progress_cadence']}", False),
                        ("", False)]
    right_blocks: list[tuple[str, bool]] = [("ACCOMMODATIONS", True), ("", False)]
    for a in r["accommodations"]:
        right_blocks.append((f"- {a['text']} (applies to: {_scope(a['applies_to'])})", False))
    right_blocks += [("", False), ("SERVICES", True), ("", False)]
    for s in r["services"]:
        right_blocks.append(
            (f"- {s['type']}: {s['minutes_per_week']} min/wk, {s['frequency']}, {s['provider_role']}",
             s["provider_role"] == "Unassigned"))

    column(left_x, left_w, left_blocks, body_top)
    column(right_x, right_w, right_blocks, body_top)
    # Column divider.
    pdf.line(mid + gutter / 2, body_top - 6, mid + gutter / 2, _BOTTOM)
    return pdf.build()


def render_html(record: dict[str, Any]) -> str:
    r = record
    d = r["dates"]
    esc = html_lib.escape

    def rows(items: list[tuple[str, str]]) -> str:
        return "".join(
            f"<tr><th>{esc(k)}</th><td>{esc(v)}</td></tr>" for k, v in items
        )

    goals_html = ""
    for i, g in enumerate(r["goals"], start=1):
        goals_html += (
            f"<div class='goal'><h4>Goal {i}</h4><p>{esc(g['text'])}</p>"
            f"<table class='kv'>{rows([('Baseline', g['baseline']), ('Target', g['target']), ('Measure', g['measure']), ('Progress cadence', g['progress_cadence'])])}</table></div>"
        )
    acc_html = "".join(
        f"<li>{esc(a['text'])} <span class='scope'>(applies to: {esc(_scope(a['applies_to']))})</span></li>"
        for a in r["accommodations"]
    )
    svc_rows = "".join(
        f"<tr><td>{esc(s['type'])}</td><td>{s['minutes_per_week']}</td><td>{esc(s['frequency'])}</td>"
        f"<td class='{'unassigned' if s['provider_role'] == 'Unassigned' else ''}'>{esc(s['provider_role'])}</td>"
        f"<td>{esc(s['start'] or '-')}</td><td>{esc(s['end'] or '-')}</td></tr>"
        for s in r["services"]
    )

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>IEP - {esc(_display_name(r['student_ref']))} ({esc(r['student_ref'])})</title>
<style>
  body {{ font-family: Helvetica, Arial, sans-serif; color: #1a1a1a; max-width: 760px;
         margin: 24px auto; padding: 0 20px; line-height: 1.4; }}
  h1 {{ font-size: 20px; margin: 0; }}
  .sub {{ font-size: 13px; font-weight: bold; margin: 2px 0 8px; }}
  .banner {{ background: #1a1a1a; color: #fff; font-size: 11px; font-weight: bold;
             padding: 4px 8px; letter-spacing: .5px; }}
  h3 {{ background: #e0e0e0; padding: 4px 8px; font-size: 13px; margin: 18px 0 8px; }}
  table {{ border-collapse: collapse; width: 100%; font-size: 12px; }}
  table.kv th {{ text-align: left; width: 150px; vertical-align: top; padding: 2px 6px; }}
  table.info th {{ text-align: left; width: 180px; padding: 3px 8px; background: #f4f4f4; }}
  table.info td, table.info th, table.svc td, table.svc th {{ border: 1px solid #bbb; padding: 4px 8px; }}
  table.svc th {{ background: #eee; font-size: 11px; text-align: left; }}
  .goal {{ border-left: 3px solid #888; padding-left: 10px; margin: 10px 0; }}
  .goal h4 {{ margin: 4px 0; }}
  .scope {{ color: #666; font-size: 11px; }}
  .unassigned {{ color: #b00; font-weight: bold; }}
  .sig {{ margin-top: 8px; }} .sig div {{ border-top: 1px solid #333; width: 260px;
          margin-top: 26px; padding-top: 2px; font-size: 11px; }}
</style></head><body>
<h1>{esc(DISTRICT_NAME)}</h1>
<div class="sub">Individualized Education Program (IEP)</div>
<div class="banner">CONFIDENTIAL - SYNTHETIC DEMO DATA - NOT A REAL STUDENT</div>
<h3>Student Information</h3>
<table class="info">{rows([
    ('Student', _display_name(r['student_ref'])), ('Student ID', r['student_ref']),
    ('School', SCHOOL_NAME), ('School Year', r['school_year']),
    ('Eligibility', r['disability_category']),
    ('Annual Review', d['annual_review'] or 'Not stated'),
    ('Triennial Reevaluation', d['triennial_reeval'] or 'Not stated'),
    ('Last Progress Report', d['last_progress_report'] or 'Not stated')])}</table>
<h3>Measurable Annual Goals</h3>{goals_html}
<h3>Accommodations</h3><ul>{acc_html}</ul>
<h3>Special Education and Related Services</h3>
<table class="svc"><tr><th>Service</th><th>Min/wk</th><th>Frequency</th><th>Provider</th><th>Start</th><th>End</th></tr>{svc_rows}</table>
<h3>Signatures</h3>
<div class="sig"><div>Case Manager: Ms. Jordan Lee</div><div>Parent/Guardian (synthetic)</div></div>
</body></html>
"""
