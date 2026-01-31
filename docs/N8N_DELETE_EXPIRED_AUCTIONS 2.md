# N8N: Delete Expired Auctions Before File Processing

## Overview
This guide shows how to add a step to delete expired auctions (expiration_date < NOW()) before processing new files in the N8N workflow.

## Option 1: Use PostgreSQL Function (Recommended)

### Step 1: Add PostgreSQL Node
1. In your N8N workflow, add a new **PostgreSQL** node
2. Name it: **"Delete Expired Auctions"**
3. Place it right after **"Daily Schedule (6 AM)"** and before the download nodes

### Step 2: Configure the Node
1. **Operation**: Select **"Execute Query"**
2. **Query**: Enter the following SQL:
   ```sql
   SELECT delete_expired_auctions() as deleted_count;
   ```
3. **Credentials**: Use your existing PostgreSQL credentials

### Step 3: Connect the Node
- Connect **"Daily Schedule (6 AM)"** → **"Delete Expired Auctions"**
- Connect **"Delete Expired Auctions"** → **"Download GoDaddy Tomorrow"**, **"Download GoDaddy Today"**, **"Download Namecheap Auctions"**, **"Download Namecheap Buy Now"** (all 4 in parallel)

### Result
The function will:
- Delete all auctions where `expiration_date < NOW()`
- Return the count of deleted records
- The count will be available in the node output as `deleted_count`

---

## Option 2: Fix Existing Delete Node

If you want to use the existing "Delete table or rows" node:

### Configuration:
1. **Operation**: Keep as **"Delete Table or Rows"**
2. **Table**: `auctions`
3. **Where Clause**:
   - **Column**: `expiration_date`
   - **Condition**: `<` (less than)
   - **Value**: `NOW()` (PostgreSQL function, NOT JavaScript)

**Important**: In the value field, you need to use PostgreSQL's `NOW()` function. However, N8N's PostgreSQL node might not allow direct SQL functions in the value field.

**Workaround**: Use `CURRENT_TIMESTAMP` or configure it as:
- **Value**: Leave empty or use `CURRENT_TIMESTAMP`
- Or use **"Execute Query"** operation with:
  ```sql
  DELETE FROM auctions WHERE expiration_date < NOW();
  ```

---

## Recommended Approach

**Use Option 1** (PostgreSQL function) because:
- ✅ Uses the existing `delete_expired_auctions()` function
- ✅ Returns the count of deleted records
- ✅ Has error handling built into the function
- ✅ More maintainable (function can be updated without changing N8N workflow)

## Example Node Configuration (Option 1)

```json
{
  "parameters": {
    "operation": "executeQuery",
    "query": "SELECT delete_expired_auctions() as deleted_count;",
    "options": {}
  },
  "type": "n8n-nodes-base.postgres",
  "name": "Delete Expired Auctions",
  "credentials": {
    "postgres": {
      "id": "DxQODs2W8TambApf",
      "name": "Postgres account"
    }
  }
}
```

## Workflow Order

```
Daily Schedule (6 AM)
    ↓
Delete Expired Auctions  ← NEW NODE
    ↓
    ├─→ Download GoDaddy Tomorrow
    ├─→ Download GoDaddy Today
    ├─→ Download Namecheap Auctions
    └─→ Download Namecheap Buy Now
```

## Testing

After adding the node, test it:
1. Check the node output - it should show `deleted_count` with the number of records deleted
2. Verify in your database that expired records are gone
3. Ensure the workflow continues to download and process files normally




