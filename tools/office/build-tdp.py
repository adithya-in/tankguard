"""Build the three TDP deliverables from the templates.

Copy rules: no em dashes, no "X, not Y" antithesis, no rhetorical fragments.
Every claim carries the number or the limit that backs it.

DOCX keeps the template's section (TIH header, footer, page fields) and rebuilds
the body. XLSX rebuilds both sheets as clean tables. PPTX keeps the template's
label boxes, logo and divider, and rebuilds the content as headline plus cards.
"""
import os
import shutil

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import (WD_ALIGN_PARAGRAPH, WD_BREAK, WD_TAB_ALIGNMENT,
                            WD_TAB_LEADER)
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor
from openpyxl import load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from pptx import Presentation
from pptx.dml.color import RGBColor as PRGB
from pptx.enum.dml import MSO_LINE
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt as PPt

DL = r"C:\Users\DELL\Downloads"
OUT = r"C:\Users\DELL\tankguard-gh\docs\office"

DOCX_SRC = os.path.join(DL, "Project Proposal Format TDP .docx")
XLSX_SRC = os.path.join(DL, "Budget & Milestone TDP.xlsx")
PPTX_SRC = os.path.join(DL, "Presentation Template.pptx")

DATE = "31 October 2026"
TITLE = "TankGuard: self-powered monitoring, pump control and sludge cleaning for water tanks"
PI = "Dr. Vishnu Vasudev"
AFFIL = "Nuke Labs (industry partner)"
THEME = "TIH IoT Technology Development Program 2026"
BLUE = RGBColor(0x1F, 0x4E, 0x79)
MID_BLUE = RGBColor(0x2E, 0x74, 0xB5)

EXEC = [
    "TankGuard is a self-powered monitoring and cleaning system for water storage "
    "tanks in homes and institutions. It measures water quality in the tank, reports "
    "one score, controls the household pump, and cleans the sludge that settles on "
    "the floor. All of it runs on the local network, with no cloud service, "
    "subscription or account.",

    "The system has three units. M1 sits on the tank lid and reads turbidity, TDS, "
    "pH, temperature and water level through submerged probes. It computes a "
    "weighted score between 0 and 100 and serves the dashboard from its own flash "
    "memory. H1 sits next to the pump switch, shows the score on a 1.8 inch colour "
    "display, and drives the pump through an isolated relay and contactor. C1 is "
    "the cleaning arm: two rigid links of 20 cm each, a ring brush at the tip, and a "
    "submersible pump that draws the loosened sludge through the centre of the head.",

    "Tanks degrade without warning. Disinfectant residual is gone within 24 to 48 "
    "hours of filling. Particles settle into a sludge layer at the floor, biofilm "
    "forms on the walls, and algae grow faster in warm water. The water is unsafe "
    "before it smells or looks wrong. The usual remedy is a full drain and a manual "
    "scrub, which discards the whole stored volume.",

    "TankGuard measures, decides and cleans at the edge. One cleaning cycle covers "
    "90 percent of the floor. A 2 cm ring at the wall stays out of reach, and the "
    "design record states it. The dashboard reports the data source and the coverage "
    "limit, so the owner knows what was measured and what was cleaned.",

    "The project delivers a working prototype of M1 and H1, the C1 cleaning arm with "
    "its planner and controller, the dashboard served by the tank unit, and field "
    "validation at TRL 6 or above with an industry partner.",
]

HISTORY = [
    "TankGuard started as a water-quality monitor. Five probes fed an edge-computed "
    "score, and the device served its own dashboard over Wi-Fi. The first build "
    "showed that an ESP8266 can carry the whole stack without a cloud service.",
    "Field trials exposed the real failure mode. Measurement alone does not clean a "
    "tank. The sludge layer keeps feeding turbidity and biofilm, and the household "
    "still has to drain and scrub the tank by hand. The product therefore moved from "
    "monitoring to care: a home unit that runs the pump safely, and an arm that "
    "removes the sludge without emptying the tank.",
    "The current design keeps the five probes, the score weights and the local-only "
    "architecture. It replaces the abandoned drain-and-flush mechanism with the "
    "cleaning arm described here.",
]

PROBLEM = [
    "Storage tanks degrade silently. Residual chlorine disappears within 24 to 48 "
    "hours. Suspended solids settle into a sludge layer. Biofilm forms on internal "
    "surfaces, and algae grow in warm water. By the time the problem is visible, the "
    "water is already unsafe.",
    "Current options either monitor without acting or clean by draining the whole "
    "tank. Monitoring tells the owner there is a problem and leaves the work to "
    "them. A full drain wastes the stored water and needs manual labour.",
    "The gap is largest where it matters most. Schools, hospitals and apartment "
    "buildings store large volumes, clean to a fixed calendar, and cannot tell "
    "whether the last clean helped.",
]

OBJECTIVES = [
    "Objective 1: measure and score water quality at the edge. Five probes "
    "(turbidity, TDS, pH, temperature, level) are digitised through an ADS1115 and "
    "fused into a weighted score (turbidity 40 percent, TDS 25, pH 25, temperature "
    "10). Acceptance: the score repeats within 2 points across ten consecutive "
    "samples in still water.",
    "Objective 2: make the result readable without a phone. H1 shows the score, "
    "level, the four readings, pump state and link health on a 1.8 inch display. It "
    "controls the pump in automatic mode (on below the low-level setpoint, off above "
    "the high) with a manual override that releases safely.",
    "Objective 3: clean the tank floor without draining it. C1 sweeps three "
    "concentric rings at 8.0, 23.7 and 39.4 cm with a 16 cm ring brush and a central "
    "suction intake, covering 90 percent of the floor per cycle, and parks in a "
    "fixed rest pose at both ends of the cycle.",
    "Objective 4: prove it in the field. Twelve months to TRL 6 or above, with three "
    "installations, 90 days of continuous operation, and a published measurement of "
    "score accuracy, cleaning coverage and water saved against a full drain.",
]

DELIVERABLES = [
    "D1. M1 monitor: an ESP8266 unit on the tank lid with five calibrated probes, an "
    "edge score, and the web dashboard served from flash.",
    "D2. H1 home unit: an ESP8266 with a 1.8 inch display, automatic pump control "
    "through an isolated relay and contactor, and a manual override.",
    "D3. C1 cleaning arm: an ESP32 controller, a two-link arm, a ring brush head "
    "with suction, a path planner and an executor, with the coverage analysis that "
    "states its limits.",
    "D4. Field evidence: three installations, 90 days of data, and a TRL 6 evidence "
    "pack covering score accuracy and cleaning coverage.",
]

MILESTONES = [
    ("1", "Requirements and monitor prototype", "T0 + 2 months",
     "M1 assembled and calibrated. Score validated against reference instruments. "
     "Dashboard served from flash."),
    ("2", "Home unit and dashboard", "T0 + 4 months",
     "H1 installed with pump control. Dashboard, session log and device table "
     "complete."),
    ("3", "Cleaning arm", "T0 + 8 months",
     "C1 built. Three-ring cycle executed. Coverage and repeatability measured."),
    ("4", "Field validation", "T0 + 12 months",
     "Three installations, 90 days of data, TRL 6 evidence pack."),
]

BUDGET_ROWS = [
    ("Manpower", "0"),
    ("Equipment (exclusive of GST)", "15,600"),
    ("Consumables", "0"),
    ("Travel", "0"),
    ("Miscellaneous", "0"),
    ("Contingency (max 5%)", "780"),
    ("Sub total", "16,380"),
    ("Overhead (max 20%)", "3,276"),
    ("Faculty fee (max 20%)", "3,931"),
    ("Total (7+8+9)", "23,587"),
    ("GST (18%)", "0"),
    ("Grand total", "23,587"),
]

BUDGET_NOTE = [
    "Equipment split, indicative: M1 monitor INR 6,500; H1 home unit INR 1,800; C1 "
    "cleaning arm INR 7,300. The C1 figure covers two 12 V planetary gearmotors, an "
    "ESP32, two H-bridges, a submersible pump, the brush head and the enclosure.",
    "Contingency is capped at 5 percent of project value, overhead at 20 percent of "
    "the sub total, and the faculty fee at 20 percent of the total.",
    "Manpower, consumables, travel and miscellaneous heads will be agreed at the "
    "grant kickoff. Equipment figures are vendor quotes pending confirmation.",
]

TRANCHE_ROWS = [
    ("Project start (T0)", "8,235", "M1 monitor build and dashboard"),
    ("T0 + 6 months", "9,415", "H1 home unit and C1 cleaning arm"),
    ("T0 + 12 months", "5,937", "Field validation and evidence pack"),
    ("Total", "23,587", ""),
]

SUPPORT = [
    "TankGuard Technical Specification, document TG-SPEC-2026-001, October 2026, "
    "7 pages.",
    "Firmware for all three units, compiling for ESP8266 (M1 and H1) and ESP32 "
    "(C1), with the React dashboard served from M1 flash.",
    "Design record (docs/CLEANER.md): kinematics, coverage analysis and control "
    "limits, including the 2 cm wall ring the arm cannot reach.",
    "Coverage planner (tools/swept_area.html) and the generated path used by the "
    "controller (firmware/c1_cleaner/path.h).",
    "Patentability disclosure and the minimum bill of materials.",
]

CATEGORY = (
    "New-to-the-world product. The combination of edge-computed water scoring, a "
    "dashboard hosted on the device, safe pump control and a selective cleaning arm "
    "on one local network is not offered by monitoring products or by full-drain "
    "cleaning services. The closest alternatives cover one part of the problem."
)

# --------------------------------------------------------------------------- #
# DOCX
# --------------------------------------------------------------------------- #
def shade(cell, hexcolor="1F4E79"):
    tcPr = cell._tc.get_or_add_tcPr()
    for old in tcPr.findall(qn("w:shd")):
        tcPr.remove(old)
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hexcolor)
    tcPr.append(shd)


def table(doc, headers, rows, widths=None, right_cols=()):
    t = doc.add_table(rows=1, cols=len(headers))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    hdr = t.rows[0].cells
    for i, h in enumerate(headers):
        hdr[i].text = ""
        r = hdr[i].paragraphs[0].add_run(h)
        r.bold = True
        r.font.size = Pt(9.5)
        r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        shade(hdr[i])
    trPr = t.rows[0]._tr.get_or_add_trPr()
    tblHeader = OxmlElement("w:tblHeader")
    tblHeader.set(qn("w:val"), "true")
    trPr.append(tblHeader)

    for row in rows:
        cells = t.add_row().cells
        for i, val in enumerate(row):
            cells[i].text = ""
            p = cells[i].paragraphs[0]
            r = p.add_run(str(val))
            r.font.size = Pt(9.5)
            if i in right_cols:
                p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            shade(cells[i], "FFFFFF")
    if widths:
        for i, w in enumerate(widths):
            for row in t.rows:
                row.cells[i].width = w
    doc.add_paragraph()
    return t


def para(doc, text, size=11, bold=False, color=None, align=None,
         space_after=6, space_before=0):
    p = doc.add_paragraph()
    r = p.add_run(text)
    r.font.size = Pt(size)
    r.bold = bold
    if color is not None:
        r.font.color.rgb = color
    if align is not None:
        p.alignment = align
    p.paragraph_format.space_after = Pt(space_after)
    if space_before:
        p.paragraph_format.space_before = Pt(space_before)
    return p


def heading(doc, text, level):
    p = doc.add_heading(text, level=level)
    pPr = p._p.get_or_add_pPr()
    for old in pPr.findall(qn("w:numPr")):
        pPr.remove(old)
    numPr = OxmlElement("w:numPr")
    ilvl = OxmlElement("w:ilvl")
    ilvl.set(qn("w:val"), "0")
    numId = OxmlElement("w:numId")
    numId.set(qn("w:val"), "0")
    numPr.append(ilvl)
    numPr.append(numId)
    pPr.append(numPr)
    size = 15 if level == 1 else 12.5
    color = BLUE if level == 1 else MID_BLUE
    for r in p.runs:
        r.font.size = Pt(size)
        r.font.bold = True
        r.font.color.rgb = color
    p.paragraph_format.space_before = Pt(14 if level == 1 else 10)
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.keep_with_next = True
    return p


def rebuild_docx():
    path = os.path.join(OUT, "TankGuard_Project_Proposal.docx")
    doc = Document(DOCX_SRC)

    body = doc.element.body
    for child in list(body):
        if child.tag == qn("w:sectPr"):
            continue
        body.remove(child)

    # ---- title page -------------------------------------------------------
    para(doc, "Project Proposal", 20, True, BLUE, WD_ALIGN_PARAGRAPH.CENTER,
         4, space_before=190)
    para(doc, "For Consideration Under", 11, False, None, WD_ALIGN_PARAGRAPH.CENTER, 2)
    para(doc, THEME, 15, True, BLUE, WD_ALIGN_PARAGRAPH.CENTER, 18)
    para(doc, TITLE, 16, True, BLUE, WD_ALIGN_PARAGRAPH.CENTER, 16)
    para(doc, "Submitted by", 11, False, None, WD_ALIGN_PARAGRAPH.CENTER, 2)
    para(doc, PI, 14, True, BLUE, WD_ALIGN_PARAGRAPH.CENTER, 2)
    para(doc, AFFIL, 11, False, None, WD_ALIGN_PARAGRAPH.CENTER, 10)
    para(doc, "Theme: " + THEME, 10.5, False, None, WD_ALIGN_PARAGRAPH.CENTER, 2)
    para(doc, "Date of submission: " + DATE, 10.5, False, None, WD_ALIGN_PARAGRAPH.CENTER, 2)
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

    # ---- contents ---------------------------------------------------------
    heading(doc, "Contents", 1)
    for line, page in (
        ("1  Cover Sheet", "3"),
        ("2  Executive Summary", "3"),
        ("3  Background", "3"),
        ("     3.1  History", "3"),
        ("     3.2  Statement of the problem", "4"),
        ("     3.3  Objectives", "4"),
        ("     3.4  Deliverables", "4"),
        ("     3.5  Project plan with major milestones", "5"),
        ("     3.6  Resources and budget", "5"),
        ("     3.7  Category of new technology/product", "6"),
        ("4  Appendix", "6"),
        ("     4.1  Supporting documentation", "6"),
    ):
        p = doc.add_paragraph()
        p.paragraph_format.tab_stops.add_tab_stop(
            Pt(440), WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.DOTS)
        p.paragraph_format.space_after = Pt(4)
        r = p.add_run(line + "\t" + page)
        r.font.size = Pt(11)
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

    # ---- 1 cover sheet ----------------------------------------------------
    heading(doc, "1  Cover Sheet", 1)
    table(
        doc,
        ["Field", "Detail"],
        [
            ("Project title", TITLE),
            ("Principal investigator", PI),
            ("Designation", "Principal Investigator"),
            ("Affiliation", AFFIL),
            ("Co-investigator", "None"),
            ("Collaborator", "Nuke Labs (build, field access, commercialisation)"),
            ("Theme", THEME),
            ("Date of submission", DATE),
        ],
        widths=[Pt(150), Pt(300)],
    )

    # ---- 2 executive summary ---------------------------------------------
    heading(doc, "2  Executive Summary", 1)
    for t in EXEC:
        para(doc, t)

    # ---- 3 background -----------------------------------------------------
    heading(doc, "3  Background", 1)

    heading(doc, "3.1  History", 2)
    for t in HISTORY:
        para(doc, t)

    heading(doc, "3.2  Statement of the problem", 2)
    for t in PROBLEM:
        para(doc, t)

    heading(doc, "3.3  Objectives", 2)
    for t in OBJECTIVES:
        para(doc, t)

    heading(doc, "3.4  Deliverables", 2)
    for t in DELIVERABLES:
        para(doc, t)

    h = heading(doc, "3.5  Project plan with major milestones", 2)
    h.paragraph_format.page_break_before = True
    para(doc, "Twelve months from T0, with a demonstration at every gate.")
    table(doc, ["#", "Milestone", "Period", "Delivered at the gate"],
          MILESTONES, widths=[Pt(24), Pt(150), Pt(70), Pt(210)])

    heading(doc, "3.6  Resources and budget", 2)
    table(doc, ["Item", "Amount (INR)"], BUDGET_ROWS,
          widths=[Pt(300), Pt(154)], right_cols=(1,))
    for t in BUDGET_NOTE:
        para(doc, t, 10)

    cap = para(doc, "Tranche disbursement schedule", 12.5, True, MID_BLUE,
               space_after=6)
    cap.paragraph_format.space_before = Pt(14)
    cap.paragraph_format.keep_with_next = True
    cap.paragraph_format.page_break_before = True
    table(doc, ["Timeline", "Amount (INR)", "Milestone covered"],
          TRANCHE_ROWS, widths=[Pt(110), Pt(90), Pt(254)], right_cols=(1,))

    heading(doc, "3.7  Category of new technology/product", 2)
    para(doc, CATEGORY)

    # ---- 4 appendix -------------------------------------------------------
    heading(doc, "4  Appendix", 1)
    heading(doc, "4.1  Supporting documentation", 2)
    for t in SUPPORT:
        p = para(doc, t)
        p.paragraph_format.left_indent = Pt(14)
        p.paragraph_format.space_after = Pt(4)

    # heading styles: the template's carry a bullet and a magenta Heading 2
    for name, size, hexcolor in (("Heading 1", 15, "1F4E79"), ("Heading 2", 12.5, "2E74B5")):
        st = doc.styles[name]
        pPr = st.element.get_or_add_pPr()
        for n in pPr.findall(qn("w:numPr")):
            pPr.remove(n)
        st.font.size = Pt(size)
        st.font.bold = True
        rPr = st.element.get_or_add_rPr()
        col = rPr.find(qn("w:color"))
        if col is not None:
            col.set(qn("w:val"), hexcolor)
            for attr in (qn("w:themeColor"), qn("w:themeShade"), qn("w:themeTint")):
                col.attrib.pop(attr, None)

    # template metadata and the placeholder author fields
    sec = doc.sections[0]
    for part in (sec.header, sec.first_page_footer):
        for t in part.tables:
            for row in t.rows:
                for cell in row.cells:
                    for p in list(cell.paragraphs):
                        for r in p.runs:
                            if "14-July-2021" in r.text:
                                r.text = r.text.replace("14-July-2021", "31-October-2026")

    for part in (sec.first_page_footer, sec.footer, sec.header, sec.first_page_header):
        doomed = []
        for el in part._element.iter():
            hit = (el.tag == qn("w:t") and el.text and el.text.strip() in ("Author2", "Author3")) or (
                el.tag == qn("w:instrText") and el.text and ("Author2" in el.text or "Author3" in el.text)
            )
            if hit:
                p = el
                while p is not None and p.tag != qn("w:p"):
                    p = p.getparent()
                if p is not None:
                    doomed.append(p)
        for p in doomed:
            parent = p.getparent()
            if parent is not None:
                parent.remove(p)

    for t in list(sec.first_page_header.tables):
        t._element.getparent().remove(t._element)

    doc.core_properties.title = TITLE
    doc.core_properties.author = PI
    doc.core_properties.subject = THEME
    doc.save(path)
    return path

# --------------------------------------------------------------------------- #
# XLSX
# --------------------------------------------------------------------------- #
NAVY = "1F4E79"
STEEL = "2E74B5"
BAND = "EFF3F9"
THIN = Side(style="thin", color="B7C3D3")
BOX = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)


def wipe(ws, rows, cols):
    for r in range(1, rows + 1):
        for c in range(1, cols + 1):
            cell = ws.cell(row=r, column=c)
            cell.value = None
            cell.border = Border()
            cell.fill = PatternFill(fill_type=None)


def style_block(ws, r1, c1, r2, c2, header=True):
    for r in range(r1, r2 + 1):
        for c in range(c1, c2 + 1):
            cell = ws.cell(row=r, column=c)
            cell.border = BOX
            cell.font = Font(name="Calibri", size=10,
                             bold=(header and r == r1))
            if header and r == r1:
                cell.fill = PatternFill("solid", fgColor=STEEL)
                cell.font = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
            elif r % 2 == 0:
                cell.fill = PatternFill("solid", fgColor=BAND)
            cell.alignment = Alignment(vertical="center", wrap_text=True)


def rebuild_xlsx():
    path = os.path.join(OUT, "TankGuard_Budget_Milestone.xlsx")
    shutil.copyfile(XLSX_SRC, path)
    wb = load_workbook(path)

    # ---------------- sheet 1: summary ------------------------------------
    ms = wb["Milestones"]
    for rng in list(ms.merged_cells.ranges):
        ms.unmerge_cells(str(rng))
    wipe(ms, 40, 14)

    widths = {"A": 7, "B": 29, "C": 13, "D": 2.5, "E": 5.5, "F": 31,
              "G": 15, "H": 34, "I": 2.5, "J": 19, "K": 14, "L": 38}
    for col, w in widths.items():
        ms.column_dimensions[col].width = w

    for rng, text in (("A1:C1", "Budget"), ("E1:H1", "Milestone Timelines"),
                      ("J1:L1", "Tranche Disbursement Schedule")):
        ms.merge_cells(rng)
        cell = ms[rng.split(":")[0]]
        cell.value = text
        cell.font = Font(name="Calibri", size=12, bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor=NAVY)
        cell.alignment = Alignment(horizontal="center", vertical="center")
    ms.row_dimensions[1].height = 26
    ms.row_dimensions[3].height = 34

    heads = {
        "A3": "Sr. No.", "B3": "Item", "C3": "Total (Rs.)",
        "E3": "S No", "F3": "Milestone / Deliverable", "G3": "Time period",
        "H3": "Remarks",
        "J3": "Timeline", "K3": "Amount to be released (INR)",
        "L3": "Milestone / deliverables completed",
    }
    for coord, text in heads.items():
        ms[coord] = text

    # budget block
    budget = [
        ("1", "Manpower", 0), ("2", "Equipment (exclusive of GST)", 15600),
        ("3", "Consumables", 0), ("4", "Travel", 0),
        ("5", "Miscellaneous expenses", 0), ("6", "Contingency (max 5%)", 780),
        ("7", "Sub total", 16380), ("8", "Overhead (max 20%)", 3276),
        ("9", "Faculty fee (max 20%)", 3931), ("10", "Total (7+8+9)", 23587),
        ("11", "GST (18% of 10)", 0), ("12", "Grand total (10+11)", 23587),
    ]
    for i, (no, name, amt) in enumerate(budget):
        r = 4 + i
        ms[f"A{r}"] = int(no)
        ms[f"B{r}"] = name
        ms[f"C{r}"] = amt
        ms[f"C{r}"].number_format = "#,##0"
        ms[f"C{r}"].alignment = Alignment(horizontal="right", vertical="center")
        ms[f"A{r}"].alignment = Alignment(horizontal="center", vertical="center")

    # milestones block
    miles = [
        ("1", "Milestone 1: Monitor prototype", "T0 + 2 months", "M1 calibrated, score validated"),
        ("2", "Milestone 2: Home unit and dashboard", "T0 + 4 months", "H1 pump control, dashboard live"),
        ("3", "Milestone 3: Cleaning arm", "T0 + 8 months", "C1 built, coverage measured"),
        ("4", "Milestone 4: Field validation", "T0 + 12 months", "3 sites, 90 days, TRL 6 pack"),
        ("", "Total", "", ""),
    ]
    for i, (no, name, when, remark) in enumerate(miles):
        r = 4 + i
        ms[f"E{r}"] = no if no else None
        ms[f"F{r}"] = name
        ms[f"G{r}"] = when
        ms[f"H{r}"] = remark
        ms[f"E{r}"].alignment = Alignment(horizontal="center", vertical="center")

    # tranche block
    tranche = [
        ("Project start (T0)", 8235, "M1 monitor build and dashboard"),
        ("T0 + 6 months", 9415, "H1 home unit and C1 cleaning arm"),
        ("T0 + 12 months", 5937, "Field validation and evidence pack"),
        ("Total", 23587, ""),
    ]
    for i, (when, amt, what) in enumerate(tranche):
        r = 4 + i
        ms[f"J{r}"] = when
        ms[f"K{r}"] = amt
        ms[f"K{r}"].number_format = "#,##0"
        ms[f"K{r}"].alignment = Alignment(horizontal="right", vertical="center")
        ms[f"L{r}"] = what

    style_block(ms, 3, 1, 15, 3)
    style_block(ms, 3, 5, 8, 8)
    style_block(ms, 3, 10, 7, 12)

    for r in range(4, 16):
        ms.row_dimensions[r].height = 29
        ms[f"B{r}"].alignment = Alignment(vertical="center", wrap_text=True)
    for r in (10, 13, 15):
        for c in range(1, 4):
            cell = ms.cell(row=r, column=c)
            cell.font = Font(name="Calibri", size=10, bold=True)
    for r in (8, 7):
        for c in range(5, 9):
            cell = ms.cell(row=r, column=c)
            if r == 8:
                cell.font = Font(name="Calibri", size=10, bold=True)
    for c in range(10, 13):
        ms.cell(row=7, column=c).font = Font(name="Calibri", size=10, bold=True)

    ms.print_area = "A1:L15"
    ms.page_setup.orientation = "landscape"
    ms.page_setup.paperSize = 9
    ms.page_setup.fitToWidth = 1
    ms.page_setup.fitToHeight = 1
    ms.sheet_properties.pageSetUpPr.fitToPage = True
    ms.print_options.horizontalCentered = True
    ms.print_options.verticalCentered = True
    ms.page_margins.left = ms.page_margins.right = 0.35
    ms.page_margins.top = ms.page_margins.bottom = 0.4

    # ---------------- sheet 2: expenditure --------------------------------
    b = wb["Budget"]
    for rng in list(b.merged_cells.ranges):
        b.unmerge_cells(str(rng))
    wipe(b, 40, 10)

    b.column_dimensions["B"].width = 6
    b.column_dimensions["C"].width = 44
    b.column_dimensions["D"].width = 24

    b.merge_cells("B2:D2")
    b["B2"] = "Milestone Expenditure Sheet"
    b["B2"].font = Font(name="Calibri", size=13, bold=True, color=NAVY)
    b["B2"].alignment = Alignment(vertical="center")
    b.row_dimensions[2].height = 24

    b.merge_cells("B3:D3")
    b["B3"] = "Grant total: INR 23,587"
    b["B3"].font = Font(name="Calibri", size=11, bold=True, color=STEEL)
    b["B3"].alignment = Alignment(horizontal="right", vertical="center")

    for coord, text in (("B4", "Sr. No."), ("C4", "Expenditure heads"),
                        ("D4", "Total funding (INR)")):
        b[coord] = text

    heads2 = [
        ("1", "Manpower", 0), ("2", "Equipment (exclusive of GST)", 15600),
        ("3", "Consumables", 0), ("4", "Travel", 0),
        ("5", "Miscellaneous expenses", 0), ("6", "Contingency (max 5%)", 780),
        ("7", "Sub total", 16380), ("8", "Overhead (max 20%)", 3276),
        ("9", "Faculty fee (max 20%)", 3931), ("10", "Total (7+8+9)", 23587),
        ("11", "GST (18% of 10)", 0), ("12", "Grand total (10+11)", 23587),
    ]
    for i, (no, name, amt) in enumerate(heads2):
        r = 5 + i
        b[f"B{r}"] = int(no)
        b[f"C{r}"] = name
        b[f"D{r}"] = amt
        b[f"D{r}"].number_format = "#,##0"

    style_block(b, 4, 2, 16, 4)
    for r in range(5, 17):
        b.row_dimensions[r].height = 22
        b[f"B{r}"].alignment = Alignment(horizontal="center", vertical="center")
        b[f"D{r}"].alignment = Alignment(horizontal="right", vertical="center")
    for r in (11, 14, 16):
        for c in range(2, 5):
            b.cell(row=r, column=c).font = Font(name="Calibri", size=10, bold=True)

    b.merge_cells("B18:D18")
    b["B18"] = ("80 percent of each tranche is spent before the next is claimed. "
                "Tranche amounts are set out on the Milestones sheet.")
    b["B18"].font = Font(name="Calibri", size=9, italic=True, color="404040")
    b["B18"].alignment = Alignment(vertical="center", wrap_text=True)
    b.row_dimensions[18].height = 30

    b.print_area = "B2:D18"
    b.page_setup.orientation = "portrait"
    b.page_setup.paperSize = 9
    b.page_setup.fitToWidth = 1
    b.page_setup.fitToHeight = 1
    b.sheet_properties.pageSetUpPr.fitToPage = True
    b.print_options.horizontalCentered = True
    b.print_options.verticalCentered = True
    b.page_margins.left = b.page_margins.right = 0.5
    b.page_margins.top = b.page_margins.bottom = 0.5

    wb.save(path)
    return path

# --------------------------------------------------------------------------- #
# PPTX
# --------------------------------------------------------------------------- #
NAVY_P = PRGB(0x1F, 0x38, 0x64)
BLUE_P = PRGB(0x2E, 0x74, 0xB5)
INK = PRGB(0x26, 0x26, 0x26)
GREY = PRGB(0x59, 0x59, 0x59)
CARD = PRGB(0xF4, 0xF7, 0xFB)
BORDER = PRGB(0xD3, 0xDC, 0xE8)
WHITE = PRGB(0xFF, 0xFF, 0xFF)
GREEN = PRGB(0x05, 0x96, 0x69)
AMBER = PRGB(0xD9, 0x77, 0x06)
RED = PRGB(0xDC, 0x26, 0x26)

LABEL_TEXT = {
    2: "The problem",
    3: "Why current practice fails",
    4: "The system",
    5: "The score",
    6: "The cleaning arm",
    7: "What is already built",
    8: "What is different",
    9: "Plan and milestones",
    10: "Impact and market",
    11: "Budget",
    12: "Funding",
    13: "Team and conclusion",
}

OLD_LABELS = {
    "Guidelines", "Key Points", "Problem Statement", "Solution", "USP / Differentiator",
    "Impact", "Project Plan / Methodology", "Milestones", "Market Size",
    "Resources & Budget", "Funding So Far", "Team", "Conclusion",
}


def tbox(slide, x, y, w, h, anchor=MSO_ANCHOR.TOP):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = 0
    tf.margin_right = 0
    tf.margin_top = 0
    tf.margin_bottom = 0
    return box


def write(tf, blocks):
    """blocks: list of dicts with text/size/bold/color/space_after/align/italic."""
    tf.clear()
    first = True
    for b in blocks:
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        p.text = b["text"]
        p.alignment = b.get("align", PP_ALIGN.LEFT)
        p.space_after = PPt(b.get("space_after", 6))
        p.line_spacing = b.get("line_spacing", 1.0)
        for r in p.runs:
            r.font.size = PPt(b.get("size", 13))
            r.font.bold = b.get("bold", False)
            r.font.italic = b.get("italic", False)
            r.font.color.rgb = b.get("color", INK)
            r.font.name = "Calibri"


def headline(slide, text, size=23):
    box = tbox(slide, 0.72, 1.02, 11.9, 0.9)
    write(box.text_frame, [{"text": text, "size": size, "bold": True, "color": NAVY_P}])


def band(slide, y, text, h=0.82, size=13.5):
    shp = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.72),
                                 Inches(y), Inches(11.9), Inches(h))
    shp.adjustments[0] = 0.12
    shp.fill.solid()
    shp.fill.fore_color.rgb = PRGB(0xED, 0xF2, 0xF9)
    shp.line.fill.background()
    shp.shadow.inherit = False
    bar = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.74),
                                 Inches(y + 0.12), Inches(0.06), Inches(h - 0.24))
    bar.adjustments[0] = 0.5
    bar.fill.solid()
    bar.fill.fore_color.rgb = NAVY_P
    bar.line.fill.background()
    bar.shadow.inherit = False
    box = tbox(slide, 0.98, y + 0.08, 11.4, h - 0.16, anchor=MSO_ANCHOR.MIDDLE)
    write(box.text_frame, [{"text": text, "size": size, "color": NAVY_P}])


def footer(slide, number):
    box = tbox(slide, 0.72, 7.02, 8.0, 0.3)
    write(box.text_frame, [{"text": "TankGuard  |  TIH IoT Technology Development Program 2026",
                            "size": 9.5, "color": GREY}])
    box2 = tbox(slide, 11.2, 7.02, 1.4, 0.3)
    write(box2.text_frame, [{"text": str(number), "size": 9.5, "color": GREY,
                             "align": PP_ALIGN.RIGHT}])


def card(slide, x, y, w, h, title, lines, title_size=15, body_size=12.5,
         accent=None):
    shp = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y),
                                 Inches(w), Inches(h))
    shp.adjustments[0] = 0.045
    shp.fill.solid()
    shp.fill.fore_color.rgb = CARD
    shp.line.color.rgb = BORDER
    shp.line.width = PPt(0.9)
    shp.shadow.inherit = False
    shp.text_frame.text = ""

    if accent is not None:
        bar = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x + 0.02),
                                     Inches(y + 0.18), Inches(0.07), Inches(h - 0.36))
        bar.adjustments[0] = 0.5
        bar.fill.solid()
        bar.fill.fore_color.rgb = accent
        bar.line.fill.background()
        bar.shadow.inherit = False

    inner_x = x + 0.3
    inner_w = w - 0.6
    tb = tbox(slide, inner_x, y + 0.12, inner_w, h - 0.24, anchor=MSO_ANCHOR.MIDDLE)
    blocks = [{"text": title, "size": title_size, "bold": True, "color": NAVY_P,
               "space_after": 8}]
    for line in lines:
        blocks.append({"text": line, "size": body_size, "color": INK,
                       "space_after": 7, "line_spacing": 1.05})
    write(tb.text_frame, blocks)


def add_table(slide, x, y, widths, headers, rows, head_h=0.45, row_h=0.62,
              size=12, align=None, bold_rows=()):
    total_w = sum(widths)
    shape = slide.shapes.add_table(len(rows) + 1, len(headers), Inches(x), Inches(y),
                                   Inches(total_w),
                                   Inches(head_h + row_h * len(rows)))
    tbl = shape.table
    tbl.first_row = True
    tbl.horz_banding = False
    for i, w in enumerate(widths):
        tbl.columns[i].width = Inches(w)
    tbl.rows[0].height = Inches(head_h)
    for i in range(len(rows)):
        tbl.rows[i + 1].height = Inches(row_h)

    def put(cell, text, bold=False, color=INK, fill=None, sz=size, right=False):
        cell.text = str(text)
        cell.margin_left = Inches(0.12)
        cell.margin_right = Inches(0.12)
        cell.margin_top = Inches(0.05)
        cell.margin_bottom = Inches(0.05)
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE
        if fill is not None:
            cell.fill.solid()
            cell.fill.fore_color.rgb = fill
        for p in cell.text_frame.paragraphs:
            p.alignment = PP_ALIGN.RIGHT if right else PP_ALIGN.LEFT
            for r in p.runs:
                r.font.size = PPt(sz)
                r.font.bold = bold
                r.font.color.rgb = color
                r.font.name = "Calibri"

    for c, h in enumerate(headers):
        put(tbl.cell(0, c), h, bold=True, color=WHITE, fill=BLUE_P)
    for r, row in enumerate(rows, start=1):
        fill = WHITE if r % 2 else PRGB(0xE9, 0xED, 0xF6)
        for c, val in enumerate(row):
            right = bool(align and align[c])
            put(tbl.cell(r, c), val, fill=fill, right=right,
                bold=(r in bold_rows))
    return tbl


def build_title(slide):
    shape = None
    for sh in slide.shapes:
        if sh.has_text_frame:
            shape = sh
            break
    if shape is None:
        return
    tf = shape.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    write(tf, [
        {"text": "TankGuard", "size": 46, "bold": True, "color": NAVY_P,
         "align": PP_ALIGN.CENTER, "space_after": 14},
        {"text": "Self-powered monitoring, pump control and sludge cleaning for water tanks",
         "size": 19, "color": GREY, "align": PP_ALIGN.CENTER, "space_after": 20},
        {"text": "Dr. Vishnu Vasudev  |  Nuke Labs (industry partner)",
         "size": 15, "bold": True, "color": BLUE_P, "align": PP_ALIGN.CENTER,
         "space_after": 6},
        {"text": THEME, "size": 13, "color": GREY, "align": PP_ALIGN.CENTER,
         "space_after": 4},
        {"text": "Submission: " + DATE, "size": 13, "color": GREY,
         "align": PP_ALIGN.CENTER},
    ])


def clear_body(slide, label):
    for sh in list(slide.shapes):
        if label is not None and sh._element is label._element:
            continue
        sh._element.getparent().remove(sh._element)


def relabel(slide, new_label):
    for sh in slide.shapes:
        if sh.has_text_frame and sh.text_frame.text.strip() in OLD_LABELS:
            tf = sh.text_frame
            for i, p in enumerate(tf.paragraphs):
                if i == 0 and p.runs:
                    p.runs[0].text = new_label
                    for r in p.runs[1:]:
                        r.text = ""
                else:
                    for r in p.runs:
                        r.text = ""
            return sh
    return None


def score_panel(slide):
    rows = [("Turbidity", 40, BLUE_P), ("TDS", 25, BLUE_P), ("pH", 25, BLUE_P),
            ("Temperature", 10, BLUE_P)]
    top = 2.28
    for i, (name, weight, color) in enumerate(rows):
        y = top + i * 0.62
        lb = tbox(slide, 0.72, y, 2.0, 0.32)
        write(lb.text_frame, [{"text": name, "size": 13, "color": INK}])
        track = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(2.78),
                                       Inches(y + 0.05), Inches(2.75), Inches(0.2))
        track.adjustments[0] = 0.5
        track.fill.solid()
        track.fill.fore_color.rgb = PRGB(0xE3, 0xE9, 0xF2)
        track.line.fill.background()
        track.shadow.inherit = False
        fillw = 2.75 * weight / 40.0
        bar = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(2.78),
                                     Inches(y + 0.05), Inches(fillw), Inches(0.2))
        bar.adjustments[0] = 0.5
        bar.fill.solid()
        bar.fill.fore_color.rgb = color
        bar.line.fill.background()
        bar.shadow.inherit = False
        val = tbox(slide, 5.62, y, 0.75, 0.32)
        write(val.text_frame, [{"text": str(weight), "size": 13, "bold": True,
                                "color": NAVY_P, "align": PP_ALIGN.RIGHT}])

    cap = tbox(slide, 0.72, 4.92, 5.6, 0.6)
    write(cap.text_frame, [{"text": "Weights out of 100. Water level is tracked for pump control "
                                    "and is not part of the score.",
                            "size": 11.5, "color": GREY}])

    bands = [("GOOD", "70 to 100", "Water is within limits. Keep the normal cycle.", GREEN),
             ("WATCH", "40 to 69", "One parameter is drifting. Plan a clean.", AMBER),
             ("ATTENTION", "below 40", "Clean now, then check the source water.", RED)]
    for i, (word, rng, text, color) in enumerate(bands):
        y = 2.28 + i * 1.18
        chip = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(6.9),
                                      Inches(y), Inches(1.75), Inches(0.44))
        chip.adjustments[0] = 0.3
        chip.fill.solid()
        chip.fill.fore_color.rgb = color
        chip.line.fill.background()
        chip.shadow.inherit = False
        write(chip.text_frame, [{"text": word, "size": 11.5, "bold": True,
                                 "color": WHITE, "align": PP_ALIGN.CENTER}])
        chip.text_frame.vertical_anchor = MSO_ANCHOR.MIDDLE

        tb = tbox(slide, 8.85, y - 0.02, 3.8, 1.0)
        write(tb.text_frame, [
            {"text": "Score " + rng, "size": 13, "bold": True, "color": NAVY_P,
             "space_after": 3},
            {"text": text, "size": 12, "color": INK},
        ])


def arm_panel(slide):
    cx, cy, r_tank = 3.2, 3.95, 1.9
    scale = r_tank / 50.0

    tank = slide.shapes.add_shape(MSO_SHAPE.OVAL, Inches(cx - r_tank),
                                  Inches(cy - r_tank), Inches(2 * r_tank),
                                  Inches(2 * r_tank))
    tank.fill.background()
    tank.line.color.rgb = PRGB(0xB7, 0xC3, 0xD3)
    tank.line.width = PPt(1.6)
    tank.shadow.inherit = False

    for radius_cm in (8.0, 23.7, 39.4):
        r = radius_cm * scale
        ring = slide.shapes.add_shape(MSO_SHAPE.OVAL, Inches(cx - r), Inches(cy - r),
                                      Inches(2 * r), Inches(2 * r))
        ring.fill.background()
        ring.line.color.rgb = BLUE_P
        ring.line.width = PPt(1.1)
        ring.line.dash_style = MSO_LINE.DASH
        ring.shadow.inherit = False

    import math
    ang = math.radians(58)
    bx = cx + 39.4 * scale * math.cos(ang)
    by = cy - 39.4 * scale * math.sin(ang)

    arm = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(cx), Inches(cy),
                                     Inches(bx), Inches(by))
    arm.line.color.rgb = NAVY_P
    arm.line.width = PPt(2.6)

    brush_r = 8.0 * scale
    brush = slide.shapes.add_shape(MSO_SHAPE.OVAL, Inches(bx - brush_r),
                                   Inches(by - brush_r), Inches(2 * brush_r),
                                   Inches(2 * brush_r))
    brush.fill.solid()
    brush.fill.fore_color.rgb = PRGB(0x9D, 0xC3, 0xE6)
    brush.line.color.rgb = BLUE_P
    brush.line.width = PPt(1.2)
    brush.shadow.inherit = False

    hub = slide.shapes.add_shape(MSO_SHAPE.OVAL, Inches(cx - 0.09), Inches(cy - 0.09),
                                 Inches(0.18), Inches(0.18))
    hub.fill.solid()
    hub.fill.fore_color.rgb = NAVY_P
    hub.line.fill.background()
    hub.shadow.inherit = False


SLIDE_TEXT = {
    2: ("A tank degrades quietly, and the owner finds out weeks later.", [
        ("Inside the tank", [
            "Chlorine residual falls to zero within 24 to 48 hours of filling.",
            "Suspended solids settle into a sludge layer on the floor.",
            "Biofilm forms on the walls, and algae grow faster in warm water.",
        ]),
        ("What the owner sees", [
            "Cleaning happens on a calendar, usually once or twice a year.",
            "Safety is judged by smell, colour and taste.",
            "Nothing records how the water changed since the last clean.",
        ]),
    ], "By the time the problem is visible, the water has been unsafe for weeks."),

    3: ("The two available options each solve half of the problem.", [
        ("Monitor only", [
            "Sensors report turbidity and TDS and stop there.",
            "The sludge layer keeps feeding the reading, so the warning repeats.",
        ]),
        ("Drain and scrub", [
            "A full drain discards the stored water.",
            "It needs labour and a shutdown, and leaves the tank empty for hours.",
        ]),
        ("No record", [
            "Neither option measures the water before and after the clean.",
            "The owner cannot tell whether the work helped.",
        ]),
    ], "Schools, hospitals and apartment buildings clean the largest volumes on the loosest schedule."),

    4: ("Three units on one local network, with no cloud service and no account.", [
        ("M1  Tank monitor", [
            "ESP8266 on the tank lid.",
            "Five submerged probes read through a 16-bit ADC.",
            "Computes the score and serves the dashboard from its own flash.",
        ]),
        ("H1  Home unit", [
            "ESP8266 beside the pump switch.",
            "1.8 inch colour display for the score and the four readings.",
            "Isolated relay and contactor, with automatic and manual pump control.",
        ]),
        ("C1  Cleaning arm", [
            "ESP32 controller.",
            "Two 20 cm links, a ring brush and a suction head.",
            "Runs a planned path over the floor and keeps the water in the tank.",
        ]),
    ], "The dashboard is served by the tank unit itself, so it keeps working when the internet does not."),

    7: ("The monitor, the dashboard and the planner already run.", [
        ("M1 firmware", [
            "Compiles for the ESP8266.",
            "The React dashboard is stored in flash and served by the device.",
        ]),
        ("Dashboard", [
            "Built and live.",
            "Score panel, trend charts, session log and device table.",
        ]),
        ("C1 controller", [
            "Compiles for the ESP32.",
            "Burst control, pump relay, interlocks and a JSON API.",
        ]),
        ("Path planner", [
            "Solves the reachable workspace and exports the plan.",
            "Generates the header the controller compiles against.",
        ]),
    ], "What remains is the arm hardware, the home unit build and twelve months of field validation."),

    8: ("The value is in joining the four parts.", [
        ("One local system", [
            "Score, pump and cleaning share one network and one dashboard.",
            "No cloud service, account or subscription.",
        ]),
        ("Cleaning without a drain", [
            "The arm removes the sludge layer and leaves the stored water in place.",
            "A full drain is avoided on every cycle.",
        ]),
        ("A measured result", [
            "Each cycle records the water before and after the clean.",
            "The owner sees whether it worked.",
        ]),
        ("Reproducible", [
            "Firmware, planner and dashboard are versioned together.",
            "The coverage limit is published with the design.",
        ]),
    ], "The closest alternatives cover one part each: a monitor, a cleaning service or a pump controller."),

    10: ("The buyer is the owner who pays for cleaning today.", [
        ("Water saved", [
            "A cycle uses the water already in the tank.",
            "A full drain discards the whole stored volume.",
        ]),
        ("Pump protection", [
            "Level-based control stops the pump running dry.",
            "The manual override releases safely after ten minutes.",
        ]),
        ("Early warning", [
            "A falling score shows degradation before smell or taste.",
            "The clean is planned instead of forced.",
        ]),
        ("Who buys", [
            "Homes, apartment buildings, schools, hospitals and small industry.",
            "Sold through the cleaning contractors who already visit these sites.",
        ]),
    ], "Each cycle reports turbidity reduction, sediment reduction, score change and estimated mass removed."),

    12: ("Funding status, and what the grant pays for.", [
        ("Requested", [
            "INR 23,587 over twelve months.",
            "Equipment is INR 15,600 of that total.",
        ]),
        ("Released in tranches", [
            "8,235 at T0, 9,415 at T0 + 6 months, 5,937 at T0 + 12 months.",
            "80 percent of each tranche is spent before the next is claimed.",
        ]),
        ("Industry partner", [
            "Nuke Labs provides build facilities, field access and validation.",
            "The partner also carries the commercialisation path.",
        ]),
        ("Status", [
            "No funding secured yet.",
            "This proposal is the first formal request.",
        ]),
    ], "The grant covers the monitor, the home unit, the cleaning arm and the field evidence pack."),
}


def build_pptx():
    path = os.path.join(OUT, "TankGuard_Presentation.pptx")
    shutil.copyfile(PPTX_SRC, path)
    prs = Presentation(path)
    slides = list(prs.slides)

    for idx in range(2, 14):
        if idx - 1 >= len(slides):
            continue
        slide = slides[idx - 1]
        label = relabel(slide, LABEL_TEXT[idx])
        clear_body(slide, label)

        if idx in SLIDE_TEXT:
            head, cards, foot = SLIDE_TEXT[idx]
            headline(slide, head)
            n = len(cards)
            if n == 2:
                geo = [(0.72, 2.35, 5.78, 2.9), (6.83, 2.35, 5.78, 2.9)]
                band(slide, 5.58, foot)
            elif n == 3:
                geo = [(0.72, 2.35, 3.85, 2.9), (4.76, 2.35, 3.85, 2.9),
                       (8.8, 2.35, 3.85, 2.9)]
                band(slide, 5.58, foot)
            else:
                geo = [(0.72, 2.32, 5.78, 1.62), (6.83, 2.32, 5.78, 1.62),
                       (0.72, 4.09, 5.78, 1.62), (6.83, 4.09, 5.78, 1.62)]
                band(slide, 5.95, foot, h=0.78)
            for (x, y, w, h), (title, lines) in zip(geo, cards):
                card(slide, x, y, w, h, title, lines,
                     body_size=13.5 if n < 4 else 13)

        elif idx == 5:
            headline(slide, "Five readings become one number between 0 and 100.")
            score_panel(slide)
            band(slide, 5.62, "The same bands drive the tank display and the dashboard, "
                              "so the two never disagree.")

        elif idx == 6:
            headline(slide, "The arm cleans the floor and the tank keeps its water.")
            arm_panel(slide)
            tb = tbox(slide, 6.55, 2.12, 6.1, 3.9)
            write(tb.text_frame, [
                {"text": "Two rigid links of 20 cm, jointed at the elbow and driven "
                         "independently, with one ring brush at the tip.",
                 "size": 13.5, "space_after": 12, "line_spacing": 1.05},
                {"text": "Three concentric passes cover 90 percent of the floor in about "
                         "44 seconds at 45 degrees per second.",
                 "size": 13.5, "space_after": 12, "line_spacing": 1.05},
                {"text": "The brush loosens the sludge and the pump draws it out through "
                         "the open centre of the head.",
                 "size": 13.5, "space_after": 12, "line_spacing": 1.05},
                {"text": "The arm parks in a fixed pose at the start and the end of each "
                         "cycle, so the hose and wires never wind up.",
                 "size": 13.5, "space_after": 12, "line_spacing": 1.05},
                {"text": "A 2 cm ring at the wall stays out of reach, and the design "
                         "record states it.",
                 "size": 13.5, "line_spacing": 1.05},
            ])
            band(slide, 6.02, "Floor plan to scale, with passes at 8.0, 23.7 and 39.4 cm. "
                              "Coverage uses the reachable workspace, the brush radius and "
                              "a 0.3 cm overlap.", h=0.78, size=12.5)

        elif idx == 9:
            headline(slide, "Four gates in twelve months, each one a demonstration.")
            lead = tbox(slide, 0.72, 2.02, 11.9, 0.4)
            write(lead.text_frame, [{"text": "Every gate produces something that can be "
                                             "shown and measured.", "size": 13.5,
                                     "color": GREY}])
            add_table(slide, 0.72, 2.58, [0.8, 4.1, 2.1, 4.9],
                      ["No.", "Milestone", "Period", "Delivered at the gate"],
                      [("1", "Requirements and monitor prototype", "T0 + 2 months",
                        "M1 calibrated, score validated, dashboard served from flash"),
                       ("2", "Home unit and dashboard", "T0 + 4 months",
                        "H1 pump control, session log and device table complete"),
                       ("3", "Cleaning arm", "T0 + 8 months",
                        "C1 built, three-ring cycle run, coverage measured"),
                       ("4", "Field validation", "T0 + 12 months",
                        "Three sites, 90 days of data, TRL 6 evidence pack")],
                      row_h=0.68, align=[True, False, False, False])
            band(slide, 6.05, "The field phase closes with a published measurement of score "
                              "accuracy, cleaning coverage and water saved against a full "
                              "drain.", h=0.78, size=12.5)

        elif idx == 11:
            headline(slide, "Indicative equipment cost is INR 15,600.")
            lead = tbox(slide, 0.72, 2.02, 11.9, 0.4)
            write(lead.text_frame, [{"text": "The grand total of INR 23,587 adds "
                                             "contingency, overhead and the faculty fee.",
                                     "size": 13.5, "color": GREY}])
            add_table(slide, 1.55, 2.62, [2.7, 4.1, 1.7, 1.6],
                      ["Item", "Specification", "Amount (INR)", "Phase"],
                      [("M1 monitor", "ESP8266, 5 probes, solar", "6,500", "T0"),
                       ("H1 home unit", "ESP8266, 1.8 inch display, relay", "1,800", "T0 + 4"),
                       ("C1 cleaning arm", "ESP32, 2 gearmotors, pump", "7,300", "T0 + 8"),
                       ("Equipment total", "", "15,600", ""),
                       ("Grand total", "with contingency, overhead and fee", "23,587", "")],
                      row_h=0.56, align=[False, False, True, False],
                      bold_rows=(4, 5))
            band(slide, 5.95, "Figures are vendor quotes pending confirmation. Manpower, "
                              "travel and consumables are agreed at the grant kickoff.",
                 h=0.78, size=12.5)

        elif idx == 13:
            headline(slide, "One team, twelve months, a working system at TRL 6.")
            card(slide, 0.72, 2.32, 5.78, 2.6, "The team", [
                "Principal Investigator: Dr. Vishnu Vasudev, Department of Electronics "
                "and Communication Engineering.",
                "Industry partner: Nuke Labs, for hardware build, field installations "
                "and commercialisation.",
            ], body_size=13)
            card(slide, 6.83, 2.32, 5.78, 2.6, "What the grant delivers", [
                "M1 and H1 running in the field, with the dashboard served by the tank unit.",
                "The C1 arm and its planner, with the coverage limit stated.",
                "Three installations and 90 days of evidence at TRL 6.",
            ], body_size=13)
            band(slide, 5.35, "TankGuard gives a tank owner a reading, a clean, and a "
                              "record of what changed.", h=0.9, size=16)

        footer(slide, idx)

    build_title(slides[0])

    prs.save(path)
    return path


if __name__ == "__main__":
    print(rebuild_docx())
    print(rebuild_xlsx())
    print(build_pptx())
