
import sys
import os
import logging

# Add src to path
sys.path.append(os.path.join(os.getcwd(), 'backend/src'))

from services.csv_parser_service import CSVParserService

# Configure logging to see output
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_namecheap_parsing():
    parser = CSVParserService()
    
    # Test Case 1: Standard Market Sales Format (from code expectation)
    # name, startDate, endDate, price
    content_valid = """name,startDate,endDate,price,url
    test1.com,2023-01-01,2023-12-31,10.00,http://example.com"""
    
    print("\n--- Test 1: Standard Headers ---")
    results = list(parser.parse_csv(content_valid, 'namecheap', 'Namecheap_Market_Sales.csv'))
    print(f"Results: {len(results)}")
    if len(results) == 0:
        print("FAILED to parse standard headers")
        
    # Test Case 2: Alternative Headers (Case sensitivity)
    content_caps = """Name,StartDate,EndDate,Price,Url
    test2.com,2023-01-01,2023-12-31,20.00,http://example.com"""
    
    print("\n--- Test 2: Capitalized Headers ---")
    results = list(parser.parse_csv(content_caps, 'namecheap', 'Namecheap_Market_Sales.csv'))
    print(f"Results: {len(results)}")

    # Test Case 3: Missing End Date (Should fail/skip)
    content_no_end = """name,startDate,price
    test3.com,2023-01-01,10.00"""
    
    print("\n--- Test 3: Missing End Date ---")
    results = list(parser.parse_csv(content_no_end, 'namecheap', 'Namecheap_Market_Sales.csv'))
    print(f"Results: {len(results)}")
    
    # Test Case 5: User Provided Sample
    content_user_sample = """url,name,startDate,endDate,price,startPrice,renewPrice,bidCount,ahrefsDomainRating,umbrellaRanking,cloudflareRanking,estibotValue,extensionsTaken,keywordSearchCount,registeredDate,lastSoldPrice,lastSoldYear,isPartnerSale,semrushAScore,majesticCitation,ahrefsBacklinks,semrushBacklinks,majesticBacklinks,majesticTrustFlow,goValue
https://www.namecheap.com/market/sale/2RWaPo3CJb32sMzrzpuQse/,sgs.cc,2026-01-23T08:38:08Z,2026-02-15T16:00:00Z,1.00,1.00,13.98,1,0,,,140.00,340,241000,2015-01-15T00:00:00Z,,,1,,,16,,,,1116.00
https://www.namecheap.com/market/sale/qMNdQL59ujA93Mo8yDKmzk/,menu.pro,2026-02-03T10:31:53Z,2026-03-04T16:00:00Z,1.00,1.00,33.98,1,1,,,270.00,384,633000,2016-01-26T00:00:00Z,,,1,2,,9,31,,,3853.00"""

    print("\n--- Test 5: User Sample ---")
    results = list(parser.parse_csv(content_user_sample, 'namecheap', 'Namecheap_Market_Sales.csv'))
    print(f"Results: {len(results)}")
    if len(results) > 0:
        print(f"Sample First Record: {results[0]}")
    else:
         print("FAILED to parse user sample")


    # Test Case 6: Market Sales with Quoted Headers and Spaces (Simulating potential issue)
    content_complex = """"Name"," Start Date "," End Date "," Price "
    "quoted.com","2023-01-01","2023-12-31","100.00"
    """
    print("\n--- Test 6: Complex Market Sales Headers ---")
    results = list(parser.parse_csv(content_complex, 'namecheap', 'Namecheap_Market_Sales.csv'))
    print(f"Results: {len(results)}")
    if len(results) > 0:
        print(f"First Record: {results[0]}")
    else:
        print("FAILED to parse complex headers")


    # Test Case 7: Tab Delimited File (Simulating different dialect)
    content_tab = """Name\tStart Date\tEnd Date\tPrice\n"tab.com"\t"2023-01-01"\t"2023-12-31"\t"50.00" """
    print("\n--- Test 7: Tab Delimited Headers ---")
    results = list(parser.parse_csv(content_tab, 'namecheap', 'Namecheap_Market_Sales.csv'))
    print(f"Results: {len(results)}")
    if len(results) > 0:
        print(f"First Record: {results[0]}")
    else:
        print("FAILED to parse tab delimited headers")

if __name__ == "__main__":
    test_namecheap_parsing()
