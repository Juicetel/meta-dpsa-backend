# Google Translate API Setup Guide

This document explains how to set up Google Cloud Translation API for the DPSA Bot's multilingual support.

## Overview

The DPSA Bot uses Google Cloud Translation API v2 to support 9 of South Africa's 11 official languages:

### ✅ Supported Languages
- English (en)
- Afrikaans (af)
- isiZulu (zu)
- isiXhosa (xh)
- Sepedi / Northern Sotho (nso)
- Setswana (tn)
- Sesotho (st)
- Xitsonga (ts)
- siSwati (ss)

### ❌ Unsupported (Fallback to English)
- Tshivenda (ve)
- isiNdebele (nr)

## Setup Instructions

### 1. Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project or select an existing one
3. Note your project ID

### 2. Enable Cloud Translation API

1. Navigate to **APIs & Services** → **Library**
2. Search for "Cloud Translation API"
3. Click **Enable**

### 3. Create Service Account

1. Go to **IAM & Admin** → **Service Accounts**
2. Click **Create Service Account**
3. Enter details:
   - **Name**: `dpsa-translator` (or any descriptive name)
   - **Description**: "Service account for DPSA Bot translation"
4. Click **Create and Continue**
5. Grant role: **Cloud Translation API User**
6. Click **Continue** → **Done**

### 4. Generate Service Account Key

1. Click on the newly created service account
2. Go to the **Keys** tab
3. Click **Add Key** → **Create New Key**
4. Select **JSON** format
5. Click **Create**
6. The JSON key file will download automatically

### 5. Configure Locally (Development)

1. Rename the downloaded file to `google-credentials.json`
2. Move it to the project root directory:
   ```
   c:\Users\Thato Molaba\Documents\DPSA Bot\google-credentials.json
   ```
3. Verify it's in `.gitignore` (it already is - line 11)
4. The `.env` file already points to it:
   ```env
   GOOGLE_APPLICATION_CREDENTIALS=./google-credentials.json
   ```

### 6. Configure for Deployment (Production)

For Cloudflare Pages, Vercel, or Render deployment, you need to use an environment variable instead of a file.

#### Option A: Set GOOGLE_CREDENTIALS_JSON (Recommended)

1. Open your `google-credentials.json` file
2. Copy the entire JSON content (all of it - it's one line)
3. In your deployment platform (Cloudflare Pages / Vercel / Render):
   - Go to **Environment Variables** settings
   - Add a new variable:
     - **Name**: `GOOGLE_CREDENTIALS_JSON`
     - **Value**: Paste the entire JSON content
4. The code already handles this automatically (see `tools/lang_detector.py:50-56`)

#### Option B: Use Google Cloud Secret Manager (Advanced)

For production systems, consider using Google Cloud Secret Manager for better security.

## How It Works

### Language Detection

When a user sends a message:
1. System detects language using `tools/lang_detector.py`
2. Returns ISO code + confidence score
3. If confidence < 0.5, defaults to English

### Translation Flow

**Incoming Query:**
```
User (isiZulu) → Detect → Translate to English → Pipeline Processing
```

**Outgoing Response:**
```
Pipeline (English) → Translate to User's Language → User receives response
```

### Language Selection

Users can explicitly select their language:
1. Send a greeting ("Hello", "Sawubona", "Dumela")
2. Bot responds with language options
3. User clicks/types their preferred language
4. Selection saved in session for subsequent messages

## Testing Language Support

### Test Language Detection

```bash
cd "c:\Users\Thato Molaba\Documents\DPSA Bot"
source venv/Scripts/activate
python tools/lang_detector.py
```

### Test Translation

```bash
python tools/translator.py
```

### Test in API

```bash
# Start the API
uvicorn api.main:app --reload --port 8000

# Send a test request in isiZulu
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Sawubona, ngicela usizo",
    "session_id": "test123",
    "images": []
  }'
```

## Workflow Files

Language support is coordinated by these workflow files:

- **`workflows/language_router.md`** - Main language detection and routing logic
- **`workflows/query_handler.md`** - Full pipeline including translation steps
- **`prompts/language_prompt.md`** - LLM prompts for language handling

## Tools Used

- **`tools/lang_detector.py`** - Detects language of input text
- **`tools/translator.py`** - Translates between English and SA languages
- **`tools/greeting_handler.py`** - Manages greeting responses and language selection

## Cost Considerations

### Google Cloud Translation API Pricing (as of 2024)

- **Free tier**: 500,000 characters per month
- **Paid tier**: $20 per 1 million characters

### Estimated Usage

For a typical query:
- Average query: 50 characters
- Average response: 200 characters
- **Total per conversation turn**: ~250 characters
- **Free tier capacity**: ~2,000 conversation turns per month

For production deployment with higher traffic, monitor usage in Google Cloud Console.

## Troubleshooting

### Error: "google.cloud module not found"

Install the required package:
```bash
pip install google-cloud-translate
```

### Error: "Could not authenticate with Google Cloud"

Check that:
1. `google-credentials.json` exists in project root
2. `.env` has `GOOGLE_APPLICATION_CREDENTIALS=./google-credentials.json`
3. The JSON file has valid credentials (not expired)

### Error: "Cloud Translation API has not been enabled"

Go to Google Cloud Console and enable the API (see Step 2 above).

### Language not being detected correctly

- Ensure text is at least 10 characters long
- Check detection confidence score in logs
- Short phrases may default to English (this is expected)

## Security Notes

⚠️ **NEVER commit credentials to GitHub**

- ✅ `google-credentials.json` is in `.gitignore`
- ✅ `.env` is in `.gitignore`
- ✅ Use environment variables for deployment
- ❌ Never paste credentials in code comments
- ❌ Never share credentials via email or chat

## References

- [Google Cloud Translation API Docs](https://cloud.google.com/translate/docs)
- [Supported Languages List](https://cloud.google.com/translate/docs/languages)
- [Python Client Library](https://googleapis.dev/python/translation/latest/index.html)
- [Pricing Calculator](https://cloud.google.com/products/calculator)

---

**Last Updated**: 2026-04-09
**Contact**: AI Team
