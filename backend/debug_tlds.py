import sys
import os
from dotenv import load_dotenv

# Setup paths and env
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
load_dotenv(os.path.join(os.path.dirname(__file__), 'src/.env'))
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

from utils.config import get_settings
from services.domain_scoring_service import DomainScoringService

def check_tlds():
    print("--- Checking Settings ---")
    settings = get_settings()
    print(f"TIER_1_TLDS in settings: {settings.TIER_1_TLDS}")
    print(f"MIN_WORD_RECOGNITION_RATIO: {settings.MIN_WORD_RECOGNITION_RATIO}")
    
    if '.ai' in settings.TIER_1_TLDS:
        print("PASS: .ai FOUND in settings")
    else:
        print("FAIL: .ai NOT FOUND in settings")

    print("\n--- Checking DomainScoringService ---")
    service = DomainScoringService()
    print(f"tier_1_tlds in service: {service.tier_1_tlds}")
    
    if '.ai' in service.tier_1_tlds:
        print("PASS: .ai FOUND in service")
        
        # Test a .ai domain
        from models.domain_analysis import NamecheapDomain
        test_domain = NamecheapDomain(
            name="example.ai",
            auction_type="auction",
            price=10.0,
            currency="USD",
            time_left="1d"
        )
        passed, reason = service._stage1_filter(test_domain)
        print(f"Test 'example.ai' filter status: {'PASSED' if passed else 'FAILED'}")
        if not passed:
            print(f"Reason: {reason}")
    else:
        print("FAIL: .ai NOT FOUND in service")

if __name__ == "__main__":
    check_tlds()
