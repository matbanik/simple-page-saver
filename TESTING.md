# Testing Guide for Simple Page Saver

## Quick Start Testing

### 1. Backend Testing

**Test 1: Basic Server Health**
```bash
cd backend
python main.py
```

Expected output:
```
╔═══════════════════════════════════════════════════╗
║      Simple Page Saver API Server                ║
╚═══════════════════════════════════════════════════╝

🚀 Server starting on http://localhost:8077
📝 API Documentation: http://localhost:8077/docs
🔑 AI Enabled: False (or True if API key is set)
```

Open browser: `http://localhost:8077`

Expected response:
```json
{
  "status": "healthy",
  "service": "Simple Page Saver API",
  "version": "1.0.0",
  "ai_enabled": false
}
```

**Test 2: Preprocessing**
```bash
cd backend
python3 << 'EOF'
from preprocessing import HTMLPreprocessor

html = """
<html>
<head>
    <script>alert('bad');</script>
    <style>body { color: red; }</style>
</head>
<body>
    <h1>Test Page</h1>
    <p>This is a test paragraph with <a href="/test">a link</a>.</p>
    <img src="/test.jpg" alt="Test image">
</body>
</html>
"""

preprocessor = HTMLPreprocessor()
cleaned, metadata = preprocessor.preprocess(html, "http://example.com")

print("Original size:", metadata['original_size'])
print("Final size:", metadata['final_size'])
print("Reduction:", metadata['reduction_percentage'], "%")
print("\nCleaned HTML preview:")
print(cleaned[:500])
EOF
```

**Test 3: Link Extraction**
```bash
cd backend
python3 << 'EOF'
from preprocessing import HTMLPreprocessor

html = """
<html>
<body>
    <a href="/page1">Internal 1</a>
    <a href="https://example.com/page2">Internal 2</a>
    <a href="https://external.com">External</a>
    <img src="/image.jpg">
    <a href="/doc.pdf">PDF</a>
</body>
</html>
"""

preprocessor = HTMLPreprocessor()
links = preprocessor.extract_links(html, "https://example.com")

print("Internal links:", len(links['internal_links']))
for link in links['internal_links']:
    print("  -", link)

print("\nExternal links:", len(links['external_links']))
for link in links['external_links']:
    print("  -", link)

print("\nMedia links:", len(links['media_links']))
for link in links['media_links']:
    print("  -", link)
EOF
```

**Test 4: HTML to Markdown (without AI)**
```bash
cd backend
python3 << 'EOF'
from ai_converter import AIConverter

html = """
<html>
<body>
    <h1>Main Title</h1>
    <p>This is a paragraph with <strong>bold text</strong>.</p>
    <ul>
        <li>Item 1</li>
        <li>Item 2</li>
    </ul>
    <a href="https://example.com">Example Link</a>
</body>
</html>
"""

converter = AIConverter()  # Will use html2text fallback without API key
markdown, used_ai, error = converter.convert_to_markdown(html, "Test Page")

print("Used AI:", used_ai)
print("Error:", error)
print("\nMarkdown output:")
print(markdown)
EOF
```

**Test 5: API Endpoint (using curl)**
```bash
# Start server in one terminal:
cd backend && python main.py

# In another terminal:
curl -X POST http://localhost:8077/process-html \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com",
    "html": "<html><body><h1>Test</h1><p>Content</p></body></html>",
    "title": "Test Page"
  }'
```

Expected: JSON response with markdown content.

### 2. Chrome Extension Testing

**Test 1: Load Extension**
1. Open Chrome
2. Go to `chrome://extensions/`
3. Enable "Developer mode"
4. Click "Load unpacked"
5. Select the `extension` folder
6. Verify no errors in console

**Test 2: Extension Popup**
1. Click extension icon in toolbar
2. Verify popup opens
3. Check that all UI elements are visible:
   - "Extract Current Page" button
   - "Map Site" button
   - Depth selector
   - Status area

**Test 3: Single Page Extraction (Manual)**

Since the backend needs to be running and we need a real browser, here's the manual test procedure:

1. **Start backend**:
   ```bash
   cd backend
   python main.py
   ```

2. **Navigate to a test page** (e.g., `https://example.com`)

3. **Click extension icon**

4. **Click "Extract Current Page"**

5. **Expected behavior**:
   - Status message: "Extracting current page..."
   - A markdown file downloads automatically
   - Status changes to: "✓ Page saved: example_com.md"

6. **Verify the downloaded file**:
   - Open the .md file
   - Should contain markdown version of the page

**Test 4: Site Mapping**

1. Navigate to a simple website (e.g., `https://example.com`)
2. Click extension icon
3. Select depth: 1
4. Click "Map Site"
5. Expected:
   - Status: "Mapping site (depth: 1)..."
   - URL list appears with discovered links
   - Each URL has a checkbox and type badge (INT/EXT/MEDIA)
   - Status: "✓ Found X URLs"

**Test 5: Filtering URLs**

After mapping:
1. Type "test" in search box
2. Verify only matching URLs are visible
3. Uncheck "Internal" filter
4. Verify internal links are hidden
5. Check "External" filter
6. Verify external links are shown

**Test 6: Batch Extraction**

1. Map a site (depth 0 or 1)
2. Select 2-3 URLs
3. Check "Download as ZIP"
4. Click "Extract Selected Pages"
5. Expected:
   - Progress bar appears
   - Status updates for each page
   - Multiple files download with timestamp prefix
   - Status: "✓ Extraction complete! X pages saved."

### 3. Integration Testing

**Test 1: End-to-End Flow**
1. Start backend
2. Load extension
3. Navigate to https://example.com
4. Extract current page
5. Verify markdown file is created and contains content

**Test 2: Error Handling - Backend Down**
1. Stop backend server
2. Try to extract a page
3. Expected: Error message in status area

**Test 3: Error Handling - Invalid Page**
1. Navigate to `chrome://extensions/`
2. Try to extract page
3. Expected: Should handle gracefully (chrome:// pages can't be accessed)

### 4. Performance Testing

**Test: Multiple Pages**
1. Map a small site (depth 1, ~5-10 pages)
2. Select all pages
3. Extract them
4. Monitor:
   - Time taken
   - Memory usage
   - Tab management (tabs should open and close)
   - No tabs left open after completion

## Test Results Template

```
Date: [DATE]
Tester: [NAME]

Backend Tests:
[ ] Server starts successfully
[ ] Health check endpoint works
[ ] Preprocessing reduces HTML size
[ ] Link extraction works
[ ] Markdown conversion works
[ ] API endpoints respond correctly

Extension Tests:
[ ] Extension loads without errors
[ ] Popup UI displays correctly
[ ] Single page extraction works
[ ] Site mapping works
[ ] URL filtering works
[ ] Batch extraction works

Integration Tests:
[ ] End-to-end flow completes
[ ] Error handling works (backend down)
[ ] Error handling works (invalid pages)

Performance:
[ ] Multiple pages extract successfully
[ ] Tabs open and close properly
[ ] No memory leaks observed
[ ] Processing time acceptable

Issues Found:
[List any issues]

Notes:
[Additional observations]
```

## Common Issues During Testing

### Backend won't start
- Check Python version: `python --version` (need 3.8+)
- Install dependencies: `pip install -r requirements.txt`
- Check port 8077 is not in use: `lsof -i :8077` (Linux/Mac) or `netstat -ano | findstr :8077` (Windows)

### Extension won't load
- Check manifest.json syntax
- Ensure all referenced files exist
- Check Chrome console for errors

### No markdown output
- Check backend logs
- Verify API endpoint is correct
- Check CORS settings
- Look at browser console (F12)

### Pages not extracting
- Check Chrome permissions
- Verify tabs permission is granted
- Look for JavaScript errors in console
- Check if page is accessible (not chrome://)

## Automated Testing (Future)

For future implementation:
- Backend unit tests with pytest
- Extension integration tests with Puppeteer
- API endpoint tests with httpx
- Performance benchmarks
