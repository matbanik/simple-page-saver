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
- **Screenshot Capture** - CDP-based full-page screenshots with infinite scroll detection
- **Selective Downloads** - Choose to download content, media links, external links, screenshots, or all
- **Job Tracking** - Visual job list with real-time progress that persists across popup closes
- **Pause/Resume** - Interrupt and continue long-running site mapping jobs
- **Site Mapping** - Discover and map entire sites (0-3 levels deep) with parent-child tracking
- **Batch Processing** - Extract multiple pages with progress tracking
- **Link Categorization** - Automatic sorting (internal/external/media)
- **ZIP Downloads** - Bundle multiple pages into single archive
- **Warnings System** - Detailed warnings.txt file for issues encountered during extraction
- **AI Toggle** - Control costs with on/off switch
- **Custom AI Instructions** - 7 preset templates for common tasks
- **Connection Management** - Automatic reconnection with retry logic and health monitoring
- **Visual Feedback** - Real-time progress, status updates, and connection status indicator

### Backend Server
- **GUI Management Interface** - Configure and control server visually
- **Command-Line Support** - Full control via arguments
- **Job Management** - Track all processing jobs with UUID-based identification
- **Encrypted Settings** - API keys stored securely
- **Advanced Logging** - Configurable levels with full OpenRouter request/response visibility
- **Smart Preprocessing** - 3-tier mode system (light/medium/aggressive) with safety checks
- **AI Integration** - OpenRouter API with multiple model support
- **Intelligent Fallback Chain** - AI → Trafilatura → html2text with 3 extraction modes
- **Extraction Modes** - Balanced, Recall (more content), Precision (cleaner output)
- **Standalone Executable** - Single .exe file distribution

### Screenshot Capture (New in 2.2)
- **Full-Page Screenshots** - Chrome DevTools Protocol (CDP) for capturing entire page beyond viewport
- **Infinite Scroll Detection** - Automatic detection and warnings for dynamically loading pages
- **Black & White Optimization** - Default B&W conversion reduces file size by 60%+ using true binary thresholding
- **Preserve Color Option** - Optional full-color screenshots with checkbox control
- **WebP Compression** - 30-40% smaller file sizes compared to JPEG
- **Auto-Crop Protection** - Pages exceeding 16,384px height automatically cropped with warning
- **Warnings System** - warnings.txt file includes all issues (infinite scroll, cropping, extraction errors)
- **Flexible Download** - Screenshots bundled in ZIP or downloaded separately

### Job Management & Persistence (New in 2.2)
- **Pause/Resume** - Pause long-running site mapping jobs and resume later from exact position
- **Dual Persistence** - Jobs saved to both IndexedDB (browser-side) and backend (server-side)
- **Browser Restart Survival** - Jobs persist across browser restarts and tab closes
- **View Progress** - Check discovered URLs and progress for paused jobs
- **State Preservation** - Complete job state saved (discovered URLs, processing queue, parent-child relationships)
- **Resume Continuation** - Seamlessly continue from saved state with all data intact
- **Stop Control** - Stop jobs while preserving all discovered data

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
3. Monitor connection status (green indicator = connected)
4. Select download options:
   - ☑ Download page content (markdown)
   - ☐ Download media links (txt file)
   - ☐ Download external links (txt file)
   - ☐ Include screenshot (full-page CDP capture)
     - ☐ Preserve color (default: B&W for smaller file size)
   - ☐ Create ZIP file
5. Choose extraction mode (Balanced/Recall/Precision)
6. Click "Extract Current Page"
7. Watch real-time progress in job tracker
8. Files download automatically when complete
   - If screenshot enabled: receives warnings.txt if issues detected

**Extract Page with Screenshot**:
1. Navigate to any webpage
2. Click extension icon
3. Check "Include screenshot"
4. Optional: Check "Preserve color" for full-color screenshot (larger file size)
5. Select other options (content, media links, etc.)
6. Click "Extract Current Page"
7. Receive files:
   - page_title.md (markdown content)
   - screenshot_page-title_timestamp.webp (full-page screenshot)
   - warnings.txt (if infinite scroll or other issues detected)
   - All bundled in ZIP if selected

**Extract Multiple Pages (Site Mapping)**:
1. Navigate to a website
2. Click extension icon
3. Set crawl depth (0-3 levels)
4. Click "Map Site"
5. Site mapping begins - discovers all URLs up to specified depth
6. **Pause/Resume Controls**:
   - Click "Pause" button to temporarily halt mapping
   - Click "Resume" to continue from exact saved state
   - Click "Stop" to halt permanently (preserves discovered data)
   - Click "View Progress" to see all discovered URLs
7. Jobs persist across browser restarts
8. Select URLs to extract
9. Choose "Download as ZIP"
10. Click "Extract Selected Pages"
11. Monitor progress in active jobs section

**Job Tracking**:
- View all active and recent jobs in popup
- Color-coded status: 🟢 Completed, 🟡 Processing, 🔴 Failed, ⚪ Pending, 🟠 Paused
- Click any job to see details
- Jobs persist across popup closes and browser restarts (dual storage: IndexedDB + backend)
- **Pause/Resume/Stop buttons** for active site mapping jobs
- **View Progress button** for paused jobs to see discovered URLs
- Auto-refresh every 5 seconds
- Complete state preservation for resumed jobs

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
├── manifest.json          # Extension configuration (includes debugger permission)
├── popup.html/js          # User interface with screenshot controls
├── background.js          # Service worker (orchestration, pause/resume)
├── content-script.js      # Page extraction
├── screenshot-utils.js    # CDP-based screenshot capture
├── warnings-tracker.js    # Warnings collection system
├── job-storage.js         # IndexedDB persistence layer
└── jszip.min.js          # ZIP file creation
```

**Features**:
- Popup UI for user interaction with screenshot and pause/resume controls
- Background service worker for tab management and job persistence
- Content scripts for HTML extraction
- Real-time progress tracking with pause/resume support
- CDP integration for full-page screenshots
- IndexedDB storage for job persistence across browser restarts
- Warnings system for issue tracking

### Backend: Python FastAPI
```
backend/
├── launcher.py            # Unified entry point (CLI support)
├── gui.py                 # Tkinter management interface
├── main.py                # FastAPI application with job endpoints
├── settings_manager.py    # Encrypted settings storage
├── logging_config.py      # Advanced logging system
├── preprocessing.py       # Smart 3-tier HTML preprocessing
├── ai_converter.py        # AI + Trafilatura + html2text chain
├── job_manager.py         # Job tracking and persistence
└── build.py              # Executable builder
```

**Processing Pipeline**:
1. **Stage 1 - Smart Preprocessing**:
   - Light mode: Remove scripts/styles only (default)
   - Medium mode: Remove navigation and ads
   - Aggressive mode: Readability extraction with 80% safety check
2. **Stage 2 - Link Extraction**: Categorize internal/external/media links
3. **Stage 3 - Conversion Chain**:
   - Try AI (OpenRouter) if API key configured
   - Fallback to Trafilatura with extraction mode (balanced/recall/precision)
   - Final fallback to html2text
4. **Stage 4 - Job Tracking**: Update progress and store results
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

**Process HTML** (with custom prompt and extraction mode):
```json
POST /process-html
{
  "url": "https://example.com",
  "html": "<html>...</html>",
  "title": "Page Title",
  "use_ai": true,
  "custom_prompt": "Extract product details...",
  "extraction_mode": "balanced",
  "job_id": "optional-existing-job-id"
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

**Job Management**:
```
GET /jobs?status=processing&limit=50   # List jobs
GET /jobs/{job_id}                     # Get job details
POST /jobs/{job_id}/pause              # Pause a running job
POST /jobs/{job_id}/resume             # Resume a paused job
POST /jobs/{job_id}/stop               # Stop a job (preserves data)
DELETE /jobs/{job_id}                  # Delete job
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

**Connection indicator shows red/orange**:
1. Verify backend is running (check logs or GUI)
2. Extension automatically retries with exponential backoff
3. Orange = attempting reconnection (wait 30s for health check)
4. Green = connected and healthy
5. Extension will auto-reconnect when backend restarts

**No downloads**:
1. Check connection status indicator (should be green)
2. Verify backend is running
3. Test with GUI "Test Backend Health" button
4. Check Chrome download settings
5. Look at service worker console (click "service worker" link)
6. Review active jobs section for errors

**AI not working**:
1. Enable AI toggle in extension
2. Test with GUI "Test AI Connection" button
3. Check API key in backend settings
4. Review backend logs for OpenRouter request/response details
5. Try different extraction mode (Recall for more content)

**Jobs not showing progress**:
1. Check backend connection (green indicator)
2. Click "Refresh" button in jobs section
3. Jobs auto-refresh every 5 seconds
4. Check service worker console for errors
5. Verify backend `/jobs` endpoint is accessible

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
│   ├── manifest.json          # Includes debugger permission for CDP
│   ├── popup.html/js          # UI with screenshot and pause/resume controls
│   ├── background.js          # Connection management, pause/resume, persistence
│   ├── content-script.js      # Page extraction
│   ├── screenshot-utils.js    # CDP screenshot capture with infinite scroll detection
│   ├── warnings-tracker.js    # Warnings collection and formatting
│   ├── job-storage.js         # IndexedDB wrapper for job persistence
│   └── jszip.min.js          # ZIP file creation
├── backend/                    # Python backend
│   ├── launcher.py            # Entry point (CLI)
│   ├── gui.py                 # Management GUI
│   ├── main.py                # FastAPI app with pause/resume endpoints
│   ├── job_manager.py         # Job tracking with pause/resume support
│   ├── settings_manager.py    # Encrypted settings
│   ├── logging_config.py      # Logging system
│   ├── preprocessing.py       # 3-tier HTML preprocessing
│   ├── ai_converter.py        # AI + Trafilatura + html2text
│   ├── build.py              # Executable builder
│   ├── requirements.txt       # Python dependencies
│   ├── start_gui.bat         # GUI launcher
│   └── start_server.bat      # Server launcher
├── logs/                      # Server logs
├── README.md                  # This file
├── CODE_REVIEW_FINDINGS.md   # Bug fixes documentation
├── BACKEND_GUI_GUIDE.md      # Detailed backend docs
├── TESTING.md                # Testing guide
└── LAUNCHER_QUICKSTART.txt   # Quick reference
```

## Documentation

- **README.md** (this file) - Main overview
- **CODE_REVIEW_FINDINGS.md** - Bug fixes and improvements log
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

### Extraction Modes

Choose the optimal fallback extraction strategy:
- **Balanced** (default) - Standard precision/recall tradeoff
- **Recall** - Captures more content, may include some noise
- **Precision** - Cleaner output, may miss some peripheral content

Works with Trafilatura fallback when AI is unavailable or disabled.

### Selective Downloads

Choose exactly what to download:
- **Page Content** - Markdown-formatted main content
- **Media Links** - List of all images, videos, audio files
- **External Links** - List of all outbound links
- **ZIP Packaging** - Bundle everything in single archive

All options work independently or together.

### Job Tracking & Persistence

- **UUID-Based Jobs** - Every operation tracked with unique ID
- **Dual Persistence** - Jobs stored in both IndexedDB (browser) and backend (server)
- **Browser Restart Survival** - Complete job state persists across browser restarts
- **Real-Time Progress** - Current step, percentage, status message
- **Status Indicators** - Visual color-coded status (pending/processing/completed/failed/paused)
- **Pause/Resume/Stop** - Full control over long-running site mapping jobs
- **State Preservation** - Complete state saved: discovered URLs, processing queue, parent-child relationships
- **Seamless Continuation** - Resume picks up exactly where paused, no data loss
- **View Progress** - Check discovered URLs for paused jobs
- **Auto-Refresh** - Jobs list updates every 5 seconds
- **Click Details** - Click any job to see full information
- **Accessible Anywhere** - Jobs accessible from any tab via backend storage

### Connection Management

- **Health Monitoring** - Backend checked every 30 seconds
- **Automatic Retry** - 3 attempts with exponential backoff (2s, 4s, 8s)
- **Visual Status** - Green/orange/red indicator in popup
- **Auto-Reconnect** - Seamlessly reconnects when backend restarts
- **Graceful Degradation** - Clear error messages when backend unavailable

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
- Comprehensive OpenRouter request/response logging (API key masked)
- Full request details visible in logs
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
- Trafilatura - Intelligent content extraction
- html2text - Markdown conversion fallback
- OpenRouter - AI API gateway
- JSZip - ZIP file creation
- Tkinter - GUI framework
- PyInstaller - Executable builder
- Chrome Extensions Manifest V3

## Version

**Current Version**: 2.2
**Last Updated**: 2025-11-12

### What's New in 2.2

#### 📸 Screenshot Capture System
- **CDP-Based Full-Page Screenshots** - Captures entire page beyond viewport using Chrome DevTools Protocol
- **Infinite Scroll Detection** - Automatically detects dynamically loading content (MutationObserver + IntersectionObserver)
- **Black & White Optimization** - Default B&W conversion reduces file size by 60%+ using true binary thresholding (luminosity method)
- **Preserve Color Option** - Optional full-color screenshots with checkbox control
- **WebP Compression** - 30-40% smaller file sizes compared to JPEG while maintaining quality
- **Auto-Crop Protection** - Pages exceeding 16,384px height automatically cropped with warning
- **warnings.txt File** - Comprehensive issue reporting (infinite scroll detection, cropping, extraction errors, link issues)
- **Flexible Download** - Screenshots bundled in ZIP or downloaded separately
- **Debugger Permission** - Added to manifest.json for CDP access

#### ⏸️ Pause/Resume/Stop Controls
- **Pause Site Mapping Jobs** - Temporarily halt long-running jobs without losing progress
- **Resume from Saved State** - Continue exactly where paused with complete state restoration
- **Stop Control** - Permanently halt jobs while preserving all discovered data
- **View Progress** - Check discovered URLs and progress for paused jobs
- **Pause/Resume/Stop Buttons** - Added to job cards in popup UI

#### 💾 Dual Persistence System
- **IndexedDB Storage** - Browser-side persistence (extension/job-storage.js)
- **Backend Storage** - Server-side persistence (backend/job_manager.py)
- **Browser Restart Survival** - Jobs persist across browser restarts and tab closes
- **Complete State Preservation** - Saves discovered URLs, processing queue, parent-child relationships, progress
- **Seamless State Restoration** - Resume loads complete state from IndexedDB
- **Redundant Backup** - Dual storage ensures no data loss

#### 🌳 Parent-Child URL Tracking
- **Relationship Mapping** - Tracks which URL discovered which child URL
- **Map Data Structure** - O(1) lookups for parent relationships
- **Ready for Tree View** - Data infrastructure complete for hierarchical display
- **Depth Tracking** - Each URL tagged with its discovery level

#### 🔧 Bug Fixes (See CODE_REVIEW_FINDINGS.md)
- ✅ Site mapping now actually pauses (while loop check added)
- ✅ Parent-child relationships populated during discovery
- ✅ Complete job state saved to IndexedDB (full persistence)
- ✅ Resume continuation implemented (continueSiteMapping function)
- ✅ Jobs saved to IndexedDB on creation
- ✅ Screenshot filename sanitization fixed (fallback for empty titles)
- ✅ API endpoint consistency improvements

#### 📋 New Files Added
- `extension/screenshot-utils.js` - CDP screenshot capture with infinite scroll detection
- `extension/warnings-tracker.js` - Warnings collection and formatting system
- `extension/job-storage.js` - IndexedDB wrapper for job persistence
- `CODE_REVIEW_FINDINGS.md` - Comprehensive bug fixes documentation

#### 🔌 New API Endpoints
- `POST /jobs/{job_id}/pause` - Pause a running job
- `POST /jobs/{job_id}/resume` - Resume a paused job
- `POST /jobs/{job_id}/stop` - Stop a job while preserving data

---

### What's New in 2.1
- ✨ Job tracking system with persistence across popup closes
- 🔄 Automatic reconnection with retry logic and health monitoring
- 🎯 Trafilatura integration with 3 extraction modes (Balanced/Recall/Precision)
- ☑️ Selective download options (content, media links, external links)
- 🟢 Visual connection status indicator
- 📊 Real-time job progress display with color-coded status
- 🔧 Smart 3-tier preprocessing (light/medium/aggressive) with safety checks
- 📝 Enhanced OpenRouter logging with full request/response visibility

---

**Simple Page Saver** - Professional web content extraction with AI
