// Content Script for Simple Page Saver
// This script runs on web pages and provides utilities for extraction

// The main extraction is done via chrome.scripting.executeScript in background.js
// This content script can be used for additional page-specific functionality if needed

// Listen for messages from background script
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === 'EXTRACT_PAGE_DATA') {
        // Extract page data
        const data = {
            html: document.documentElement.outerHTML,
            title: document.title,
            url: window.location.href,
            meta: extractMetadata()
        };
        sendResponse(data);
        return true;
    }
});

// Extract metadata from the page
function extractMetadata() {
    const meta = {};

    // Get meta description
    const description = document.querySelector('meta[name="description"]');
    if (description) {
        meta.description = description.content;
    }

    // Get meta keywords
    const keywords = document.querySelector('meta[name="keywords"]');
    if (keywords) {
        meta.keywords = keywords.content;
    }

    // Get author
    const author = document.querySelector('meta[name="author"]');
    if (author) {
        meta.author = author.content;
    }

    // Get Open Graph data
    const ogTitle = document.querySelector('meta[property="og:title"]');
    if (ogTitle) {
        meta.ogTitle = ogTitle.content;
    }

    const ogDescription = document.querySelector('meta[property="og:description"]');
    if (ogDescription) {
        meta.ogDescription = ogDescription.content;
    }

    const ogImage = document.querySelector('meta[property="og:image"]');
    if (ogImage) {
        meta.ogImage = ogImage.content;
    }

    return meta;
}

// Utility function to get cleaned text content
function getCleanedText() {
    // Remove script and style elements
    const clone = document.body.cloneNode(true);
    const scripts = clone.querySelectorAll('script, style');
    scripts.forEach(el => el.remove());

    return clone.textContent || clone.innerText || '';
}

// Mark that content script is loaded
console.log('Simple Page Saver content script loaded');
