import os
from datetime import date, datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER

# ── Brand colours ────────────────────────────────────────────────────────────
GREEN_DARK  = colors.HexColor("#1E3A1E")
GREEN_MID   = colors.HexColor("#2D4A2D")
GREEN_LIGHT = colors.HexColor("#EAF3E4")
GREEN_ACCENT= colors.HexColor("#4A7C4A")
RED_ALERT   = colors.HexColor("#C0392B")
GREY_TEXT   = colors.HexColor("#555555")
GREY_LIGHT  = colors.HexColor("#F5FAF3")
WHITE       = colors.white
BLACK       = colors.HexColor("#1A1A1A")

# ── Styles ───────────────────────────────────────────────────────────────────
def _styles():
    return {
        "company":   ParagraphStyle("company",   fontSize=22, textColor=GREEN_DARK,  fontName="Helvetica-Bold", leading=26),
        "tagline":   ParagraphStyle("tagline",   fontSize=9,  textColor=GREEN_ACCENT, fontName="Helvetica",      leading=13),
        "doc_title": ParagraphStyle("doc_title", fontSize=18, textColor=GREEN_DARK,  fontName="Helvetica-Bold", leading=22),
        "section":   ParagraphStyle("section",   fontSize=10, textColor=GREEN_DARK,  fontName="Helvetica-Bold", leading=14),
        "body":      ParagraphStyle("body",      fontSize=9,  textColor=BLACK,       fontName="Helvetica",      leading=13),
        "body_grey": ParagraphStyle("body_grey", fontSize=9,  textColor=GREY_TEXT,   fontName="Helvetica",      leading=13),
        "bold":      ParagraphStyle("bold",      fontSize=9,  textColor=BLACK,       fontName="Helvetica-Bold", leading=13),
        "right":     ParagraphStyle("right",     fontSize=9,  textColor=BLACK,       fontName="Helvetica",      leading=13, alignment=TA_RIGHT),
        "right_bold":ParagraphStyle("right_bold",fontSize=10, textColor=GREEN_DARK,  fontName="Helvetica-Bold", leading=14, alignment=TA_RIGHT),
        "total":     ParagraphStyle("total",     fontSize=12, textColor=GREEN_DARK,  fontName="Helvetica-Bold", leading=16, alignment=TA_RIGHT),
        "badge":     ParagraphStyle("badge",     fontSize=9,  textColor=WHITE,       fontName="Helvetica-Bold", leading=13, alignment=TA_CENTER),
        "footer":    ParagraphStyle("footer",    fontSize=8,  textColor=GREY_TEXT,   fontName="Helvetica",      leading=11, alignment=TA_CENTER),
        "dispatch_title": ParagraphStyle("dispatch_title", fontSize=14, textColor=GREEN_DARK, fontName="Helvetica-Bold", leading=18),
        "dispatch_body":  ParagraphStyle("dispatch_body",  fontSize=10, textColor=BLACK,      fontName="Helvetica",      leading=15),
        "dispatch_bold":  ParagraphStyle("dispatch_bold",  fontSize=10, textColor=BLACK,      fontName="Helvetica-Bold", leading=15),
    }


def _status_color(status: str):
    return {
        "Pending":   colors.HexColor("#E67E22"),
        "Confirmed": colors.HexColor("#2980B9"),
        "Dispatched":colors.HexColor("#8E44AD"),
        "Delivered": colors.HexColor("#27AE60"),
        "Cancelled": colors.HexColor("#C0392B"),
    }.get(status, GREY_TEXT)


# ─────────────────────────────────────────────────────────────────────────────
#  CUSTOMER INVOICE PDF
# ─────────────────────────────────────────────────────────────────────────────

def generate_customer_invoice(order, output_path: str):
    """
    Generates a professional customer invoice PDF.
    `order` is an Order dataclass with .items list populated.
    """
    if not hasattr(order, "invoice_discount_amount"):
        try:
            from backend.database import get_connection
            with get_connection() as conn:
                cur = conn.cursor()
                cur.execute("""
                    SELECT COALESCE(discount_amount,0), COALESCE(price_override_notes,'')
                    FROM invoices
                    WHERE order_id=%s
                    ORDER BY id DESC
                    LIMIT 1
                """, (order.id,))
                row = cur.fetchone()
                if row:
                    order.invoice_discount_amount = float(row[0] or 0)
                    order.price_override_notes = row[1] or ""
        except Exception:
            order.invoice_discount_amount = 0
            order.price_override_notes = ""

    S = _styles()
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=18*mm, rightMargin=18*mm,
        topMargin=14*mm,  bottomMargin=14*mm,
    )
    W = A4[0] - 36*mm   # usable width
    story = []

    # ── TOP HEADER BAR ────────────────────────────────────────────────────────
    inv_num = f"INV-{order.id:05d}"
    inv_date = datetime.now().strftime("%d %B %Y")
    due_date = date.today().replace(day=min(date.today().day + 30, 28))
    due_str  = due_date.strftime("%d %B %Y")

    header_data = [[
        Paragraph("🌱 Hind Agro Products", S["company"]),
        Paragraph(f"<b>INVOICE</b>", ParagraphStyle("inv", fontSize=20, textColor=GREEN_DARK,
                                                     fontName="Helvetica-Bold", alignment=TA_RIGHT))
    ]]
    header_tbl = Table(header_data, colWidths=[W*0.55, W*0.45])
    header_tbl.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
    ]))
    story.append(header_tbl)

    tagline_data = [[
        Paragraph("Growing together, harvesting success.", S["tagline"]),
        Paragraph(f"<font color='#888888'>{inv_num}</font>",
                  ParagraphStyle("inv_num", fontSize=10, textColor=GREY_TEXT,
                                 fontName="Helvetica", alignment=TA_RIGHT))
    ]]
    tagline_tbl = Table(tagline_data, colWidths=[W*0.55, W*0.45])
    tagline_tbl.setStyle(TableStyle([("BOTTOMPADDING", (0,0), (-1,-1), 0)]))
    story.append(tagline_tbl)
    story.append(Spacer(1, 4*mm))
    story.append(HRFlowable(width="100%", thickness=2, color=GREEN_DARK, spaceAfter=4*mm))

    # ── BILL TO + INVOICE META ────────────────────────────────────────────────
    status_color = _status_color(order.status)
    meta_data = [
        [
            Paragraph("<b>BILL TO</b>", S["section"]),
            "",
            Paragraph("<b>INVOICE DETAILS</b>", S["section"]),
        ],
        [
            Paragraph(order.customer_name or "—", ParagraphStyle("cn", fontSize=12,
                      textColor=GREEN_DARK, fontName="Helvetica-Bold", leading=15)),
            "",
            Table([
                [Paragraph("Invoice No:", S["body_grey"]), Paragraph(f"<b>{inv_num}</b>", S["bold"])],
                [Paragraph("Order No:",   S["body_grey"]), Paragraph(f"<b>ORD-{order.id:05d}</b>", S["bold"])],
                [Paragraph("Date:",       S["body_grey"]), Paragraph(f"<b>{inv_date}</b>", S["bold"])],
                [Paragraph("Due Date:",   S["body_grey"]), Paragraph(f"<b>{due_str}</b>", S["bold"])],
                [Paragraph("Status:",     S["body_grey"]),
                 Paragraph(f"<b>{order.status}</b>",
                           ParagraphStyle("st", fontSize=9, textColor=status_color,
                                          fontName="Helvetica-Bold", leading=13))],
            ], colWidths=[22*mm, 38*mm],
               style=TableStyle([
                   ("ROWBACKGROUNDS", (0,0), (-1,-1), [WHITE, GREY_LIGHT]),
                   ("TOPPADDING",    (0,0), (-1,-1), 3),
                   ("BOTTOMPADDING", (0,0), (-1,-1), 3),
                   ("LEFTPADDING",   (0,0), (-1,-1), 4),
               ]))
        ],
    ]
    meta_tbl = Table(meta_data, colWidths=[W*0.38, W*0.04, W*0.58])
    meta_tbl.setStyle(TableStyle([
        ("VALIGN",        (0,0), (-1,-1), "TOP"),
        ("TOPPADDING",    (0,0), (-1,-1), 3),
        ("BOTTOMPADDING", (0,0), (-1,-1), 3),
    ]))
    story.append(meta_tbl)
    story.append(Spacer(1, 6*mm))

    # ── ITEMS TABLE ───────────────────────────────────────────────────────────
    item_header = [
        Paragraph("<b>#</b>",          S["badge"]),
        Paragraph("<b>Plant Name</b>", S["badge"]),
        Paragraph("<b>Qty</b>",        S["badge"]),
        Paragraph("<b>Unit Price</b>", S["badge"]),
        Paragraph("<b>Subtotal</b>",   S["badge"]),
    ]
    rows = [item_header]
    for i, item in enumerate(order.items, 1):
        rows.append([
            Paragraph(str(i), ParagraphStyle("cn", fontSize=9, fontName="Helvetica",
                                              alignment=TA_CENTER, textColor=GREY_TEXT)),
            Paragraph(str(item.plant_name or "—"), S["body"]),
            Paragraph(str(item.quantity),   ParagraphStyle("c", fontSize=9, fontName="Helvetica",
                                                            alignment=TA_CENTER, textColor=BLACK)),
            Paragraph(f"Rs. {float(item.unit_price):.2f}", S["right"]),
            Paragraph(f"Rs. {float(item.subtotal):.2f}",  S["right"]),
        ])

    col_w = [10*mm, W - 10*mm - 18*mm - 28*mm - 28*mm, 18*mm, 28*mm, 28*mm]
    items_tbl = Table(rows, colWidths=col_w, repeatRows=1)
    items_tbl.setStyle(TableStyle([
        # Header row
        ("BACKGROUND",    (0,0), (-1,0),  GREEN_DARK),
        ("TEXTCOLOR",     (0,0), (-1,0),  WHITE),
        ("TOPPADDING",    (0,0), (-1,0),  7),
        ("BOTTOMPADDING", (0,0), (-1,0),  7),
        ("FONTNAME",      (0,0), (-1,0),  "Helvetica-Bold"),
        ("FONTSIZE",      (0,0), (-1,0),  9),
        # Data rows
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [WHITE, GREEN_LIGHT]),
        ("TOPPADDING",    (0,1), (-1,-1), 6),
        ("BOTTOMPADDING", (0,1), (-1,-1), 6),
        ("LEFTPADDING",   (0,0), (-1,-1), 6),
        ("RIGHTPADDING",  (0,0), (-1,-1), 6),
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
        # Borders
        ("LINEBELOW",     (0,0), (-1,0),  1, GREEN_DARK),
        ("LINEBELOW",     (0,1), (-1,-1), 0.3, colors.HexColor("#D0E8C8")),
        ("BOX",           (0,0), (-1,-1), 1, colors.HexColor("#C8DFC0")),
    ]))
    story.append(items_tbl)
    story.append(Spacer(1, 4*mm))

    # ── TOTALS ────────────────────────────────────────────────────────────────
    subtotal = sum(float(i.subtotal) for i in order.items)
    discount = min(float(getattr(order, "invoice_discount_amount", 0) or 0), subtotal)
    tax       = 0.0   # adjust if GST needed
    total     = subtotal - discount + tax

    totals_data = [
        [Paragraph("Subtotal:", S["right"]),  Paragraph(f"Rs. {subtotal:.2f}", S["right"])],
    ]
    if discount > 0:
        totals_data.append([
            Paragraph("Discount:", S["right"]),
            Paragraph(f"- Rs. {discount:.2f}", S["right"]),
        ])
    totals_data.extend([
        [Paragraph("Tax (GST):", S["right"]), Paragraph(f"Rs. {tax:.2f}", S["right"])],
        [Paragraph("<b>TOTAL AMOUNT</b>", ParagraphStyle("tl", fontSize=11, textColor=GREEN_DARK,
                                                          fontName="Helvetica-Bold", alignment=TA_RIGHT)),
         Paragraph(f"<b>Rs. {total:.2f}</b>", ParagraphStyle("tv", fontSize=11, textColor=GREEN_DARK,
                                                               fontName="Helvetica-Bold", alignment=TA_RIGHT))],
    ])
    totals_tbl = Table(totals_data, colWidths=[W - 55*mm, 55*mm])
    total_row = len(totals_data) - 1
    totals_tbl.setStyle(TableStyle([
        ("TOPPADDING",    (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ("LINEABOVE",     (0,total_row), (-1,total_row),  1.5, GREEN_DARK),
        ("BACKGROUND",    (0,total_row), (-1,total_row),  GREEN_LIGHT),
        ("LEFTPADDING",   (0,0), (-1,-1), 6),
        ("RIGHTPADDING",  (0,0), (-1,-1), 6),
    ]))
    story.append(totals_tbl)
    story.append(Spacer(1, 6*mm))

    # ── FULFILMENT DETAILS (staff names + receiver) ──────────────────────────
    packed_by     = getattr(order, "packed_by",     "") or ""
    dispatched_by = getattr(order, "dispatched_by", "") or ""
    received_by   = getattr(order, "received_by",   "") or ""

    if any([packed_by, dispatched_by, received_by]):
        story.append(HRFlowable(width="100%", thickness=0.5, color=GREEN_ACCENT,
                                spaceBefore=2*mm, spaceAfter=3*mm))
        story.append(Paragraph("<b>FULFILMENT DETAILS</b>", S["section"]))
        story.append(Spacer(1, 2*mm))

        staff_rows = []
        if packed_by:
            staff_rows.append([
                Paragraph("📦  Packed By:", S["body_grey"]),
                Paragraph(f"<b>{packed_by}</b>", S["bold"]),
            ])
        if dispatched_by:
            staff_rows.append([
                Paragraph("🚚  Dispatched By:", S["body_grey"]),
                Paragraph(f"<b>{dispatched_by}</b>", S["bold"]),
            ])
        if received_by:
            staff_rows.append([
                Paragraph("✅  Received By:", S["body_grey"]),
                Paragraph(f"<b>{received_by}</b>",
                          ParagraphStyle("rcv", fontSize=9, textColor=GREEN_ACCENT,
                                         fontName="Helvetica-Bold", leading=13)),
            ])

        staff_tbl = Table(staff_rows, colWidths=[40*mm, W - 40*mm])
        staff_tbl.setStyle(TableStyle([
            ("TOPPADDING",    (0,0), (-1,-1), 4),
            ("BOTTOMPADDING", (0,0), (-1,-1), 4),
            ("LEFTPADDING",   (0,0), (-1,-1), 6),
            ("ROWBACKGROUNDS",(0,0), (-1,-1), [WHITE, GREEN_LIGHT]),
            ("BOX",           (0,0), (-1,-1), 0.5, colors.HexColor("#C8DFC0")),
        ]))
        story.append(staff_tbl)
        story.append(Spacer(1, 4*mm))

    # ── DELIVERY STATUS BOX ────────────────────────────────────────────────────
    delivery_status = getattr(order, "delivery_status", "") or ""
    failure_reason  = getattr(order, "failure_reason",  "") or ""
    delivery_notes  = getattr(order, "delivery_notes",  "") or ""

    if delivery_status:
        ds_color = {
            "Delivered":        colors.HexColor("#27AE60"),
            "Out for Delivery": colors.HexColor("#2980B9"),
            "Failed":           colors.HexColor("#C0392B"),
            "Pending":          colors.HexColor("#E67E22"),
        }.get(delivery_status, GREY_TEXT)

        ds_rows = [[
            Paragraph("Delivery Status:", S["body_grey"]),
            Paragraph(f"<b>{delivery_status}</b>",
                      ParagraphStyle("ds", fontSize=9, textColor=ds_color,
                                     fontName="Helvetica-Bold", leading=13)),
        ]]
        if failure_reason:
            ds_rows.append([
                Paragraph("Failure Reason:", S["body_grey"]),
                Paragraph(f"<b>{failure_reason}</b>", S["bold"]),
            ])
        if delivery_notes:
            ds_rows.append([
                Paragraph("Notes:", S["body_grey"]),
                Paragraph(delivery_notes, S["body"]),
            ])

        ds_tbl = Table(ds_rows, colWidths=[40*mm, W - 40*mm])
        ds_tbl.setStyle(TableStyle([
            ("TOPPADDING",    (0,0), (-1,-1), 4),
            ("BOTTOMPADDING", (0,0), (-1,-1), 4),
            ("LEFTPADDING",   (0,0), (-1,-1), 6),
            ("BACKGROUND",    (0,0), (-1,-1), GREEN_LIGHT),
            ("BOX",           (0,0), (-1,-1), 0.5, colors.HexColor("#C8DFC0")),
        ]))
        story.append(ds_tbl)
        story.append(Spacer(1, 4*mm))

    # ── NOTES ─────────────────────────────────────────────────────────────────
    price_note = getattr(order, "price_override_notes", "") or ""
    if price_note:
        story.append(Paragraph("<b>Price / Discount Note:</b>", S["section"]))
        story.append(Spacer(1, 2*mm))
        story.append(Paragraph(price_note, S["body_grey"]))
        story.append(Spacer(1, 4*mm))

    if order.notes:
        story.append(Paragraph("<b>Notes:</b>", S["section"]))
        story.append(Spacer(1, 2*mm))
        story.append(Paragraph(order.notes, S["body_grey"]))
        story.append(Spacer(1, 4*mm))

    # ── FOOTER ────────────────────────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=1, color=GREEN_ACCENT, spaceBefore=4*mm, spaceAfter=3*mm))
    story.append(Paragraph(
        "Thank you for your order!  |  Hind Agro Products  |  Contact: +91 00000 00000  |  info@hindagroproducts.com",
        S["footer"]
    ))
    story.append(Paragraph(
        "Plants are perishable. Please inspect upon delivery. All sales final after 24 hours.",
        ParagraphStyle("disc", fontSize=7, textColor=GREY_TEXT, fontName="Helvetica",
                       alignment=TA_CENTER, leading=10)
    ))

    doc.build(story)


# ─────────────────────────────────────────────────────────────────────────────
#  DISPATCH SLIP PDF
# ─────────────────────────────────────────────────────────────────────────────

def generate_dispatch_slip(order, output_path: str):
    """
    Generates a clean dispatch/packing slip for the warehouse/dispatch team.
    """
    S = _styles()
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=18*mm, rightMargin=18*mm,
        topMargin=14*mm,  bottomMargin=14*mm,
    )
    W = A4[0] - 36*mm
    story = []

    # ── HEADER ────────────────────────────────────────────────────────────────
    story.append(Paragraph("DISPATCH / PACKING SLIP", S["dispatch_title"]))
    story.append(Paragraph("Hind Agro Products  —  Internal Use Only",
                            ParagraphStyle("sub", fontSize=9, textColor=GREY_TEXT,
                                           fontName="Helvetica", leading=12)))
    story.append(HRFlowable(width="100%", thickness=2, color=GREEN_DARK,
                             spaceBefore=3*mm, spaceAfter=4*mm))

    # ── ORDER META BOX ─────────────────────────────────────────────────────────
    now = datetime.now().strftime("%d %b %Y, %I:%M %p")
    meta = [
        ["Order #",    f"ORD-{order.id:05d}",  "Date Printed:", now],
        ["Customer:",  order.customer_name or "—", "Order Status:", order.status],
    ]
    meta_tbl = Table(meta, colWidths=[24*mm, W*0.38, 28*mm, W*0.35])
    meta_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), GREEN_LIGHT),
        ("FONTNAME",      (0,0), (0,-1),  "Helvetica-Bold"),
        ("FONTNAME",      (2,0), (2,-1),  "Helvetica-Bold"),
        ("FONTSIZE",      (0,0), (-1,-1), 10),
        ("TEXTCOLOR",     (0,0), (0,-1),  GREEN_DARK),
        ("TEXTCOLOR",     (2,0), (2,-1),  GREEN_DARK),
        ("TOPPADDING",    (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ("LEFTPADDING",   (0,0), (-1,-1), 8),
        ("BOX",           (0,0), (-1,-1), 1.5, GREEN_ACCENT),
        ("INNERGRID",     (0,0), (-1,-1), 0.5, colors.HexColor("#C8DFC0")),
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
    ]))
    story.append(meta_tbl)
    story.append(Spacer(1, 6*mm))

    # ── ITEMS CHECKLIST ────────────────────────────────────────────────────────
    story.append(Paragraph("ITEMS TO PACK", ParagraphStyle(
        "ph", fontSize=11, textColor=GREEN_DARK, fontName="Helvetica-Bold", leading=16)))
    story.append(Spacer(1, 2*mm))

    check_header = [
        Paragraph("<b>   </b>", S["badge"]),   # checkbox col
        Paragraph("<b>#</b>", S["badge"]),
        Paragraph("<b>Plant Name</b>", S["badge"]),
        Paragraph("<b>Category</b>", S["badge"]),
        Paragraph("<b>QTY</b>", S["badge"]),
        Paragraph("<b>Packed By</b>", S["badge"]),
    ]
    check_rows = [check_header]
    for i, item in enumerate(order.items, 1):
        check_rows.append([
            Paragraph("☐", ParagraphStyle("cb", fontSize=14, fontName="Helvetica",
                                           alignment=TA_CENTER, textColor=GREEN_DARK)),
            Paragraph(str(i), ParagraphStyle("n", fontSize=10, fontName="Helvetica",
                                              alignment=TA_CENTER, textColor=GREY_TEXT)),
            Paragraph(str(item.plant_name or "—"),
                      ParagraphStyle("pn", fontSize=10, fontName="Helvetica-Bold",
                                     textColor=BLACK, leading=14)),
            Paragraph("—", ParagraphStyle("cat", fontSize=10, fontName="Helvetica",
                                           textColor=GREY_TEXT, leading=14)),
            Paragraph(f"<b>{item.quantity}</b>",
                      ParagraphStyle("qty", fontSize=11, fontName="Helvetica-Bold",
                                     alignment=TA_CENTER, textColor=GREEN_DARK)),
            Paragraph("________________",
                      ParagraphStyle("pb", fontSize=9, fontName="Helvetica",
                                     textColor=GREY_TEXT, alignment=TA_CENTER)),
        ])

    col_w = [10*mm, 10*mm, W*0.35, W*0.20, 18*mm, W*0.20]
    check_tbl = Table(check_rows, colWidths=col_w, repeatRows=1)
    check_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0),  GREEN_DARK),
        ("TEXTCOLOR",     (0,0), (-1,0),  WHITE),
        ("TOPPADDING",    (0,0), (-1,0),  8),
        ("BOTTOMPADDING", (0,0), (-1,0),  8),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [WHITE, GREEN_LIGHT]),
        ("TOPPADDING",    (0,1), (-1,-1), 8),
        ("BOTTOMPADDING", (0,1), (-1,-1), 8),
        ("LEFTPADDING",   (0,0), (-1,-1), 6),
        ("RIGHTPADDING",  (0,0), (-1,-1), 6),
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
        ("BOX",           (0,0), (-1,-1), 1.5, colors.HexColor("#C8DFC0")),
        ("LINEBELOW",     (0,0), (-1,0),  1.5, GREEN_DARK),
        ("LINEBELOW",     (0,1), (-1,-1), 0.4, colors.HexColor("#D0E8C8")),
    ]))
    story.append(check_tbl)
    story.append(Spacer(1, 8*mm))

    # ── SIGN-OFF BOX ──────────────────────────────────────────────────────────
    signoff_data = [[
        Table([
            [Paragraph("<b>Packed By:</b>", S["dispatch_bold"])],
            [Paragraph("Name: ____________________________", S["dispatch_body"])],
            [Paragraph("Signature: _______________________", S["dispatch_body"])],
            [Paragraph("Date/Time: _______________________", S["dispatch_body"])],
        ], style=TableStyle([("TOPPADDING",(0,0),(-1,-1),4),("BOTTOMPADDING",(0,0),(-1,-1),4)])),

        Table([
            [Paragraph("<b>Dispatched By:</b>", S["dispatch_bold"])],
            [Paragraph("Name: ____________________________", S["dispatch_body"])],
            [Paragraph("Signature: _______________________", S["dispatch_body"])],
            [Paragraph("Vehicle No: ______________________", S["dispatch_body"])],
        ], style=TableStyle([("TOPPADDING",(0,0),(-1,-1),4),("BOTTOMPADDING",(0,0),(-1,-1),4)])),

        Table([
            [Paragraph("<b>Received By (Customer):</b>", S["dispatch_bold"])],
            [Paragraph("Name: ____________________________", S["dispatch_body"])],
            [Paragraph("Signature: _______________________", S["dispatch_body"])],
            [Paragraph("Date/Time: _______________________", S["dispatch_body"])],
        ], style=TableStyle([("TOPPADDING",(0,0),(-1,-1),4),("BOTTOMPADDING",(0,0),(-1,-1),4)])),
    ]]
    signoff_tbl = Table(signoff_data, colWidths=[W/3, W/3, W/3])
    signoff_tbl.setStyle(TableStyle([
        ("BOX",           (0,0), (0,0),   1, colors.HexColor("#C8DFC0")),
        ("BOX",           (1,0), (1,0),   1, colors.HexColor("#C8DFC0")),
        ("BOX",           (2,0), (2,0),   1, colors.HexColor("#C8DFC0")),
        ("BACKGROUND",    (0,0), (-1,-1), GREEN_LIGHT),
        ("TOPPADDING",    (0,0), (-1,-1), 8),
        ("BOTTOMPADDING", (0,0), (-1,-1), 8),
        ("LEFTPADDING",   (0,0), (-1,-1), 8),
        ("VALIGN",        (0,0), (-1,-1), "TOP"),
    ]))
    story.append(signoff_tbl)

    # ── FOOTER ────────────────────────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=1, color=GREEN_ACCENT,
                             spaceBefore=6*mm, spaceAfter=3*mm))
    story.append(Paragraph(
        f"Hind Agro Products  |  Printed: {now}  |  Order ORD-{order.id:05d}  |  CONFIDENTIAL - INTERNAL USE",
        S["footer"]
    ))

    doc.build(story)
