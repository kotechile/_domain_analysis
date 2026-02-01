
import json

INPUT_FILE = "/Users/jorgefernandezilufi/Documents/_article_research/_domain_analysis/n8n/Download and Process Auction Files - Supabase Storage - FIXED.json"
OUTPUT_FILE = "/Users/jorgefernandezilufi/Documents/_article_research/_domain_analysis/n8n/Download and Process Auction Files - Supabase Storage - FINAL.json"

def patch_headers():
    with open(INPUT_FILE, 'r') as f:
        data = json.load(f)
        
    for node in data['nodes']:
        if "to Supabase" in node['name'] and node['type'] == "n8n-nodes-base.httpRequest":
            params = node.get('parameters', {})
            
            # Enable Headers (Crucial fix)
            params['sendHeaders'] = True
            
            # Ensure compatibility fields are persisted
            params['inputDataFieldName'] = 'data'
            params['binaryPropertyName'] = 'data'
            
            node['parameters'] = params

    with open(OUTPUT_FILE, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"Patched 'sendHeaders' and saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    patch_headers()
