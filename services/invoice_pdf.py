"""
invoice_pdf.py
Generates two PDFs for every order:
  1. Customer Invoice  – payment details, billing address
  2. Dispatch Sheet    – packing list for the dispatch team
Both are saved to the user's Downloads folder and opened automatically.
"""

import os
import platform
import subprocess
from datetime import date, timedelta

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_RIGHT, TA_CENTER, TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)

# ── Colour palette ────────────────────────────────────────────────────────────
GREEN_DARK  = colors.HexColor("#1E3A1E")
GREEN_MID   = colors.HexColor("#2D4A2D")
GREEN_LIGHT = colors.HexColor("#EAF3E4")
GREEN_LINE  = colors.HexColor("#C8DFC0")
GREY_TEXT   = colors.HexColor("#555555")
RED_ALERT   = colors.HexColor("#C0392B")
WHITE       = colors.white
BLACK       = colors.black

PAGE_W, PAGE_H = A4
MARGIN = 20 * mm


def _downloads_dir() -> str:
    home = os.path.expanduser("~")
    dl = os.path.join(home, "Downloads")
    return dl if os.path.isdir(dl) else home


def _open_file(path: str):
    """Open the PDF with the system default viewer."""
    try:
        if platform.system() == "Windows":
            os.startfile(path)
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
    except Exception:
        pass


def _base_styles():
    s = getSampleStyleSheet()
    s.add(ParagraphStyle("CompanyName",
        fontSize=22, textColor=GREEN_DARK, fontName="Helvetica-Bold",
        spaceAfter=2))
    s.add(ParagraphStyle("Tagline",
        fontSize=9, textColor=GREY_TEXT, fontName="Helvetica",
        spaceAfter=10))
    s.add(ParagraphStyle("SectionHead",
        fontSize=11, textColor=GREEN_DARK, fontName="Helvetica-Bold",
        spaceBefore=10, spaceAfter=4))
    s.add(ParagraphStyle("BodySmall",
        fontSize=9, textColor=BLACK, fontName="Helvetica",
        leading=14))
    s.add(ParagraphStyle("BodySmallGrey",
        fontSize=9, textColor=GREY_TEXT, fontName="Helvetica",
        leading=14))
    s.add(ParagraphStyle("TotalLabel",
        fontSize=11, textColor=GREEN_DARK, fontName="Helvetica-Bold",
        alignment=TA_RIGHT))
    s.add(ParagraphStyle("TotalValue",
        fontSize=13, textColor=GREEN_DARK, fontName="Helvetica-Bold",
        alignment=TA_RIGHT))
    s.add(ParagraphStyle("DocTitle",
        fontSize=16, textColor=WHITE, fontName="Helvetica-Bold",
        alignment=TA_RIGHT))
    s.add(ParagraphStyle("SmallRight",
        fontSize=8, textColor=GREY_TEXT, fontName="Helvetica",
        alignment=TA_RIGHT))
    return s


# ─────────────────────────────────────────────────────────────────────────────
#  CUSTOMER INVOICE
# ─────────────────────────────────────────────────────────────────────────────

from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle,
    Paragraph, Spacer
)
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from num2words import num2words

def generate_customer_invoice(order):

    out_dir = _downloads_dir()
    filename = f"Invoice_Order_{order.id}.pdf"
    path = os.path.join(out_dir, filename)

    doc = SimpleDocTemplate(
        path,
        pagesize=A4,
        leftMargin=8*mm,
        rightMargin=8*mm,
        topMargin=8*mm,
        bottomMargin=8*mm
    )

    styles = getSampleStyleSheet()
    story = []

    # =========================================================
    # COMPANY HEADER
    # =========================================================

    company = """
    <b>HIND AGRO PRODUCTS</b><br/>
    KHASARA No. 38/5, Kila No. 24/22 and 24/21-1/2<br/>
    Vill. Sanpka, Pataudi, Gurugram<br/>
    Contact : 9911301983<br/>
    E-Mail : hindagroproducts@yahoo.com<br/>
    GSTIN/UIN : 06BDVPK6852R1ZE<br/>
    State Name : Haryana, Code : 06
    """

    title = "<font size=16><b>Bill of Supply</b></font>"

    header_tbl = Table([
        [
            Paragraph(company, styles["BodyText"]),
            Paragraph(title, styles["BodyText"])
        ]
    ], colWidths=[120*mm, 60*mm])

    header_tbl.setStyle(TableStyle([
        ("BOX", (0,0), (-1,-1), 1, colors.black),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (0,0), (-1,-1), 6),
        ("RIGHTPADDING", (0,0), (-1,-1), 6),
        ("TOPPADDING", (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
    ]))

    story.append(header_tbl)

    # =========================================================
    # BUYER + CONSIGNEE
    # =========================================================

    buyer = f"""
    <b>Buyer (Bill To)</b><br/>
    {order.customer_name}<br/>
    PAN : XXXXXXXX<br/>
    State : Uttar Pradesh<br/>
    """

    consignee = f"""
    <b>Consignee (Ship To)</b><br/>
    {order.customer_name}<br/>
    PAN : XXXXXXXX<br/>
    State : Uttar Pradesh
    """

    party_tbl = Table([
        [
            Paragraph(consignee, styles["BodyText"]),
            Paragraph(buyer, styles["BodyText"])
        ]
    ], colWidths=[90*mm, 90*mm])

    party_tbl.setStyle(TableStyle([
        ("BOX", (0,0), (-1,-1), 1, colors.black),
        ("INNERGRID", (0,0), (-1,-1), 1, colors.black),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (0,0), (-1,-1), 6),
        ("TOPPADDING", (0,0), (-1,-1), 6),
    ]))

    story.append(party_tbl)

    # =========================================================
    # INVOICE DETAILS
    # =========================================================

    invoice_data = [
        ["Invoice No.", f"{order.id}"],
        ["Date", date.today().strftime("%d-%b-%Y")],
        ["Dispatch Through", "ROAD"],
        ["Destination", "Customer Location"]
    ]

    invoice_tbl = Table(invoice_data, colWidths=[50*mm, 130*mm])

    invoice_tbl.setStyle(TableStyle([
        ("BOX", (0,0), (-1,-1), 1, colors.black),
        ("INNERGRID", (0,0), (-1,-1), 1, colors.black),
        ("LEFTPADDING", (0,0), (-1,-1), 5),
        ("TOPPADDING", (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
    ]))

    story.append(invoice_tbl)
    story.append(Spacer(1, 5))

    # =========================================================
    # ITEMS TABLE
    # =========================================================

    rows = [[
        "Sl",
        "Description of Goods",
        "HSN/SAC",
        "Qty",
        "Rate",
        "Amount"
    ]]

    total = 0

    for i, item in enumerate(order.items, 1):

        subtotal = float(item.subtotal)
        total += subtotal

        rows.append([
            str(i),
            str(item.plant_name),
            "060290",
            str(item.quantity),
            f"{float(item.unit_price):.2f}",
            f"{subtotal:.2f}"
        ])

    rows.append([
        "",
        "TOTAL",
        "",
        "",
        "",
        f"{total:.2f}"
    ])

    items_tbl = Table(rows, colWidths=[
        12*mm,
        80*mm,
        25*mm,
        20*mm,
        20*mm,
        30*mm
    ])

    items_tbl.setStyle(TableStyle([
        ("BOX", (0,0), (-1,-1), 1, colors.black),
        ("INNERGRID", (0,0), (-1,-1), 0.8, colors.black),

        ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),

        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTNAME", (0,-1), (-1,-1), "Helvetica-Bold"),

        ("ALIGN", (0,0), (-1,-1), "CENTER"),

        ("LEFTPADDING", (0,0), (-1,-1), 4),
        ("RIGHTPADDING", (0,0), (-1,-1), 4),

        ("TOPPADDING", (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
    ]))

    story.append(items_tbl)
    story.append(Spacer(1, 5))

    # =========================================================
    # AMOUNT IN WORDS
    # =========================================================

    amount_words = num2words(total, to='cardinal', lang='en_IN')

    words_para = Paragraph(
        f"<b>Amount Chargeable (in words)</b><br/>"
        f"INR {amount_words.title()} Only",
        styles["BodyText"]
    )

    story.append(words_para)
    story.append(Spacer(1, 8))

    # =========================================================
    # FOOTER
    # =========================================================

    footer_data = [[
        Paragraph("""
        <b>Declaration</b><br/>
        We declare that this invoice shows the actual price
        of the goods described and that all particulars
        are true and correct.
        """, styles["BodyText"]),

        Paragraph("""
        <b>Company's Bank Details</b><br/>
        A/c Holder : HIND AGRO PRODUCTS<br/>
        Bank : ICICI BANK<br/>
        A/c No : 162905001692<br/>
        IFSC : ICIC0001629
        """, styles["BodyText"])
    ]]

    footer_tbl = Table(footer_data, colWidths=[90*mm, 90*mm])

    footer_tbl.setStyle(TableStyle([
        ("BOX", (0,0), (-1,-1), 1, colors.black),
        ("INNERGRID", (0,0), (-1,-1), 1, colors.black),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (0,0), (-1,-1), 6),
        ("TOPPADDING", (0,0), (-1,-1), 6),
    ]))

    story.append(footer_tbl)

    story.append(Spacer(1, 15))

    sign = Paragraph(
        "<para align='right'><b>for HIND AGRO PRODUCTS</b><br/><br/><br/>Authorised Signatory</para>",
        styles["BodyText"]
    )

    story.append(sign)

    doc.build(story)

    return path


# ─────────────────────────────────────────────────────────────────────────────
#  DISPATCH SHEET
# ─────────────────────────────────────────────────────────────────────────────

def generate_dispatch_sheet(order) -> str:
    """
    Generates a packing/dispatch sheet for the warehouse team.
    """
    out_dir  = _downloads_dir()
    filename = f"Dispatch_Order_{order.id}.pdf"
    path     = os.path.join(out_dir, filename)

    doc = SimpleDocTemplate(
        path, pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN, bottomMargin=MARGIN,
        title=f"Dispatch Sheet – Order #{order.id}",
        author="Hind Agro Products"
    )

    s = _base_styles()
    story = []

    # ── Header ────────────────────────────────────────────────────────────────
    hdr_data = [[
        Paragraph("Hind Agro Products", s["CompanyName"]),
        Paragraph("<b>DISPATCH SHEET</b>", s["DocTitle"])
    ]]
    hdr_tbl = Table(hdr_data, colWidths=[(PAGE_W - 2*MARGIN) * 0.55,
                                         (PAGE_W - 2*MARGIN) * 0.45])
    hdr_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), colors.HexColor("#1A3A1A")),
        ("TOPPADDING",    (0, 0), (-1, -1), 14),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
        ("LEFTPADDING",   (0, 0), (0, -1), 16),
        ("RIGHTPADDING",  (-1, 0), (-1, -1), 16),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(hdr_tbl)
    story.append(Spacer(1, 6 * mm))

    # ── Order info grid ───────────────────────────────────────────────────────
    info_data = [
        [Paragraph("<b>Order No:</b>",    s["BodySmall"]),
         Paragraph(f"ORD-{order.id:05d}", s["BodySmall"]),
         Paragraph("<b>Date:</b>",        s["BodySmall"]),
         Paragraph(date.today().strftime("%d %b %Y"), s["BodySmall"])],
        [Paragraph("<b>Customer:</b>",    s["BodySmall"]),
         Paragraph(str(order.customer_name), s["BodySmall"]),
         Paragraph("<b>Status:</b>",      s["BodySmall"]),
         Paragraph(str(order.status),     s["BodySmall"])],
    ]
    if order.notes:
        info_data.append([
            Paragraph("<b>Notes:</b>", s["BodySmall"]),
            Paragraph(str(order.notes), s["BodySmallGrey"]),
            "", ""
        ])

    info_tbl = Table(info_data, colWidths=[30*mm, 65*mm, 25*mm, 48*mm])
    info_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), GREEN_LIGHT),
        ("TOPPADDING",    (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ("BOX",           (0, 0), (-1, -1), 0.5, GREEN_LINE),
        ("INNERGRID",     (0, 0), (-1, -1), 0.3, GREEN_LINE),
    ]))
    story.append(info_tbl)
    story.append(Spacer(1, 6 * mm))

    # ── Packing checklist ─────────────────────────────────────────────────────
    story.append(Paragraph("Packing Checklist", s["SectionHead"]))
    story.append(Spacer(1, 2 * mm))

    pack_rows = [[
        Paragraph("<b>#</b>",          s["BodySmall"]),
        Paragraph("<b>Plant Name</b>", s["BodySmall"]),
        Paragraph("<b>Qty to Pack</b>",s["BodySmall"]),
        Paragraph("<b>Packed</b>",     s["BodySmall"]),
        Paragraph("<b>Checked</b>",    s["BodySmall"]),
    ]]

    for i, item in enumerate(order.items, 1):
        pack_rows.append([
            Paragraph(str(i), s["BodySmall"]),
            Paragraph(str(item.plant_name), s["BodySmall"]),
            Paragraph(f"<b>{item.quantity}</b>", s["BodySmall"]),
            Paragraph("[ &nbsp; &nbsp; &nbsp; ]", s["BodySmall"]),
            Paragraph("[ &nbsp; &nbsp; &nbsp; ]", s["BodySmall"]),
        ])

    pack_tbl = Table(pack_rows,
                     colWidths=[10*mm, 80*mm, 28*mm, 28*mm, 28*mm],
                     repeatRows=1)
    pack_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), GREEN_MID),
        ("TEXTCOLOR",     (0, 0), (-1, 0), WHITE),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, 0), 9),
        ("TOPPADDING",    (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [WHITE, GREEN_LIGHT]),
        ("GRID",          (0, 0), (-1, -1), 0.4, GREEN_LINE),
        ("ALIGN",         (2, 0), (-1, -1), "CENTER"),
        ("FONTSIZE",      (0, 1), (-1, -1), 10),
    ]))
    story.append(pack_tbl)
    story.append(Spacer(1, 10 * mm))

    # ── Sign-off section ──────────────────────────────────────────────────────
    total_qty = sum(item.quantity for item in order.items)
    total_items = len(order.items)

    signoff_data = [[
        Paragraph(f"<b>Total Items:</b> {total_items} &nbsp;&nbsp; "
                  f"<b>Total Qty:</b> {total_qty}", s["BodySmall"]),
        "",
    ],[
        Paragraph("Packed by: _______________________  &nbsp; Date: __________", s["BodySmall"]),
        Paragraph("Checked by: _______________________  &nbsp; Date: __________", s["BodySmall"]),
    ],[
        Paragraph("Driver / Courier: ___________________________", s["BodySmall"]),
        Paragraph("Dispatch Time: ___________________________", s["BodySmall"]),
    ]]
    signoff_tbl = Table(signoff_data,
                        colWidths=[(PAGE_W - 2*MARGIN) / 2,
                                   (PAGE_W - 2*MARGIN) / 2])
    signoff_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), GREEN_LIGHT),
        ("TOPPADDING",    (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING",   (0, 0), (-1, -1), 12),
        ("BOX",           (0, 0), (-1, -1), 0.5, GREEN_LINE),
        ("INNERGRID",     (0, 0), (-1, -1), 0.3, GREEN_LINE),
        ("SPAN",          (0, 0), (-1, 0)),
    ]))
    story.append(signoff_tbl)
    story.append(Spacer(1, 6 * mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=GREEN_LINE))
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph(
        f"Hind Agro Products &nbsp;|&nbsp; Dispatch Sheet for ORD-{order.id:05d} &nbsp;|&nbsp; "
        f"Generated: {date.today().strftime('%d %b %Y')}",
        s["SmallRight"]
    ))

    doc.build(story)
    return path


# ─────────────────────────────────────────────────────────────────────────────
#  PUBLIC ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

def generate_and_open(order) -> tuple[str, str]:
    """
    Generates both PDFs, opens them, returns (invoice_path, dispatch_path).
    order.items must be populated before calling this.
    """
    inv_path  = generate_customer_invoice(order)
    disp_path = generate_dispatch_sheet(order)
    _open_file(inv_path)
    _open_file(disp_path)
    return inv_path, disp_path
