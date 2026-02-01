
import json

INPUT_FILE = "/Users/jorgefernandezilufi/Documents/_article_research/_domain_analysis/n8n/Download and Process Auction Files - Supabase Storage - FINAL_v2.json"
OUTPUT_FILE = "/Users/jorgefernandezilufi/Documents/_article_research/_domain_analysis/n8n/Download and Process Auction Files - Supabase Storage - FINAL_v3.json"

def patch_url():
    with open(INPUT_FILE, 'r') as f:
        data = json.load(f)
        
    for node in data['nodes']:
        if "to Supabase" in node['name'] and node['type'] == "n8n-nodes-base.httpRequest":
            params = node.get('parameters', {})
            
            # Update URL to use binary fileName directly, which is more reliable than json.filename here
            if "url" in params:
                current_url = params['url']
                new_url = current_url.replace("{{ $json.filename }}", "{{ $binary.data.fileName }}")
                params['url'] = new_url
                print(f"Updated URL for '{node['name']}' to: {new_url}")
                
            node['parameters'] = params

    with open(OUTPUT_FILE, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"Saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    patch_url()
