# 🗂️ Simple Page Saver

An interactive Chrome extension with Python FastAPI backend that extracts web content and converts it to clean markdown files using AI-powered processing.

## Features

- **Single Page Extraction**: Extract and convert the current page to markdown with one click
- **Site Mapping**: Discover and map entire sites with configurable crawl depth (0-3 levels)
- **Link Categorization**: Automatically categorize links as internal, external, or media
- **Batch Processing**: Extract multiple pages in a single operation
- **AI-Powered Conversion**: Uses OpenRouter API for intelligent HTML-to-markdown conversion
- **Offline Fallback**: Works without AI using html2text when API is unavailable
- **Multiple Output Options**: Download as individual files or bundled with common prefix
- **Visual Feedback**: Real-time progress tracking and status updates

## Architecture

### Frontend: Chrome Extension
- **Popup UI**: User interface for interaction
- **Background Service Worker**: Orchestrates tab management and API communication
- **Content Scripts**: Extract HTML and metadata from pages

### Backend: Python FastAPI
- **Preprocessing Pipeline**: Multi-stage HTML cleaning to reduce token count
- **AI Integration**: OpenRouter API for intelligent markdown conversion
- **Link Extraction**: Categorize and extract all types of links
- **Cost Estimation**: Calculate processing costs before extraction

## Installation

### Prerequisites

- Python 3.8 or higher
- Chrome browser
- OpenRouter API key (optional, for AI conversion)

### Backend Setup

1. **Navigate to backend directory**:
   ```bash
   cd backend
   ```

2. **Create virtual environment** (recommended):
   ```bash
   python -m venv venv

   # On Windows:
   venv\Scripts\activate

   # On Linux/Mac:
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**:
   ```bash
   # Copy example environment file
   cp .env.example .env

   # Edit .env and add your OpenRouter API key
   # Get one from: https://openrouter.ai/keys
   ```

   Edit `.env`:
   ```env
   OPENROUTER_API_KEY=your_actual_api_key_here
   DEFAULT_MODEL=deepseek/deepseek-chat
   MAX_TOKENS=32000
   SERVER_PORT=8077
   ```

5. **Start the server**:
   ```bash
   python main.py
   ```

   You should see:
   ```
   ╔═══════════════════════════════════════════════════╗
   ║      Simple Page Saver API Server                ║
   ╚═══════════════════════════════════════════════════╝

   🚀 Server starting on http://localhost:8077
   📝 API Documentation: http://localhost:8077/docs
   🔑 AI Enabled: True
   ```

6. **Test the server**:
   Open browser and go to `http://localhost:8077`

   You should see:
   ```json
   {
     "status": "healthy",
     "service": "Simple Page Saver API",
     "version": "1.0.0",
     "ai_enabled": true
   }
   ```

### Chrome Extension Setup

1. **Navigate to Chrome extensions page**:
   - Open Chrome
   - Go to `chrome://extensions/`
   - Enable "Developer mode" (toggle in top right)

2. **Load the extension**:
   - Click "Load unpacked"
   - Select the `extension` folder from this project
   - The extension should appear in your extensions list

3. **Pin the extension** (optional but recommended):
   - Click the puzzle icon in Chrome toolbar
   - Find "Simple Page Saver"
   - Click the pin icon

4. **Replace placeholder icons** (optional):
   - The extension comes with placeholder icon files
   - Replace files in `extension/icons/` with actual PNG images:
     - `icon16.png` (16x16)
     - `icon32.png` (32x32)
     - `icon48.png` (48x48)
     - `icon128.png` (128x128)

### Windows Service Setup (Optional)

To run the backend as a Windows service using NSSM:

1. **Download NSSM**:
   - Get from: https://nssm.cc/download
   - Extract to a folder (e.g., `C:\nssm`)

2. **Install service**:
   ```cmd
   # Open Command Prompt as Administrator
   cd C:\nssm\win64

   # Install service
   nssm install SimplePageSaver
   ```

3. **Configure service**:
   - **Path**: `C:\path\to\python.exe` (your Python executable)
   - **Startup directory**: `C:\path\to\simple-page-saver\backend`
   - **Arguments**: `main.py`
   - **Environment**: Add line `PYTHONPATH=C:\path\to\simple-page-saver\backend`

4. **Start service**:
   ```cmd
   nssm start SimplePageSaver
   ```

5. **Check status**:
   ```cmd
   nssm status SimplePageSaver
   ```

## Usage

### Basic Usage

1. **Extract Current Page**:
   - Navigate to any web page
   - Click the extension icon
   - Click "Extract Current Page"
   - Wait for processing
   - Markdown file will be automatically downloaded

2. **Map Site and Extract Multiple Pages**:
   - Navigate to a website
   - Click the extension icon
   - Select crawl depth (0-3 levels)
   - Click "Map Site"
   - Wait for URL discovery
   - Select URLs you want to extract (checkboxes)
   - Choose output format (ZIP or individual files)
   - Click "Extract Selected Pages"
   - Wait for processing and download

### Link Type Filters

When mapping a site, you can filter discovered links:
- **Internal**: Same-domain links (auto-selected)
- **External**: Cross-domain links
- **Media**: Images, videos, PDFs, documents

### Search URLs

After mapping a site, use the search box to filter URLs by keyword.

### Configuration

Click "⚙️ Configure API Endpoint" to change the backend URL (default: `http://localhost:8077`).

## How It Works

### Preprocessing Pipeline

The backend uses a three-stage preprocessing approach to reduce HTML size:

**Stage 1 - Aggressive Stripping**:
- Removes scripts, styles, SVGs
- Removes HTML comments
- Strips data attributes, tracking pixels
- Removes event handlers

**Stage 2 - Content Isolation**:
- Uses readability algorithm to extract main content
- Removes navigation, headers, footers
- Removes sidebars and ads

**Stage 3 - Semantic Simplification**:
- Keeps only semantic HTML tags
- Preserves links (href) and images (src, alt)
- Removes all other attributes
- Normalizes whitespace

**Result**: Typically reduces HTML by 70-90%, bringing large pages down to ~20K tokens or less.

### AI Conversion

The system uses OpenRouter API to convert preprocessed HTML to markdown:

1. **Model Selection**: Defaults to `deepseek/deepseek-chat` (very cost-effective)
2. **Token Management**: Automatically chunks large content if needed
3. **Retry Logic**: Exponential backoff for rate limits and errors
4. **Fallback**: Uses html2text if API is unavailable

### Supported Models

- `deepseek/deepseek-chat` - $0.14/$0.28 per 1M tokens (recommended)
- `openai/gpt-3.5-turbo` - $0.50/$1.50 per 1M tokens
- `openai/gpt-4-turbo` - $10.00/$30.00 per 1M tokens
- `anthropic/claude-3-haiku` - $0.25/$1.25 per 1M tokens
- `anthropic/claude-3-sonnet` - $3.00/$15.00 per 1M tokens

Change the model in `.env`:
```env
DEFAULT_MODEL=openai/gpt-3.5-turbo
```

## Cost Estimation

Typical costs per page (using deepseek/deepseek-chat):
- Small page (10K tokens): ~$0.002
- Medium page (20K tokens): ~$0.004
- Large page (30K tokens): ~$0.006

For 100 pages: ~$0.20-$0.60 depending on page size.

## Troubleshooting

### Backend Issues

**"Connection refused" or "Failed to fetch"**:
- Ensure backend is running (`python main.py`)
- Check firewall settings
- Verify port 8077 is not blocked
- Try accessing `http://localhost:8077` in browser

**"API error 401" or "API error 403"**:
- Check your OpenRouter API key in `.env`
- Verify key is valid at https://openrouter.ai/keys
- Check for sufficient credits

**"Rate limited"**:
- Slow down extraction rate
- Upgrade OpenRouter plan
- Switch to cheaper model (deepseek)

**"Module not found" errors**:
- Ensure all dependencies are installed: `pip install -r requirements.txt`
- Verify virtual environment is activated

### Extension Issues

**Extension not loading**:
- Ensure Developer mode is enabled
- Check for errors in Chrome extension page
- Try reloading the extension
- Check manifest.json syntax

**"Failed to download"**:
- Check Chrome download settings
- Ensure download location is writable
- Check if popup blocker is interfering

**"No response from backend"**:
- Verify backend is running
- Check API endpoint configuration
- Look at browser console (F12) for errors
- Check CORS settings

**Tabs not closing after extraction**:
- Check Chrome permissions
- Manually close stuck tabs
- Restart Chrome if needed

### Content Quality Issues

**Markdown output is messy**:
- Try a different AI model (GPT-4 gives better results)
- Check if preprocessing is too aggressive
- Some complex pages may not convert well

**Missing content**:
- Increase `DELAY_AFTER_LOAD` in background.js for slow sites
- Some dynamic content may not load fully
- Try extracting manually after page fully loads

**Links not working**:
- Relative links may not resolve correctly
- Check source page URL structure
- May need manual adjustment

## Development

### Project Structure

```
simple-page-saver/
├── extension/
│   ├── manifest.json          # Extension configuration
│   ├── popup.html             # UI interface
│   ├── popup.js               # UI logic
│   ├── background.js          # Service worker (orchestration)
│   ├── content-script.js      # Page extraction
│   └── icons/                 # Extension icons
├── backend/
│   ├── main.py               # FastAPI application
│   ├── preprocessing.py      # HTML preprocessing pipeline
│   ├── ai_converter.py       # OpenRouter API integration
│   ├── requirements.txt      # Python dependencies
│   └── .env                  # Configuration (not in git)
└── README.md
```

### API Endpoints

**GET /** - Health check
```json
{
  "status": "healthy",
  "service": "Simple Page Saver API",
  "version": "1.0.0",
  "ai_enabled": true
}
```

**POST /process-html** - Convert HTML to markdown
```json
{
  "url": "https://example.com",
  "html": "<html>...</html>",
  "title": "Page Title"
}
```

**POST /extract-links** - Extract and categorize links
```json
{
  "html": "<html>...</html>",
  "base_url": "https://example.com"
}
```

**POST /estimate-cost** - Estimate processing cost
```json
{
  "html": "<html>...</html>",
  "model": "deepseek/deepseek-chat"
}
```

### Testing

**Test backend**:
```bash
cd backend
python main.py
# In another terminal:
curl http://localhost:8077
```

**Test preprocessing**:
```bash
python
>>> from preprocessing import HTMLPreprocessor
>>> p = HTMLPreprocessor()
>>> html = "<html><body><p>Test</p></body></html>"
>>> cleaned, meta = p.preprocess(html)
>>> print(meta)
```

**Test AI conversion**:
```bash
python
>>> from ai_converter import AIConverter
>>> c = AIConverter()
>>> md, used_ai, error = c.convert_to_markdown("<html><body><h1>Test</h1></body></html>")
>>> print(md)
```

## Known Limitations

1. **ZIP Download**: Currently downloads files with a common prefix instead of a true ZIP file. To enable ZIP, integrate JSZip library.

2. **Rate Limiting**: OpenRouter APIs have rate limits. Slow down extraction if you hit limits.

3. **Dynamic Content**: Some JavaScript-heavy sites may not render fully. Increase `DELAY_AFTER_LOAD` if needed.

4. **Large Sites**: Mapping sites with thousands of pages can be slow. Use appropriate depth limits.

5. **Authentication**: Cannot extract pages behind login walls (browser context is not shared).

## Future Enhancements

- True ZIP file creation using JSZip
- Browser session persistence for authenticated pages
- Custom CSS selector extraction
- Markdown preview before download
- Cloud storage integration
- Scheduled/automated extraction
- Better error recovery and retry
- Cost tracking and budgets

## License

MIT License - Feel free to use and modify as needed.

## Support

For issues, questions, or contributions:
1. Check this README's troubleshooting section
2. Review backend logs for errors
3. Check Chrome console (F12) for extension errors
4. Verify API key and configuration

## Credits

Built with:
- FastAPI (backend framework)
- BeautifulSoup & readability-lxml (HTML processing)
- html2text (fallback conversion)
- OpenRouter (AI API gateway)
- Chrome Extensions Manifest V3

---

**Happy Scraping! 🗂️**
