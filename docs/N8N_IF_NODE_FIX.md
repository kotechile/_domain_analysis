# Fix N8N IF Node: String vs Number Comparison

## Problem

The IF node condition is comparing a string to a number:
- `{{ $json.status_code }}` returns a **string** (e.g., `"20000"`)
- Comparing to number `20000` fails because `"20000" !== 20000`

## Solution Options

### Option 1: Convert String to Number (Recommended)

In the IF node condition:

**Value 1**: 
```
{{ Number($json.status_code) }}
```

**Operation**: `is not equal to`

**Value 2**: 
```
20000
```

This converts the string to a number before comparison.

### Option 2: Compare String to String

**Value 1**: 
```
{{ $json.status_code }}
```

**Operation**: `is not equal to`

**Value 2**: 
```
"20000"
```

**Note**: Make sure to include quotes around `20000` to make it a string.

### Option 3: Use String Comparison Function

**Value 1**: 
```
{{ String($json.status_code) }}
```

**Operation**: `is not equal to`

**Value 2**: 
```
"20000"
```

## Step-by-Step Fix

1. **Open your N8N workflow** (Summary or Details)
2. **Click on the IF node** (the one checking for errors)
3. **In the Parameters tab**, find the condition:
   - Current: `{{ $json.status_code }}` is not equal to `20000`
4. **Update Value 1** to:
   ```
   {{ Number($json.status_code) }}
   ```
5. **Keep Value 2** as: `20000` (number)
6. **Save the workflow** (Ctrl+S / Cmd+S)

## Alternative: Use String Comparison

If Option 1 doesn't work, try:

1. **Value 1**: `{{ $json.status_code }}`
2. **Operation**: `is not equal to`
3. **Value 2**: `"20000"` (with quotes - make it a string)

## Verification

After fixing, test the workflow:

1. Click "Execute Workflow" in N8N
2. Check the IF node output
3. Verify it correctly routes:
   - **True path** (error): When status_code ≠ 20000
   - **False path** (success): When status_code = 20000

## Why This Happens

DataForSEO API returns `status_code` as a number in JSON, but N8N's DataForSEO node might convert it to a string when processing. Always check the actual data type in N8N by:

1. Clicking the expression editor (`fx` button)
2. Browsing the data structure
3. Checking the actual type of `status_code`

## Recommended Fix

Use **Option 1** (convert to number):

```
Value 1: {{ Number($json.status_code) }}
Operation: is not equal to
Value 2: 20000
```

This is the most reliable approach as it handles both string and number inputs.

















