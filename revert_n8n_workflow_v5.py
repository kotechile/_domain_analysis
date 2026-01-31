
import json
import os

FILE_PATH = "n8n/Download and Process Auction Files - Supabase Storage.json"
# Placeholder URL - User must update this!
BACKEND_URL_DIRECT = "http://YOUR_VPS_IP:8010/api/v1/auctions/upload-csv"

def revert_workflow_v5():
    if not os.path.exists(FILE_PATH):
        print(f"File not found: {FILE_PATH}")
        return

    with open(FILE_PATH, 'r') as f:
        workflow = json.load(f)

    target_nodes_prefixes = [
        "Upload GoDaddy Tomorrow",
        "Upload GoDaddy Today",
        "Upload Namecheap Auctions",
        "Upload Namecheap Buy Now",
        "Upload NameSilo"
    ]
    
    # Identify Trigger Nodes to delete
    trigger_nodes_to_delete = []
    
    existing_nodes = {n['name']: n for n in workflow['nodes']}
    
    for node in workflow['nodes']:
        name = node['name']
        if "Trigger Backend Processing" in name:
            trigger_nodes_to_delete.append(name)
    
    # Update Upload Nodes
    for prefix in target_nodes_prefixes:
        # Find the node that matches this prefix 
        found_node = None
        for name in existing_nodes:
            if name.startswith(prefix):
                found_node = existing_nodes[name]
                break
        
        if not found_node:
            continue
            
        print(f"Updating node to V5 Direct (Query Params): {found_node['name']}")
        
        # New Name
        new_name = prefix + " to Backend"
        found_node['name'] = new_name
        
        # Determine Input Field
        input_field = "file_0"
        if "Namecheap" in prefix or "NameSilo" in prefix:
            input_field = "data"
            
        # Determine Enum Values
        site = "godaddy"
        if "Namecheap" in prefix: site = "namecheap"
        if "NameSilo" in prefix: site = "namesilo"
        
        offering = "auction"
        if "Buy Now" in prefix: offering = "buy_now"
        
        # Configure for Direct Backend Upload
        # Multipart Body for File
        # Query Params for site/offering
        found_node['parameters'] = {
            "method": "POST",
            "url": BACKEND_URL_DIRECT,
            "sendBody": True,
            "contentType": "multipart-form-data",
            "bodyParameters": {
                "parameters": [
                    {
                        "name": "file",
                        "parameterType": "formBinaryData",
                        "inputDataFieldName": input_field
                    }
                ]
            },
            "sendQuery": True,
            "queryParameters": {
                "parameters": [
                    {
                        "name": "auction_site",
                        "value": site
                    },
                    {
                        "name": "offering_type",
                        "value": offering
                    }
                ]
            },
            "options": {}
        }
        
        # Remove credentials or auth headers
        if 'credentials' in found_node:
            del found_node['credentials']
            
    # Remove Trigger Nodes
    workflow['nodes'] = [n for n in workflow['nodes'] if n['name'] not in trigger_nodes_to_delete]
    
    # Fix Connections
    new_connections = {}
    upload_nodes_new_names = [prefix + " to Backend" for prefix in target_nodes_prefixes]
    
    for source, targets in workflow['connections'].items():
        new_source = source
        for prefix in target_nodes_prefixes:
            if source.startswith(prefix) and "Trigger" not in source:
                new_source = prefix + " to Backend"
                break
        
        if "Trigger Backend Processing" in source:
            continue 
            
        new_target_groups = []
        for group in targets.get('main', []):
            new_group = []
            for t in group:
                target_node = t['node']
                
                if "Trigger Backend Processing" in target_node:
                    if new_source in upload_nodes_new_names:
                        t['node'] = "Aggregate Results"
                        new_group.append(t)
                else:
                    for prefix in target_nodes_prefixes:
                        if target_node.startswith(prefix) and "Trigger" not in target_node:
                            t['node'] = prefix + " to Backend"
                            break
                    new_group.append(t)
                    
            if new_group:
                new_target_groups.append(new_group)
                
        if new_target_groups:
             new_connections[new_source] = {'main': new_target_groups}

    workflow['connections'] = new_connections

    with open(FILE_PATH, 'w') as f:
        json.dump(workflow, f, indent=2)
    print("Updated N8N workflow to V5 Direct (Query Params). YOU MUST EDIT URL.")

if __name__ == "__main__":
    revert_workflow_v5()
