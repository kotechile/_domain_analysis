# N8N HTTP Request URL Fix

## Error Message

```
Problem in node 'HTTP Request'
Invalid URL: https://httpbin.org/post. URL must start with "http" or "https".
```

This error occurs even though the URL clearly starts with "https://". This is usually caused by N8N not recognizing the expression result as a valid URL string.

## Solutions (Try in Order)

### Solution 1: Use String() Conversion (Most Common Fix)

In the HTTP Request node's **URL** field, use:

```
{{ String($('Webhook').item.json.body.callback_url) }}
```

This forces N8N to treat the value as a string.

### Solution 2: Use Expression Editor to Select Field

1. Click the **expression editor icon** (`</>`) next to the URL field
2. Navigate to: `Webhook` → `item` → `json` → `body` → `callback_url`
3. Select it directly - this ensures the correct path

### Solution 3: Check if Using Correct Node Reference

If the HTTP Request node is connected to the **IF node** (not directly to Webhook), you might need:

```
{{ String($('IF').item.json.body.callback_url) }}
```

Or if it's after DataForSEO:

```
{{ String($('Webhook').item.json.body.callback_url) }}
```

**Important**: The node reference depends on which node the HTTP Request is connected to.

### Solution 4: Use $json if Connected to Previous Node

If the HTTP Request node receives data from the **DataForSEO node** or **IF node**, try:

```
{{ String($json.body.callback_url) }}
```

But this usually doesn't work because `callback_url` is in the Webhook data, not in DataForSEO output.

### Solution 5: Hardcode for Testing (Temporary)

To test if the issue is with the expression:

1. Temporarily hardcode the URL:
   ```
   https://overmild-untenuously-penney.ngrok-free.dev/api/v1/n8n/webhook/backlinks
   ```

2. If this works, the issue is with the expression evaluation
3. Then try Solution 1 with `String()` conversion

### Solution 6: Check for Hidden Characters

1. Click in the URL field
2. Select all (Cmd+A / Ctrl+A)
3. Delete and retype the expression:
   ```
   {{ String($('Webhook').item.json.body.callback_url) }}
   ```

Sometimes copy-paste can introduce hidden characters.

## Recommended Fix

**Use this expression in the HTTP Request node URL field:**

```
{{ String($('Webhook').item.json.body.callback_url) }}
```

The `String()` function ensures N8N treats the value as a string, which should resolve the validation error.

## Verification

After applying the fix:

1. **Save the workflow**
2. **Activate the workflow** (toggle should be ON)
3. **Test with curl:**
   ```bash
   curl -X POST https://n8n.aichieve.net/webhook/webhook/backlinks \
     -H "Content-Type: application/json" \
     -d '{
       "domain": "test.com",
       "callback_url": "https://httpbin.org/post",
       "request_id": "test-123",
       "type": "summary"
     }'
   ```
4. **Check N8N Executions**:
   - HTTP Request node should execute successfully
   - No "Invalid URL" error
   - Status should be green (success)

## Why This Happens

N8N's HTTP Request node validates the URL field strictly. Sometimes when using expressions, N8N might:
- Evaluate the expression to a different type (object, array, etc.)
- Not recognize the string as a valid URL format
- Have issues with expression evaluation order

Using `String()` explicitly converts the value to a string, which helps N8N's validator recognize it as a valid URL.

## Additional Notes

- **For Summary Workflow**: Use the same fix in the HTTP Request node (success callback)
- **For Detailed Workflow**: Use the same fix in both success and error callback HTTP Request nodes
- **Error Callback**: Should also use `{{ String($('Webhook').item.json.body.callback_url) }}`

## Still Not Working?

If `String()` doesn't work, try:

1. **Check the actual value**: Add a "Set" node before HTTP Request to log the value:
   - Add a **Set** node
   - Set a field: `test_url` = `{{ $('Webhook').item.json.body.callback_url }}`
   - Check the output to see what value it actually has

2. **Use JSON.stringify()**:
   ```
   {{ JSON.stringify($('Webhook').item.json.body.callback_url).replace(/"/g, '') }}
   ```

3. **Check N8N version**: Some older versions have expression evaluation bugs. Update N8N if possible.

















