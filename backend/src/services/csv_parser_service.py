"""
CSV Parser Service for multiple auction site formats
"""

import csv
import io
import json
from typing import List, Dict, Any, Optional, Iterator
from datetime import datetime
import structlog

from models.auctions import AuctionInput

logger = structlog.get_logger()


class CSVParserService:
    """Service for parsing CSV files from different auction sites"""
    
    def parse_csv(self, source: Any, auction_site: str, filename: str = '', is_file: bool = False) -> Iterator[AuctionInput]:
        """
        Parse CSV content based on auction site format
        
        Args:
            source: Raw CSV content as string OR file path if is_file=True
            auction_site: Source auction site ('namecheap', 'godaddy', 'namesilo', etc.)
            filename: Original filename (used for format detection)
            is_file: Whether source is a file path
            
        Returns:
            Iterator of AuctionInput objects
        """
        if is_file:
            # Use utf-8-sig to handle BOM automatically
            with open(source, 'r', encoding='utf-8-sig', errors='replace') as f:
                yield from self._parse_csv_internal(f, auction_site, filename)
        else:
            csv_file = io.StringIO(source)
            yield from self._parse_csv_internal(csv_file, auction_site, filename)

    def _parse_csv_internal(self, csv_file: Any, auction_site: str, filename: str = '') -> Iterator[AuctionInput]:
        # Check for empty file
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
            # Try generic parser
            logger.warning("Unknown auction site, using generic parser", auction_site=auction_site)
            yield from self.parse_generic_csv(csv_file, auction_site, is_handle=True)
    
    def parse_namecheap_csv(self, content: Any, filename: str = '', is_handle: bool = False) -> Iterator[AuctionInput]:
        """
        Parse Namecheap CSV format
        
        Two formats supported:
        1. Namecheap_Market_Sales: url, name, startDate, endDate, price, ... (auction format)
        2. Namecheap_Market_Sales_Buy_Now: permalink, domain, price, extensions_taken (buy now format)
        """
        try:
            # Load content into string if bytes or file handle
            if hasattr(content, 'read'):
                content_str = content.read()
            else:
                content_str = content

            # Log raw start of file to debug structure/BOM/delimiters
            logger.info("Raw CSV Content Start", 
                       filename=filename, 
                       preview=content_str[:500] if len(content_str) > 0 else "EMPTY",
                       length=len(content_str))

            if not content_str:
                logger.warning("CSV content is empty", filename=filename)
                return

            csv_file = io.StringIO(content_str)
            
            # Use Sniffer to detect delimiter
            try:
                dialect = csv.Sniffer().sniff(content_str[:4096], delimiters=',;\t')
                logger.info("Detected CSV dialect", delimiter=dialect.delimiter, quotechar=dialect.quotechar)
                reader = csv.DictReader(csv_file, dialect=dialect)
            except Exception as e:
                logger.warning("CSV Sniffer failed, falling back to default", error=str(e))
                csv_file.seek(0)
                reader = csv.DictReader(csv_file)
            
            # Check if headers exist
            if not reader.fieldnames:
                logger.warning("CSV file has no headers or is empty", filename=filename)
                return
            
            # Clean headers (strip whitespace)
            reader.fieldnames = [str(h).strip() for h in reader.fieldnames] if reader.fieldnames else []
            
            logger.info("Final Cleaned Headers", headers=reader.fieldnames)

            # Helper to find column case-insensitively
            def find_col(possible_names):
                if not reader.fieldnames:
                    return None
                for name in possible_names:
                    if name in reader.fieldnames:
                        return name
                # Fallback: check case-insensitive match
                lower_map = {str(f).lower(): f for f in reader.fieldnames}
                for name in possible_names:
                    if name.lower() in lower_map:
                        return lower_map[name.lower()]
                return None

            # Check if this is the Buy Now format (has 'domain' and 'permalink' columns, no 'name' or 'startDate')
            is_buy_now_format = False
            if reader.fieldnames:
                # Use flexible column detection
                domain_col = find_col(['domain', 'Domain'])
                permalink_col = find_col(['permalink', 'Permalink'])
                name_col = find_col(['name', 'Name'])
                start_date_col = find_col(['startDate', 'start_date', 'Start Date'])
                
                # Buy Now format: has domain and permalink, but no name or startDate
                if domain_col and permalink_col and not name_col and not start_date_col:
                    is_buy_now_format = True
                    logger.info("Detected NameCheap Buy Now format from columns", filename=filename)
                elif filename and 'namecheap_market_sales_buy_now' in filename.lower():
                    is_buy_now_format = True
                    logger.info("Detected NameCheap Buy Now format from filename", filename=filename)
            
            if is_buy_now_format:
                # Parse Buy Now format: permalink, domain, price, extensions_taken
                domain_key = find_col(['domain', 'Domain']) or 'domain'
                price_key = find_col(['price', 'Price']) or 'price'
                
                for row_num, row in enumerate(reader, start=2):
                    try:
                        domain_name = row.get(domain_key, '').strip()
                        if not domain_name:
                            logger.warning("Skipping row with empty domain", row=row_num)
                            continue
                        
                        # Buy Now format has no dates - use far future date
                        from datetime import datetime, timezone
                        far_future_date = datetime(2099, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
                        
                        # Parse price (this is the buy now price)
                        current_bid = self._parse_price(row.get(price_key, ''))
                        
                        # Store all original data in source_data
                        source_data = {k: v for k, v in row.items()}
                        
                        auction = AuctionInput(
                            domain=domain_name,
                            start_date=None,  # Buy Now listings don't have start dates
                            expiration_date=far_future_date,  # Use far future date (no expiration)
                            end_date=far_future_date,  # Also set to far future date
                            current_bid=current_bid,
                            auction_site='namecheap',
                            source_data=source_data
                        )
                        
                        yield auction
                        
                    except Exception as e:
                        logger.warning("Failed to parse NameCheap Buy Now CSV row", row=row_num, error=str(e))
                        continue
                
                logger.info("Parsed NameCheap Buy Now CSV")
            else:
                # Parse Market Sales format: url, name, startDate, endDate, price, ...
                logger.info("Detected headers for Market Sales", headers=reader.fieldnames, filename=filename)
                
                name_key = find_col(['name', 'Name', 'Domain', 'domain', 'domain_name']) or 'name'
                
                # Date keys
                start_date_keys = ['startDate', 'StartDate', 'start_date', 'Start Date']
                end_date_keys = ['endDate', 'EndDate', 'end_date', 'End Date', 'Auction End']
                price_keys = ['price', 'Price', 'currentBid', 'current_bid', 'Current Bid']
                
                # Pre-fetch existing keys to avoid searching every row
                found_start_key = find_col(start_date_keys)
                found_end_key = find_col(end_date_keys)
                found_price_key = find_col(price_keys)
                
                logger.info("Mapped columns for Market Sales", 
                           name_key=name_key, 
                           start_key=found_start_key, 
                           end_key=found_end_key, 
                           price_key=found_price_key)

                skipped_log_count = 0
                MAX_SKIPPED_LOGS = 10
                
                for row_num, row in enumerate(reader, start=2):
                    try:
                        domain_name = row.get(name_key, '').strip()
                        if not domain_name:
                            if skipped_log_count < MAX_SKIPPED_LOGS:
                                logger.warning("Skipping row with empty name", row=row_num)
                                skipped_log_count += 1
                            continue
                        
                        # Parse dates with robust column checking
                        start_date = self._parse_date(row.get(found_start_key, '')) if found_start_key else None
                        end_date = self._parse_date(row.get(found_end_key, '')) if found_end_key else None
                        
                        if not end_date:
                            if skipped_log_count < MAX_SKIPPED_LOGS:
                                logger.warning("Skipping row without endDate", row=row_num, domain=domain_name, found_key=found_end_key, raw_value=row.get(found_end_key, '') if found_end_key else 'N/A')
                                skipped_log_count += 1
                            continue
                        
                        # Parse current_bid/price
                        current_bid = self._parse_price(row.get(found_price_key, '')) if found_price_key else None
                        
                        # Store all original data in source_data
                        source_data = {k: v for k, v in row.items()}
                        
                        auction = AuctionInput(
                            domain=domain_name,
                            start_date=start_date,
                            expiration_date=end_date,
                            end_date=end_date,  # Also set for compatibility
                            current_bid=current_bid,
                            auction_site='namecheap',
                            source_data=source_data
                        )
                        
                        yield auction
                        
                    except Exception as e:
                        if skipped_log_count < MAX_SKIPPED_LOGS:
                            logger.warning("Failed to parse CSV row", row=row_num, error=str(e))
                            skipped_log_count += 1
                        continue
                
                logger.info("Parsed Namecheap Market Sales CSV")
            
        except Exception as e:
            logger.error("Failed to parse Namecheap CSV", error=str(e), filename=filename)
            raise
    
    def parse_godaddy_csv(self, content: Any, is_handle: bool = False) -> Iterator[AuctionInput]:
        """
        Parse GoDaddy CSV format
        
        Expected columns: Domain, Start Date, End Date, Price, ...
        (Format to be determined based on actual GoDaddy export)
        """
        try:
            csv_file = content if is_handle else io.StringIO(content)
            reader = csv.DictReader(csv_file)
            
            # Check if headers exist
            if not reader.fieldnames:
                logger.warning("GoDaddy CSV file has no headers or is empty")
                return
            
            for row_num, row in enumerate(reader, start=2):
                try:
                    # GoDaddy format may use different column names
                    domain_name = row.get('Domain', '').strip() or row.get('domain', '').strip()
                    if not domain_name:
                        logger.warning("Skipping row with empty domain", row=row_num)
                        continue
                    
                    # Try different date column name variations
                    start_date = (
                        self._parse_date(row.get('Start Date', '')) or
                        self._parse_date(row.get('startDate', '')) or
                        self._parse_date(row.get('start_date', ''))
                    )
                    
                    end_date = (
                        self._parse_date(row.get('End Date', '')) or
                        self._parse_date(row.get('endDate', '')) or
                        self._parse_date(row.get('end_date', '')) or
                        self._parse_date(row.get('Expiration Date', '')) or
                        self._parse_date(row.get('expirationDate', '')) or
                        self._parse_date(row.get('expiration_date', ''))
                    )
                    
                    if not end_date:
                        logger.warning("Skipping row without expiration date", row=row_num, domain=domain_name)
                        continue
                    
                    # Parse current_bid/price
                    current_bid = self._parse_price(
                        row.get('Price', '') or row.get('price', '') or 
                        row.get('Current Bid', '') or row.get('currentBid', '') or 
                        row.get('current_bid', '')
                    )
                    
                    source_data = {k: v for k, v in row.items()}
                    
                    auction = AuctionInput(
                        domain=domain_name,
                        start_date=start_date,
                        expiration_date=end_date,
                        end_date=end_date,
                        current_bid=current_bid,
                        auction_site='godaddy',
                        source_data=source_data
                    )
                    
                    yield auction
                    
                except Exception as e:
                    logger.warning("Failed to parse GoDaddy CSV row", row=row_num, error=str(e))
                    continue
            
            logger.info("Parsed GoDaddy CSV")
            
        except Exception as e:
            logger.error("Failed to parse GoDaddy CSV", error=str(e))
            raise
    
    def parse_namesilo_csv(self, content: Any, is_handle: bool = False) -> Iterator[AuctionInput]:
        """
        Parse NameSilo CSV format
        
        Expected columns: ID, Leader User ID, Owner User ID, Domain ID, Domain, Status, Type,
        Opening Bid, Current Bid, Max Bid, Domain Created On, Auction End, Url, Bid Count, External Provider
        
        Note: NameSilo auctions do NOT have an end_date (expiration_date). They are active auctions.
        The "Auction End" field is used as the start_date for tracking purposes.
        """
        try:
            csv_file = content if is_handle else io.StringIO(content)
            
            # Debug: Read first bit of file to ensure it's not empty/garbled
            sample = "N/A"
            if is_handle and hasattr(csv_file, 'readable') and csv_file.readable():
                # Peek start of file
                pos = csv_file.tell()
                sample = csv_file.read(500) # Read more bytes to see full header
                csv_file.seek(pos)
                logger.info("NameSilo CSV File Content Peek", sample=sample, position=pos)
            
            reader = csv.DictReader(csv_file)
            
            # Log available columns for debugging
            if reader.fieldnames:
                logger.info("NameSilo CSV columns detected", columns=list(reader.fieldnames))
            else:
                msg = f"NameSilo CSV has no header row or empty file. Content Start: '{sample}'"
                logger.warning(msg)
                return
            
            count = 0
            for row_num, row in enumerate(reader, start=2):
                try:
                    # NameSilo format uses "Domain" column (case-sensitive)
                    domain_name = row.get('Domain', '').strip()
                    if not domain_name:
                        logger.warning("Skipping row with empty Domain", row=row_num, available_keys=list(row.keys()))
                        continue
                    
                    # Parse "Domain Created On" as start_date (when domain was created)
                    start_date = self._parse_date(row.get('Domain Created On', ''))
                    
                    # NameSilo auctions SHOULD have an expiration_date for auctions
                    # For 'Offer/Counter Offer' (Buy Now), it might be empty or valid
                    # Use "Auction End" if available, otherwise far future
                    auction_end_date = self._parse_date(row.get('Auction End', ''))
                    
                    # Parse Current Bid
                    try:
                        current_bid_str = row.get('Current Bid', '0').strip()
                        current_bid = float(current_bid_str) if current_bid_str else 0.0
                    except (ValueError, TypeError):
                        current_bid = 0.0

                    # Parse Url
                    url = row.get('Url', '').strip()

                    from datetime import datetime, timezone
                    far_future_date = datetime(2099, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
                    
                    final_expiration_date = auction_end_date if auction_end_date else far_future_date
                    
                    # For active auctions, we want the real end date
                    # For buy now/make offer, 2099 is appropriate if no date provided
                    
                    auction = AuctionInput(
                        domain=domain_name,
                        start_date=start_date,
                        expiration_date=final_expiration_date,
                        end_date=final_expiration_date,
                        current_bid=current_bid,
                        auction_site='namesilo',
                        source_data=row,
                        link=url
                    )
                    
                    yield auction
                    count += 1
                    
                except Exception as e:
                    logger.warning("Failed to parse NameSilo CSV row", row=row_num, error=str(e))
                    continue
            
            if count == 0:
                logger.warning(f"No valid NameSilo auctions found. Headers: {reader.fieldnames}. Content Start: '{sample}'")
            
            logger.info("Parsed NameSilo CSV streaming started")
            
        except Exception as e:
            logger.error("Failed to parse NameSilo CSV", error=str(e))
            raise
    
    def parse_generic_csv(self, content: Any, auction_site: str, is_handle: bool = False) -> Iterator[AuctionInput]:
        """
        Generic CSV parser that tries to detect common column patterns
        
        Looks for: domain, name, expiration_date, end_date, expiration, etc.
        """
        try:
            csv_file = content if is_handle else io.StringIO(content)
            reader = csv.DictReader(csv_file)
            
            # Get column names
            columns = reader.fieldnames or []
            logger.info("Generic CSV parser", columns=columns, auction_site=auction_site)
            
            # Find domain column
            domain_col = None
            for col in ['domain', 'name', 'Domain', 'Name', 'domain_name']:
                if col in columns:
                    domain_col = col
                    break
            
            # Find expiration date column
            exp_date_col = None
            for col in ['expiration_date', 'end_date', 'expirationDate', 'endDate', 
                       'Expiration Date', 'End Date', 'expiration', 'expires']:
                if col in columns:
                    exp_date_col = col
                    break
            
            # Find start date column
            start_date_col = None
            for col in ['start_date', 'startDate', 'Start Date', 'start']:
                if col in columns:
                    start_date_col = col
                    break
            
            if not domain_col or not exp_date_col:
                raise ValueError(f"Required columns not found. Need domain column and expiration date column. Found: {columns}")
            
            for row_num, row in enumerate(reader, start=2):
                try:
                    domain_name = row.get(domain_col, '').strip()
                    if not domain_name:
                        continue
                    
                    end_date = self._parse_date(row.get(exp_date_col, ''))
                    if not end_date:
                        logger.warning("Skipping row without expiration date", row=row_num, domain=domain_name)
                        continue
                    
                    start_date = self._parse_date(row.get(start_date_col, '')) if start_date_col else None
                    
                    # Find price column
                    price_col = None
                    for col in ['price', 'Price', 'currentBid', 'current_bid', 'Current Bid', 'bid', 'Bid']:
                        if col in columns:
                            price_col = col
                            break
                    
                    current_bid = self._parse_price(row.get(price_col, '')) if price_col else None
                    
                    source_data = {k: v for k, v in row.items()}
                    
                    auction = AuctionInput(
                        domain=domain_name,
                        start_date=start_date,
                        expiration_date=end_date,
                        end_date=end_date,
                        current_bid=current_bid,
                        auction_site=auction_site.lower(),
                        source_data=source_data
                    )
                    
                    yield auction
                    
                except Exception as e:
                    logger.warning("Failed to parse generic CSV row", row=row_num, error=str(e))
                    continue
            
            logger.info("Parsed generic CSV", auction_site=auction_site)
            
        except Exception as e:
            logger.error("Failed to parse generic CSV", error=str(e))
            raise
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse date string in various formats"""
        if not date_str or date_str.strip() == '':
            return None
        
        try:
            # Handle ISO format with Z
            if date_str.endswith('Z'):
                date_str = date_str[:-1] + '+00:00'
            
            # Try ISO format first
            try:
                return datetime.fromisoformat(date_str)
            except ValueError:
                pass
            
            # Try common date formats
            formats = [
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%d',
                '%m/%d/%Y',
                '%d/%m/%Y',
                '%Y-%m-%dT%H:%M:%S',
                '%Y-%m-%dT%H:%M:%S.%f',
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(date_str.strip(), fmt)
                except ValueError:
                    continue
            
            logger.warning("Could not parse date", date_str=date_str)
            return None
            
        except Exception as e:
            logger.warning("Date parsing error", date_str=date_str, error=str(e))
            return None
    
    def _parse_price(self, price_str: str) -> Optional[float]:
        """Parse price/bid string, removing currency symbols and formatting"""
        if not price_str or price_str.strip() == '':
            return None
        
        try:
            # Remove currency symbols, commas, and whitespace
            import re
            # Remove everything except digits, dots, and minus signs
            cleaned = re.sub(r'[^\d.-]', '', str(price_str).strip())
            if not cleaned or cleaned == '-' or cleaned == '.':
                return None
            return float(cleaned)
        except (ValueError, TypeError) as e:
            logger.warning("Could not parse price", price_str=price_str, error=str(e))
            return None
    
    def parse_godaddy_json(self, content: Any, is_handle: bool = False) -> List[AuctionInput]:
        """
        Parse GoDaddy JSON format
        """
        auctions = []
        
        try:
            # Parse JSON content
            if is_handle:
                data = json.load(content)
            else:
                data = json.loads(content)
            
            # Extract data array
            if not isinstance(data, dict) or 'data' not in data:
                raise ValueError("JSON must have a 'data' array")
            
            listings = data.get('data', [])
            if not isinstance(listings, list):
                raise ValueError("'data' must be an array")
            
            logger.info("Parsing GoDaddy JSON", total_listings=len(listings))
            
            for idx, listing in enumerate(listings, start=1):
                try:
                    if not isinstance(listing, dict):
                        logger.warning("Skipping non-dict listing", index=idx)
                        continue
                    
                    # Extract domain name
                    domain_name = listing.get('domainName', '').strip()
                    if not domain_name:
                        logger.warning("Skipping listing with empty domainName", index=idx)
                        continue
                    
                    # Parse auction end time (expiration_date)
                    auction_end_time_str = listing.get('auctionEndTime', '')
                    if not auction_end_time_str:
                        logger.warning("Skipping listing without auctionEndTime", index=idx, domain=domain_name)
                        continue
                    
                    expiration_date = self._parse_date(auction_end_time_str)
                    if not expiration_date:
                        logger.warning("Could not parse auctionEndTime", index=idx, domain=domain_name, date_str=auction_end_time_str)
                        continue
                    
                    # Parse price (current bid)
                    price_str = listing.get('price', '')
                    current_bid = self._parse_price(price_str)
                    
                    # Extract link (auction URL)
                    link = listing.get('link', '').strip() or None
                    
                    # Store all original data in source_data
                    source_data = {k: v for k, v in listing.items()}
                    # Also include meta information if available
                    if 'meta' in data:
                        source_data['_meta'] = data['meta']
                    
                    auction = AuctionInput(
                        domain=domain_name,
                        start_date=None,  # GoDaddy JSON doesn't provide start date
                        expiration_date=expiration_date,
                        end_date=expiration_date,
                        current_bid=current_bid,
                        auction_site='godaddy',
                        source_data=source_data,
                        link=link
                    )
                    
                    auctions.append(auction)
                    
                except Exception as e:
                    logger.warning("Failed to parse GoDaddy JSON listing", index=idx, error=str(e))
                    continue
            
            logger.info("Parsed GoDaddy JSON", total_auctions=len(auctions))
            return auctions
            
        except json.JSONDecodeError as e:
            logger.error("Failed to parse JSON", error=str(e))
            raise ValueError(f"Invalid JSON format: {str(e)}")
        except Exception as e:
            logger.error("Failed to parse GoDaddy JSON", error=str(e))
            raise



