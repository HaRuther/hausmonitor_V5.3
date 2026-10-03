from __future__ import annotations

from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Iterable

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image as RImage,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

BLUE = "#17365d"
ACCENT = "#2878cc"
GREEN = "#059669"
ORANGE = "#d97706"
RED = "#c62828"
LIGHT_BLUE = "#7fc3ff"
MUTED = "#667085"


def f(value, digits=3):
    return "–" if value is None else f"{value:.{digits}f}"


def _dt(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def _safe_text(value):
    text = "" if value is None else str(value)
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def tab(rows, widths=None):
    safe_rows = []
    for row in rows:
        safe_rows.append(
            [cell if hasattr(cell, "wrapOn") else Paragraph(_safe_text(cell), _table_style()) for cell in row]
        )
    table = Table(safe_rows, repeatRows=1, colWidths=widths, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(BLUE)),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#9aa7b4")),
                ("FONTSIZE", (0, 0), (-1, -1), 7.5),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f7fa")]),
            ]
        )
    )
    return table


def _table_style():
    return ParagraphStyle(
        "ReportTableCell",
        fontName="Helvetica",
        fontSize=7.5,
        leading=9,
        textColor=colors.HexColor("#172033"),
    )


def _figure_image(fig, width=181 * mm, height=82 * mm):
    buffer = BytesIO()
    fig.savefig(buffer, format="png", dpi=170, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    buffer.seek(0)
    image = RImage(buffer, width=width, height=height)
    image._source_buffer = buffer
    return image


def _format_date_axis(ax):
    locator = mdates.AutoDateLocator(minticks=3, maxticks=8)
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))
    ax.grid(True, axis="y", color="#d9e1ea", linewidth=0.7)
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(axis="both", labelsize=8)


def build_level_chart(campaigns):
    rows = []
    for campaign in campaigns:
        date = _dt(campaign.get("measured_at"))
        house = campaign.get("stats", {}).get("house", {})
        delta = house.get("delta")
        se = house.get("se")
        if date is not None and delta is not None:
            rows.append((date, float(delta), None if se is None else float(se)))
    if not rows:
        return None
    rows.sort(key=lambda item: item[0])
    dates = [row[0] for row in rows]
    delta = [row[1] for row in rows]
    low = [row[1] - row[2] if row[2] is not None else row[1] for row in rows]
    high = [row[1] + row[2] if row[2] is not None else row[1] for row in rows]

    fig, ax = plt.subplots(figsize=(8.6, 3.7))
    ax.fill_between(dates, low, high, color=LIGHT_BLUE, alpha=0.35, label="± Standardfehler")
    ax.plot(dates, delta, color=ACCENT, linewidth=2.2, marker="o", markersize=4, label="Änderung Haus")
    ax.axhline(0, color="#59636e", linewidth=0.9)
    ax.set_title("Hausänderung gegenüber der Referenz")
    ax.set_ylabel("Änderung [mm]")
    _format_date_axis(ax)
    ax.legend(loc="best", fontsize=8, frameon=False)
    fig.tight_layout()
    return _figure_image(fig)


def build_sd_chart(campaigns):
    rows = []
    for campaign in campaigns:
        date = _dt(campaign.get("measured_at"))
        stats = campaign.get("stats", {})
        sw = stats.get("SW", {}).get("sd")
        so = stats.get("SO", {}).get("sd")
        if date is not None and (sw is not None or so is not None):
            rows.append((date, sw, so))
    if not rows:
        return None
    rows.sort(key=lambda item: item[0])
    dates = [row[0] for row in rows]
    sw = [float("nan") if row[1] is None else float(row[1]) for row in rows]
    so = [float("nan") if row[2] is None else float(row[2]) for row in rows]

    fig, ax = plt.subplots(figsize=(8.6, 3.5))
    ax.plot(dates, sw, color=GREEN, linewidth=2.0, marker="o", markersize=3.5, label="SD SW")
    ax.plot(dates, so, color=ORANGE, linewidth=2.0, marker="o", markersize=3.5, label="SD SO")
    ax.set_title("Standardabweichung der Rohmessungen")
    ax.set_ylabel("Standardabweichung [mm]")
    _format_date_axis(ax)
    ax.legend(loc="best", fontsize=8, frameon=False)
    fig.tight_layout()
    return _figure_image(fig, height=78 * mm)


def build_crack_chart(point):
    rows = []
    for measurement in point.get("measurements", []):
        date = _dt(measurement.get("measured_at"))
        value = measurement.get("value")
        if date is not None and value is not None:
            rows.append((date, float(value)))
    if not rows:
        return None
    rows.sort(key=lambda item: item[0])
    dates = [row[0] for row in rows]
    values = [row[1] for row in rows]
    baseline = point.get("baseline")
    if baseline is None:
        baseline = values[0]
    baseline = float(baseline)
    warning = point.get("warning_delta")
    alarm = point.get("alarm_delta")

    fig, ax = plt.subplots(figsize=(8.6, 3.4))
    ax.plot(dates, values, color=ACCENT, linewidth=2.2, marker="o", markersize=4, label="Messwert")
    ax.axhline(baseline, color="#59636e", linewidth=1.0, linestyle="--", label="Referenz")
    if warning is not None:
        warning = abs(float(warning))
        ax.axhline(baseline + warning, color=ORANGE, linewidth=1.1, linestyle="--", label="Warnbereich")
        ax.axhline(baseline - warning, color=ORANGE, linewidth=1.1, linestyle="--")
    if alarm is not None:
        alarm = abs(float(alarm))
        ax.axhline(baseline + alarm, color=RED, linewidth=1.1, linestyle=":", label="Alarmbereich")
        ax.axhline(baseline - alarm, color=RED, linewidth=1.1, linestyle=":")
    ax.set_title(f"Rissverlauf: {point.get('name', 'Messstelle')}")
    ax.set_ylabel(f"Messwert [{point.get('unit') or 'mm'}]")
    _format_date_axis(ax)
    ax.legend(loc="best", fontsize=7.5, frameon=False, ncol=2)
    fig.tight_layout()
    return _figure_image(fig, height=74 * mm)


def _image_flowable(path, max_width=82 * mm, max_height=58 * mm):
    path = Path(path)
    if not path.is_file():
        return None
    try:
        image = RImage(str(path))
        image._restrictSize(max_width, max_height)
        return image
    except Exception:
        return None


def _photo_pair(first_path, latest_path, first_label, latest_label, styles):
    first = _image_flowable(first_path)
    latest = _image_flowable(latest_path)
    cells = []
    for image, label in ((first, first_label), (latest, latest_label)):
        content = []
        if image is not None:
            content.append(image)
        content.append(Spacer(1, 1.5 * mm))
        content.append(Paragraph(_safe_text(label), styles["Caption"]))
        cells.append(content)
    table = Table([cells], colWidths=[88 * mm, 88 * mm], hAlign="LEFT")
    table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("BOX", (0, 0), (-1, -1), 0.25, colors.HexColor("#d9e1ea")), ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#d9e1ea")), ("PADDING", (0, 0), (-1, -1), 5)]))
    return table


def _level_photo_paths(level_dir, campaign_id):
    root = Path(level_dir)
    if not root.is_dir():
        return []
    allowed = {".jpg", ".jpeg", ".png", ".webp"}
    return sorted(path for path in root.glob(f"level-{campaign_id}-*") if path.suffix.lower() in allowed)


def _period(campaigns, points):
    dates = []
    for campaign in campaigns:
        date = _dt(campaign.get("measured_at"))
        if date:
            dates.append(date)
    for point in points:
        for measurement in point.get("measurements", []):
            date = _dt(measurement.get("measured_at"))
            if date:
                dates.append(date)
    if not dates:
        return "Keine datierten Messungen"
    return f"{min(dates):%d.%m.%Y} bis {max(dates):%d.%m.%Y}"


def _styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="CoverTitle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=28, leading=32, textColor=colors.HexColor(BLUE), alignment=TA_CENTER, spaceAfter=7 * mm))
    styles.add(ParagraphStyle(name="CoverSub", parent=styles["Normal"], fontSize=14, leading=18, textColor=colors.HexColor(MUTED), alignment=TA_CENTER, spaceAfter=12 * mm))
    styles.add(ParagraphStyle(name="Caption", parent=styles["Normal"], fontSize=7.5, leading=9, textColor=colors.HexColor(MUTED), alignment=TA_CENTER))
    styles.add(ParagraphStyle(name="Small", parent=styles["Normal"], fontSize=8, leading=10, textColor=colors.HexColor(MUTED)))
    styles["Heading1"].textColor = colors.HexColor(BLUE)
    styles["Heading2"].textColor = colors.HexColor(BLUE)
    styles["Heading3"].textColor = colors.HexColor(BLUE)
    return styles


def _page_number(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#d9e1ea"))
    canvas.line(12 * mm, 10 * mm, A4[0] - 12 * mm, 10 * mm)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(colors.HexColor(MUTED))
    canvas.drawString(12 * mm, 6 * mm, "Hausmonitor Monitoringbericht")
    canvas.drawRightString(A4[0] - 12 * mm, 6 * mm, f"Seite {doc.page}")
    canvas.restoreState()


def make_report(cs, pts, assessment, level_dir, crack_dir, year=None):
    campaigns = list(cs)
    points = list(pts)
    if year:
        campaigns = [c for c in campaigns if str(c.get("measured_at", "")).startswith(str(year))]
        filtered_points = []
        for point in points:
            clone = dict(point)
            clone["measurements"] = [m for m in point.get("measurements", []) if str(m.get("measured_at", "")).startswith(str(year))]
            filtered_points.append(clone)
        points = filtered_points

    output = BytesIO()
    doc = SimpleDocTemplate(output, pagesize=A4, rightMargin=12 * mm, leftMargin=12 * mm, topMargin=13 * mm, bottomMargin=14 * mm, title=f"Hausmonitor Bericht{' ' + str(year) if year else ''}", author="Hausmonitor")
    styles = _styles()
    story = []

    # Titelseite
    story.extend([Spacer(1, 24 * mm), Paragraph("HAUSMONITOR", styles["CoverTitle"]), Paragraph(f"Monitoringbericht{' ' + str(year) if year else ''}", styles["CoverSub"])])
    summary = [
        ["Berichtszeitraum", _period(campaigns, points)],
        ["Erstellt am", datetime.now().strftime("%d.%m.%Y %H:%M")],
        ["Nivellement-Messreihen", str(len(campaigns))],
        ["Rissmessstellen", str(len(points))],
    ]
    cover_table = Table(summary, colWidths=[62 * mm, 90 * mm], hAlign="CENTER")
    cover_table.setStyle(TableStyle([("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eaf2fb")), ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor(BLUE)), ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"), ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#c8d4df")), ("PADDING", (0, 0), (-1, -1), 8), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    story.extend([cover_table, Spacer(1, 12 * mm), Paragraph("Automatische Lagebeurteilung", styles["Heading2"]), Paragraph(_safe_text(assessment), styles["BodyText"]), Spacer(1, 16 * mm), Paragraph("Hinweis: Statistische Bewertungen unterstützen das Monitoring, ersetzen aber keine bautechnische oder geotechnische Begutachtung.", styles["Small"]), PageBreak()])

    # Nivellement
    story.extend([Paragraph("Nivellement", styles["Heading1"]), Spacer(1, 2 * mm)])
    if campaigns:
        rows = [["Datum", "Haus", "Δ", "SE", "SNR", "Terrasse", "GW", "Luft"]]
        for campaign in campaigns:
            stats = campaign.get("stats", {})
            house = stats.get("house", {})
            terrace = stats.get("terrace", {})
            rows.append([str(campaign.get("measured_at", "")).replace("T", " "), f(house.get("value")), f(house.get("delta")), f(house.get("se")), f(house.get("snr"), 2), f(terrace.get("value")), f(campaign.get("groundwater")), f(campaign.get("air_temp"), 1)])
        story.extend([tab(rows, [32 * mm, 20 * mm, 18 * mm, 18 * mm, 17 * mm, 22 * mm, 18 * mm, 17 * mm]), Spacer(1, 5 * mm)])
        level_chart = build_level_chart(campaigns)
        if level_chart:
            story.extend([Paragraph("Änderung mit Fehlerband", styles["Heading2"]), level_chart, Spacer(1, 4 * mm)])
        sd_chart = build_sd_chart(campaigns)
        if sd_chart:
            story.extend([Paragraph("Messstreuung", styles["Heading2"]), sd_chart, Spacer(1, 4 * mm)])

        photo_sections = []
        for campaign in campaigns:
            photos = _level_photo_paths(level_dir, campaign.get("id"))
            if not photos:
                continue
            photo_sections.extend([Paragraph(f"Messreihe {_safe_text(str(campaign.get('measured_at', '')).replace('T', ' '))}", styles["Heading3"])])
            row = []
            for path in photos:
                image = _image_flowable(path, 82 * mm, 58 * mm)
                if image:
                    row.append([image, Paragraph(_safe_text(path.name), styles["Caption"])])
                if len(row) == 2:
                    photo_sections.append(Table([row], colWidths=[88 * mm, 88 * mm], hAlign="LEFT", style=[("VALIGN", (0, 0), (-1, -1), "TOP"), ("PADDING", (0, 0), (-1, -1), 4)]))
                    row = []
            if row:
                while len(row) < 2:
                    row.append("")
                photo_sections.append(Table([row], colWidths=[88 * mm, 88 * mm], hAlign="LEFT", style=[("VALIGN", (0, 0), (-1, -1), "TOP"), ("PADDING", (0, 0), (-1, -1), 4)]))
        if photo_sections:
            story.extend([PageBreak(), Paragraph("Nivellement-Fotos", styles["Heading1"]), *photo_sections])
    else:
        story.append(Paragraph("Für den gewählten Zeitraum liegen keine Nivellement-Messreihen vor.", styles["BodyText"]))

    # Rissmonitoring
    story.extend([PageBreak(), Paragraph("Rissmonitoring", styles["Heading1"]), Spacer(1, 2 * mm)])
    if not points:
        story.append(Paragraph("Es sind keine Rissmessstellen vorhanden.", styles["BodyText"]))
    for index, point in enumerate(points):
        if index:
            story.append(PageBreak())
        measurements = point.get("measurements", [])
        heading = _safe_text(point.get("name") or "Messstelle")
        meta = f"Ort: {_safe_text(point.get('location') or '–')} · Art: {_safe_text(point.get('crack_type') or '–')} · Status: {_safe_text(point.get('status') or '–')} · Änderung: {f(point.get('delta'))} {_safe_text(point.get('unit') or 'mm')}"
        story.extend([Paragraph(heading, styles["Heading2"]), Paragraph(meta, styles["BodyText"]), Spacer(1, 3 * mm)])
        chart = build_crack_chart(point)
        if chart:
            story.extend([chart, Spacer(1, 3 * mm)])
        if measurements:
            rows = [["Datum", "Temp.", "Wert", "Δ", "Notiz"]]
            for measurement in measurements:
                rows.append([str(measurement.get("measured_at", "")).replace("T", " "), f(measurement.get("air_temp"), 1), f(measurement.get("value")), f(measurement.get("delta")), measurement.get("notes") or ""])
            story.extend([tab(rows, [38 * mm, 18 * mm, 21 * mm, 21 * mm, 76 * mm]), Spacer(1, 4 * mm)])
        else:
            story.append(Paragraph("Für den gewählten Zeitraum liegen keine Messungen vor.", styles["BodyText"]))

        photos = [m for m in measurements if m.get("photo_filename") and (Path(crack_dir) / m["photo_filename"]).is_file()]
        if photos:
            first = photos[0]
            latest = photos[-1]
            story.extend([Paragraph("Fotovergleich", styles["Heading3"]), _photo_pair(Path(crack_dir) / first["photo_filename"], Path(crack_dir) / latest["photo_filename"], f"Erstes Foto · {str(first.get('measured_at', '')).replace('T', ' ')}", f"Aktuelles Foto · {str(latest.get('measured_at', '')).replace('T', ' ')}", styles)])

    story.extend([Spacer(1, 6 * mm), Paragraph("Dokumentationshinweis", styles["Heading2"]), Paragraph("Dieser Bericht wurde aus den in Hausmonitor gespeicherten Messreihen, statistischen Kennwerten und Bilddateien erzeugt. Fehlende Werte werden mit einem Gedankenstrich dargestellt.", styles["Small"])])
    doc.build(story, onFirstPage=_page_number, onLaterPages=_page_number)
    output.seek(0)
    return output
