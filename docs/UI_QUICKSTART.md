# UI Quick Start Guide

## ✅ UI is Ready!

The React frontend is built and ready to test the article extraction system.

---

## 🚀 Starting the Full System

### 1. Start Backend Services

```bash
cd /mnt/c/Users/denys/work/article-2-text

# Terminal 1: Start Go API
./api/bin/api

# Terminal 2: Start Go Worker
./worker-go/bin/worker

# Terminal 3: Start Python AI Worker (optional for now)
source venv/bin/activate
cd worker-python/app
python main.py
```

### 2. Start Frontend

```bash
cd /mnt/c/Users/denys/work/article-2-text/frontend
npm run dev
```

The UI will be available at: **http://localhost:5173**

---

## 🔐 Login

Default test credentials (from database):
- **Email:** `test@example.com`
- **Password:** `password123`

---

## 🎯 Using the UI

### **1. Dashboard**
- Big URL input box at top
- Paste any article URL (e.g., `https://www.forentrepreneurs.com/saas-metrics-2/`)
- Click "Extract" button
- Watch job appear in list below with live status updates

### **2. Job Monitoring**
Jobs update every 2 seconds showing:
- 🟢 Completed (green)
- 🟡 Processing (yellow) 
- 🔴 Failed (red)
- Progress percentage for active jobs

### **3. Job Details**
Click any job to see:
- Full metadata (word count, images, timing)
- First 2000 characters preview
- Quality warnings (navigation, JS code detected)
- Download button for full markdown
- "View Comparison" button

### **4. Comparison View**
- Side-by-side: Go worker output vs Python baseline
- Automatic issue detection
- Metrics comparison (word counts, quality scores)
- Download both versions

### **5. API Key Page**
- Your API key for programmatic access
- Usage statistics
- curl examples for integration

---

## 🐛 Quality Detection Features

The UI automatically detects common extraction problems:

### ❌ **Navigation Menus**
```
Skip to content
Posts
Categories
Tags
Home
About Us
```

### ❌ **JavaScript Code**
```
hbspt.forms.create({
  portalId: '76750',
  formId: 'be74ea1d-...'
});
```

### ⚠️  **Content Structure Issues**
- Article content starting too late (after 1000+ characters)
- Excessive empty lines
- Missing sections

These appear as warnings in yellow boxes on the job detail page.

---

## 📊 Testing the Comparison Feature

### **How it Works:**
1. Extract an article via the UI (creates Go worker output)
2. The system looks for a matching Python baseline in `/results` directory
3. If found, shows side-by-side comparison
4. If not found, shows "No Python baseline for comparison"

### **Test Articles with Baselines:**
These articles have Python baselines in `/results`:
- `https://www.forentrepreneurs.com/saas-economics-1/`
- Any other article already in `/results` folder

### **Creating New Baselines:**
To compare new articles:
1. Extract via UI (Go worker)
2. Extract same URL using old Python tool:
   ```bash
   source venv/bin/activate
   python3 -m src.article_extractor --gemini https://example.com/article
   ```
3. File saves to `/results` automatically
4. Refresh comparison page in UI

---

## 🎨 UI Features Showcase

### **Live Updates**
- Job list refreshes every 2 seconds
- Progress bars update in real-time
- No manual refresh needed

### **Responsive Design**
- Works on desktop and tablet
- Side-by-side comparison stacks on mobile

### **Download Options**
- Download markdown from job list
- Download from job detail page
- Download both Go and Python versions from comparison

### **Quality Scoring**
- Automatic detection of 4+ issue types
- Color-coded severity (high/medium/low)
- Actionable warnings

---

## 🔧 Configuration

### **Change API URL**
Edit `frontend/vite.config.ts`:
```typescript
server: {
  proxy: {
    '/api': {
      target: 'http://your-api-url:8080',
      changeOrigin: true,
    },
  },
}
```

### **Adjust Polling Interval**
Edit `frontend/src/pages/Dashboard.tsx`:
```typescript
refetchInterval: 2000, // Change to 5000 for 5 seconds
```

---

## 📸 What You'll See

### **Dashboard View:**
```
┌─────────────────────────────────────────────┐
│ Article Extraction Tester    [API Key] [Logout]│
├─────────────────────────────────────────────┤
│                                              │
│ 📝 Extract New Article                      │
│ [https://example.com/article    ] [Extract] │
│                                              │
│ ─────────────────────────────────────────   │
│                                              │
│ 📊 Recent Extractions                       │
│ 🟢 SaaS Metrics 2.0                         │
│    8,391 words • 29 images • 10s            │
│    [View] [Download]                         │
│                                              │
│ 🟡 Startup Killer (Processing... 50%)       │
│                                              │
│ 🔴 Invalid URL (Failed)                     │
│    Error: 404 Not Found                     │
└─────────────────────────────────────────────┘
```

### **Job Detail with Warnings:**
```
┌─────────────────────────────────────────────┐
│ SaaS Metrics 2.0                            │
│ Status: ✅ Completed • 10.2s                │
│                                              │
│ ⚠️ Quality Warnings:                        │
│ • Navigation menus detected in content      │
│ • JavaScript code not removed               │
│ • Content starts too late (200+ chars)      │
│                                              │
│ [Download] [View Comparison]                 │
│                                              │
│ Preview:                                     │
│ # SaaS Metrics 2.0                          │
│ **Author:** David Skok                      │
│ ---                                          │
│ ❌ Skip to content                          │
│ ❌ Posts                                    │
│ ...                                          │
└─────────────────────────────────────────────┘
```

### **Comparison View:**
```
┌──────────────────────────────────────────────┐
│ Go Worker (NEW)   │ Python (BASELINE)        │
├───────────────────┼──────────────────────────┤
│ ❌ 8,391 words    │ ✅ 3,500 words           │
│                   │                          │
│ # Title           │ # Title                  │
│ ---               │ **Source:** [link]       │
│ ❌ Skip to...     │ **Published:** 2010...   │
│ ❌ Posts          │ ---                      │
│ ❌ Categories     │ ## Part 1: Looking...    │
│                   │ For those new...         │
└───────────────────┴──────────────────────────┘

🔍 Detected Issues:
• ❌ Navigation menus present (50+ lines)
• ❌ 138% more content than baseline
```

---

## ✅ Success Checklist

After starting the UI, verify:
- [ ] Can login with test credentials
- [ ] Can submit URL for extraction
- [ ] Job appears in list immediately
- [ ] Job status updates automatically (no refresh)
- [ ] Can click job to see details
- [ ] Can download markdown file
- [ ] Quality warnings appear (if extraction has issues)
- [ ] Comparison view works (if baseline exists)
- [ ] API key page shows key and documentation

---

## 🐛 Troubleshooting

### **"Cannot connect to API"**
- Make sure Go API is running on port 8080
- Check `http://localhost:8080/health` returns OK

### **"Login failed"**
- Verify user exists in database:
  ```bash
  psql postgresql://postgres:postgres@localhost:5432/article_extraction \
    -c "SELECT email FROM users WHERE email='test@example.com';"
  ```
- Reset credits if needed:
  ```bash
  psql postgresql://postgres:postgres@localhost:5432/article_extraction \
    -c "UPDATE users SET credits = 10000 WHERE email='test@example.com';"
  ```

### **Jobs not updating**
- Check Go Worker is running
- Check Redis is running: `redis-cli ping`
- Check browser console for errors

### **No comparison available**
- Python baseline must exist in `/results` folder
- Filename must match job title (normalized)
- Or extract the same URL with Python tool first

---

## 🎉 Next Steps

Now that the UI is working:

1. **Test extraction quality:**
   - Try various articles from forentrepreneurs.com
   - Compare Go worker output with Python baseline
   - Document quality issues

2. **Fix Go worker extraction:**
   - Based on UI findings, update extraction logic
   - Improve site configs
   - Add better filtering

3. **Enhance UI (optional):**
   - Add more quality metrics
   - Batch extraction feature
   - Site config viewer/editor

---

**The UI is ready for testing!** 🚀

Start with: `cd frontend && npm run dev`

Then open: http://localhost:5173



