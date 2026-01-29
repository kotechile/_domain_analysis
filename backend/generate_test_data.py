import csv
import random
from datetime import datetime, timedelta

def generate_large_csv(filename, num_records=500000):
    fieldnames = ['url', 'name', 'startDate', 'endDate', 'price']
    
    start_time = datetime.utcnow()
    
    with open(filename, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for i in range(num_records):
            domain = f"test-domain-{i}-{random.randint(1000, 9999)}.com"
            writer.writerow({
                'url': f"https://www.namecheap.com/market/domain/{domain}/",
                'name': domain,
                'startDate': (start_time - timedelta(days=1)).isoformat() + 'Z',
                'endDate': (start_time + timedelta(days=7)).isoformat() + 'Z',
                'price': f"${random.randint(10, 5000)}"
            })
            
            if i % 10000 == 0:
                print(f"Generated {i} records...")

    print(f"Successfully generated {filename} with {num_records} records.")

if __name__ == "__main__":
    generate_large_csv('large_test_auctions.csv', 500000)
