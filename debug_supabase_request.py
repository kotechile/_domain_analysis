
import requests
import os

URL = "https://sbdomain.giniloh.com/storage/v1/object/auction-csvs/debug-test.txt"
TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJzdXBhYmFzZSIsImlhdCI6MTc2NDYzNjk2MCwiZXhwIjo0OTIwMzEwNTYwLCJyb2xlIjoic2VydmljZV9yb2xlIn0.hMqiDDJIp9xxZtHJtyfvxs6utizP9F-mHqonRw0EFVc"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "x-upsert": "true",
    "Content-Type": "text/plain"
}

data = "Hello World via Python Debug Script"

print(f"Testing Upload to: {URL}")
try:
    response = requests.post(URL, headers=headers, data=data)
    print(f"Status Code: {response.status_code}")
    print(f"Response Body: {response.text}")
except Exception as e:
    print(f"Request failed: {e}")
