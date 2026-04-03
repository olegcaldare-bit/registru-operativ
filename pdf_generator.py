from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import io
from datetime import datetime

LUNI_RO = ["", "Ianuarie", "Februarie", "Martie", "Aprilie", "Mai", "Iunie",
           "Iulie", "August", "Septembrie", "Octombrie", "Noiembrie", "Decembrie"]

def fmt_dt(val):
    if not val:
        return "—"
    try:
        dt = datetime.fromisoformat(str(val))
        return dt.strftime("%d.%m.%Y\n%H:%M")
    except:
        return str(val)

def fmt_date(val):
    if not val:
        return "—"
    try:
        dt = datetime.fromisoformat(str(val))
        return dt.strftime("%d.%m.%Y")
    except:
        return str(val)

def generate_monthly_pdf(fise, luna, an):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=1*cm,
        rightMargin=1*cm,
        topMargin=1.5*cm,
        bottomMargin=1.5*cm,
        title=f"Registru Operativ {LUNI_RO[luna]} {an}"
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("title", fontSize=13, alignment=TA_CENTER, spaceAfter=4, fontName="Helvetica-Bold")
    sub_style = ParagraphStyle("sub", fontSize=10, alignment=TA_CENTER, spaceAfter=12, fontName="Helvetica")
    cell_style = ParagraphStyle("cell", fontSize=7, fontName="Helvetica", leading=9)
    cell_bold = ParagraphStyle("cellb", fontSize=7, fontName="Helvetica-Bold", leading=9)

    elements = []
    elements.append(Paragraph("Anexa nr.2", sub_style))
    elements.append(Paragraph("REGISTRU OPERATIV", title_style))
    elements.append(Paragraph("pentru efectuarea lucrărilor la sistemelor de evidență", sub_style))
    elements.append(Paragraph(f"Luna: <b>{LUNI_RO[luna]} {an}</b>", sub_style))
    elements.append(Spacer(1, 0.3*cm))

    # Header
    headers = [
        Paragraph("Nr.\nenreg.", cell_bold),
        Paragraph("Data\nemiterii", cell_bold),
        Paragraph("Denumirea lucrărilor", cell_bold),
        Paragraph("Locul desfășurării\n(adresă poștală / electrică)", cell_bold),
        Paragraph("Personalul care execută\n(Șef lucrări + Membri, grupa)", cell_bold),
        Paragraph("Admitent", cell_bold),
        Paragraph("Începutul lucrării\nData, ora", cell_bold),
        Paragraph("Sfârșitul lucrării\nData, ora", cell_bold),
        Paragraph("Semn.\nadmitent", cell_bold),
        Paragraph("Stare", cell_bold),
    ]

    data = [headers]

    for f in fise:
        sef = f.get("sef_lucrari", {}) or {}
        admitent = f.get("admitent", {}) or {}
        tip = f.get("tip_lucrare", {}) or {}
        membri = f.get("membri", []) or []

        personal = f"{sef.get('nume_complet','—')} (gr.{sef.get('grupa_securitate','?')})"
        for m in membri:
            personal += f"\n{m.get('nume_complet','—')} (gr.{m.get('grupa_securitate','?')})"

        adresa = ""
        if f.get("adresa_postala"):
            adresa += f.get("adresa_postala", "")
        if f.get("adresa_electrica"):
            adresa += f"\n{f.get('adresa_electrica','')}"

        # Semnătură admitent
        semn = ""
        if f.get("semnat_sfarsit_de_user"):
            u = f["semnat_sfarsit_de_user"]
            semn = f"✓ {u.get('nume_complet','')}\n{fmt_dt(f.get('semnat_sfarsit_la'))}"
        elif f.get("semnat_inceput_de_user"):
            u = f["semnat_inceput_de_user"]
            semn = f"✓ {u.get('nume_complet','')}\n{fmt_dt(f.get('semnat_inceput_la'))}"

        stare = f.get("stare", "").upper()
        stare_color = {"EMIS": "#2563eb", "IN_LUCRU": "#d97706", "SEMNAT": "#16a34a", "ANULAT": "#dc2626"}.get(stare, "#000")

        row = [
            Paragraph(str(f.get("nr_ordine", "")), cell_style),
            Paragraph(fmt_date(f.get("data_emitere")), cell_style),
            Paragraph(tip.get("denumire", "—"), cell_style),
            Paragraph(adresa or "—", cell_style),
            Paragraph(personal, cell_style),
            Paragraph(admitent.get("nume_complet", "—"), cell_style),
            Paragraph(fmt_dt(f.get("ora_inceput")), cell_style),
            Paragraph(fmt_dt(f.get("ora_sfarsit")), cell_style),
            Paragraph(semn, cell_style),
            Paragraph(stare, cell_bold),
        ]
        data.append(row)

    col_widths = [1.2*cm, 2*cm, 4.5*cm, 5*cm, 5.5*cm, 3.5*cm, 2.8*cm, 2.8*cm, 3.5*cm, 1.8*cm]

    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#1e3a5f")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 7),
        ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#94a3b8")),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#f0f4f8")]),
        ("TOPPADDING", (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ("LEFTPADDING", (0,0), (-1,-1), 3),
        ("RIGHTPADDING", (0,0), (-1,-1), 3),
    ]))

    elements.append(table)
    elements.append(Spacer(1, 1*cm))
    elements.append(Paragraph(f"Generat la: {datetime.now().strftime('%d.%m.%Y %H:%M')}", sub_style))

    doc.build(elements)
    buffer.seek(0)
    return buffer.read()

def generate_fisa_pdf(fisa):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=2*cm,
        rightMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("t", fontSize=14, alignment=TA_CENTER, fontName="Helvetica-Bold", spaceAfter=6)
    label_style = ParagraphStyle("l", fontSize=9, fontName="Helvetica-Bold")
    value_style = ParagraphStyle("v", fontSize=9, fontName="Helvetica")
    center_style = ParagraphStyle("c", fontSize=9, fontName="Helvetica", alignment=TA_CENTER)

    sef = fisa.get("sef_lucrari") or {}
    admitent = fisa.get("admitent") or {}
    tip = fisa.get("tip_lucrare") or {}
    membri = fisa.get("membri") or []

    elements = []
    elements.append(Paragraph("FIȘĂ DE LUCRĂRI", title_style))
    elements.append(Paragraph(f"Nr. {fisa.get('nr_ordine')} / {fmt_date(fisa.get('data_emitere'))}", center_style))
    elements.append(Spacer(1, 0.5*cm))

    info_data = [
        [Paragraph("Denumirea lucrărilor:", label_style), Paragraph(tip.get("denumire", "—"), value_style)],
        [Paragraph("Adresă poștală:", label_style), Paragraph(fisa.get("adresa_postala") or "—", value_style)],
        [Paragraph("Adresă electrică:", label_style), Paragraph(fisa.get("adresa_electrica") or "—", value_style)],
        [Paragraph("Șef lucrări:", label_style), Paragraph(f"{sef.get('nume_complet','—')} — Grupa {sef.get('grupa_securitate','?')}", value_style)],
        [Paragraph("Admitent:", label_style), Paragraph(admitent.get("nume_complet", "—"), value_style)],
    ]

    for i, m in enumerate(membri, 1):
        info_data.append([
            Paragraph(f"Membru {i}:", label_style),
            Paragraph(f"{m.get('nume_complet','—')} — Grupa {m.get('grupa_securitate','?')}", value_style)
        ])

    info_table = Table(info_data, colWidths=[5*cm, 12*cm])
    info_table.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("TOPPADDING", (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LINEBELOW", (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 0.8*cm))

    # Semnături
    semn_data = [
        [
            Paragraph("ÎNCEPUT LUCRARE", ParagraphStyle("sh", fontSize=10, fontName="Helvetica-Bold", alignment=TA_CENTER)),
            Paragraph("FINALIZARE LUCRARE", ParagraphStyle("sh", fontSize=10, fontName="Helvetica-Bold", alignment=TA_CENTER)),
        ],
        [
            Paragraph(f"Data/Ora: {fmt_dt(fisa.get('ora_inceput'))}" if fisa.get("ora_inceput") else "Data/Ora: ___________", center_style),
            Paragraph(f"Data/Ora: {fmt_dt(fisa.get('ora_sfarsit'))}" if fisa.get("ora_sfarsit") else "Data/Ora: ___________", center_style),
        ],
        [
            Paragraph(f"Confirmat de: {(fisa.get('semnat_inceput_de_user') or {}).get('nume_complet','___________')}", center_style),
            Paragraph(f"Confirmat de: {(fisa.get('semnat_sfarsit_de_user') or {}).get('nume_complet','___________')}", center_style),
        ],
        [
            Paragraph(f"Semnătură electronică: ✓" if fisa.get("semnat_inceput_la") else "Semnătură: __________", center_style),
            Paragraph(f"Semnătură electronică: ✓" if fisa.get("semnat_sfarsit_la") else "Semnătură: __________", center_style),
        ],
    ]

    semn_table = Table(semn_data, colWidths=[8.5*cm, 8.5*cm])
    semn_table.setStyle(TableStyle([
        ("BOX", (0,0), (0,-1), 1, colors.HexColor("#1e3a5f")),
        ("BOX", (1,0), (1,-1), 1, colors.HexColor("#1e3a5f")),
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#1e3a5f")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING", (0,0), (-1,-1), 8),
        ("BOTTOMPADDING", (0,0), (-1,-1), 8),
        ("LINEBELOW", (0,1), (-1,-2), 0.5, colors.HexColor("#e2e8f0")),
    ]))
    elements.append(semn_table)
    elements.append(Spacer(1, 0.5*cm))

    stare = fisa.get("stare", "").upper()
    elements.append(Paragraph(f"Stare: <b>{stare}</b> | Generat: {datetime.now().strftime('%d.%m.%Y %H:%M')}", center_style))

    doc.build(elements)
    buffer.seek(0)
    return buffer.read()
