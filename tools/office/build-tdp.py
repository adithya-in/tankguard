"""Build the three TDP deliverables from the templates.

Copy rules: no em dashes, no "X, not Y" antithesis, no rhetorical fragments.
Every claim carries the number or the limit that backs it.

DOCX keeps the template's section (TIH header, footer, page fields) and rebuilds
the body. XLSX rebuilds both sheets as clean tables. PPTX keeps the template's
label boxes, logo and divider, and rebuilds the content as headline plus cards.
"""
import os
import shutil
import time

from docx import Document
from docx.enum.table import WD_ALIGN_VERTICAL, WD_TABLE_ALIGNMENT
from docx.enum.text import (WD_ALIGN_PARAGRAPH, WD_BREAK, WD_TAB_ALIGNMENT,
                            WD_TAB_LEADER)
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor
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
INST = "Sree Buddha College of Engineering"
DEPT = "Department of Electronics and Communication Engineering"
AFFIL = INST + ", " + DEPT
PARTNER = "Nuke Labs (industry partner)"
PROGRAM = "TIH IoT Technology Development Program 2026"
THEME = "Water Management"
ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
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

    "The monitoring prototype is built. The M1 firmware, the dashboard and the path "
    "planner run, and INR 23,587 of parts have already been invested. The grant funds "
    "the step from that prototype to a certified product: the arm hardware, twenty-five "
    "pilot units, certification and twelve field installations.",

    "The project delivers a production revision of M1 and H1, twenty-five pilot units of "
    "the C1 cleaning arm, twelve field installations, certification, "
    "and three paying pilot customers. The arm has already reached TRL 7: both joints "
    "ran in a real 500 L tank. The project takes the integrated system to TRL 8, with "
    "the unit cost and the service model proven before the first production run.",
]

COMMERCIAL = [
    "The buyer is the contractor or facility manager who already pays for cleaning. "
    "A household buys a clean, not a device, so the arm is sold to the contractor who "
    "visits the tank, and the monitor is sold to the institution that wants a reading "
    "between cleans.",

    "Price targets: INR 39,999 for the complete system (M1, H1 and C1) against INR "
    "15,600 of parts, a gross margin near 61 percent. The monitor and home unit alone "
    "sell at INR 16,999 for sites that do not need the arm.",

    "Market base: 79 million urban households in the 2011 Census, of which about 60 "
    "percent are assumed to store water in a tank (47 million), plus 1.5 million "
    "schools and 70,000 hospitals. A tank clean sells for INR 1,500 to 4,000 in urban "
    "India, once or twice a year.",

    "Route to revenue: three paying pilot sites in the grant year, converted to "
    "reference accounts; two channel partners in the following year, one in cleaning "
    "services and one in plumbing distribution; a target of 250 units in the first "
    "full year of sale.",

    "The grant pays for the pilot line and the pilot units. Certification is carried "
    "by Nuke Labs, which also holds the channel and the service network.",
]

HISTORY = [
    "Household and building tank monitoring is well covered. Singh et al. (2021) "
    "monitored level and pH in a building tank over 2.4 GHz radio with a cloud "
    "dashboard. Rayni et al. (2023) added turbidity and TDS on an ESP32 and displayed "
    "them in Blynk. Irawan et al. (2024) reported a household unit with pH, TDS, "
    "turbidity and temperature, and Nugraha (2026) added a 16-bit ADS1115 front end "
    "with rule-based classification. Each ends at the reading: the owner is told the "
    "water is bad and must arrange the clean.",
    "Cleaning has been studied separately. Megalingam et al. (2022) simulated a robot "
    "that cleans tank floors and walls in Gazebo under ROS, and wall-climbing cleaners "
    "are sold for large tanks. Neither is a selective floor cleaner that leaves the "
    "stored water in place, and neither reports how much of the floor it covered.",
    "TankGuard began as a monitor in that first group. Field trials showed the gap: a "
    "reading does not remove the sludge that keeps producing it. The design moved to a "
    "planned arm that cleans the floor without a drain, driven by the same score.",
]

GAP = (
    "Previous work either measures the water or cleans the tank. Monitoring systems "
    "(Singh 2021; Rayni 2023; Irawan 2024) stop at the reading and leave the clean to "
    "the owner. Cleaning robots (Megalingam 2022) are simulated or built for large "
    "walls, and none reports floor coverage or keeps the stored water. TankGuard closes "
    "the loop: one local score decides when to clean, a planned arm cleans 90 percent "
    "of the floor without draining, and the same score reports whether the clean worked."
)

PROBLEM = [
    "Storage tanks degrade silently. Residual chlorine disappears within 24 to 48 "
    "hours, suspended solids settle into a sludge layer, biofilm forms on internal "
    "surfaces, and algae grow in warm water. By the time it is visible, the water is "
    "already unsafe.",
    "Current options either monitor without acting or clean by draining the whole "
    "tank. Monitoring tells the owner there is a problem and leaves the work to "
    "them. A full drain wastes the stored water and needs manual labour.",
    "The gap is largest where it matters most: schools, hospitals and apartment "
    "blocks store large volumes, clean to a fixed calendar, and cannot tell whether "
    "the last clean helped.",
]

OBJECTIVES = [
    GAP,
    "Objective 1: measure and score water quality at the edge. Five probes "
    "(turbidity, TDS, pH, temperature, level) are digitised through an ADS1115 and "
    "fused into a weighted score (40/25/25/10). Acceptance: the score repeats within "
    "2 points over ten consecutive samples in still water.",
    "Objective 2: make the result readable without a phone. H1 shows the score, "
    "level, the four readings, pump state and link health on a 1.8 inch display. It "
    "controls the pump in automatic mode (on below the low-level setpoint, off above "
    "the high) with a manual override that releases safely.",
    "Objective 3: clean the tank floor without draining it. C1 sweeps three "
    "concentric rings at 8.0, 23.7 and 39.4 cm with a 16 cm ring brush and a central "
    "suction intake, covering 90 percent of the floor per cycle, and parks in a "
    "fixed rest pose at both ends of the cycle.",
    "Objective 4: prove it in the field and take it to market. The arm has reached TRL 7 "
    "in a real 500 L tank; the monitor is at TRL 6. Twelve months later the integrated "
    "system is at TRL 8, with twenty-five pilot units, twelve installations, "
    "certification and three paying customers.",
]

DELIVERABLES = [
    "D1. M1 monitor, production revision: the ESP8266 board with five calibrated "
    "probes, an edge score, the dashboard in flash, and an enclosure that can be "
    "moulded at volume.",
    "D2. H1 home unit, production revision: the display board, isolated relay and "
    "contactor interface, and a manual override that passes electrical safety review.",
    "D3. C1 cleaning arm, pilot build: twenty-five units with the two-link arm, ring brush, "
    "suction head and the planner-generated path, at a confirmed unit cost.",
    "D4. Commercial pack: twelve installations, certification filed, three "
    "paying pilot customers, a channel agreement, and the TRL 8 evidence set.",
]

MILESTONES = [
    ("1", "Design freeze and line procurement", "T0 + 3 months",
     "Moulder, moulds, printer, PnP and reflow installed. Arm and enclosure frozen. "
     "Certification scope agreed with the test laboratory."),
    ("2", "Pilot build and lab qualification", "T0 + 6 months",
     "Twenty-five pilot sets built in-house and calibrated against reference "
     "instruments. IP68 and EMC pre-compliance passed. Unit cost confirmed."),
    ("3", "Field deployment", "T0 + 9 months",
     "Twelve installations in three cities with sixty days of continuous operation. "
     "Installation manual and service workflow complete."),
    ("4", "Commercial readiness", "T0 + 12 months",
     "Certification filed, three paying pilot customers, channel "
     "agreement signed, TRL 8 evidence pack."),
]

EQUIPMENT_ROWS = [
    ("Used 100 T injection moulder", "4,50,000"),
    ("Three moulds (toolroom)", "3,50,000"),
    ("Chiller, dryer, granulator", "2,00,000"),
    ("Semi-auto stencil printer", "2,50,000"),
    ("Two-head vision pick-and-place", "3,10,000"),
    ("Six-zone reflow oven", "2,16,500"),
    ("Rework station", "20,000"),
    ("Stencils", "10,000"),
    ("Four ESD benches", "1,16,000"),
    ("Soldering stations and microscope", "48,000"),
    ("Oscilloscope, PSU, DMM", "27,000"),
    ("Functional-test fixtures", "1,50,000"),
    ("Calibration", "40,000"),
    ("Hand tools, crimpers, bench consumables", "39,788"),
    ("Electrical, air, fume, fire", "1,20,000"),
    ("Freight and installation", "80,000"),
    ("Equipment total", "24,27,288"),
]

BUDGET_ROWS = [
    ("Manpower", "7,20,000"),
    ("Equipment", "24,27,288"),
    ("Consumables", "3,40,000"),
    ("Travel", "1,00,000"),
    ("Miscellaneous", "17,966"),
    ("Contingency (max 5%)", "1,80,263"),
    ("Sub total", "37,85,517"),
    ("Overhead (max 20%)", "0"),
    ("Faculty fee", "2,00,000"),
    ("Total (7+8+9)", "39,85,517"),
    ("GST (18%)", "7,17,393"),
    ("Grand total (inclusive of GST)", "47,02,910"),
]

BUDGET_NOTE = [
    "Equipment is the pilot line, itemised in the appendix: moulder, moulds, stencil "
    "printer, pick-and-place, reflow, fixtures and bench. Manpower covers two engineers "
    "at Nuke Labs for twelve months. Consumables cover twenty-five pilot sets and PCB "
    "fabrication.",
    "Travel covers twelve field installations. Miscellaneous covers market work and "
    "small items; certification is carried by Nuke Labs. "
    "Contingency is 5 percent of direct cost, no overhead is claimed, and GST at 18 "
    "percent is shown on the total. Prototype parts to date total INR 23,587, already "
    "invested and not part of this request.",
]

TRANCHE_ROWS = [
    ("Project start (T0)", "25,66,222",
     "Line procurement, tooling and design freeze"),
    ("T0 + 6 months", "16,23,623",
     "Pilot build, certification testing and field deployment"),
    ("T0 + 12 months", "5,13,065",
     "Validation close-out, certification and commercial launch"),
    ("Total", "47,02,910", ""),
]

SUPPORT = [
    "TankGuard Technical Specification, document TG-SPEC-2026-001, October 2026, "
    "7 pages.",
    "Firmware for all three units, compiling for ESP8266 (M1, H1 and C1), with the "
    "React dashboard served from M1 flash.",
    "Design record (docs/CLEANER.md): kinematics, coverage analysis and control "
    "limits, including the 2 cm wall ring the arm cannot reach.",
    "Coverage planner (tools/swept_area.html) and the generated path used by the "
    "controller (firmware/c1_cleaner/path.h).",
    "TRL 7 evidence note (TG-TRL-2026-001), October 2026, covering the 500 L tank test.",
    "Patentability disclosure (prior-art record, no filing claimed) and the minimum "
    "bill of materials.",
    "Prototype spend to date: INR 23,587 in parts, with the monitor running at TRL 6.",
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


def copy_template(src, dst, tries=12):
    """Copy over a template, retrying while Office still holds the destination."""
    for attempt in range(tries):
        try:
            shutil.copyfile(src, dst)
            return
        except PermissionError:
            if attempt == tries - 1:
                raise
            time.sleep(1.5)


def no_borders(t):
    tblPr = t._tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), "nil")
        borders.append(el)
    tblPr.append(borders)


def cover_band(sec):
    fp = sec.first_page_footer
    p = fp.paragraphs[0].insert_paragraph_before()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(0)
    p.add_run().add_picture(os.path.join(ASSETS, "cover_band.png"),
                            width=Inches(6.5))


def save_retry(save_fn, tries=12):
    """Save over a file that Office may still hold open."""
    for attempt in range(tries):
        try:
            save_fn()
            return
        except PermissionError:
            if attempt == tries - 1:
                raise
            time.sleep(1.5)


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
    para(doc, PROGRAM, 15, True, BLUE, WD_ALIGN_PARAGRAPH.CENTER, 18)
    para(doc, TITLE, 16, True, BLUE, WD_ALIGN_PARAGRAPH.CENTER, 16)
    para(doc, "Submitted by", 11, False, None, WD_ALIGN_PARAGRAPH.CENTER, 2)
    para(doc, PI, 14, True, BLUE, WD_ALIGN_PARAGRAPH.CENTER, 2)
    para(doc, INST, 11, False, None, WD_ALIGN_PARAGRAPH.CENTER, 2)
    para(doc, "Industry partner: Nuke Labs", 11, False, None, WD_ALIGN_PARAGRAPH.CENTER, 10)
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
        ("     3.8  Commercialisation plan", "6"),
        ("4  Appendix", "6"),
        ("     4.1  Supporting documentation", "6"),
        ("     4.2  Equipment breakdown", "7"),
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
    para(doc, "Twelve months from T0, with a deliverable at every gate.")
    table(doc, ["#", "Milestone", "Period", "Delivered at the gate"],
          MILESTONES, widths=[Pt(24), Pt(150), Pt(70), Pt(210)])

    heading(doc, "3.6  Resources and budget", 2)
    table(doc, ["Item", "Amount (INR)"], BUDGET_ROWS,
          widths=[Pt(300), Pt(154)], right_cols=(1,))
    for t in BUDGET_NOTE:
        para(doc, t, 9.5, space_after=4)

    cap = para(doc, "Tranche disbursement schedule", 12.5, True, MID_BLUE,
               space_after=6)
    cap.paragraph_format.space_before = Pt(14)
    cap.paragraph_format.keep_with_next = True
    table(doc, ["Timeline", "Amount (INR, incl. GST)", "Milestone covered"],
          TRANCHE_ROWS, widths=[Pt(120), Pt(120), Pt(214)], right_cols=(1,))

    heading(doc, "3.7  Category of new technology/product", 2)
    para(doc, CATEGORY)

    heading(doc, "3.8  Commercialisation plan", 2)
    for t in COMMERCIAL:
        para(doc, t)

    # ---- 4 appendix -------------------------------------------------------
    heading(doc, "4  Appendix", 1)
    heading(doc, "4.1  Supporting documentation", 2)
    for t in SUPPORT:
        p = para(doc, t)
        p.paragraph_format.left_indent = Pt(14)
        p.paragraph_format.space_after = Pt(4)

    heading(doc, "4.2  Equipment breakdown", 2)
    para(doc, "Pilot line, exclusive of GST. Figures are vendor quotes and negotiated "
              "targets at the time of writing.", 10)
    table(doc, ["Equipment item", "Amount (INR)"], EQUIPMENT_ROWS,
          widths=[Pt(330), Pt(124)], right_cols=(1,))

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
    cover_band(sec)
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
    doc.core_properties.subject = PROGRAM
    save_retry(lambda: doc.save(path))
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
    copy_template(XLSX_SRC, path)
    wb = load_workbook(path)

    # ---------------- sheet 1: summary ------------------------------------
    ms = wb["Milestones"]
    for rng in list(ms.merged_cells.ranges):
        ms.unmerge_cells(str(rng))
    wipe(ms, 40, 14)

    widths = {"A": 7, "B": 29, "C": 16, "D": 2.5, "E": 5.5, "F": 31,
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
    ms.row_dimensions[3].height = 40

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
        ("1", "Manpower", 720000), ("2", "Equipment", 2427288),
        ("3", "Consumables", 340000), ("4", "Travel", 100000),
        ("5", "Miscellaneous expenses", 17966), ("6", "Contingency (max 5%)", 180263),
        ("7", "Sub total", 3785517), ("8", "Overhead (max 20%)", 0),
        ("9", "Faculty fee", 200000), ("10", "Total (7+8+9)", 3985517),
        ("11", "GST (18%)", 717393), ("12", "Grand total (10+11)", 4702910),
    ]
    for i, (no, name, amt) in enumerate(budget):
        r = 4 + i
        ms[f"A{r}"] = int(no)
        ms[f"B{r}"] = name
        ms[f"C{r}"] = amt
        ms[f"C{r}"].number_format = "#,##,##0"
        ms[f"C{r}"].alignment = Alignment(horizontal="right", vertical="center")
        ms[f"A{r}"].alignment = Alignment(horizontal="center", vertical="center")

    # milestones block
    miles = [
        ("1", "Milestone 1: Design freeze and line procurement", "T0 + 3 months", "Line installed, design frozen"),
        ("2", "Milestone 2: Pilot build and lab qualification", "T0 + 6 months", "25 sets, IP68 and EMC passed"),
        ("3", "Milestone 3: Field deployment", "T0 + 9 months", "12 sites, 60 days of operation"),
        ("4", "Milestone 4: Commercial readiness", "T0 + 12 months", "3 paying pilots, TRL 8 pack"),
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
        ("Project start (T0)", 2566222, "Line procurement, tooling, design freeze"),
        ("T0 + 6 months", 1623623, "Pilot build, certification, field deployment"),
        ("T0 + 12 months", 513065, "Validation, certification, commercial launch"),
        ("Total", 4702910, ""),
    ]
    for i, (when, amt, what) in enumerate(tranche):
        r = 4 + i
        ms[f"J{r}"] = when
        ms[f"K{r}"] = amt
        ms[f"K{r}"].number_format = "#,##,##0"
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
    b.column_dimensions["C"].width = 40
    for col in ("D", "E", "F", "G"):
        b.column_dimensions[col].width = 17

    b.merge_cells("B2:G2")
    b["B2"] = "Milestone Expenditure Sheet"
    b["B2"].font = Font(name="Calibri", size=13, bold=True, color=NAVY)
    b["B2"].alignment = Alignment(vertical="center")
    b.row_dimensions[2].height = 24

    b.merge_cells("B3:G3")
    b["B3"] = "Grant total: INR 42,31,200"
    b["B3"].font = Font(name="Calibri", size=11, bold=True, color=STEEL)
    b["B3"].alignment = Alignment(horizontal="right", vertical="center")

    for coord, text in (("B4", "Sr. No."), ("C4", "Expenditure heads"),
                        ("D4", "Tranche 1 (T0)"), ("E4", "Tranche 2 (T0 + 6)"),
                        ("F4", "Tranche 3 (T0 + 12)"), ("G4", "Total (INR)")):
        b[coord] = text

    heads2 = [
        ("1", "Manpower", 240000, 240000, 240000),
        ("2", "Equipment", 1600000, 827288, 0),
        ("3", "Consumables", 100000, 140000, 100000),
        ("4", "Travel", 30000, 40000, 30000),
        ("5", "Miscellaneous expenses", 5966, 6000, 6000),
        ("6", "Contingency (max 5%)", 98798, 62664, 18801),
        ("7", "Sub total", 2074764, 1315952, 394801),
        ("8", "Overhead (max 20%)", 0, 0, 0),
        ("9", "Faculty fee", 100000, 60000, 40000),
        ("10", "Total (7+8+9)", 2174764, 1375952, 434801),
        ("11", "GST (18%)", 391458, 247671, 78264),
        ("12", "Grand total (10+11)", 2566222, 1623623, 513065),
    ]
    for i, (no, name, t1, t2, t3) in enumerate(heads2):
        r = 5 + i
        b[f"B{r}"] = int(no)
        b[f"C{r}"] = name
        for col, val in (("D", t1), ("E", t2), ("F", t3)):
            b[f"{col}{r}"] = val
            b[f"{col}{r}"].number_format = "#,##,##0"
        b[f"G{r}"] = t1 + t2 + t3
        b[f"G{r}"].number_format = "#,##,##0"

    style_block(b, 4, 2, 16, 7)
    for r in range(5, 17):
        b.row_dimensions[r].height = 22
        b[f"B{r}"].alignment = Alignment(horizontal="center", vertical="center")
        for col in ("D", "E", "F", "G"):
            b[f"{col}{r}"].alignment = Alignment(horizontal="right", vertical="center")
    for r in (11, 14, 16):
        for c in range(2, 8):
            b.cell(row=r, column=c).font = Font(name="Calibri", size=10, bold=True)

    b.merge_cells("B18:G18")
    b["B18"] = ("80 percent of each tranche is spent before the next is claimed. "
                "GST at 18 percent is shown on the total. Prototype parts to date "
                "(INR 23,587) were invested before T0 and are not part of this request.")
    b["B18"].font = Font(name="Calibri", size=9, italic=True, color="404040")
    b["B18"].alignment = Alignment(vertical="center", wrap_text=True)
    b.row_dimensions[18].height = 30

    b.print_area = "B2:G18"
    b.page_setup.orientation = "landscape"
    b.page_setup.paperSize = 9
    b.page_setup.fitToWidth = 1
    b.page_setup.fitToHeight = 1
    b.sheet_properties.pageSetUpPr.fitToPage = True
    b.print_options.horizontalCentered = True
    b.print_options.verticalCentered = True
    b.page_margins.left = b.page_margins.right = 0.5
    b.page_margins.top = b.page_margins.bottom = 0.5

    # ---------------- sheet 3: equipment ----------------------------------
    eq = wb.create_sheet("Equipment")
    eq.column_dimensions["B"].width = 6
    eq.column_dimensions["C"].width = 46
    eq.column_dimensions["D"].width = 18

    eq.merge_cells("B2:D2")
    eq["B2"] = "Equipment breakdown - pilot line"
    eq["B2"].font = Font(name="Calibri", size=13, bold=True, color=NAVY)
    eq["B2"].alignment = Alignment(vertical="center")
    eq.row_dimensions[2].height = 24

    eq.merge_cells("B3:D3")
    eq["B3"] = "Exclusive of GST. Vendor quotes and negotiated targets."
    eq["B3"].font = Font(name="Calibri", size=10, italic=True, color="404040")
    eq["B3"].alignment = Alignment(vertical="center")

    for coord, text in (("B4", "Sr. No."), ("C4", "Item"), ("D4", "Amount (INR)")):
        eq[coord] = text

    for i, (name, amount) in enumerate(EQUIPMENT_ROWS):
        r = 5 + i
        eq[f"B{r}"] = i + 1
        eq[f"C{r}"] = name
        eq[f"D{r}"] = int(amount.replace(",", ""))
        eq[f"D{r}"].number_format = "#,##,##0"

    style_block(eq, 4, 2, 4 + len(EQUIPMENT_ROWS), 4)
    for r in range(5, 5 + len(EQUIPMENT_ROWS)):
        eq.row_dimensions[r].height = 20
        eq[f"B{r}"].alignment = Alignment(horizontal="center", vertical="center")
        eq[f"D{r}"].alignment = Alignment(horizontal="right", vertical="center")
    last = 4 + len(EQUIPMENT_ROWS)
    for c in range(2, 5):
        eq.cell(row=last, column=c).font = Font(name="Calibri", size=10, bold=True)

    eq.print_area = f"B2:D{last}"
    eq.page_setup.paperSize = 9
    eq.page_setup.fitToWidth = 1
    eq.page_setup.fitToHeight = 0
    eq.sheet_properties.pageSetUpPr.fitToPage = True
    eq.print_options.horizontalCentered = True

    save_retry(lambda: wb.save(path))
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
        {"text": "Dr. Vishnu Vasudev, Sree Buddha College of Engineering",
         "size": 15, "bold": True, "color": BLUE_P, "align": PP_ALIGN.CENTER,
         "space_after": 4},
        {"text": "Industry partner: Nuke Labs", "size": 14, "color": GREY,
         "align": PP_ALIGN.CENTER, "space_after": 12},
        {"text": PROGRAM, "size": 13, "color": GREY, "align": PP_ALIGN.CENTER,
         "space_after": 4},
        {"text": "Theme: " + THEME + "   |   Submission: " + DATE, "size": 13,
         "color": GREY, "align": PP_ALIGN.CENTER},
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

    7: ("The monitor runs at TRL 6. The arm has run in a real tank at TRL 7.", [
        ("M1 firmware", [
            "Compiles for the ESP8266.",
            "The React dashboard is stored in flash and served by the device.",
        ]),
        ("Dashboard", [
            "Built and live.",
            "Score panel, trend charts, session log and device table.",
        ]),
        ("C1 controller", [
            "Compiles for the ESP8266.",
            "Burst control, pump relay, interlocks and a JSON API.",
        ]),
        ("Path planner", [
            "Solves the reachable workspace and exports the plan.",
            "Generates the header the controller compiles against.",
        ]),
    ], "INR 23,587 invested. Both joints ran in a 500 L tank in October 2026; the grant "
       "builds the line and the pilot units."),

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

    10: ("The buyer is the contractor who already charges for the clean.", [
        ("Who buys", [
            "Cleaning contractors and facility managers first.",
            "Households reach the product through them.",
        ]),
        ("Price target", [
            "INR 39,999 for M1, H1 and C1.",
            "Against INR 15,600 of parts, a 61 percent margin.",
        ]),
        ("Market base", [
            "About 47 million urban tanks.",
            "Plus 1.5 million schools and 70,000 hospitals.",
        ]),
        ("Water saved", [
            "A cycle uses the water already in the tank.",
            "A full drain discards the whole stored volume.",
        ]),
    ], "A tank clean sells for INR 1,500 to 4,000, so the arm is sold to whoever already charges for it."),

    12: ("INR 47.03 lakh builds the pilot line and the product.", [
        ("Requested", [
            "INR 47,02,910 over twelve months, GST included.",
            "That is 94 percent of the programme ceiling.",
        ]),
        ("Already invested", [
            "INR 23,587 of prototype parts.",
            "The arm has run in a 500 L tank; the monitor and planner run.",
        ]),
        ("Released in tranches", [
            "25.66 lakh at T0, 16.24 lakh at month 6, 5.13 lakh at month 12.",
            "80 percent of each tranche is spent before the next is claimed.",
        ]),
        ("Partner", [
            "Nuke Labs provides build facilities, field access and the service channel.",
            "The partner carries the commercialisation path.",
        ]),
    ], "The grant pays for the pilot line, the pilot units and two engineers, "
       "which a first customer will not fund."),
}


def build_pptx():
    path = os.path.join(OUT, "TankGuard_Presentation.pptx")
    copy_template(PPTX_SRC, path)
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
            headline(slide, "Four gates in twelve months, each one a commercial step.")
            lead = tbox(slide, 0.72, 2.02, 11.9, 0.4)
            write(lead.text_frame, [{"text": "The prototype is the starting point. Each gate "
                                             "moves it closer to a sellable unit.",
                                     "size": 13.5, "color": GREY}])
            add_table(slide, 0.72, 2.58, [0.8, 4.1, 2.1, 4.9],
                      ["No.", "Milestone", "Period", "Delivered at the gate"],
                      [("1", "Design freeze and line procurement", "T0 + 3 months",
                        "Line installed, design frozen, certification scope agreed"),
                       ("2", "Pilot build and lab qualification", "T0 + 6 months",
                        "25 sets, IP68 and EMC passed, unit cost confirmed"),
                       ("3", "Field deployment", "T0 + 9 months",
                        "12 sites in 3 cities, 60 days of operation"),
                       ("4", "Commercial readiness", "T0 + 12 months",
                        "Certification filed, 3 paying pilots, TRL 8")],
                      row_h=0.68, align=[True, False, False, False])
            band(slide, 6.05, "The last gate is a sale: three paying customers and a signed "
                              "channel agreement, with the unit cost proven.",
                 h=0.78, size=12.5)

        elif idx == 11:
            headline(slide, "The request is INR 47.03 lakh for twelve months.")
            lead = tbox(slide, 0.72, 2.02, 11.9, 0.4)
            write(lead.text_frame, [{"text": "The pilot line, two engineers, the pilot "
                                             "units and the field work. GST is on the total.",
                                     "size": 13.5, "color": GREY}])
            add_table(slide, 0.72, 2.45, [3.3, 2.3],
                      ["Cost head", "Amount (INR)"],
                      [("Equipment (pilot line)", "24,27,288"),
                       ("Manpower", "7,20,000"),
                       ("Consumables", "3,40,000"),
                       ("Travel and misc", "1,17,966"),
                       ("Contingency, faculty, GST", "10,97,656"),
                       ("Total", "47,02,910")],
                      row_h=0.5, align=[False, True], bold_rows=(6,))
            card(slide, 6.55, 2.45, 6.0, 3.4, "What the grant buys", [
                "The pilot line: moulder, moulds, printer, PnP, reflow.",
                "Two Nuke Labs engineers for twelve months.",
                "Twenty-five pilot sets and the test fixtures.",
                "Twelve field installations.",
            ], body_size=13)
            band(slide, 6.15, "Prototype spend to date is INR 23,587, already invested. "
                              "The request builds the line and the product.",
                 h=0.78, size=12.5)

        elif idx == 13:
            headline(slide, "A working arm in a real tank. A certified system in twelve months.")
            card(slide, 0.72, 2.32, 5.78, 2.6, "The team", [
                "Principal Investigator: Dr. Vishnu Vasudev, Sree Buddha College of "
                "Engineering, Department of Electronics and Communication Engineering.",
                "Industry partner: Nuke Labs, for hardware build, field access and the "
                "service channel.",
            ], body_size=12.5)
            card(slide, 6.83, 2.32, 5.78, 2.6, "What the grant delivers", [
                "Twenty-five pilot units and twelve installations in three cities.",
                "Certification filed, with the unit cost proven.",
                "Three paying pilot customers and a signed channel agreement.",
            ], body_size=12.5)
            band(slide, 5.35, "TankGuard gives a tank owner a reading, a clean, and a "
                              "record of what changed.", h=0.9, size=16)

        footer(slide, idx)

    build_title(slides[0])
    slides[0].shapes.add_picture(os.path.join(ASSETS, "iitb.png"),
                                 Inches(11.55), Inches(6.35), width=Inches(1.05))

    save_retry(lambda: prs.save(path))
    return path


if __name__ == "__main__":
    print(rebuild_docx())
    print(rebuild_xlsx())
    print(build_pptx())
