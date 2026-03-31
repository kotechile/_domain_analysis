#!/usr/bin/env python3
import time
import requests
import sys

URL = "https://scout.buildomain.com/api/v1/auctions/upload-progress/latest-active"

def format_time_diff(started_str, updated_str):
    return ""

def main():
    print(f"Monitoring active auction upload jobs at {URL}")
    print("Press Ctrl+C to exit.\n")
    
    last_processed = 0
    last_time = time.time()
    
    try:
        while True:
            try:
                resp = requests.get(URL, timeout=5)
                
                if resp.status_code != 200:
                    print(f"\rAPI Error: {resp.status_code}. Retrying...", end="", flush=True)
                    time.sleep(2)
                    continue
                    
                data = resp.json()
                
                if not data.get("success") or data.get("status") == "completed":
                    print("\rNo active jobs currently processing! (Or latest is finished)", end="", flush=True)
                else:
                    filename = data.get("filename", "")
                    stage = data.get("current_stage", "")
                    total = data.get("total_records", 0)
                    processed = data.get("processed_records", 0)
                    pct = data.get("progress_percentage", 0)
                    
                    # Calculate speed
                    current_time = time.time()
                    elapsed = current_time - last_time
                    speed = 0
                    if elapsed > 0:
                        speed = (processed - last_processed) / elapsed
                        
                    last_processed = processed
                    last_time = current_time
                    
                    status_line = (
                        f"\r🚀 {filename} | "
                        f"Stage: {stage} | "
                        f"Processed: {processed:,}/{total:,} ({pct:.2f}%) | "
                        f"Speed: {speed:,.1f} req/s"
                    )
                    
                    # Clear line and print
                    sys.stdout.write('\033[2K\033[1G')
                    sys.stdout.write(status_line)
                    sys.stdout.flush()
            
            except Exception as e:
                sys.stdout.write(f"\rConnection error... reconnecting... {e}          ")
                sys.stdout.flush()
                
            time.sleep(2.5)  # Fetch every 2.5 seconds
            
    except KeyboardInterrupt:
        print("\n\nStopped monitoring.")

if __name__ == "__main__":
    main()
