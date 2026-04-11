"""
PDF generation service for executive domain analysis exports.
"""

import io
from datetime import datetime
from typing import Any, Dict, Iterable, List

import structlog
from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

logger = structlog.get_logger(__name__)


class PDFService:
    """Service for generating executive PDF reports from hydrated report data."""

    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _setup_custom_styles(self):
        self.styles.add(
            ParagraphStyle(
                name="ReportTitle",
                parent=self.styles["Title"],
                fontSize=24,
                leading=30,
                textColor=HexColor("#0f172a"),
                alignment=TA_CENTER,
                spaceAfter=20,
            )
        )
        self.styles.add(
            ParagraphStyle(
                name="SectionHeader",
                parent=self.styles["Heading2"],
                fontSize=15,
                leading=19,
                textColor=HexColor("#0f172a"),
                backColor=HexColor("#f8fafc"),
                borderPadding=8,
                spaceBefore=10,
                spaceAfter=10,
            )
        )
        self.styles.add(
            ParagraphStyle(
                name="Muted",
                parent=self.styles["Normal"],
                fontSize=9,
                leading=12,
                textColor=HexColor("#475569"),
            )
        )
        self.styles.add(
            ParagraphStyle(
                name="Body",
                parent=self.styles["Normal"],
                fontSize=10,
                leading=15,
                textColor=HexColor("#111827"),
            )
        )
        self.styles.add(
            ParagraphStyle(
                name="BulletItem",
                parent=self.styles["Normal"],
                fontSize=10,
                leading=14,
                leftIndent=12,
                bulletIndent=0,
                textColor=HexColor("#111827"),
            )
        )

    def generate_domain_analysis_pdf(self, domain: str, report_data: Dict[str, Any]) -> bytes:
        """Generate an executive PDF report for a domain."""
        try:
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(
                buffer,
                pagesize=A4,
                rightMargin=0.6 * inch,
                leftMargin=0.6 * inch,
                topMargin=0.6 * inch,
                bottomMargin=0.6 * inch,
            )

            story: List[Any] = []
            story.extend(self._build_header(domain, report_data))
            story.extend(self._build_metric_snapshot(report_data))
            story.extend(self._build_ai_memo(report_data))
            story.extend(self._build_wayback_section(report_data))
            story.extend(self._build_list_section("Dominance Points", report_data.get("llm_analysis", {}).get("good_highlights", [])))
            story.extend(self._build_list_section("Major Concerns", report_data.get("llm_analysis", {}).get("major_concerns", [])))
            story.extend(self._build_action_plan(report_data))
            story.extend(self._build_traffic_history(report_data))
            story.extend(self._build_backlinks_section(report_data))
            story.extend(self._build_refdomains_section(report_data))
            story.extend(self._build_keywords_section(report_data))

            doc.build(story, onFirstPage=self._add_page_footer, onLaterPages=self._add_page_footer)

            pdf_bytes = buffer.getvalue()
            buffer.close()
            logger.info("PDF generated successfully", domain=domain, size_bytes=len(pdf_bytes))
            return pdf_bytes
        except Exception as exc:
            logger.error("Failed to generate PDF", domain=domain, error=str(exc))
            raise

    def _build_header(self, domain: str, report_data: Dict[str, Any]) -> List[Any]:
        story: List[Any] = [
            Paragraph("Domain Scout Executive Report", self.styles["ReportTitle"]),
            Paragraph(domain, self.styles["Heading1"]),
            Spacer(1, 0.08 * inch),
        ]

        report_date = self._format_timestamp(report_data.get("analysis_timestamp"))
        generated_at = self._format_timestamp(report_data.get("generated_at"))
        processing_time = report_data.get("processing_time_seconds")

        meta_rows = [
            ["Report timestamp", report_date],
            ["Generated at", generated_at],
            ["Processing time", f"{processing_time:.1f}s" if isinstance(processing_time, (int, float)) else "N/A"],
        ]
        story.append(self._build_key_value_table(meta_rows, [1.8 * inch, 4.6 * inch]))
        story.append(Spacer(1, 0.18 * inch))
        return story

    def _build_metric_snapshot(self, report_data: Dict[str, Any]) -> List[Any]:
        metrics = report_data.get("data_for_seo_metrics", {})
        llm_analysis = report_data.get("llm_analysis", {})
        buy_recommendation = (llm_analysis.get("buy_recommendation") or {}).get("recommendation", "PENDING")
        confidence = llm_analysis.get("confidence_score", 0) or 0

        rows = [
            ["Domain Rating", self._fmt_number(metrics.get("domain_rating_dr"))],
            ["Organic Traffic", self._fmt_number(metrics.get("organic_traffic_est"))],
            ["Backlinks", self._fmt_number(metrics.get("total_backlinks"))],
            ["Referring Domains", self._fmt_number(metrics.get("total_referring_domains"))],
            ["SaaS AI Consensus", buy_recommendation],
            ["Confidence Score", f"{confidence:.0%}"],
        ]

        return [
            Paragraph("Executive Snapshot", self.styles["SectionHeader"]),
            self._build_key_value_table(rows, [2.2 * inch, 4.2 * inch]),
            Spacer(1, 0.18 * inch),
        ]

    def _build_ai_memo(self, report_data: Dict[str, Any]) -> List[Any]:
        llm_analysis = report_data.get("llm_analysis", {})
        buy_recommendation = llm_analysis.get("buy_recommendation", {}) or {}
        story: List[Any] = [Paragraph("Executive Summary Memo", self.styles["SectionHeader"])]

        summary = llm_analysis.get("summary") or "No executive memo available."
        story.append(Paragraph(summary, self.styles["Body"]))

        reasoning = buy_recommendation.get("reasoning")
        if reasoning:
            story.append(Spacer(1, 0.08 * inch))
            story.append(Paragraph(f"<b>Recommendation reasoning:</b> {reasoning}", self.styles["Body"]))

        story.append(Spacer(1, 0.18 * inch))
        return story

    def _build_wayback_section(self, report_data: Dict[str, Any]) -> List[Any]:
        wayback = report_data.get("wayback_machine_summary", {})
        rows = [
            ["First snapshot", self._fmt_value(wayback.get("first_capture_year"))],
            ["Total captures", self._fmt_number(wayback.get("total_captures"))],
            ["Historical risk", self._fmt_value(wayback.get("historical_risk_assessment"), "No critical history risks detected.")],
        ]
        return [
            Paragraph("Wayback Pulse", self.styles["SectionHeader"]),
            self._build_key_value_table(rows, [1.8 * inch, 4.6 * inch]),
            Spacer(1, 0.18 * inch),
        ]

    def _build_list_section(self, title: str, items: Iterable[str]) -> List[Any]:
        story: List[Any] = [Paragraph(title, self.styles["SectionHeader"])]
        values = [item for item in (items or []) if item]
        if not values:
            story.append(Paragraph("No items available.", self.styles["Body"]))
        else:
            for item in values:
                story.append(Paragraph(item, self.styles["BulletItem"], bulletText="•"))
        story.append(Spacer(1, 0.18 * inch))
        return story

    def _build_action_plan(self, report_data: Dict[str, Any]) -> List[Any]:
        action_plan = report_data.get("llm_analysis", {}).get("action_plan", {}) or {}
        story: List[Any] = [Paragraph("Action Plan", self.styles["SectionHeader"])]
        sections = [
            ("Immediate Actions", action_plan.get("immediate_actions", [])),
            ("First Month", action_plan.get("first_month", [])),
            ("Long-Term Strategy", action_plan.get("long_term_strategy", [])),
        ]

        for label, items in sections:
            story.append(Paragraph(label, self.styles["Heading4"]))
            if items:
                for item in items:
                    story.append(Paragraph(item, self.styles["BulletItem"], bulletText="•"))
            else:
                story.append(Paragraph("No actions listed.", self.styles["Body"]))
            story.append(Spacer(1, 0.08 * inch))

        story.append(Spacer(1, 0.1 * inch))
        return story

    def _build_traffic_history(self, report_data: Dict[str, Any]) -> List[Any]:
        story: List[Any] = [Paragraph("Traffic History", self.styles["SectionHeader"])]
        rank_overview = (report_data.get("historical_data") or {}).get("rank_overview", {}) or {}
        traffic_points = rank_overview.get("organic_traffic", []) or []

        if not traffic_points:
            story.append(Paragraph("Traffic history is not available for this report.", self.styles["Body"]))
            story.append(Spacer(1, 0.18 * inch))
            return story

        recent_points = traffic_points[-12:]
        rows = [["Date", "Organic Traffic"]]
        for point in recent_points:
            rows.append([self._fmt_value(point.get("date")), self._fmt_number(point.get("value"))])

        story.append(Paragraph("Recent monthly traffic points", self.styles["Muted"]))
        story.append(self._build_table(rows, [2.0 * inch, 2.2 * inch]))
        story.append(Spacer(1, 0.18 * inch))
        return story

    def _build_backlinks_section(self, report_data: Dict[str, Any]) -> List[Any]:
        backlinks = report_data.get("backlinks", {}) or {}
        items = backlinks.get("items", []) or []
        story: List[Any] = [
            Paragraph("Backlinks Summary", self.styles["SectionHeader"]),
            Paragraph(
                f"Top {len(items)} backlinks shown out of {self._fmt_number(backlinks.get('total_count'))}.",
                self.styles["Muted"],
            ),
        ]

        if not items:
            story.append(Paragraph("No backlink rows available.", self.styles["Body"]))
        else:
            rows = [["Source Domain", "DR", "Source URL", "Anchor", "Target"]]
            for item in items:
                rows.append([
                    self._truncate(item.get("domain"), 28),
                    self._fmt_number(item.get("domain_rank")),
                    self._truncate(item.get("url_from"), 42),
                    self._truncate(item.get("anchor_text"), 24),
                    self._truncate(item.get("url_to"), 42),
                ])
            story.append(self._build_table(rows, [1.3 * inch, 0.5 * inch, 1.95 * inch, 1.2 * inch, 1.95 * inch], font_size=7.5))

        story.append(Spacer(1, 0.18 * inch))
        return story

    def _build_refdomains_section(self, report_data: Dict[str, Any]) -> List[Any]:
        ref_domains = report_data.get("referring_domains", {}) or {}
        items = ref_domains.get("items", []) or []
        story: List[Any] = [
            Paragraph("Referring Domains Summary", self.styles["SectionHeader"]),
            Paragraph(
                f"Top {len(items)} referring domains shown out of {self._fmt_number(ref_domains.get('total_count'))}.",
                self.styles["Muted"],
            ),
        ]

        if not items:
            story.append(Paragraph("No referring domain rows available.", self.styles["Body"]))
        else:
            rows = [["Domain", "DR", "Backlinks", "Anchor", "First Seen"]]
            for item in items:
                rows.append([
                    self._truncate(item.get("domain"), 32),
                    self._fmt_number(item.get("domain_rank")),
                    self._fmt_number(item.get("backlinks_count")),
                    self._truncate(item.get("anchor_text"), 26),
                    self._fmt_value(item.get("first_seen"), "N/A"),
                ])
            story.append(self._build_table(rows, [2.0 * inch, 0.55 * inch, 0.85 * inch, 1.5 * inch, 1.3 * inch], font_size=8))

        story.append(Spacer(1, 0.18 * inch))
        return story

    def _build_keywords_section(self, report_data: Dict[str, Any]) -> List[Any]:
        keywords = report_data.get("keywords", {}) or {}
        items = keywords.get("items", []) or []
        story: List[Any] = [
            Paragraph("Keywords Summary", self.styles["SectionHeader"]),
            Paragraph(
                f"Top {len(items)} keywords shown out of {self._fmt_number(keywords.get('total_count'))}.",
                self.styles["Muted"],
            ),
        ]

        if not items:
            story.append(Paragraph("No keyword rows available.", self.styles["Body"]))
        else:
            rows = [["Keyword", "Position", "Volume", "CPC", "Ranking URL"]]
            for item in items:
                rows.append([
                    self._truncate(item.get("keyword"), 28),
                    self._fmt_number(item.get("position")),
                    self._fmt_number(item.get("search_volume")),
                    self._fmt_currency(item.get("cpc")),
                    self._truncate(item.get("ranking_url"), 42),
                ])
            story.append(self._build_table(rows, [1.9 * inch, 0.65 * inch, 0.8 * inch, 0.6 * inch, 2.45 * inch], font_size=8))

        story.append(Spacer(1, 0.18 * inch))
        return story

    def _build_table(self, rows: List[List[str]], col_widths: List[float], font_size: float = 9) -> Table:
        table = Table(rows, colWidths=col_widths, repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), HexColor("#0f172a")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), font_size),
                    ("ALIGN", (1, 1), (2, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [HexColor("#f8fafc"), colors.white]),
                    ("GRID", (0, 0), (-1, -1), 0.25, HexColor("#cbd5e1")),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        return table

    def _build_key_value_table(self, rows: List[List[str]], col_widths: List[float]) -> Table:
        table = Table(rows, colWidths=col_widths)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (0, -1), HexColor("#f8fafc")),
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("TEXTCOLOR", (0, 0), (-1, -1), HexColor("#111827")),
                    ("GRID", (0, 0), (-1, -1), 0.25, HexColor("#cbd5e1")),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 7),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )
        return table

    def _fmt_number(self, value: Any) -> str:
        if value in (None, ""):
            return "0"
        try:
            number = float(value)
        except (TypeError, ValueError):
            return str(value)
        if number.is_integer():
            return f"{int(number):,}"
        return f"{number:,.2f}"

    def _fmt_currency(self, value: Any) -> str:
        if value in (None, ""):
            return "$0.00"
        try:
            return f"${float(value):,.2f}"
        except (TypeError, ValueError):
            return str(value)

    def _fmt_value(self, value: Any, default: str = "N/A") -> str:
        if value in (None, ""):
            return default
        return str(value)

    def _truncate(self, value: Any, max_len: int) -> str:
        text = self._fmt_value(value, "")
        if len(text) <= max_len:
            return text
        return f"{text[:max_len - 1]}…"

    def _format_timestamp(self, value: Any) -> str:
        if not value:
            return "N/A"
        try:
            if isinstance(value, datetime):
                dt = value
            else:
                dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            return dt.strftime("%B %d, %Y %H:%M")
        except Exception:
            return str(value)

    def _add_page_footer(self, canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(HexColor("#64748b"))
        canvas.drawString(doc.leftMargin, 0.35 * inch, f"Generated by Domain Scout • Page {doc.page}")
        canvas.restoreState()
