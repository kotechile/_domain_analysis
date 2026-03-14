"""
Auctions Service for managing multi-source domain auction data
"""

from typing import List, Dict, Any, Optional
import structlog
from datetime import datetime

from models.auctions import AuctionInput, Auction
from services.database import get_database
from services.csv_parser_service import CSVParserService

logger = structlog.get_logger()


class AuctionsService:
    """Service for auction operations"""
    
    def __init__(self):
        self.db = get_database()
        self.csv_parser = CSVParserService()
    
    def load_auctions_from_csv(self, file_content: Any, auction_site: str, filename: str = '', is_file: bool = False) -> List[AuctionInput]:
        """
        Parse CSV file and return list of AuctionInput objects
        
        Args:
            file_content: Raw CSV content as string OR file path if is_file=True
            auction_site: Source auction site ('namecheap', 'godaddy', 'namesilo', etc.)
            filename: Original filename (used for format detection)
            is_file: Whether file_content is a file path
            
        Returns:
            List of AuctionInput objects
        """
        logger.info("Loading auctions from CSV", auction_site=auction_site, filename=filename, is_file=is_file)
        
        try:
            auctions = self.csv_parser.parse_csv(file_content, auction_site, filename, is_file=is_file)
            logger.info("Parsed CSV", auction_site=auction_site, filename=filename, count=len(auctions))
            return auctions
        except Exception as e:
            logger.error("Failed to parse CSV", auction_site=auction_site, filename=filename, error=str(e))
            raise
    
    def load_auctions_from_json(self, file_content: Any, auction_site: str, filename: str = '', is_file: bool = False) -> List[AuctionInput]:
        """
        Parse JSON file and return list of AuctionInput objects
        
        Args:
            file_content: Raw JSON content as string OR file path if is_file=True
            auction_site: Source auction site ('godaddy', etc.)
            filename: Original filename (used for format detection)
            is_file: Whether file_content is a file path
            
        Returns:
            List of AuctionInput objects
        """
        logger.info("Loading auctions from JSON", auction_site=auction_site, filename=filename, is_file=is_file)
        
        try:
            auction_site_lower = auction_site.lower().strip()
            
            if auction_site_lower == 'godaddy':
                if is_file:
                    with open(file_content, 'r', encoding='utf-8', errors='replace') as f:
                        auctions = self.csv_parser.parse_godaddy_json(f, is_handle=True)
                else:
                    auctions = self.csv_parser.parse_godaddy_json(file_content)
            else:
                raise ValueError(f"JSON parsing not supported for auction site: {auction_site}")
            
            logger.info("Parsed JSON", auction_site=auction_site, filename=filename, count=len(auctions))
            return auctions
        except Exception as e:
            logger.error("Failed to parse JSON", auction_site=auction_site, filename=filename, error=str(e))
            raise
    
    async def truncate_and_load(self, auctions: List[AuctionInput]) -> Dict[str, Any]:
        """
        Truncate auctions table and bulk insert new records
        
        Args:
            auctions: List of AuctionInput objects
            
        Returns:
            Dict with load statistics
        """
        try:
            logger.info("Starting truncate and load", total_auctions=len(auctions))
            
            # Step 1: Truncate table
            logger.info("Step 1: Truncating auctions table")
            await self.db.truncate_auctions()
            logger.info("Table truncated successfully")
            
            # Step 2: Convert to Auction objects and prepare for database
            logger.info("Step 2: Converting to database format")
            auction_dicts = []
            for auction_input in auctions:
                try:
                    auction = auction_input.to_auction()
                    auction_dict = {
                        'domain': auction.domain,
                        'start_date': auction.start_date.isoformat() if auction.start_date else None,
                        'expiration_date': auction.expiration_date.isoformat(),
                        'auction_site': auction.auction_site,
                        'current_bid': auction.current_bid,
                        'source_data': auction.source_data,
                        'link': auction.link,  # Direct link to auction listing (e.g., GoDaddy auction URL)
                        'preferred': False,
                        'has_statistics': False,
                        'processed': False  # New records are unprocessed
                    }
                    auction_dicts.append(auction_dict)
                except Exception as e:
                    logger.warning("Failed to convert auction", domain=auction_input.domain, error=str(e))
                    continue
            
            # Step 3: Bulk insert
            logger.info("Step 3: Starting bulk insert", total=len(auction_dicts))
            result = await self.db.bulk_insert_auctions(auction_dicts)
            logger.info("Bulk insert complete", inserted=result['inserted'], skipped=result['skipped'])
            
            return {
                "success": True,
                "message": f"Loaded {result['inserted']} auctions, skipped {result['skipped']} duplicates",
                "loaded_count": result['inserted'],
                "skipped_count": result['skipped'],
                "total_count": result['total']
            }
            
        except Exception as e:
            logger.error("Failed to truncate and load auctions", error=str(e))
            raise
    
    async def get_preferred_auctions_without_stats(self, limit: int = 1000) -> List[Dict[str, Any]]:
        """
        Get preferred auctions without statistics, ordered by expiration_date ASC
        
        Args:
            limit: Maximum number of records to return
            
        Returns:
            List of auction dictionaries
        """
        return await self.db.get_preferred_auctions_without_stats(limit=limit)
    
    async def get_scored_auctions_without_page_statistics(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get scored auctions without page_statistics, ordered by most recent (created_at DESC)
        
        Args:
            limit: Maximum number of records to return
            
        Returns:
            List of auction dictionaries
        """
        return await self.db.get_scored_auctions_without_page_statistics(limit=limit)
    
    async def get_scored_auctions_without_traffic_data(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get scored auctions without traffic_data, ordered by most recent (created_at DESC)
        
        Args:
            limit: Maximum number of records to return
            
        Returns:
            List of auction dictionaries
        """
        return await self.db.get_scored_auctions_without_traffic_data(limit=limit)
    
    async def get_scored_auctions_closest_to_expire_without_traffic_data(self, limit: int = 1000) -> List[Dict[str, Any]]:
        """
        Get scored auctions closest to expire (ordered by expiration_date ASC) that don't have traffic_data, up to limit
        
        Args:
            limit: Maximum number of records to return (up to 1000 for bulk traffic endpoint)
            
        Returns:
            List of auction dictionaries with domain and expiration_date
        """
        return await self.db.get_scored_auctions_closest_to_expire_without_traffic_data(limit=limit)
    
    async def get_scored_auctions_closest_to_expire(self, limit: int = 1000) -> List[Dict[str, Any]]:
        """
        Get scored auctions closest to expire (ordered by expiration_date ASC), up to limit
        
        Args:
            limit: Maximum number of records to return (up to 1000 for bulk rank endpoint)
            
        Returns:
            List of auction dictionaries with domain and expiration_date
        """
        return await self.db.get_scored_auctions_closest_to_expire(limit=limit)
    
    async def get_auctions_without_backlinks_closest_to_expire(self, limit: int = 1000) -> List[Dict[str, Any]]:
        """
        Get auctions closest to expire (ordered by expiration_date ASC) that don't have backlinks data, up to limit
        
        Args:
            limit: Maximum number of records to return (up to 1000 for bulk backlinks endpoint)
            
        Returns:
            List of auction dictionaries with domain, expiration_date, and id
        """
        return await self.db.get_auctions_without_backlinks_closest_to_expire(limit=limit)
    
    async def get_auctions_without_spam_score_closest_to_expire(self, limit: int = 1000) -> List[Dict[str, Any]]:
        """
        Get auctions closest to expire (ordered by expiration_date ASC) that don't have spam score data, up to limit
        
        Args:
            limit: Maximum number of records to return (up to 1000 for bulk spam score endpoint)
            
        Returns:
            List of auction dictionaries with domain, expiration_date, and id
        """
        return await self.db.get_auctions_without_spam_score_closest_to_expire(limit=limit)
    
    async def mark_has_statistics(self, domain_names: List[str]) -> int:
        """
        Mark auctions as having statistics
        
        Args:
            domain_names: List of domain names to update
            
        Returns:
            Number of records updated
        """
        return await self.db.mark_has_statistics(domain_names)
    
    async def get_auctions_report(
        self,
        filters: Optional[Dict[str, Any]] = None,
        sort_by: str = 'expiration_date',
        order: str = 'asc',
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Get auctions report with page_statistics from auctions table
        
        Args:
            filters: Dict with optional filters (preferred, auction_site, etc.)
            sort_by: Field to sort by
            order: Sort order ('asc' or 'desc')
            limit: Maximum number of records
            offset: Number of records to skip
            
        Returns:
            Dict with auctions list, total count, and pagination info
        """
        return await self.db.get_auctions_with_statistics(
            filters=filters,
            sort_by=sort_by,
            order=order,
            limit=limit,
            offset=offset
        )
    
    async def get_auctions_missing_any_metric_with_filters(
        self,
        filters: Optional[Dict[str, Any]] = None,
        sort_by: str = 'expiration_date',
        sort_order: str = 'asc',
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        Get auctions matching filters that are missing ANY of the four DataForSEO metrics
        
        Args:
            filters: Dict with optional filters (preferred, auction_site, tlds, offering_type, etc.)
            sort_by: Field to sort by (default 'expiration_date')
            sort_order: Sort order 'asc' or 'desc' (default 'asc')
            limit: Maximum number of records to return (default 1000)
            
        Returns:
            List of auction dictionaries with domain, expiration_date, and id
        """
        return await self.db.get_auctions_missing_any_metric_with_filters(
            filters=filters,
            sort_by=sort_by,
            sort_order=sort_order,
            limit=limit
        )
    

    