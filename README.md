# Simple Page Saver

A professional web scraping solution combining a Chrome extension with an AI-powered Python backend for converting web content into clean, structured markdown files.

## Overview

Simple Page Saver is a full-featured web content extraction tool that:
- Extracts web pages visible in browser tabs
- Converts HTML to clean markdown using AI or local processing
- Supports batch processing with configurable crawl depth
- Provides both GUI and command-line interfaces
- Includes enterprise-grade security (encrypted API keys) and logging

## Key Features

### Chrome Extension
- **Single Page Extraction** - One-click conversion of current page
- **Site Mapping** - Discover and map entire sites (0-3 levels deep)
- **Batch Processing** - Extract multiple pages with progress tracking
- **Link Categorization** - Automatic sorting (internal/external/media)
- **ZIP Downloads** - Bundle multiple pages into single archive
- **AI Toggle** - Control costs with on/off switch
- **Custom AI Instructions** - 7 preset templates for common tasks
- **Visual Feedback** - Real-time progress and status updates

### Backend Server
- **GUI Management Interface** - Configure and control server visually
- **Command-Line Support** - Full control via arguments
- **Encrypted Settings** - API keys stored securely
- **Advanced Logging** - Configurable levels with API key masking
- **Multi-Stage Processing** - 70-90% HTML size reduction
- **AI Integration** - OpenRouter API with multiple model support
- **Offline Fallback** - Works without AI using html2text
- **Standalone Executable** - Single .exe file distribution

### Security & Privacy
- API keys encrypted using cryptography library
- Machine-specific encryption (PBKDF2 + Fernet)
- Keys never logged in plain text
- Settings stored in encrypted JSON format

## Quick Start

### Option 1: Using Pre-Built Executable (Recommended)

1. **Download or build executable**:
   ```powershell
   cd backend
   .\build.ps1
   ```

2. **Launch GUI to configure**:
   ```powershell
   SimplePageSaver.exe -gui
   ```
   Or double-click: `start_gui.bat`

3. **In GUI**:
   - Enter your OpenRouter API key (get from https://openrouter.ai/keys)
   - Select AI model (deepseek/deepseek-chat recommended for cost)
   - Set log level (INFO recommended)
   - Click "Save Settings"
   - Click "Start Server"

4. **Load Chrome extension**:
   - Open Chrome: `chrome://extensions/`
   - Enable "Developer mode"
   - Click "Load unpacked"
   - Select the `extension` folder

### Option 2: Using Python Directly

1. **Install dependencies**:
   ```powershell
   cd backend
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Launch GUI**:
   ```powershell
   python launcher.py -gui
   ```
   Configure settings and start server

3. **Load Chrome extension** (same as above)

## Usage

### Backend Management

**GUI Mode** (Visual Configuration):
```powershell
SimplePageSaver.exe -gui         # Executable
python launcher.py -gui          # Python
start_gui.bat                    # Double-click launcher
```

**Server Mode** (Direct Start):
```powershell
SimplePageSaver.exe              # Default port 8077
SimplePageSaver.exe -p 8080      # Custom port
SimplePageSaver.exe --log-level DEBUG   # Debug mode
```

**Get Help**:
```powershell
SimplePageSaver.exe --help
```

### Chrome Extension

**Extract Single Page**:
1. Navigate to any webpage
2. Click extension icon
3. Click "Extract Current Page"
4. Markdown file downloads automatically

**Extract Multiple Pages**:
1. Navigate to a website
2. Click extension icon
3. Set crawl depth (0-3 levels)
4. Click "Map Site"
5. Select URLs to extract
6. Choose "Download as ZIP"
7. Click "Extract Selected Pages"

**Custom AI Instructions**:
1. Enable AI in extension
2. Select preset or write custom instructions:
   - Extract Product Details
   - Highlight Keywords
   - Price Comparison Tables
   - Customer Reviews Summary
   - Contact Information
   - Product Specifications
   - Links and Resources
3. Extract pages with custom processing

## Architecture

### Frontend: Chrome Extension (Manifest V3)
```
extension/
├── manifest.json          # Extension configuration
├── popup.html/js          # User interface
├── background.js          # Service worker (orchestration)
├── content-script.js      # Page extraction
└── jszip.min.js          # ZIP file creation
```

**Features**:
- Popup UI for user interaction
- Background service worker for tab management
- Content scripts for HTML extraction
- Real-time progress tracking

### Backend: Python FastAPI
```
backend/
├── launcher.py            # Unified entry point (CLI support)
├── gui.py                 # Tkinter management interface
├── main_updated.py        # FastAPI application
├── settings_manager.py    # Encrypted settings storage
├── logging_config.py      # Advanced logging system
├── preprocessing.py       # HTML preprocessing pipeline
├── ai_converter.py        # OpenRouter API integration
└── build.py              # Executable builder
```

**Processing Pipeline**:
1. **Stage 1 - Aggressive Stripping**: Remove scripts, styles, tracking
2. **Stage 2 - Content Isolation**: Extract main content using readability
3. **Stage 3 - Semantic Simplification**: Keep only semantic HTML
4. **AI Conversion**: OpenRouter API or html2text fallback
5. **Output**: Clean markdown with preserved links and structure

## Configuration

### Settings File: `settings.json`

```json
{
  "server_port": 8077,
  "default_model": "deepseek/deepseek-chat",
  "max_tokens": 32000,
  "log_level": "INFO",
  "openrouter_api_key_encrypted": "encrypted_value"
}
```

**Managed via GUI** - All settings configurable through visual interface

### Supported AI Models

| Model | Cost (per 1M tokens) | Use Case |
|-------|---------------------|----------|
| deepseek/deepseek-chat | $0.14 / $0.28 | Recommended (cost-effective) |
| openai/gpt-3.5-turbo | $0.50 / $1.50 | Faster processing |
| openai/gpt-4-turbo | $10.00 / $30.00 | Best quality |
| anthropic/claude-3-haiku | $0.25 / $1.25 | Fast and cheap |
| anthropic/claude-3-sonnet | $3.00 / $15.00 | Balanced quality/cost |

**Cost Control**:
- AI toggle in extension (OFF by default)
- Clear cost warnings when enabled
- Fallback mode completely free

## Logging

### Log Files
- Location: `backend/logs/simple_page_saver_YYYYMMDD.log`
- New file created daily
- API keys automatically masked as `***MASKED_API_KEY***`

### Log Levels
- **DEBUG**: Verbose (HTML sizes, token counts, metadata)
- **INFO**: Standard operations (recommended)
- **WARNING**: Potential issues
- **ERROR**: Errors that don't stop operation
- **CRITICAL**: Fatal errors

**View Logs**:
- GUI: Real-time log viewer at bottom
- PowerShell: `Get-Content backend\logs\*.log -Tail 50`
- File: Open in any text editor

## Building Executable

```powershell
cd backend
.\build.ps1
```

**Output**: `dist/SimplePageSaver.exe` (~40-50MB)

**Features**:
- Single-file executable
- No Python installation required
- Includes all dependencies
- Command-line argument support
- Works on any Windows machine

## API Endpoints

**Health Check**:
```
GET http://localhost:8077/
```

**Process HTML** (with custom prompt support):
```json
POST /process-html
{
  "url": "https://example.com",
  "html": "<html>...</html>",
  "title": "Page Title",
  "use_ai": true,
  "custom_prompt": "Extract product details..."
}
```

**Extract Links**:
```json
POST /extract-links
{
  "html": "<html>...</html>",
  "base_url": "https://example.com"
}
```

**Estimate Cost**:
```json
POST /estimate-cost
{
  "html": "<html>...</html>",
  "model": "deepseek/deepseek-chat"
}
```

**Interactive Docs**: `http://localhost:8077/docs`

## Troubleshooting

### Backend Issues

**Server won't start**:
1. Check port not in use: `netstat -ano | findstr :8077`
2. Check logs in GUI or `backend/logs/`
3. Try different port: `SimplePageSaver.exe -p 8080`
4. Verify settings in GUI

**API key errors**:
1. Verify key at https://openrouter.ai/keys
2. Check key has credits
3. Re-enter in GUI and save
4. Check logs for details

**Permission errors**:
- Run as administrator
- Check write permissions on logs folder
- Verify settings.json is not read-only

### Extension Issues

**Extension won't load**:
1. Enable Developer mode in `chrome://extensions/`
2. Check for errors in extension page
3. Click "Reload" if already loaded
4. Check console for JavaScript errors

**No downloads**:
1. Verify backend is running
2. Test with GUI "Test Backend Health" button
3. Check Chrome download settings
4. Look at service worker console (click "service worker" link)

**AI not working**:
1. Enable AI toggle in extension
2. Test with GUI "Test AI Connection" button
3. Check API key in backend settings
4. Review backend logs for errors

### Extension Console Debugging

**Service Worker Console**:
1. Go to `chrome://extensions/`
2. Find "Simple Page Saver"
3. Click "service worker" (blue link)
4. Watch console during extraction

**Popup Console**:
1. Right-click extension icon
2. Select "Inspect popup"
3. Go to Console tab

## Project Structure

```
simple-page-saver/
├── extension/                  # Chrome extension
│   ├── manifest.json
│   ├── popup.html/js
│   ├── background.js
│   ├── content-script.js
│   └── jszip.min.js
├── backend/                    # Python backend
│   ├── launcher.py            # Entry point (CLI)
│   ├── gui.py                 # Management GUI
│   ├── main_updated.py        # FastAPI app
│   ├── settings_manager.py    # Encrypted settings
│   ├── logging_config.py      # Logging system
│   ├── preprocessing.py       # HTML processing
│   ├── ai_converter.py        # AI integration
│   ├── build.py              # Executable builder
│   ├── start_gui.bat         # GUI launcher
│   └── start_server.bat      # Server launcher
├── logs/                      # Server logs
├── README.md                  # This file
├── BACKEND_GUI_GUIDE.md      # Detailed backend docs
├── TESTING.md                # Testing guide
└── LAUNCHER_QUICKSTART.txt   # Quick reference
```

## Documentation

- **README.md** (this file) - Main overview
- **BACKEND_GUI_GUIDE.md** - Detailed backend documentation
- **TESTING.md** - Testing procedures
- **LAUNCHER_QUICKSTART.txt** - Command-line reference

## Cost Estimation

Using `deepseek/deepseek-chat` (recommended):
- Small page (10K tokens): ~$0.002
- Medium page (20K tokens): ~$0.004
- Large page (30K tokens): ~$0.006

**For 100 pages**: ~$0.20-$0.60

**Cost Control**:
- AI disabled by default in extension
- Yellow warning when enabled
- Use free fallback for testing

## Security Features

- **Encrypted API Keys**: Fernet + PBKDF2 encryption
- **Masked Logging**: Keys never appear in logs
- **Machine-Specific**: Settings can't be copied to other PCs
- **No Plain Text**: All sensitive data encrypted at rest

## Advanced Features

### Custom AI Prompts

Select from 7 presets or write custom instructions:
1. **Extract Products** - Tables with title, price, description
2. **Highlight Keywords** - Bold formatting for search terms
3. **Price Comparison** - Sortable comparison tables
4. **Reviews Summary** - Aggregate review analysis
5. **Contact Info** - Extract all contact details
6. **Specifications** - Detailed spec tables
7. **Links Summary** - Categorized link lists

### Batch Processing

- Process up to 100s of pages
- Configurable crawl depth (0-3 levels)
- Filter by link type (internal/external/media)
- Search and filter URLs
- ZIP archive output
- Progress tracking

### Logging & Monitoring

- Daily log rotation
- Real-time log viewer in GUI
- Comprehensive request/response logging
- Performance metrics
- Error tracking

## System Requirements

- **Backend**: Python 3.8+ OR Windows 10/11 (for .exe)
- **Extension**: Chrome 88+ (Manifest V3 support)
- **Optional**: OpenRouter API key (for AI processing)

## License

MIT License - Free to use and modify

## Support

**Issues & Questions**:
1. Check documentation: `BACKEND_GUI_GUIDE.md`
2. Review logs: `backend/logs/`
3. Test with GUI buttons
4. Check service worker console
5. Verify API key and settings

## Credits

**Built with**:
- FastAPI - Modern Python web framework
- BeautifulSoup & readability-lxml - HTML parsing
- html2text - Markdown conversion fallback
- OpenRouter - AI API gateway
- JSZip - ZIP file creation
- Tkinter - GUI framework
- PyInstaller - Executable builder
- Chrome Extensions Manifest V3

## Version

**Current Version**: 2.0
**Last Updated**: 2025-01-10

---

**Simple Page Saver** - Professional web content extraction with AI
