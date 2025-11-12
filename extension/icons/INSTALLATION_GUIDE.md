# Chrome Extension Icon Installation Guide

## Quick Fix for Notification Error

The error "Unable to download all specified images" occurs when Chrome notifications try to use an `iconUrl` that doesn't exist or isn't properly configured.

## Installation Steps

### 1. Place the Icon Files

Download all 4 icon files (icon16.png, icon32.png, icon48.png, icon128.png) and place them in:

```
extension/
├── icons/
│   ├── icon16.png
│   ├── icon32.png
│   ├── icon48.png
│   └── icon128.png
├── manifest.json
├── popup.html
└── (other extension files)
```

**Create the `icons` folder if it doesn't exist.**

### 2. Update manifest.json

Add the following to your `manifest.json`:

```json
{
  "manifest_version": 3,
  "name": "Your Extension Name",
  "version": "1.0",
  
  "action": {
    "default_popup": "popup.html",
    "default_icon": {
      "16": "icons/icon16.png",
      "32": "icons/icon32.png",
      "48": "icons/icon48.png",
      "128": "icons/icon128.png"
    }
  },
  
  "icons": {
    "16": "icons/icon16.png",
    "32": "icons/icon32.png",
    "48": "icons/icon48.png",
    "128": "icons/icon128.png"
  }
}
```

### 3. Fix Notification Code (CRITICAL)

In your JavaScript code where you create notifications, update the `iconUrl` to point to a valid icon:

**Before (causes error):**
```javascript
chrome.notifications.create({
  type: 'basic',
  title: 'Download Complete',
  message: 'Your file has been downloaded',
  iconUrl: 'icon.png'  // ❌ This causes the error
});
```

**After (fixed):**
```javascript
chrome.notifications.create({
  type: 'basic',
  title: 'Download Complete',
  message: 'Your file has been downloaded',
  iconUrl: 'icons/icon48.png'  // ✅ Use relative path to icon
});
```

Or use an absolute path:
```javascript
chrome.notifications.create({
  type: 'basic',
  title: 'Download Complete',
  message: 'Your file has been downloaded',
  iconUrl: chrome.runtime.getURL('icons/icon48.png')  // ✅ Better approach
});
```

### 4. Update Web Accessible Resources (if needed)

If you're still getting errors, add this to your `manifest.json`:

```json
{
  "web_accessible_resources": [
    {
      "resources": ["icons/*.png"],
      "matches": ["<all_urls>"]
    }
  ]
}
```

### 5. Reload the Extension

1. Go to `chrome://extensions/`
2. Enable "Developer mode" (top right)
3. Click "Reload" on your extension
4. Test your notification again

## Common Issues

**Q: Still getting the error after adding icons?**
- Make sure the icon files are actually in the `extension/icons/` folder
- Check that the file names match exactly (case-sensitive)
- Verify the paths in your notification code use the correct relative path

**Q: Which icon size should I use for notifications?**
- Use `icon48.png` or `icon128.png` for notifications
- The 48px or 128px sizes work best for notification displays

**Q: Can I use a different icon for notifications?**
- Yes! You can create a separate notification icon (e.g., `notification-icon.png`) and reference it in your notification code

## Testing

After installation, test with this code in your background script or popup:

```javascript
chrome.notifications.create({
  type: 'basic',
  iconUrl: chrome.runtime.getURL('icons/icon48.png'),
  title: 'Test Notification',
  message: 'If you see this, the icons are working!'
});
```

Good luck with your extension!
