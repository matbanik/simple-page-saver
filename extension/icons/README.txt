# Extension Icons (Optional)

The extension currently runs without custom icons (Chrome will use a default icon).

To add custom icons:

1. Create PNG images in these sizes:
   - icon16.png (16x16 pixels)
   - icon32.png (32x32 pixels)
   - icon48.png (48x48 pixels)
   - icon128.png (128x128 pixels)

2. Place them in this directory

3. Update manifest.json to include:

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

4. Reload the extension in chrome://extensions/

You can create simple icons using:
- Online tools like favicon.io or canva.com
- Image editors like GIMP, Photoshop, or Paint.NET
- Icon generators for Chrome extensions
