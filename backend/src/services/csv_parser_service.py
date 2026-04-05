"""
CSV Parser Service for multiple auction site formats
"""

import csv
import io
import json
import re
from typing import List, Dict, Any, Optional, Iterator
from datetime import datetime, timezone
import structlog

from models.auctions import AuctionInput
from utils.date_utils import parse_iso_datetime

logger = structlog.get_logger()

def find_col_static(fieldnames, possible_names):
    if not fieldnames: return None
    lower_map = {str(f).lower(): f for f in fieldnames}
    for name in possible_names:
        if name.lower() in lower_map:
            return lower_map[name.lower()]
    return None

class CSVParserService:
    """Service for parsing CSV files from different auction sites"""
    
    def parse_csv(self, source: Any, auction_site: str, filename: str = '', is_file: bool = False) -> Iterator[AuctionInput]:
        """
        Parse CSV content based on auction site format
        """
        if is_file:
            with open(source, 'r', encoding='utf-8-sig', errors='replace') as f:
                yield from self._parse_csv_internal(f, auction_site, filename)
        else:
            csv_file = io.StringIO(source)
            yield from self._parse_csv_internal(csv_file, auction_site, filename)

    def _parse_csv_internal(self, csv_file: Any, auction_site: str, filename: str = '') -> Iterator[AuctionInput]:
        if hasattr(csv_file, 'seek') and hasattr(csv_file, 'read'):
            pos = csv_file.tell()
            content = csv_file.read(1)
            csv_file.seek(pos)
            if not content:
                logger.warning("CSV file is empty", filename=filename, auction_site=auction_site)
                return
        
        auction_site_lower = auction_site.lower().strip()
        
        if auction_site_lower == 'namecheap':
            yield from self.parse_namecheap_csv(csv_file, filename, is_handle=True)
        elif auction_site_lower == 'godaddy':
            yield from self.parse_godaddy_csv(csv_file, is_handle=True)
        elif auction_site_lower == 'namesilo':
            yield from self.parse_namesilo_csv(csv_file, is_handle=True)
        else:
            logger.warning("Unknown auction site, using generic parser", auction_site=auction_site)
            yield from self.parse_generic_csv(csv_file, auction_site, is_handle=True)
    
    def parse_namecheap_csv(self, content: Any, filename: str = '', is_handle: bool = False) -> Iterator[AuctionInput]:
        """Parse Namecheap CSV format with streaming support"""
        try:
            if is_handle:
                csv_file = content
                pos = csv_file.tell()
                peek_content = csv_file.read(8192)
                csv_file.seek(pos)
                if not peek_content: return
            else:
                if not content: return
                peek_content = content
                csv_file = io.StringIO(content)

            try:
                dialect = csv.Sniffer().sniff(peek_content[:4096], delimiters=',;\t')
                reader = csv.DictReader(csv_file, dialect=dialect)
            except Exception:
                if is_handle: csv_file.seek(pos)
                reader = csv.DictReader(csv_file)
            
            if not reader.fieldnames: return
            reader.fieldnames = [str(h).strip() for h in reader.fieldnames]

            def find_col(possible_names):
                lower_map = {str(f).lower(): f for f in reader.fieldnames}
                for name in possible_names:
                    if name.lower() in lower_map: return lower_map[name.lower()]
                return None

            domain_col = find_col(['domain', 'Domain'])
            permalink_col = find_col(['permalink', 'Permalink'])
            name_col = find_col(['name', 'Name'])
            start_date_col = find_col(['startDate', 'start_date', 'Start Date'])
            
            # Check if this is a "Buy Now" format (no start date, has price/permalink)
            # Or if the filename explicitly says so
            is_buy_now_format = (domain_col and permalink_col and not name_col and not start_date_col) or \
                               (filename and 'buy_now' in filename.lower()) or \
                               (domain_col and find_col(['price', 'Price']) and not find_col(['endDate', 'End Date']))
            
            if is_buy_now_format:
                logger.info("Detected Namecheap Buy Now format", filename=filename)
                yield from self._process_namecheap_buy_now(reader, domain_col or 'domain', find_col(['price', 'Price']) or 'price')
            else:
                yield from self._process_namecheap_market_sales(reader, name_col or 'name')
            
        except Exception as e:
            logger.error("Failed to parse Namecheap CSV", error=str(e))
            raise

    def _process_namecheap_buy_now(self, reader, domain_key, price_key) -> Iterator[AuctionInput]:
        far_future_date = datetime(2099, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
        for row in reader:
            try:
                domain_name = row.get(domain_key, '').strip()
                if not domain_name: continue
                yield AuctionInput(
                    domain=domain_name, start_date=None, expiration_date=far_future_date,
                    end_date=far_future_date, current_bid=self._parse_price(row.get(price_key, '')),
                    auction_site='namecheap', source_data={k: v for k, v in row.items()}
                )
            except Exception: continue

    def _process_namecheap_market_sales(self, reader, name_key) -> Iterator[AuctionInput]:
        found_start_key = find_col_static(reader.fieldnames, ['startDate', 'StartDate', 'start_date', 'Start Date'])
        found_end_key = find_col_static(reader.fieldnames, ['endDate', 'EndDate', 'end_date', 'End Date', 'Auction End'])
        found_price_key = find_col_static(reader.fieldnames, ['price', 'Price', 'currentBid', 'current_bid', 'Current Bid'])
        found_url_key = find_col_static(reader.fieldnames, ['url', 'Url', 'URL', 'link', 'Link'])
        
        for row in reader:
            try:
                domain_name = row.get(name_key, '').strip()
                if not domain_name: continue
                end_date = self._parse_date(row.get(found_end_key, '')) if found_end_key else None
                if not end_date: continue
                yield AuctionInput(
                    domain=domain_name, start_date=self._parse_date(row.get(found_start_key, '')) if found_start_key else None,
                    expiration_date=end_date, end_date=end_date,
                    current_bid=self._parse_price(row.get(found_price_key, '')) if found_price_key else None,
                    auction_site='namecheap', source_data={k: v for k, v in row.items()},
                    link=row.get(found_url_key, '').strip() if found_url_key else None
                )
            except Exception: continue

    def parse_godaddy_csv(self, content: Any, is_handle: bool = False) -> Iterator[AuctionInput]:
        try:
            csv_file = content if is_handle else io.StringIO(content)
            reader = csv.DictReader(csv_file)
            if not reader.fieldnames: return
            
            for row in reader:
                try:
                    domain_name = row.get('Domain', '').strip() or row.get('domain', '').strip()
                    if not domain_name: continue
                    end_date = (self._parse_date(row.get('End Date', '')) or self._parse_date(row.get('endDate', '')) or 
                               self._parse_date(row.get('Expiration Date', '')))
                    if not end_date: continue
                    yield AuctionInput(
                        domain=domain_name, expiration_date=end_date, end_date=end_date,
                        start_date=self._parse_date(row.get('Start Date', '')),
                        current_bid=self._parse_price(row.get('Price', '') or row.get('price', '')),
                        auction_site='godaddy', source_data={k: v for k, v in row.items()}
                    )
                except Exception: continue
        except Exception as e:
            logger.error("Failed to parse GoDaddy CSV", error=str(e))
            raise

    def parse_namesilo_csv(self, content: Any, is_handle: bool = False) -> Iterator[AuctionInput]:
        try:
            csv_file = content if is_handle else io.StringIO(content)
            reader = csv.DictReader(csv_file)
            if not reader.fieldnames: return
            
            fieldnames_lower = [f.lower() for f in reader.fieldnames]
            if 'sale_type' in fieldnames_lower or 'buy_now' in fieldnames_lower:
                yield from self._parse_namesilo_active_sales(reader)
            else:
                yield from self._parse_namesilo_auction_export(reader)
        except Exception as e:
            logger.error("Failed to parse NameSilo CSV", error=str(e))
            raise

    def _parse_namesilo_active_sales(self, reader) -> Iterator[AuctionInput]:
        far_future_date = datetime(2099, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
        for row in reader:
            try:
                domain_name = row.get('Domain', '').strip()
                if not domain_name: continue
                end_date = self._parse_date(row.get('End_Date', '')) or far_future_date
                yield AuctionInput(
                    domain=domain_name, expiration_date=end_date, end_date=end_date,
                    current_bid=self._parse_price(row.get('Buy_Now', '0')),
                    auction_site='namesilo', source_data={k: v for k, v in row.items()},
                    link=f"https://www.namesilo.com/marketplace/domain-details/{domain_name}"
                )
            except Exception: continue

    def _parse_namesilo_auction_export(self, reader) -> Iterator[AuctionInput]:
        far_future_date = datetime(2099, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
        for row in reader:
            try:
                domain_name = row.get('Domain', '').strip()
                if not domain_name: continue
                end_date = self._parse_date(row.get('Auction End', '')) or far_future_date
                yield AuctionInput(
                    domain=domain_name, start_date=self._parse_date(row.get('Domain Created On', '')),
                    expiration_date=end_date, end_date=end_date,
                    current_bid=self._parse_price(row.get('Current Bid', '0')),
                    auction_site='namesilo', source_data={k: v for k, v in row.items()},
                    link=row.get('Url', '').strip() or f"https://www.namesilo.com/marketplace/domain-details/{domain_name}"
                )
            except Exception: continue

    def parse_generic_csv(self, content: Any, auction_site: str, is_handle: bool = False) -> Iterator[AuctionInput]:
        try:
            csv_file = content if is_handle else io.StringIO(content)
            reader = csv.DictReader(csv_file)
            columns = reader.fieldnames or []
            domain_col = next((c for c in ['domain', 'name', 'Domain', 'Name'] if c in columns), None)
            exp_date_col = next((c for c in ['expiration_date', 'end_date', 'Expiration Date', 'End Date'] if c in columns), None)
            if not domain_col or not exp_date_col: return
            
            for row in reader:
                try:
                    domain_name = row.get(domain_col, '').strip()
                    end_date = self._parse_date(row.get(exp_date_col, ''))
                    if domain_name and end_date:
                        yield AuctionInput(
                            domain=domain_name, expiration_date=end_date, end_date=end_date,
                            auction_site=auction_site.lower(), source_data={k: v for k, v in row.items()}
                        )
                except Exception: continue
        except Exception: raise

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        if not date_str or date_str.strip() == '': return None
        try:
            parsed = parse_iso_datetime(date_str)
            if parsed: return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed
            for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%Y-%m-%dT%H:%M:%S']:
                try:
                    dt = datetime.strptime(date_str.strip(), fmt)
                    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
                except ValueError: continue
            return None
        except Exception: return None

    def _parse_price(self, price_str: str) -> Optional[float]:
        if not price_str: return None
        try:
            cleaned = re.sub(r'[^\d.-]', '', str(price_str).strip())
            return float(cleaned) if cleaned and cleaned not in ['-', '.'] else None
        except (ValueError, TypeError): return None

    def parse_godaddy_json(self, content: Any, is_handle: bool = False) -> List[AuctionInput]:
        try:
            data = json.load(content) if is_handle else json.loads(content)
            listings = data.get('data', [])
            auctions = []
            far_future_date = datetime(2099, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
            
            for listing in listings:
                try:
                    domain_name = listing.get('domainName', '').strip()
                    if not domain_name: continue
                    is_buynow = listing.get('auctionType', '').lower() == 'buynow'
                    exp_date = far_future_date if is_buynow else self._parse_date(listing.get('auctionEndTime', ''))
                    if not exp_date: continue
                    auctions.append(AuctionInput(
                        domain=domain_name, expiration_date=exp_date, end_date=exp_date,
                        current_bid=self._parse_price(listing.get('price', '')),
                        auction_site='godaddy', source_data=listing, link=listing.get('link')
                    ))
                except Exception: continue
            return auctions
        except Exception as e:
            logger.error("Failed to parse GoDaddy JSON", error=str(e))
            raise
