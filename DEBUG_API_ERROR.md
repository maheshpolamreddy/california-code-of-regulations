# Debugging Notes: API Error Investigation

## Current Status
- ✅ Website deployed and accessible
- ✅ Lazy loading implemented successfully
- ❌ API returns HTML error instead of JSON when querying

## Error Observed
```
SYSTEM FAILURE: Unexpected token '<', "<html>" is not valid JSON
```

## Root Cause Analysis
The Flask `/api/query` endpoint is crashing and returning an HTML error page instead of a JSON response.

## Actions Taken
1. Added comprehensive error handling with tracebacks
2. Added MemoryError handler for potential RAM issues
3. Committed changes: `a46b3c9`

## Next Steps
Need user to check Render logs to see:
- Exact Python traceback when query executed
- Whether it's a memory error, initialization error, or other issue

## Hypothesis
Most likely causes (in order):
1. **Memory error** - Model loading on first query exceeds 512MB RAM
2. **Initialization failure** - Agent/vectordb not properly initialized
3. **Missing dependency** - Some import failing on production
