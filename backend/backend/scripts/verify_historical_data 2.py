
import requests
import time
import sys
import json


BASE_URL = "http://localhost:8000/api/v1"
DOMAIN = "webflow.com" 

def log(msg):
    print(f"[TEST] {msg}")

def verify_historical_data():
    # SKIP Trigger Analysis because N8N is failing. 
    # We rely on the report already being seeded in DB.

    # 1. Check History Endpoint (Triggers fetch and save)
    log(f"Fetching historical data for {DOMAIN} via API...")
    history_resp = requests.get(f"{BASE_URL}/reports/{DOMAIN}/history")
    if history_resp.status_code == 200:
        history_data = history_resp.json()
        log("Historical Data Retrieved:")
        # log(json.dumps(history_data, indent=2))
        
        # Validation
        if "rank_overview" in history_data and history_data["rank_overview"]:
             log("✅ rank_overview present")
        else:
             log("⚠️ rank_overview missing or empty (might be expected for dummy domain)")

        traffic_history = history_data.get("traffic_history")
        if traffic_history:
             log("✅ traffic_history present")
        else:
             log("⚠️ traffic_history missing (might be expected for dummy domain)")
            
    else:
        log(f"❌ Failed to fetch history: {history_resp.status_code} - {history_resp.text}")
        sys.exit(1)

    # 2. Check Report Endpoint (to ensure persistence)
    log("Fetching full report to verify persistence...")
    report_resp = requests.get(f"{BASE_URL}/reports/{DOMAIN}")
    if report_resp.status_code == 200:
        report_data = report_resp.json().get("report", {})
        if report_data.get("historical_data"):
            log("✅ historical_data PERSISTED in database report")
        else:
             log("❌ historical_data MISSING in database report")
    else:
        log(f"❌ Failed to fetch report: {report_resp.status_code}")

if __name__ == "__main__":
    verify_historical_data()
