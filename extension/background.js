// Background Service Worker for Simple Page Saver
// Handles tab management, API communication, and file downloads

// Import JSZip library for creating ZIP files
importScripts('jszip.min.js');

const API_BASE_URL = 'http://localhost:8077';
const DELAY_AFTER_LOAD = 2000; // Wait 2 seconds after page load for dynamic content

console.log('[Simple Page Saver] Background service worker loaded');
console.log('[Simple Page Saver] JSZip available:', typeof JSZip !== 'undefined');

// Message handler
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    console.log('[Simple Page Saver] Received message:', request.action);

    if (request.action === 'EXTRACT_SINGLE_PAGE') {
        handleExtractSinglePage(request.url)
            .then(response => {
                console.log('[Simple Page Saver] Extract complete:', response);
                sendResponse(response);
            })
            .catch(error => {
                console.error('[Simple Page Saver] Extract failed:', error);
                sendResponse({ success: false, error: error.message });
            });
        return true; // Will respond asynchronously
    } else if (request.action === 'MAP_SITE') {
        handleMapSite(request.url, request.depth)
            .then(response => {
                console.log('[Simple Page Saver] Map complete:', response);
                sendResponse(response);
            })
            .catch(error => {
                console.error('[Simple Page Saver] Map failed:', error);
                sendResponse({ success: false, error: error.message, urls: [] });
            });
        return true;
    } else if (request.action === 'EXTRACT_MULTIPLE_PAGES') {
        handleExtractMultiplePages(request.urls, request.outputZip)
            .then(response => {
                console.log('[Simple Page Saver] Multi-extract complete:', response);
                sendResponse(response);
            })
            .catch(error => {
                console.error('[Simple Page Saver] Multi-extract failed:', error);
                sendResponse({ success: false, error: error.message });
            });
        return true;
    }
});

// Extract a single page
async function handleExtractSinglePage(url) {
    console.log('[Extract] Starting extraction for:', url);

    try {
        // Open the page in a new tab
        console.log('[Extract] Creating new tab...');
        const tab = await chrome.tabs.create({ url, active: false });
        console.log('[Extract] Tab created:', tab.id);

        // Wait for page to load
        console.log('[Extract] Waiting for page to load...');
        await waitForTabLoad(tab.id);
        console.log('[Extract] Page loaded');

        // Wait additional time for dynamic content
        console.log('[Extract] Waiting for dynamic content...');
        await sleep(DELAY_AFTER_LOAD);

        // Extract HTML from the page
        console.log('[Extract] Extracting HTML...');
        const pageData = await extractPageData(tab.id);
        console.log('[Extract] HTML extracted, size:', pageData.html.length, 'chars');

        // Send to backend for processing
        console.log('[Extract] Sending to backend...');
        const result = await processWithBackend(url, pageData.html, pageData.title);
        console.log('[Extract] Backend response received:', result.filename);

        // Download the markdown file
        console.log('[Extract] Downloading markdown file...');
        await downloadFile(result.markdown, result.filename);

        // If there are media links, create media_links.txt
        if (result.media_urls && result.media_urls.length > 0) {
            console.log('[Extract] Downloading media links file...');
            const mediaContent = result.media_urls.join('\n');
            await downloadFile(mediaContent, 'media_links.txt');
        }

        // Close the tab after processing is complete (don't block on errors)
        console.log('[Extract] Closing tab...');
        try {
            await chrome.tabs.remove(tab.id);
        } catch (tabError) {
            console.warn('[Extract] Could not close tab:', tabError.message);
            // Not a fatal error, continue
        }

        console.log('[Extract] Success!');
        return {
            success: true,
            filename: result.filename,
            wordCount: result.word_count,
            usedAI: result.used_ai
        };
    } catch (error) {
        console.error('[Extract] Error:', error);
        return {
            success: false,
            error: error.message
        };
    }
}

// Map site and discover URLs
async function handleMapSite(startUrl, depth) {
    try {
        const discoveredUrls = new Set([startUrl]);
        const processedUrls = new Set();
        const urlsToProcess = [{ url: startUrl, level: 0 }];
        const urlDataList = [];

        while (urlsToProcess.length > 0) {
            const { url, level } = urlsToProcess.shift();

            if (processedUrls.has(url) || level > depth) {
                continue;
            }

            processedUrls.add(url);

            // Open tab and extract links
            const tab = await chrome.tabs.create({ url, active: false });
            await waitForTabLoad(tab.id);
            await sleep(1000); // Shorter delay for mapping

            try {
                const pageData = await extractPageData(tab.id);

                // Extract links using backend
                const links = await extractLinks(pageData.html, url);

                // Close tab after extraction
                try {
                    await chrome.tabs.remove(tab.id);
                } catch (tabError) {
                    console.warn('[Map] Could not close tab:', tabError.message);
                }

                // Process internal links for deeper crawling
                if (level < depth) {
                    for (const link of links.internal_links) {
                        if (!discoveredUrls.has(link)) {
                            discoveredUrls.add(link);
                            urlsToProcess.push({ url: link, level: level + 1 });
                            urlDataList.push({ url: link, type: 'internal', level: level + 1 });
                        }
                    }
                }

                // Add external links (don't crawl them)
                for (const link of links.external_links) {
                    if (!discoveredUrls.has(link)) {
                        discoveredUrls.add(link);
                        urlDataList.push({ url: link, type: 'external', level: level + 1 });
                    }
                }

                // Add media links
                for (const link of links.media_links) {
                    if (!discoveredUrls.has(link)) {
                        discoveredUrls.add(link);
                        urlDataList.push({ url: link, type: 'media', level: level + 1 });
                    }
                }
            } catch (error) {
                console.error(`Error processing ${url}:`, error);
                await chrome.tabs.remove(tab.id).catch(() => {});
            }
        }

        // Add the start URL to the list
        urlDataList.unshift({ url: startUrl, type: 'internal', level: 0 });

        return {
            success: true,
            urls: urlDataList
        };
    } catch (error) {
        console.error('Map site error:', error);
        return {
            success: false,
            error: error.message,
            urls: []
        };
    }
}

// Extract multiple pages
async function handleExtractMultiplePages(urls, outputZip) {
    try {
        const results = [];
        const allMediaUrls = new Set();
        let processed = 0;

        // Send progress update
        sendProgressUpdate(0, urls.length, 'Starting extraction...');

        for (const url of urls) {
            let tabId = null;
            try {
                // Open tab
                const tab = await chrome.tabs.create({ url, active: false });
                tabId = tab.id;
                await waitForTabLoad(tab.id);
                await sleep(DELAY_AFTER_LOAD);

                // Extract data
                const pageData = await extractPageData(tab.id);

                // Process with backend
                const result = await processWithBackend(url, pageData.html, pageData.title);

                results.push(result);

                // Collect media URLs
                if (result.media_urls) {
                    result.media_urls.forEach(url => allMediaUrls.add(url));
                }

                // Close tab after successful processing
                try {
                    await chrome.tabs.remove(tabId);
                } catch (tabError) {
                    console.warn('[Extract] Could not close tab:', tabError.message);
                }

                processed++;
                sendProgressUpdate(processed, urls.length, `Processed: ${result.filename}`);

            } catch (error) {
                console.error(`Error processing ${url}:`, error);
                // Try to close tab if it was created
                if (tabId) {
                    try {
                        await chrome.tabs.remove(tabId);
                    } catch (tabError) {
                        console.warn('[Extract] Could not close tab after error:', tabError.message);
                    }
                }
                processed++;
                sendProgressUpdate(processed, urls.length, `Error: ${url}`);
            }
        }

        // Download results
        if (outputZip) {
            // Create ZIP file
            await createAndDownloadZip(results, Array.from(allMediaUrls));
        } else {
            // Download individual files
            for (const result of results) {
                await downloadFile(result.markdown, result.filename);
            }

            // Download media links file
            if (allMediaUrls.size > 0) {
                const mediaContent = Array.from(allMediaUrls).join('\n');
                await downloadFile(mediaContent, 'media_links.txt');
            }
        }

        return {
            success: true,
            processed: results.length
        };
    } catch (error) {
        console.error('Extract multiple pages error:', error);
        return {
            success: false,
            error: error.message
        };
    }
}

// Extract page data using content script
async function extractPageData(tabId) {
    const results = await chrome.scripting.executeScript({
        target: { tabId },
        func: () => {
            return {
                html: document.documentElement.outerHTML,
                title: document.title,
                url: window.location.href
            };
        }
    });

    return results[0].result;
}

// Process HTML with backend
async function processWithBackend(url, html, title) {
    // Get API URL, AI setting, and custom prompt from chrome.storage
    const storage = await chrome.storage.local.get(['apiEndpoint', 'enableAI', 'customPrompt']);
    const apiUrl = storage.apiEndpoint || API_BASE_URL;
    const enableAI = storage.enableAI ?? false; // Default to false (use fallback)
    const customPrompt = storage.customPrompt || '';

    console.log('[Backend] Using API URL:', apiUrl);
    console.log('[Backend] AI enabled:', enableAI);
    if (customPrompt) {
        console.log('[Backend] Custom prompt:', customPrompt.substring(0, 100) + '...');
    }
    console.log('[Backend] Sending request to /process-html');

    const response = await fetch(`${apiUrl}/process-html`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            url,
            html,
            title,
            use_ai: enableAI,  // Pass AI preference to backend
            custom_prompt: customPrompt  // Pass custom AI instructions
        })
    });

    console.log('[Backend] Response status:', response.status);

    if (!response.ok) {
        const errorText = await response.text();
        console.error('[Backend] Error response:', errorText);
        throw new Error(`Backend error: ${response.status} ${response.statusText}`);
    }

    return await response.json();
}

// Extract links using backend
async function extractLinks(html, baseUrl) {
    // Get API URL from chrome.storage (service workers can't use localStorage)
    const storage = await chrome.storage.local.get(['apiEndpoint']);
    const apiUrl = storage.apiEndpoint || API_BASE_URL;

    console.log('[Backend] Extracting links from:', baseUrl);

    const response = await fetch(`${apiUrl}/extract-links`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ html, base_url: baseUrl })
    });

    if (!response.ok) {
        const errorText = await response.text();
        console.error('[Backend] Link extraction error:', errorText);
        throw new Error(`Backend error: ${response.status}`);
    }

    return await response.json();
}

// Download file
async function downloadFile(content, filename) {
    console.log('[Download] Creating download for:', filename);

    // Convert content to data URL (works in service workers, unlike URL.createObjectURL)
    const base64Content = btoa(unescape(encodeURIComponent(content)));
    const dataUrl = `data:text/plain;base64,${base64Content}`;

    try {
        const downloadId = await chrome.downloads.download({
            url: dataUrl,
            filename: filename,
            saveAs: false
        });

        console.log('[Download] Download started, ID:', downloadId);
    } catch (error) {
        console.error('[Download] Download failed:', error);
        throw new Error(`Download failed: ${error.message}`);
    }
}

// Create and download ZIP file
async function createAndDownloadZip(results, mediaUrls) {
    console.log('[ZIP] Creating ZIP file with', results.length, 'pages');

    try {
        // Create new JSZip instance
        const zip = new JSZip();

        // Add each markdown file to the ZIP
        for (let i = 0; i < results.length; i++) {
            const result = results[i];
            const filename = `${i + 1}_${result.filename}`;
            console.log('[ZIP] Adding file:', filename);
            zip.file(filename, result.markdown);
        }

        // Add media links file if there are any
        if (mediaUrls.length > 0) {
            const mediaContent = mediaUrls.join('\n');
            console.log('[ZIP] Adding media_links.txt with', mediaUrls.length, 'URLs');
            zip.file('media_links.txt', mediaContent);
        }

        // Generate ZIP file as blob
        console.log('[ZIP] Generating ZIP archive...');
        const blob = await zip.generateAsync({
            type: 'blob',
            compression: 'DEFLATE',
            compressionOptions: { level: 6 }
        });

        console.log('[ZIP] ZIP created, size:', blob.size, 'bytes');

        // Convert blob to data URL for download
        const reader = new FileReader();
        const dataUrl = await new Promise((resolve, reject) => {
            reader.onloadend = () => resolve(reader.result);
            reader.onerror = reject;
            reader.readAsDataURL(blob);
        });

        // Generate filename with timestamp
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
        const zipFilename = `page_saver_${timestamp}.zip`;

        console.log('[ZIP] Downloading as:', zipFilename);

        // Download the ZIP file
        const downloadId = await chrome.downloads.download({
            url: dataUrl,
            filename: zipFilename,
            saveAs: false
        });

        console.log('[ZIP] Download started, ID:', downloadId);
    } catch (error) {
        console.error('[ZIP] Error creating ZIP:', error);
        throw new Error(`ZIP creation failed: ${error.message}`);
    }
}

// Wait for tab to load
function waitForTabLoad(tabId) {
    return new Promise((resolve, reject) => {
        const timeout = setTimeout(() => {
            reject(new Error('Tab load timeout'));
        }, 30000); // 30 second timeout

        chrome.tabs.onUpdated.addListener(function listener(updatedTabId, changeInfo) {
            if (updatedTabId === tabId && changeInfo.status === 'complete') {
                clearTimeout(timeout);
                chrome.tabs.onUpdated.removeListener(listener);
                resolve();
            }
        });
    });
}

// Sleep utility
function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

// Send progress update to popup
function sendProgressUpdate(current, total, status) {
    chrome.runtime.sendMessage({
        type: 'PROGRESS_UPDATE',
        current,
        total,
        status
    }).catch(() => {
        // Popup might be closed, ignore error
    });
}
