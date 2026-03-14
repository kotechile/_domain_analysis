-- Fix existing NameSilo records that were incorrectly set to 2099-12-31
-- Extracts the 'Auction End' date from the source_data JSON and updates the expiration_date column

UPDATE auctions
SET expiration_date = (source_data->>'Auction End')::timestamptz
WHERE auction_site = 'namesilo'
  AND expiration_date > '2090-01-01'
  AND source_data->>'Auction End' IS NOT NULL;

-- Verification query
SELECT count(*) as fixed_records 
FROM auctions 
WHERE auction_site = 'namesilo' 
  AND expiration_date < '2090-01-01' 
  AND source_data->>'Auction End' IS NOT NULL;
