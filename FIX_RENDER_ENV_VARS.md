# 🔧 FIX: Add Environment Variables to Render

## ❌ Problem: Connection Error

Your website is deployed but showing **"Connection error"** because Render doesn't have your API keys.

---

## ✅ Solution: Add Environment Variables (5 minutes)

### Step 1: Go to Render Dashboard
1. Visit: https://dashboard.render.com
2. Click on **"california-code-of-regulations"** service
3. Click on **"Environment"** tab (left sidebar)

### Step 2: Add These Variables

Click **"Add Environment Variable"** for EACH of these:

#### Variable 1: GEMINI_API_KEY
```
Key: GEMINI_API_KEY
Value: [Copy from your .env file below]
```

#### Variable 2: PINECONE_API_KEY
```
Key: PINECONE_API_KEY
Value: [Copy from your .env file below]
```

#### Variable 3: PINECONE_INDEX_NAME
```
Key: PINECONE_INDEX_NAME
Value: [Copy from your .env file below (e.g., ccr-sections)]
```

#### Variable 4: OPENAI_API_KEY (Optional)
```
Key: OPENAI_API_KEY
Value: [Copy from your .env file below]
```

---

## 📋 Your Values (From .env file)

**CHECK YOUR `.env` FILE** and copy these values:

1. Open: `c:\Users\mahesh polamreddy\.gemini\antigravity\scratch\ccr-compliance-agent\.env`

2. Find these lines and copy the values:
   - `GEMINI_API_KEY=...`
   - `PINECONE_API_KEY=...`
   - `PINECONE_INDEX_NAME=...`
   - `OPENAI_API_KEY=...`

---

## ⚙️ Step 3: Save and Redeploy

After adding all variables:
1. Click **"Save Changes"** button
2. Render will **automatically redeploy** (wait 2-3 min)
3. Website will work! ✅

---

## 🧪 Step 4: Test Again

Once redeployed:
1. Visit: https://california-code-of-regulations.onrender.com
2. Type: **"restaurant regulations"**
3. Should work without connection error! ✅

---

## 📸 Visual Guide

**Where to add variables:**
```
Render Dashboard
  → Your Service (california-code-of-regulations)
    → Environment Tab (left sidebar)
      → Add Environment Variable (button)
        → Enter Key + Value
        → Click "Add"
        → Repeat for all 3-4 variables
        → Click "Save Changes"
```

**After saving:**
- Render shows: "Deploying..."
- Wait 2-3 minutes
- Status: "Live" ✅
- Test website!

---

## ✅ Checklist

- [ ] Go to Render Environment tab
- [ ] Add GEMINI_API_KEY
- [ ] Add PINECONE_API_KEY
- [ ] Add PINECONE_INDEX_NAME
- [ ] (Optional) Add OPENAI_API_KEY
- [ ] Click "Save Changes"
- [ ] Wait for redeploy (2-3 min)
- [ ] Test website

---

**This is the ONLY remaining issue!** Once you add these keys, your website will work perfectly! 🚀
