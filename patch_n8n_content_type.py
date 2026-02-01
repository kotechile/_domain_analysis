
import json

INPUT_FILE = "/Users/jorgefernandezilufi/Documents/_article_research/_domain_analysis/n8n/Download and Process Auction Files - Supabase Storage - FINAL.json"
OUTPUT_FILE = "/Users/jorgefernandezilufi/Documents/_article_research/_domain_analysis/n8n/Download and Process Auction Files - Supabase Storage - FINAL_v2.json"

def patch_content_type():
    with open(INPUT_FILE, 'r') as f:
        data = json.load(f)
        
    for node in data['nodes']:
        if "to Supabase" in node['name'] and node['type'] == "n8n-nodes-base.httpRequest":
            params = node.get('parameters', {})
            
            # Ensure Header Parameters block exists
            if 'headerParameters' not in params:
                params['headerParameters'] = {'parameters': []}
                
            header_params_list = params['headerParameters']['parameters']
            
            # Check if Content-Type already exists
            found = False
            for hp in header_params_list:
                if hp['name'].lower() == 'content-type':
                    found = True
                    break
            
            if not found:
                header_params_list.append({
                    "name": "Content-Type",
                    "value": "={{ $binary.data.mimeType }}"
                })
                
            node['parameters'] = params

    with open(OUTPUT_FILE, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"Added Content-Type header and saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    patch_content_type()
