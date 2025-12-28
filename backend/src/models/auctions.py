"""
Auction models for multi-source domain auction data
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any
from datetime import datetime


class Auction(BaseModel):
    """Model for auction record matching database schema"""
    id: Optional[str] = None
    domain: str = Field(..., min_length=1, max_length=255)
    start_date: Optional[datetime] = None
    expiration_date: datetime
    auction_site: str = Field(..., min_length=1, max_length=100)
    current_bid: Optional[float] = None
    ranking: Optional[int] = None
    score: Optional[float] = None
    preferred: bool = False
    has_statistics: bool = False
    processed: bool = False  # Track if record has been scored
    source_data: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    @validator('domain')
    def validate_domain(cls, v):
        """Normalize domain name"""
        if not v:
            raise ValueError('Domain cannot be empty')
        # Remove protocol if present
        v = v.replace('http://', '').replace('https://', '').replace('www.', '')
        return v.lower().strip()
    
    @validator('auction_site')
    def validate_auction_site(cls, v):
        """Normalize auction site name"""
        if not v:
            raise ValueError('Auction site cannot be empty')
        return v.lower().strip()
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class AuctionInput(BaseModel):
    """Model for CSV parsing input - flexible structure for different sources"""
    domain: str
    start_date: Optional[datetime] = None
    expiration_date: Optional[datetime] = None
    end_date: Optional[datetime] = None  # Alternative field name
    current_bid: Optional[float] = None
    auction_site: str
    source_data: Optional[Dict[str, Any]] = None
    
    @validator('domain')
    def validate_domain(cls, v):
        """Normalize domain name"""
        if not v:
            raise ValueError('Domain cannot be empty')
        v = v.replace('http://', '').replace('https://', '').replace('www.', '')
        return v.lower().strip()
    
    def to_auction(self) -> Auction:
        """Convert to Auction model"""
        # Use expiration_date or end_date
        exp_date = self.expiration_date or self.end_date
        if not exp_date:
            raise ValueError('expiration_date or end_date is required')
        
        return Auction(
            domain=self.domain,
            start_date=self.start_date,
            expiration_date=exp_date,
            auction_site=self.auction_site,
            current_bid=self.current_bid,
            source_data=self.source_data
        )


class AuctionReportItem(BaseModel):
    """Model for auction report with joined statistics"""
    id: str
    domain: str
    start_date: Optional[datetime] = None
    expiration_date: datetime
    auction_site: str
    current_bid: Optional[float] = None
    ranking: Optional[int] = None
    score: Optional[float] = None
    preferred: bool
    has_statistics: bool
    # Extracted columns from page_statistics for better query performance
    backlinks: Optional[int] = None
    referring_domains: Optional[int] = None
    backlinks_spam_score: Optional[float] = None
    first_seen: Optional[datetime] = None
    # Keep page_statistics JSONB for full data access
    statistics: Optional[Dict[str, Any]] = None  # From auctions.page_statistics JSONB field
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }



