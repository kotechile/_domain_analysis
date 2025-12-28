"""
PDF Generation Service for Domain Analysis Reports
"""

import io
from datetime import datetime
from typing import Dict, Any, Optional
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor, black, darkblue, darkred, darkgreen
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.lib import colors
import structlog

logger = structlog.get_logger(__name__)


class PDFService:
    """Service for generating PDF reports from domain analysis data"""
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Setup custom paragraph styles for the PDF"""
        # Title style
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Title'],
            fontSize=24,
            textColor=darkblue,
            spaceAfter=30,
            alignment=TA_CENTER
        ))
        
        # Section header style
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=16,
            textColor=darkblue,
            spaceBefore=20,
            spaceAfter=12,
            borderWidth=1,
            borderColor=darkblue,
            borderPadding=8,
            backColor=HexColor('#f0f8ff')
        ))
        
        # Subsection header style
        self.styles.add(ParagraphStyle(
            name='SubsectionHeader',
            parent=self.styles['Heading3'],
            fontSize=14,
            textColor=darkblue,
            spaceBefore=15,
            spaceAfter=8
        ))
        
        # Recommendation style
        self.styles.add(ParagraphStyle(
            name='Recommendation',
            parent=self.styles['Normal'],
            fontSize=14,
            textColor=black,
            spaceBefore=10,
            spaceAfter=10,
            borderWidth=1,
            borderColor=black,
            borderPadding=10,
            backColor=HexColor('#f9f9f9')
        ))
        
        # Pro/Con style
        self.styles.add(ParagraphStyle(
            name='ProItem',
            parent=self.styles['Normal'],
            fontSize=11,
            textColor=darkgreen,
            spaceBefore=5,
            spaceAfter=5,
            leftIndent=20
        ))
        
        self.styles.add(ParagraphStyle(
            name='ConItem',
            parent=self.styles['Normal'],
            fontSize=11,
            textColor=darkred,
            spaceBefore=5,
            spaceAfter=5,
            leftIndent=20
        ))
    
    def generate_domain_analysis_pdf(self, domain: str, report_data: Dict[str, Any]) -> bytes:
        """Generate a comprehensive PDF report for domain analysis"""
        try:
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(
                buffer,
                pagesize=A4,
                rightMargin=72,
                leftMargin=72,
                topMargin=72,
                bottomMargin=72
            )
            
            # Build the story (content)
            story = []
            
            # Title page
            story.extend(self._build_title_page(domain, report_data))
            story.append(PageBreak())
            
            # Executive Summary
            story.extend(self._build_executive_summary(domain, report_data))
            story.append(PageBreak())
            
            # Buy Recommendation
            story.extend(self._build_buy_recommendation(report_data))
            story.append(PageBreak())
            
            # Valuable Assets
            story.extend(self._build_valuable_assets(report_data))
            
            # Major Concerns
            story.extend(self._build_major_concerns(report_data))
            story.append(PageBreak())
            
            # Content Strategy
            story.extend(self._build_content_strategy(report_data))
            
            # Action Plan
            story.extend(self._build_action_plan(report_data))
            story.append(PageBreak())
            
            # Pros and Cons
            story.extend(self._build_pros_and_cons(report_data))
            
            # Technical Details
            story.extend(self._build_technical_details(domain, report_data))
            
            # Build PDF
            doc.build(story)
            
            # Get PDF bytes
            pdf_bytes = buffer.getvalue()
            buffer.close()
            
            logger.info("PDF generated successfully", domain=domain, size_bytes=len(pdf_bytes))
            return pdf_bytes
            
        except Exception as e:
            logger.error("Failed to generate PDF", domain=domain, error=str(e))
            raise
    
    def _build_title_page(self, domain: str, report_data: Dict[str, Any]) -> list:
        """Build the title page"""
        story = []
        
        # Main title
        story.append(Paragraph(f"Domain Analysis Report", self.styles['CustomTitle']))
        story.append(Spacer(1, 20))
        
        # Domain name
        story.append(Paragraph(f"<b>Domain:</b> {domain}", self.styles['Heading1']))
        story.append(Spacer(1, 20))
        
        # Report date
        current_date = datetime.now().strftime("%B %d, %Y")
        story.append(Paragraph(f"<b>Report Date:</b> {current_date}", self.styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Confidence score
        llm_analysis = report_data.get('llm_analysis', {})
        confidence = llm_analysis.get('confidence_score', 0)
        story.append(Paragraph(f"<b>Analysis Confidence:</b> {confidence:.1%}", self.styles['Normal']))
        story.append(Spacer(1, 30))
        
        # Executive summary preview
        summary = llm_analysis.get('summary', 'No summary available')
        if len(summary) > 300:
            summary = summary[:300] + "..."
        
        story.append(Paragraph("<b>Executive Summary:</b>", self.styles['Heading3']))
        story.append(Paragraph(summary, self.styles['Normal']))
        
        return story
    
    def _build_executive_summary(self, domain: str, report_data: Dict[str, Any]) -> list:
        """Build the executive summary section"""
        story = []
        
        story.append(Paragraph("Executive Summary", self.styles['SectionHeader']))
        
        llm_analysis = report_data.get('llm_analysis', {})
        summary = llm_analysis.get('summary', 'No summary available')
        
        story.append(Paragraph(summary, self.styles['Normal']))
        
        return story
    
    def _build_buy_recommendation(self, report_data: Dict[str, Any]) -> list:
        """Build the buy recommendation section"""
        story = []
        
        story.append(Paragraph("Buy Recommendation", self.styles['SectionHeader']))
        
        llm_analysis = report_data.get('llm_analysis', {})
        buy_rec = llm_analysis.get('buy_recommendation', {})
        
        if buy_rec:
            recommendation = buy_rec.get('recommendation', 'UNKNOWN')
            confidence = buy_rec.get('confidence', 0)
            risk_level = buy_rec.get('risk_level', 'unknown')
            potential_value = buy_rec.get('potential_value', 'unknown')
            reasoning = buy_rec.get('reasoning', 'No reasoning provided')
            
            # Recommendation box
            rec_text = f"""
            <b>Recommendation:</b> {recommendation}<br/>
            <b>Confidence:</b> {confidence:.1%}<br/>
            <b>Risk Level:</b> {risk_level.title()}<br/>
            <b>Potential Value:</b> {potential_value.title()}
            """
            story.append(Paragraph(rec_text, self.styles['Recommendation']))
            
            # Reasoning
            story.append(Paragraph("<b>Reasoning:</b>", self.styles['SubsectionHeader']))
            story.append(Paragraph(reasoning, self.styles['Normal']))
        
        return story
    
    def _build_valuable_assets(self, report_data: Dict[str, Any]) -> list:
        """Build the valuable assets section"""
        story = []
        
        story.append(Paragraph("Valuable Assets", self.styles['SectionHeader']))
        
        llm_analysis = report_data.get('llm_analysis', {})
        assets = llm_analysis.get('valuable_assets', [])
        
        if assets:
            for asset in assets:
                story.append(Paragraph(f"• {asset}", self.styles['Normal']))
        else:
            story.append(Paragraph("No specific valuable assets identified.", self.styles['Normal']))
        
        return story
    
    def _build_major_concerns(self, report_data: Dict[str, Any]) -> list:
        """Build the major concerns section"""
        story = []
        
        story.append(Paragraph("Major Concerns", self.styles['SectionHeader']))
        
        llm_analysis = report_data.get('llm_analysis', {})
        concerns = llm_analysis.get('major_concerns', [])
        
        if concerns:
            for concern in concerns:
                story.append(Paragraph(f"• {concern}", self.styles['Normal']))
        else:
            story.append(Paragraph("No major concerns identified.", self.styles['Normal']))
        
        return story
    
    def _build_content_strategy(self, report_data: Dict[str, Any]) -> list:
        """Build the content strategy section"""
        story = []
        
        story.append(Paragraph("Content Strategy", self.styles['SectionHeader']))
        
        llm_analysis = report_data.get('llm_analysis', {})
        content_strategy = llm_analysis.get('content_strategy', {})
        
        if content_strategy:
            primary_niche = content_strategy.get('primary_niche', 'Not specified')
            story.append(Paragraph(f"<b>Primary Niche:</b> {primary_niche}", self.styles['Normal']))
            
            secondary_niches = content_strategy.get('secondary_niches', [])
            if secondary_niches:
                story.append(Paragraph("<b>Secondary Niches:</b>", self.styles['SubsectionHeader']))
                for niche in secondary_niches:
                    story.append(Paragraph(f"• {niche}", self.styles['Normal']))
            
            first_articles = content_strategy.get('first_articles', [])
            if first_articles:
                story.append(Paragraph("<b>Recommended First Articles:</b>", self.styles['SubsectionHeader']))
                for article in first_articles:
                    story.append(Paragraph(f"• {article}", self.styles['Normal']))
            
            target_keywords = content_strategy.get('target_keywords', [])
            if target_keywords:
                story.append(Paragraph("<b>Target Keywords:</b>", self.styles['SubsectionHeader']))
                for keyword in target_keywords:
                    story.append(Paragraph(f"• {keyword}", self.styles['Normal']))
        
        return story
    
    def _build_action_plan(self, report_data: Dict[str, Any]) -> list:
        """Build the action plan section"""
        story = []
        
        story.append(Paragraph("Action Plan", self.styles['SectionHeader']))
        
        llm_analysis = report_data.get('llm_analysis', {})
        action_plan = llm_analysis.get('action_plan', {})
        
        if action_plan:
            immediate_actions = action_plan.get('immediate_actions', [])
            if immediate_actions:
                story.append(Paragraph("<b>Immediate Actions:</b>", self.styles['SubsectionHeader']))
                for action in immediate_actions:
                    story.append(Paragraph(f"• {action}", self.styles['Normal']))
            
            first_month = action_plan.get('first_month', [])
            if first_month:
                story.append(Paragraph("<b>First Month:</b>", self.styles['SubsectionHeader']))
                for action in first_month:
                    story.append(Paragraph(f"• {action}", self.styles['Normal']))
            
            long_term = action_plan.get('long_term_strategy', [])
            if long_term:
                story.append(Paragraph("<b>Long-term Strategy:</b>", self.styles['SubsectionHeader']))
                for action in long_term:
                    story.append(Paragraph(f"• {action}", self.styles['Normal']))
        
        return story
    
    def _build_pros_and_cons(self, report_data: Dict[str, Any]) -> list:
        """Build the pros and cons section"""
        story = []
        
        story.append(Paragraph("Pros and Cons Analysis", self.styles['SectionHeader']))
        
        llm_analysis = report_data.get('llm_analysis', {})
        pros_cons = llm_analysis.get('pros_and_cons', [])
        
        if pros_cons:
            for item in pros_cons:
                item_type = item.get('type', 'unknown')
                description = item.get('description', 'No description')
                impact = item.get('impact', 'unknown')
                example = item.get('example', 'No example')
                
                if item_type == 'pro':
                    story.append(Paragraph(f"<b>✓ PRO ({impact.title()} Impact):</b> {description}", self.styles['ProItem']))
                else:
                    story.append(Paragraph(f"<b>✗ CON ({impact.title()} Impact):</b> {description}", self.styles['ConItem']))
                
                if example and example != 'No example':
                    story.append(Paragraph(f"<i>Example: {example}</i>", self.styles['Normal']))
                story.append(Spacer(1, 8))
        else:
            story.append(Paragraph("No pros and cons analysis available.", self.styles['Normal']))
        
        return story
    
    def _build_technical_details(self, domain: str, report_data: Dict[str, Any]) -> list:
        """Build the technical details section"""
        story = []
        
        story.append(Paragraph("Technical Details", self.styles['SectionHeader']))
        
        # Domain metrics
        data_for_seo_metrics = report_data.get('data_for_seo_metrics', {})
        if data_for_seo_metrics:
            story.append(Paragraph("<b>SEO Metrics:</b>", self.styles['SubsectionHeader']))
            
            metrics_data = [
                ['Metric', 'Value'],
                ['Domain Authority (DR)', str(data_for_seo_metrics.get('domain_rating_dr', 'N/A'))],
                ['Organic Traffic', f"{data_for_seo_metrics.get('organic_traffic_est', 0):,.0f}"],
                ['Total Keywords', str(data_for_seo_metrics.get('total_keywords', 'N/A'))],
                ['Total Backlinks', f"{data_for_seo_metrics.get('total_backlinks', 0):,}"],
                ['Referring Domains', str(data_for_seo_metrics.get('referring_domains', 'N/A'))]
            ]
            
            metrics_table = Table(metrics_data)
            metrics_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(metrics_table)
            story.append(Spacer(1, 20))
        
        # Wayback Machine data
        wayback_summary = report_data.get('wayback_machine_summary', {})
        if wayback_summary and wayback_summary.get('total_captures') is not None:
            story.append(Paragraph("<b>Historical Data:</b>", self.styles['SubsectionHeader']))
            
            total_captures = wayback_summary.get('total_captures', 0)
            first_capture = wayback_summary.get('first_capture_date', 'Unknown')
            last_capture = wayback_summary.get('last_capture_date', 'Unknown')
            
            story.append(Paragraph(f"• Total captures: {total_captures:,}", self.styles['Normal']))
            story.append(Paragraph(f"• First capture: {first_capture}", self.styles['Normal']))
            story.append(Paragraph(f"• Last capture: {last_capture}", self.styles['Normal']))
        else:
            story.append(Paragraph("<b>Historical Data:</b>", self.styles['SubsectionHeader']))
            story.append(Paragraph("• Historical data not available for this domain", self.styles['Normal']))
            story.append(Paragraph("• Wayback Machine data was not collected during analysis", self.styles['Normal']))
        
        return story
