"""Rebuild the TDP deliverables properly.

DOCX: keep the template's section (TIH header, footer, page fields) but replace
the body with a clean, correctly ordered proposal — the previous fill left my
text under the wrong headings and kept the template's instruction paragraphs.

XLSX: keep the template's sheets, fix the budget labels and make the sheets fit
one page wide so the PDF/print view is not split.

PPTX: replace slide text *in place*, preserving each paragraph's formatting
(the earlier pass cleared text frames, which left the title slide left-aligned
and small).
"""
import os
import shutil

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor
from openpyxl import load_workbook
from openpyxl.styles import Alignment
from pptx import Presentation
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt as PPt

DL = r"C:\Users\DELL\Downloads"
OUT = r"C:\Users\DELL\tankguard-gh\docs\office"

DOCX_SRC = os.path.join(DL, "Project Proposal Format TDP .docx")
XLSX_SRC = os.path.join(DL, "Budget & Milestone TDP.xlsx")
PPTX_SRC = os.path.join(DL, "Presentation Template.pptx")

DATE = "31 October 2026"
TITLE = ("TankGuard — self-powered IoT water-tank monitoring, pump control "
         "and automated sludge cleaning")
PI = "Dr. Vishnu Vasudev"
AFFIL = "Nuke Labs — Industry Partner"
THEME = "TIH — IoT Technology Development Program 2026"
BLUE = RGBColor(0x1F, 0x4E, 0x79)

EXEC = [
    "TankGuard is a self-powered Internet of Things (IoT) system for domestic and "
    "institutional water storage tanks. It measures water quality in the tank, scores "
    "it, controls the household pump safely, and cleans the settled sludge layer with a "
    "small robotic arm — all on the local network, with no cloud, subscription or account.",

    "The system is three units on one local network. M1 sits on the tank lid and reads "
    "turbidity, TDS, pH, temperature and level through submerged probes, computes a "
    "weighted 0-100 TankScore at the edge, and serves the dashboard itself from its own "
    "flash. H1 sits next to the pump switch, shows the score on a 1.8-inch colour "
    "display, and drives the pump through an isolated relay and contactor with automatic "
    "level control and a manual override. C1 is the cleaning arm: a two-link 20 cm + "
    "20 cm mechanism that sweeps the tank floor in three concentric passes while a ring "
    "brush loosens the sludge and a submersible pump draws it out through the centre of "
    "the head.",

    "Water safety management still relies on manual sampling and calendar-based cleaning. "
    "Tanks degrade silently: disinfectant residual dissipates within 24-48 hours, "
    "particles settle into a sludge layer at the floor, biofilm forms on the walls, and "
    "algae bloom in warm water. By the time the water smells or looks wrong it is already "
    "unsafe, and the only remedy is a full drain and manual scrub that wastes the entire "
    "stored volume.",

    "TankGuard closes that loop at the edge: sense, score, act, and verify. The cleaning "
    "arm covers 90% of the tank floor per cycle; the remaining 7.8% is a 2 cm ring at the "
    "wall that the mechanism cannot reach, and the design record states it rather than "
    "hiding it. The dashboard reports what happened, not what the vendor wishes had "
    "happened.",

    "Deliverables: (1) a working TankGuard prototype (M1 + H1); (2) the cleaning arm C1 "
    "with its planner and controller; (3) the web dashboard, served by the tank unit "
    "itself; (4) validation at TRL 6+ with an industry partner, including field data from "
    "at least three installations.",
]

HISTORY = [
    "TankGuard began as an in-tank water-quality monitor: five probes, an edge-computed "
    "score, and a dashboard served by the device itself. The first build proved that a "
    "low-cost ESP8266 can carry the whole stack — sensing, scoring, a web UI and a local "
    "Wi-Fi link — without a cloud path.",
    "Field work exposed the real failure mode. Measurement alone does not fix a tank: the "
    "sludge layer at the floor keeps feeding turbidity and biofilm, and the household's "
    "only remedy is a full drain and manual scrub. The product therefore moved from "
    "monitoring to care: a home unit that runs the pump safely, and a cleaning arm that "
    "removes the sludge layer without emptying the tank.",
    "The current design keeps every earlier decision that still holds — the five probes, "
    "the TankScore weights, the local-only architecture — and replaces the abandoned "
    "drain-and-flush mechanism with the robotic cleaning arm described here.",
]

PROBLEM = [
    "Storage tanks degrade silently. Disinfectant residual dissipates within 24-48 hours "
    "of filling; suspended particles settle into a sludge layer at the floor; biofilm "
    "forms on internal surfaces; algae proliferate in warm conditions. By the time "
    "degradation is detected by smell, taste or sight, the water is already unsafe.",
    "Existing options either monitor without acting, or clean by draining and scrubbing "
    "the entire tank, which wastes the whole stored volume and needs manual labour. No "
    "affordable product closes the loop: measure, decide, clean selectively, and show "
    "whether the cleaning worked.",
    "The problem is worst where it matters most: schools, hospitals and apartment "
    "buildings store large volumes, clean on a calendar rather than on evidence, and have "
    "no way to tell whether the last cleaning actually helped.",
]

OBJECTIVES = [
    "Objective 1 — Measure and score water quality at the edge. Five probes (turbidity, "
    "TDS, pH, temperature, level) digitised through an ADS1115 and fused into a weighted "
    "TankScore (turbidity 40%, TDS 25%, pH 25%, temperature 10%), with the same bands the "
    "display and the dashboard use (>=70 good, >=40 watch, <40 needs attention). "
    "Acceptance: score repeatable within +/-2 points across ten consecutive samples in "
    "still water.",
    "Objective 2 — Make the result readable without a phone. H1 shows TankScore, level, "
    "the four readings, pump state and link health on a 1.8-inch TFT, and controls the "
    "pump in AUTO (on below the low-level setpoint, off above the high) with a manual "
    "override that times out safely.",
    "Objective 3 — Clean the tank floor without draining it. C1 sweeps three concentric "
    "rings at 8.0 / 23.7 / 39.4 cm with a 16 cm ring brush and a central suction intake, "
    "covering 90% of the floor per cycle, and parks in a defined rest pose at both ends "
    "of every cycle.",
    "Objective 4 — Prove it in the field. Twelve months to TRL 6+: three installations, "
    "90 days of continuous operation, and a published measurement of score accuracy, "
    "cleaning coverage and water saved against a full drain.",
]

DELIVERABLES = [
    "D1 — M1 monitor: ESP8266 unit on the tank lid with five calibrated probes, edge "
    "TankScore, and the web dashboard served from LittleFS.",
    "D2 — H1 home unit: ESP8266 with a 1.8-inch TFT, automatic pump control through an "
    "isolated relay and contactor, and a manual override.",
    "D3 — C1 cleaning arm: ESP32 controller, two-link arm, ring brush head with suction, "
    "planner and path executor, with the coverage analysis that states its limits.",
    "D4 — Field evidence: three installations, 90 days of data, and a TRL 6+ evidence "
    "pack including score accuracy and cleaning coverage.",
]

MILESTONES = [
    ("1", "Requirements and monitor prototype", "T0 + 2 months",
     "M1 assembled and calibrated; TankScore validated; dashboard served from flash."),
    ("2", "Home unit and dashboard", "T0 + 4 months",
     "H1 installed with pump control; dashboard, session log and device table complete."),
    ("3", "Cleaning arm", "T0 + 8 months",
     "C1 built; three-ring cycle executed; coverage and repeatability measured."),
    ("4", "Field validation", "T0 + 12 months",
     "Three installations, 90 days of data, TRL 6+ evidence pack."),
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
    "Equipment split (indicative): M1 monitor INR 6,500; H1 home unit INR 1,800; "
    "C1 cleaning arm INR 7,300 (two 12 V planetary gearmotors, ESP32, two H-bridges, "
    "submersible pump, brush head, enclosure).",
    "Contingency cannot exceed 5% of project value; overhead cannot exceed 20% of the "
    "sub total; the faculty fee is optional and capped at 20% of the total.",
    "Manpower, consumables, travel and miscellaneous heads will be aligned during the "
    "grant kickoff; equipment figures are vendor quotes pending confirmation.",
]

TRANCHE_ROWS = [
    ("Project start (T0)", "8,235", "M1 monitor build and dashboard"),
    ("T0 + 6 months", "9,415", "H1 home unit and C1 cleaning arm"),
    ("T0 + 12 months", "5,937", "Field validation and evidence pack"),
    ("Total", "23,587", ""),
]

SUPPORT = [
    "TankGuard Technical Specification (Document Ref: TG-SPEC-2026-001), October 2026, "
    "7 pages.",
    "Firmware for all three units, compiling for ESP8266 (M1, H1) and ESP32 (C1), plus "
    "the React dashboard served from M1 flash.",
    "Design record (docs/CLEANER.md): kinematics, coverage analysis and control limits, "
    "including the 2 cm wall ring the mechanism cannot reach.",
    "Coverage planner (tools/swept_area.html) and the generated path used by the "
    "controller (firmware/c1_cleaner/path.h).",
    "Patentability disclosure and minimum bill of materials.",
]

CATEGORY = (
    "Category: New-to-the-world product / technology. The combination of edge-computed "
    "water scoring, a self-hosted dashboard, safe pump control and a selective robotic "
    "cleaning arm — all on a local network with no cloud dependency — is not offered by "
    "monitoring-only products or by full-drain cleaning services."
)

# --------------------------------------------------------------------------- #
# DOCX rebuild
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


def table(doc, headers, rows, widths=None):
    t = doc.add_table(rows=1, cols=len(headers))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    hdr = t.rows[0].cells
    for i, h in enumerate(headers):
        hdr[i].text = ""
        p = hdr[i].paragraphs[0]
        r = p.add_run(h)
        r.bold = True
        r.font.size = Pt(9.5)
        r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        shade(hdr[i])
    for row in rows:
        cells = t.add_row().cells
        for i, val in enumerate(row):
            cells[i].text = ""
            p = cells[i].paragraphs[0]
            r = p.add_run(str(val))
            r.font.size = Pt(9.5)
            shade(cells[i], "FFFFFF")
    if widths:
        for i, w in enumerate(widths):
            for row in t.rows:
                row.cells[i].width = w
    doc.add_paragraph()
    return t


def para(doc, text, size=11, bold=False, color=None, align=None, space_after=6):
    p = doc.add_paragraph()
    r = p.add_run(text)
    r.font.size = Pt(size)
    r.bold = bold
    if color is not None:
        r.font.color.rgb = color
    if align is not None:
        p.alignment = align
    p.paragraph_format.space_after = Pt(space_after)
    return p



def heading(doc, text, level):
    """Heading with explicit formatting.

    The template's Heading styles carry list numbering (a bullet) and a magenta
    theme colour that survive style-level edits, so each heading also gets
    numId=0 and direct run formatting.
    """
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
    color = BLUE if level == 1 else RGBColor(0x2E, 0x74, 0xB5)
    for r in p.runs:
        r.font.size = Pt(size)
        r.font.bold = True
        r.font.color.rgb = color
    p.paragraph_format.space_before = Pt(14 if level == 1 else 10)
    p.paragraph_format.space_after = Pt(6)
    return p


def rebuild_docx():
    path = os.path.join(OUT, "TankGuard_Project_Proposal.docx")
    doc = Document(DOCX_SRC)

    # keep the section (header/footer/page setup), drop the body
    body = doc.element.body
    for child in list(body):
        if child.tag == qn("w:sectPr"):
            continue
        body.remove(child)

    # ---- title page -------------------------------------------------------
    para(doc, "Project Proposal", 20, True, BLUE, WD_ALIGN_PARAGRAPH.CENTER, 4)
    para(doc, "For Consideration Under", 11, False, None, WD_ALIGN_PARAGRAPH.CENTER, 2)
    para(doc, THEME, 15, True, BLUE, WD_ALIGN_PARAGRAPH.CENTER, 18)
    para(doc, TITLE, 16, True, BLUE, WD_ALIGN_PARAGRAPH.CENTER, 16)
    para(doc, "Submitted by", 11, False, None, WD_ALIGN_PARAGRAPH.CENTER, 2)
    para(doc, PI, 14, True, BLUE, WD_ALIGN_PARAGRAPH.CENTER, 2)
    para(doc, AFFIL, 11, False, None, WD_ALIGN_PARAGRAPH.CENTER, 10)
    para(doc, f"Theme: {THEME}", 10.5, False, None, WD_ALIGN_PARAGRAPH.CENTER, 2)
    para(doc, f"Date of submission: {DATE}", 10.5, False, None, WD_ALIGN_PARAGRAPH.CENTER, 2)
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

    # ---- contents ---------------------------------------------------------
    heading(doc, "Contents", 1)
    for line in (
        "1  Cover Sheet",
        "2  Executive Summary",
        "3  Background",
        "     3.1  History",
        "     3.2  Statement of the problem",
        "     3.3  Objectives",
        "     3.4  Deliverables",
        "     3.5  Project plan with major milestones",
        "     3.6  Resources and budget",
        "     3.7  Category of new technology/product",
        "4  Appendix",
        "     4.1  Supporting documentation",
    ):
        para(doc, line, 11, False, None, None, 2)
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
            ("Email", ""),
            ("Co-investigator", "—"),
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

    heading(doc, "3.5  Project plan with major milestones", 2)
    para(doc, "Twelve-month plan from T0, with a gate at every milestone.")
    table(doc, ["#", "Milestone", "Period", "What is delivered"],
          MILESTONES, widths=[Pt(24), Pt(150), Pt(70), Pt(210)])

    heading(doc, "3.6  Resources and budget", 2)
    table(doc, ["Item", "Amount (INR)"], BUDGET_ROWS, widths=[Pt(240), Pt(110)])
    for t in BUDGET_NOTE:
        para(doc, t, 10)
    tr = heading(doc, "Tranche disbursement schedule", 2)
    tr.paragraph_format.page_break_before = True
    table(doc, ["Timeline", "Amount (INR)", "Milestone covered"],
          TRANCHE_ROWS, widths=[Pt(110), Pt(90), Pt(250)])

    heading(doc, "3.7  Category of new technology/product", 2)
    para(doc, CATEGORY)

    # ---- 4 appendix -------------------------------------------------------
    heading(doc, "4  Appendix", 1)
    heading(doc, "4.1  Supporting documentation", 2)
    for t in SUPPORT:
        para(doc, " " + t)

    # heading styles: drop the bullet numbering, fix the magenta Heading 2
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

    # template metadata: 2021 dates and the placeholder author lines
    sec = doc.sections[0]
    for part in (sec.header, sec.first_page_footer):
        for t in part.tables:
            for row in t.rows:
                for cell in row.cells:
                    for p in list(cell.paragraphs):
                        if p.text.strip() in ("Author2", "Author3"):
                            p._element.getparent().remove(p._element)
                            continue
                        for r in p.runs:
                            if "14-July-2021" in r.text:
                                r.text = r.text.replace("14-July-2021", "31-October-2026")

    # the empty bordered box on the cover is an empty table in the first-page header
    for t in list(sec.first_page_header.tables):
        t._element.getparent().remove(t._element)

    # "Author2"/"Author3" are DOCPROPERTY fields in the first-page footer, not
    # plain text — remove the paragraphs that carry those fields
    for part in (sec.first_page_footer, sec.footer, sec.header, sec.first_page_header):
        doomed = []
        for el in part._element.iter():
            hit = False
            if el.tag == qn("w:t") and el.text and el.text.strip() in ("Author2", "Author3"):
                hit = True
            elif el.tag == qn("w:instrText") and el.text and ("Author2" in el.text or "Author3" in el.text):
                hit = True
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

    doc.core_properties.title = TITLE
    doc.core_properties.author = PI
    doc.core_properties.subject = THEME
    doc.save(path)
    return path

# --------------------------------------------------------------------------- #
# XLSX
# --------------------------------------------------------------------------- #
def fix_xlsx():
    path = os.path.join(OUT, "TankGuard_Budget_Milestone.xlsx")
    shutil.copyfile(XLSX_SRC, path)
    wb = load_workbook(path)

    ms = wb["Milestones"]
    ms["B9"] = "Contingency (max 5%)"
    ms["B12"] = "Faculty fee (max 20%)"
    # budget column (equipment 15,600 → contingency 780 → subtotal 16,380 →
    # overhead 3,276 → fee 3,931 → total 23,587)
    for cell, val in (("C5", 15600), ("C9", 780), ("C10", 16380), ("C11", 3276),
                      ("C12", 3931), ("C13", 23587), ("C14", 0), ("C15", 23587)):
        ms[cell] = val
    for r, (name, when, remark) in zip(range(4, 9), [
        ("Project beginning (T0)", "T0", "Project plan, stakeholder alignment, BOM freeze"),
        ("Milestone 1: Requirements and monitor prototype", "T0 + 2 months",
         "M1 calibrated; TankScore validated; dashboard from flash"),
        ("Milestone 2: Home unit and dashboard", "T0 + 4 months",
         "H1 TFT + pump control; dashboard and session log"),
        ("Milestone 3: Cleaning arm", "T0 + 8 months",
         "C1 built; three-ring cycle; coverage measured"),
        ("Milestone 4: Field validation", "T0 + 12 months",
         "Three installations, 90 days, TRL 6+ evidence"),
    ]):
        ms[f"F{r}"] = name
        ms[f"G{r}"] = when
        ms[f"H{r}"] = remark

    # tranche disbursement schedule
    for cell, val in (("J4", "Project Start Date (T0)"), ("K4", 8235), ("L4", "M1 monitor build and dashboard"),
                      ("J5", "T0 + 06 months"), ("K5", 9415), ("L5", "H1 home unit and C1 cleaning arm"),
                      ("J6", "T0 + 12 months"), ("K6", 5937), ("L6", "Field validation and evidence pack"),
                      ("J7", "Total"), ("K7", 23587), ("L7", "")):
        ms[cell] = val

    b = wb["Budget"]
    for cell, val in (("D10", 0), ("D11", 15600), ("D12", 780), ("D13", 16380),
                      ("D14", 3276), ("D15", 3931), ("D16", 23587)):
        b[cell] = val
    b["H2"] = "Grant total: INR 23,587"

    # the template repeats the expenditure heads in two blocks; drop the empty
    # one so the sheet reads as a single table
    try:
        b.delete_rows(5, 5)
    except Exception:
        for r in range(5, 10):
            for c in range(2, 8):
                b.cell(row=r, column=c).value = None

    # tranche columns: label them with the real amounts instead of XXXXXX
    b["E3"] = "Tranche 1\n8,235"
    b["F3"] = "Tranche 2\n9,415"
    b["G3"] = "Tranche 3\n5,937"
    for r in range(1, 18):
        b.row_dimensions[r].height = 26
        for c in range(2, 8):
            b.cell(row=r, column=c).alignment = Alignment(wrap_text=True, vertical="center")
    b.print_area = "B2:G14"

    # milestones sheet: wrap the remarks column and fit the print area
    for r in range(1, 16):
        ms.row_dimensions[r].height = 30
        for c in (6, 7, 8, 10, 11, 12):
            ms.cell(row=r, column=c).alignment = Alignment(wrap_text=True, vertical="center")
    ms.print_area = "A1:L15"

    # renumber the surviving block and format the amounts
    for i, r in enumerate(range(5, 12)):
        b[f"B{r}"] = i + 1
        b[f"D{r}"].number_format = "#,##0"
    # the closing note should overflow across the empty cells, not wrap
    b["B13"].alignment = Alignment(wrap_text=False, vertical="center")
    b.row_dimensions[13].height = 20

    for ws in wb.worksheets:
        ws.page_setup.orientation = "landscape"
        ws.page_setup.fitToWidth = 1
        ws.page_setup.fitToHeight = 0
        ws.sheet_properties.pageSetUpPr.fitToPage = True
        ws.print_options.horizontalCentered = True

    wb.save(path)
    return path

# --------------------------------------------------------------------------- #
# PPTX — replace text in place, keeping paragraph formatting
# --------------------------------------------------------------------------- #
def set_frame(tf, lines):
    paras = list(tf.paragraphs)
    for i, line in enumerate(lines):
        if i < len(paras):
            p = paras[i]
            if p.runs:
                p.runs[0].text = line
                for r in p.runs[1:]:
                    r.text = ""
            else:
                p.text = line
        else:
            p = tf.add_paragraph()
            p.text = line
            if paras and paras[-1].runs:
                src = paras[-1].runs[0]
                if src.font.size:
                    p.runs[0].font.size = src.font.size
                p.runs[0].font.bold = src.font.bold
    for j in range(len(lines), len(paras)):
        for r in paras[j].runs:
            r.text = ""


SLIDES = {
    1: ["TankGuard",
        "Self-powered IoT water-tank monitoring, pump control and automated sludge cleaning",
        "Dr. Vishnu Vasudev"],
    2: ["Three local units, one LAN: M1 monitor, H1 home display + pump control, C1 cleaning arm.",
        "Edge-computed TankScore from five submerged probes; no cloud, no account.",
        "Dashboard served by the tank unit itself, over its own Wi-Fi.",
        "Cleaning arm covers 90% of the tank floor per cycle and parks at both ends.",
        "TRL 6+ in 12 months with three field installations."],
    3: ["Water storage tanks degrade silently: disinfectant residual dissipates within "
        "24-48 hours, particles settle into a sludge layer, biofilm forms on the walls, and "
        "algae bloom in warm water. By the time the water smells or looks wrong it is unsafe, "
        "and the only remedy is a full drain and manual scrub that wastes the whole stored volume."],
    4: ["M1 sits on the lid: five submerged probes through an ADS1115, an edge TankScore, and "
        "a web dashboard served from its own flash. H1 sits by the pump: a 1.8-inch display, "
        "automatic level control through an isolated relay and contactor, and a manual override. "
        "C1 is a two-link 20 cm + 20 cm arm that sweeps three concentric rings with a ring brush "
        "and draws the loosened sludge out through the centre of the head."],
    5: ["Unique points:",
        "1. Closed-loop care: sense, score, act, verify — with the verification shown, not claimed.",
        "2. Local-only architecture: no cloud path, no account, works when the internet does not.",
        "3. Selective cleaning: 90% floor coverage per cycle without draining the tank.",
        "4. Honest instrumentation: the dashboard states its data source and the arm's 2 cm wall ring."],
    6: ["Quantified impact:",
        "No full drain: cleaning removes the sludge layer, not the stored volume.",
        "Pump protection: level-based automatic control with a safe manual override.",
        "Early warning: a score trend catches degradation before smell or taste.",
        "Off-grid: solar and battery keep the monitor alive for weeks without sun."],
    7: ["Methodology:",
        "M1 (T0+2): probes, TankScore, dashboard served from flash.",
        "H1 + dashboard (T0+4): TFT, pump control, session log, device table.",
        "C1 (T0+8): 2R arm, planner, controller, three-ring cycle.",
        "Field (T0+12): three installations, 90 days, TRL 6+ evidence."],
    8: ["Four gates in twelve months; each one is a demo, not a status report."],
    9: ["Market: domestic and institutional water storage tanks — homes, apartment buildings, "
        "schools, hospitals and small industry. The buyer is the same person who pays the plumber "
        "today; the value is water saved, pump life and a measurable answer to \"is my water safe?\""],
    10: ["Indicative, exclusive of GST. Grand total includes contingency, overhead and faculty fee."],
    11: ["Funding so far: not yet secured. Nuke Labs is committed as the industry partner for "
         "build facilities, field access and TRL 6+ validation."],
    12: ["Team:",
         "Principal Investigator: Dr. Vishnu Vasudev, Department of Electronics and Communication Engineering.",
         "Industry partner: Nuke Labs — hardware build, field installations, commercialisation."],
    13: ["TankGuard turns tank maintenance from calendar guesswork into measured care: sensing at "
         "the edge, deciding locally, cleaning selectively, and showing its own evidence."],
}


def fix_pptx():
    path = os.path.join(OUT, "TankGuard_Presentation.pptx")
    shutil.copyfile(PPTX_SRC, path)
    prs = Presentation(path)
    slides = list(prs.slides)

    LABELS = {
        "Key Points", "Problem Statement", "Solution", "USP / Differentiator", "Impact",
        "Project Plan / Methodology", "Milestones", "Market Size", "Resources & Budget",
        "Funding So Far", "Team", "Conclusion", "Guidelines",
    }

    # rebuild the content of slides 2-13: keep the section label and any table,
    # replace the template placeholder with one clean text block
    for idx, lines in SLIDES.items():
        if idx == 1 or idx - 1 >= len(slides):
            continue
        slide = slides[idx - 1]

        label = None
        for sh in slide.shapes:
            if sh.has_text_frame and sh.text_frame.text.strip() in LABELS:
                label = sh
                break

        if label is not None and label.text_frame.text.strip() == "Guidelines":
            for p in label.text_frame.paragraphs:
                for r in p.runs:
                    if "Guidelines" in r.text:
                        r.text = r.text.replace("Guidelines", "Key Points")

        for sh in list(slide.shapes):
            if (label is not None and sh._element is label._element) or sh.has_table:
                continue
            if sh.has_text_frame:
                sh._element.getparent().remove(sh._element)

        if idx in (8, 10):
            continue  # these slides are the table; no intro block

        tall = True
        tb = slide.shapes.add_textbox(Inches(0.85), Inches(1.45), Inches(11.6), Inches(4.6))
        tf = tb.text_frame
        tf.word_wrap = True
        for i, line in enumerate(lines):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.text = line
            p.font.size = PPt(18)
            p.space_after = PPt(8)

    # milestones table (slide 8) and budget table (slide 10)
    for si, headers, rows in (
        (7, ["No.", "Milestone", "Time period"],
         [("1", "Requirements and monitor prototype", "T0 + 2 months"),
          ("2", "Home unit and dashboard", "T0 + 4 months"),
          ("3", "Cleaning arm", "T0 + 8 months"),
          ("4", "Field validation", "T0 + 12 months")]),
        (9, ["No.", "Item", "Specification", "Amount (INR)", "Phase"],
         [("1", "M1 monitor", "ESP8266 + 5 probes", "6,500", "T0"),
          ("2", "H1 home unit", "ESP8266 + TFT + relay", "1,800", "T0 + 4"),
          ("3", "C1 cleaning arm", "ESP32 + 2 motors + pump", "7,300", "T0 + 8"),
          ("", "Equipment total", "", "15,600", ""),
          ("", "Grand total", "incl. contingency, overhead, fee", "23,587", "")]),
    ):
        if si >= len(slides):
            continue
        for sh in slides[si].shapes:
            if not sh.has_table:
                continue
            tbl = sh.table
            for c, h in enumerate(headers):
                if c < len(tbl.columns):
                    tbl.rows[0].cells[c].text = h
            for r, row in enumerate(rows):
                if r + 1 >= len(tbl.rows):
                    break
                cells = tbl.rows[r + 1].cells
                for c, val in enumerate(row):
                    if c < len(cells):
                        cells[c].text = val
            for row in tbl.rows:
                row.height = Inches(0.55)

    # title slide: centre the three lines and size them
    if slides:
        for sh in slides[0].shapes:
            if sh.has_text_frame and sh.text_frame.text.strip():
                for i, p in enumerate(sh.text_frame.paragraphs):
                    p.alignment = PP_ALIGN.CENTER
                    for r in p.runs:
                        r.font.size = PPt((32, 18, 16)[min(i, 2)])
                break

    prs.save(path)
    return path


if __name__ == "__main__":
    print(rebuild_docx())
    print(fix_xlsx())
    print(fix_pptx())
