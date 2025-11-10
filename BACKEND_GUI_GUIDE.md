# Backend GUI and Advanced Features Guide

## New Features Overview

### 1. Tkinter GUI for Backend Management
A full-featured GUI application for managing the Simple Page Saver backend server.

**File**: `backend/gui.py`

**Features**:
- Configure all server settings (port, AI model, API key, log level)
- Encrypted API key storage
- Start/Stop server controls
- Automatic process detection by port
- Test backend health and AI connectivity
- Real-time log output viewer

**How to Run**:
```powershell
cd backend
python gui.py
```

### 2. Settings Management with Encryption
Replaces .env with encrypted JSON-based settings storage.

**File**: `backend/settings_manager.py`

**Features**:
- Settings stored in `settings.json`
- API key encrypted using cryptography library
- Machine-specific encryption key
- Automatic migration from .env (if needed)

**Settings Structure**:
```json
{
  "server_port": 8077,
  "default_model": "deepseek/deepseek-chat",
  "max_tokens": 32000,
  "log_level": "INFO",
  "openrouter_api_key_encrypted": "encrypted_string_here"
}
```

### 3. Advanced Logging System
Comprehensive logging with API key masking and multiple log levels.

**File**: `backend/logging_config.py`

**Features**:
- File logging to `logs/simple_page_saver_YYYYMMDD.log`
- Configurable log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
- Automatic API key masking in all logs
- AI request/response logging
- No unicode characters (PowerShell compatible)

**Log Format**:
```
[2025-01-10 12:34:56] [INFO] [simple_page_saver] Processing request for URL: https://example.com
[2025-01-10 12:34:57] [INFO] [simple_page_saver] [AI Request] Model: deepseek/deepseek-chat, Prompt size: 1234 chars
[2025-01-10 12:34:58] [INFO] [simple_page_saver] [AI Response] Model: deepseek/deepseek-chat, Status: AI, Response size: 5678 chars
```

### 4. Updated Main Application
Integrated logging and settings management.

**File**: `backend/main_updated.py`

**Key Changes**:
- Uses SettingsManager for configuration
- Comprehensive logging throughout
- Logs all API requests and responses
- Masks API keys in all output
- Accepts `custom_prompt` parameter for AI customization

### 5. Unified Launcher with Command-Line Support
Single entry point supporting both GUI and server modes via command-line arguments.

**File**: `backend/launcher.py`

**Features**:
- Default mode: Start server directly
- GUI mode: Launch management interface with `-gui` flag
- Port override: Specify custom port with `-p` or `--port`
- Log level override: Set log level with `--log-level`
- Help system: Show all options with `--help`

**Command-Line Options**:
```powershell
# Start server directly (default)
SimplePageSaver.exe

# Launch management GUI
SimplePageSaver.exe -gui
SimplePageSaver.exe --gui

# Start server on custom port
SimplePageSaver.exe -p 8080
SimplePageSaver.exe --port 8080

# Override log level
SimplePageSaver.exe --log-level DEBUG

# Show help
SimplePageSaver.exe --help
```

**Convenience Launchers**:
- `start_gui.bat` - Double-click to launch GUI
- `start_server.bat` - Double-click to start server

### 6. Build System
PyInstaller-based executable builder.

**Files**:
- `backend/build.py` - Python build script
- `backend/build.ps1` - PowerShell wrapper
- `backend/launcher.py` - Unified entry point

**How to Build**:
```powershell
cd backend
.\build.ps1
```

Output: `dist/SimplePageSaver.exe` (single executable, ~40-50MB)

### 7. Extension Reload Script
Automated extension reload helper.

**File**: `reload_extension.ps1`

**Usage**:
```powershell
.\reload_extension.ps1
```

**Note**: Chrome doesn't support full automation of extension reload. The script provides instructions and opens chrome://extensions/ for manual reload.

### 8. Custom AI Prompt Instructions (Extension)
Add custom instructions to AI processing with preset templates.

**Modified Files**:
- `extension/popup.html`
- `extension/popup.js`
- `extension/background.js`

**Features**:
- 7 preset templates for common tasks:
  1. Extract Product Details (Title, Price, Description)
  2. Highlight Specific Keyword
  3. Create Price Comparison Table
  4. Extract Customer Reviews Summary
  5. Extract Contact Information
  6. Create Product Specifications Table
  7. Summarize All Links and Resources
- Custom textarea for additional instructions
- Only shown when AI is enabled
- Saved across sessions

**How to Use**:
1. Enable AI Processing in extension
2. Select a preset from dropdown (or write custom instructions)
3. Extract pages - AI will use your custom instructions

## Installation & Setup

### Backend Setup

1. **Install new dependencies**:
```powershell
cd backend
pip install -r requirements.txt
```

New dependencies:
- `cryptography>=41.0.0` - For API key encryption
- `psutil>=5.9.0` - For process management
- `pyinstaller>=6.0.0` - For building executable

2. **Run the GUI**:
```powershell
python gui.py
```

3. **Configure settings** in the GUI:
   - Enter your OpenRouter API key
   - Select AI model
   - Set log level (INFO recommended)
   - Click "Save Settings"

4. **Start the server** using GUI controls

### Extension Setup

1. **Pull latest changes**:
```powershell
git pull
```

2. **Reload extension** in Chrome:
   - Go to `chrome://extensions/`
   - Find "Simple Page Saver"
   - Click reload icon

3. **Enable AI** and test custom prompts

## Usage Examples

### GUI Backend Manager

**Starting Server**:
1. Open GUI: `python gui.py`
2. Configure settings
3. Click "Start Server"
4. Monitor status indicator

**Testing**:
1. Click "Test Backend Health" - verifies server is running
2. Click "Test AI Connection" - sends test HTML to AI

**Stopping Server**:
1. Click "Stop Server"
2. GUI finds process by port and terminates it

### Command-Line Usage (Executable)

**Start Server Directly** (default behavior):
```powershell
# Using executable
SimplePageSaver.exe

# Or with Python
python launcher.py
```

**Launch Management GUI**:
```powershell
# Using executable
SimplePageSaver.exe -gui

# Or double-click
start_gui.bat

# Or with Python
python launcher.py -gui
```

**Start on Custom Port**:
```powershell
# Start server on port 8080
SimplePageSaver.exe -p 8080

# Start server on port 9000
SimplePageSaver.exe --port 9000
```

**Override Log Level**:
```powershell
# Debug mode (very verbose)
SimplePageSaver.exe --log-level DEBUG

# Error only
SimplePageSaver.exe --log-level ERROR
```

**Combine Options**:
```powershell
# Custom port + debug logging
SimplePageSaver.exe -p 8080 --log-level DEBUG

# GUI with pre-configured settings
SimplePageSaver.exe -gui
```

**Get Help**:
```powershell
SimplePageSaver.exe --help
```

### Custom AI Prompts

**Example 1: Extract Products**:
1. Select preset: "Extract Product Details"
2. Navigate to shopping site
3. Extract page
4. Result includes table with product info

**Example 2: Highlight Keywords**:
1. Select preset: "Highlight Specific Keyword"
2. Edit to replace [KEYWORD] with actual keyword
3. Extract page
4. Result has keyword highlighted with **bold**

**Example 3: Custom Instructions**:
1. Leave preset empty
2. Type custom instructions: "Create a bullet list of all features mentioned, sorted by importance"
3. Extract page
4. AI follows your custom instructions

## Logging

### Log Levels

- **DEBUG**: Verbose output, includes HTML sizes, token counts, full metadata
- **INFO**: Standard operational logging (recommended)
- **WARNING**: Potential issues, large content warnings
- **ERROR**: Errors that don't stop operation
- **CRITICAL**: Fatal errors

### Log File Location

`backend/logs/simple_page_saver_YYYYMMDD.log`

New file created daily.

### Reading Logs

**PowerShell**:
```powershell
Get-Content backend\logs\simple_page_saver_*.log -Tail 50
```

**GUI**: Log viewer at bottom of window shows real-time output

### API Key Security

API keys are:
1. **Encrypted** in settings.json using cryptography library
2. **Masked** in all log output as `***MASKED_API_KEY***`
3. **Never** stored in plain text
4. **Machine-specific** encryption (can't be decrypted on another computer)

## Building Executable

### Requirements

- PyInstaller installed (`pip install pyinstaller`)
- All dependencies installed
- Clean working directory (no previous builds)

### Build Process

```powershell
cd backend
.\build.ps1
```

This will:
1. Activate virtual environment (or create if needed)
2. Install/upgrade dependencies
3. Run PyInstaller with proper configuration
4. Create single-file executable

### Distributing

The executable (`dist/SimplePageSaver.exe`) is standalone and can be:
- Copied to any Windows machine
- Run without Python installed
- Double-clicked to open GUI

**Note**: First run will be slow while extracting bundled files.

## Troubleshooting

### GUI Issues

**"Port already in use"**:
- Another instance is running
- Kill process manually or use "Stop Server" first

**"Cannot start server"**:
- Check Python is in PATH
- Check all dependencies installed
- View logs for details

### Logging Issues

**"Permission denied" writing logs**:
- Run as administrator
- Check logs directory is writable

**Logs too verbose**:
- Change log level to WARNING or ERROR

### Build Issues

**PyInstaller fails**:
- Clear build/dist directories
- Update PyInstaller: `pip install --upgrade pyinstaller`
- Check no files are locked/in use

**Missing modules in exe**:
- Add `--hidden-import` flags in build.py
- Consult PyInstaller documentation

### Extension Issues

**Custom prompt not working**:
- Ensure AI is enabled
- Check backend logs for custom_prompt being received
- Verify backend is using main_updated.py (not old main.py)

## Future Enhancements

Potential improvements:
1. **GUI Improvements**:
   - Syntax highlighting in log viewer
   - Settings import/export
   - Multiple server profiles

2. **Logging Enhancements**:
   - Log rotation (keep last N days)
   - Log search/filter
   - Export logs as CSV

3. **Build System**:
   - Auto-updater
   - Installer creation
   - Digital signature

4. **Extension**:
   - Save/load custom prompts
   - Prompt templates marketplace
   - Preview AI results before download

## Support

For issues:
1. Check GUI log viewer for errors
2. Review log files in `backend/logs/`
3. Test backend health using GUI test buttons
4. Verify API key is correct and has credits

---

**Version**: 2.0.0
**Last Updated**: 2025-01-10
