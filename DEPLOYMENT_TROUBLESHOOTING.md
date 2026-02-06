# Deployment Troubleshooting Guide

## Issue: Connection Error on Render

### Root Cause Analysis

The connection error is likely caused by one of these issues:

1. **Memory Limitations**: Sentence-transformers model (all-MiniLM-L6-v2) is ~90MB and may exceed Render free tier memory during initialization
2. **Startup Timeout**: Downloading the model on first startup may exceed Gunicorn's timeout
3. **Environment Variables**: Missing Supabase credentials

### Solutions

#### Option 1: Use Render's Paid Tier ($7/month)
- Provides 512MB RAM (vs 256MB free)
- Supports larger models
- Recommended for production

#### Option 2: Revert to OpenAI Embeddings (Recommended for Free Tier)
- Smaller client library
- No model download needed
- Requires adding OpenAI credits ($5-10)

#### Option 3: Keep Sentence-Transformers + Optimize
- Add lazy loading
- Increase Gunicorn timeout
- Reduce worker count to 1
- May still fail on free tier

## Quick Fix: Revert to OpenAI for Deployment

### Step 1: Update config.py for Deployment
```python
# In config.py, use environment variable to switch models
import os

# Use OpenAI for deployment, sentence-transformers for local
if os.getenv("RENDER"):
    EMBEDDING_MODEL = "text-embedding-3-small"
    EMBEDDING_DIMENSION = 1536
else:
    EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"  
    EMBEDDING_DIMENSION = 384
```

### Step 2: Set RENDER Environment Variable
In Render dashboard:
1. Go to Environment tab
2. Add: `RENDER=true`

### Step 3: Keep Local Data as-is
- Local indexing uses sentence-transformers (free)
- Deployment uses OpenAI (requires credits)
- Supabase needs to store both embedding types OR you choose one

## Recommended Path Forward

**For Free Deployment That Works:**

1. Use sentence-transformers locally (already done ✅)
2. Deploy with minimal changes - just optimize the web app
3. Accept that Render free tier may have limits

**OR**

**For Robust Deployment:**

1. Add $5-10 OpenAI credits
2. Use OpenAI embeddings for deployment  
3. Keep sentence-transformers for local development
4. Update Supabase schema back to 1536 dimensions

## Current Status

- ✅ Local indexing complete (6,530 sections, 384-dim)
- ❌ Deployment failing (connection error)
- Decision needed: Optimize for free tier OR use paid services
