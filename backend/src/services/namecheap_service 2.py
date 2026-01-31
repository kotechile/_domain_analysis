"""
Namecheap Service for processing CSV files and managing Namecheap domain data
"""

import csv
import io
from typing import List, Dict, Any
from datetime import datetime
import structlog

from models.domain_analysis import NamecheapDomain, ScoredDomain
from services.database import get_database
from services.domain_scoring_service import DomainScoringService

logger = structlog.get_logger()


class NamecheapService:
    """Service for Namecheap domain operations"""
    
    def __init__(self):
        self.db = get_database()
    
    def parse_csv_file(self, file_content: str) -> List[NamecheapDomain]:
        """
        Parse CSV content into list of NamecheapDomain objects
        
        Expected CSV format with header:
        url,name,startDate,endDate,price,startPrice,renewPrice,bidCount,ahrefsDomainRating,...
        
        Args:
            file_content: Raw CSV content as string
            
        Returns:
            List of NamecheapDomain objects
        """
        domains = []
        
        try:
            # Use StringIO to read CSV from string
            csv_file = io.StringIO(file_content)
            reader = csv.DictReader(csv_file)
            
            for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is row 1)
                try:
                    # Parse dates (format: 2025-11-29T23:30:00Z)
                    def parse_date(date_str):
                        if not date_str or date_str.strip() == '':
                            return None
                        try:
                            # Handle ISO format with Z
                            if date_str.endswith('Z'):
                                date_str = date_str[:-1] + '+00:00'
                            return datetime.fromisoformat(date_str)
                        except Exception as e:
                            logger.warning("Failed to parse date", row=row_num, date=date_str, error=str(e))
                            return None
                    
                    # Parse numeric values
                    def parse_float(value):
                        if not value or value.strip() == '':
                            return None
                        try:
                            return float(value)
                        except (ValueError, TypeError):
                            return None
                    
                    def parse_int(value):
                        if not value or value.strip() == '':
                            return None
                        try:
                            return int(float(value))  # Handle "10.00" -> 10
                        except (ValueError, TypeError):
                            return None
                    
                    def parse_bool(value):
                        if not value or value.strip() == '':
                            return None
                        return str(value).lower() in ('true', '1', 'yes', 'y')
                    
                    # Extract domain name from 'name' field
                    domain_name = row.get('name', '').strip()
                    if not domain_name:
                        logger.warning("Skipping row with empty name", row=row_num)
                        continue
                    
                    # Create NamecheapDomain object
                    domain = NamecheapDomain(
                        url=row.get('url', '').strip() or None,
                        name=domain_name,
                        start_date=parse_date(row.get('startDate', '')),
                        end_date=parse_date(row.get('endDate', '')),
                        price=parse_float(row.get('price', '')),
                        start_price=parse_float(row.get('startPrice', '')),
                        renew_price=parse_float(row.get('renewPrice', '')),
                        bid_count=parse_int(row.get('bidCount', '')),
                        ahrefs_domain_rating=parse_float(row.get('ahrefsDomainRating', '')),
                        umbrella_ranking=parse_int(row.get('umbrellaRanking', '')),
                        cloudflare_ranking=parse_int(row.get('cloudflareRanking', '')),
                        estibot_value=parse_float(row.get('estibotValue', '')),
                        extensions_taken=parse_int(row.get('extensionsTaken', '')),
                        keyword_search_count=parse_int(row.get('keywordSearchCount', '')),
                        registered_date=parse_date(row.get('registeredDate', '')),
                        last_sold_price=parse_float(row.get('lastSoldPrice', '')),
                        last_sold_year=parse_int(row.get('lastSoldYear', '')),
                        is_partner_sale=parse_bool(row.get('isPartnerSale', '')),
                        semrush_a_score=parse_int(row.get('semrushAScore', '')),
                        majestic_citation=parse_int(row.get('majesticCitation', '')),
                        ahrefs_backlinks=parse_int(row.get('ahrefsBacklinks', '')),
                        semrush_backlinks=parse_int(row.get('semrushBacklinks', '')),
                        majestic_backlinks=parse_int(row.get('majesticBacklinks', '')),
                        majestic_trust_flow=parse_float(row.get('majesticTrustFlow', '')),
                        go_value=parse_float(row.get('goValue', ''))
                    )
                    
                    domains.append(domain)
                    
                except Exception as e:
                    logger.warning("Failed to parse CSV row", row=row_num, error=str(e))
                    continue
            
            logger.info("Parsed Namecheap CSV", total_rows=len(domains))
            return domains
            
        except Exception as e:
            logger.error("Failed to parse CSV file", error=str(e))
            raise
    
    async def load_namecheap_csv(self, file_content: str) -> Dict[str, Any]:
        """
        Orchestrate full CSV load workflow:
        1. Parse CSV file
        2. Score domains (Stage 1: pre-screening, Stage 2: semantic analysis for passing domains)
        3. Truncate existing table
        4. Bulk insert new records with scores
        
        Args:
            file_content: Raw CSV content as string
            
        Returns:
            Dict with load statistics including scoring stats
        """
        try:
            logger.info("Starting CSV load workflow", file_size=len(file_content))
            
            # Step 1: Parse CSV file
            logger.info("Step 1: Parsing CSV file...")
            domains = self.parse_csv_file(file_content)
            logger.info("CSV parsing complete", domains_count=len(domains))
            
            if not domains:
                return {
                    "success": False,
                    "message": "No valid domains found in CSV",
                    "loaded_count": 0,
                    "skipped_count": 0,
                    "total_count": 0,
                    "passed_count": 0,
                    "failed_count": 0
                }
            
            # Step 2: Score domains (pre-screening + semantic analysis)
            logger.info("Step 2: Scoring domains (pre-screening + semantic analysis)...")
            scoring_service = DomainScoringService()
            scored_domains = scoring_service.score_domains(domains)
            
            # Separate passed and failed domains
            passed_domains = [s for s in scored_domains if s.filter_status == 'PASS']
            failed_domains = [s for s in scored_domains if s.filter_status == 'FAIL']
            
            logger.info("Domain scoring complete", 
                       total=len(scored_domains),
                       passed=len(passed_domains),
                       failed=len(failed_domains))
            
            # Step 3: Truncate existing table
            logger.info("Step 3: Truncating existing table...")
            await self.db.truncate_namecheap_domains()
            logger.info("Table truncated successfully")
            
            # Step 4: Bulk insert new records with scores
            logger.info("Step 4: Starting bulk insert with scores", total_domains=len(scored_domains))
            result = await self.db.load_namecheap_domains_with_scores(scored_domains)
            logger.info("Bulk insert complete", inserted=result['inserted'], skipped=result['skipped'])
            
            return {
                "success": True,
                "message": f"Loaded {result['inserted']} domains, skipped {result['skipped']} duplicates. {len(passed_domains)} passed filtering, {len(failed_domains)} failed.",
                "loaded_count": result['inserted'],
                "skipped_count": result['skipped'],
                "total_count": result['total'],
                "passed_count": len(passed_domains),
                "failed_count": len(failed_domains),
                "scoring_stats": {
                    "passed": len(passed_domains),
                    "failed": len(failed_domains),
                    "top_score": passed_domains[0].total_meaning_score if passed_domains else None
                }
            }
            
        except Exception as e:
            logger.error("Failed to load Namecheap CSV", error=str(e), exc_info=True)
            return {
                "success": False,
                "message": f"Failed to load CSV: {str(e)}",
                "loaded_count": 0,
                "skipped_count": 0,
                "total_count": 0,
                "passed_count": 0,
                "failed_count": 0
            }
