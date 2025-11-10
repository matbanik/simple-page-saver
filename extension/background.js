// Background Service Worker for Simple Page Saver
// Handles tab management, API communication, and file downloads

const API_BASE_URL = 'http://localhost:8077';
const DELAY_AFTER_LOAD = 2000; // Wait 2 seconds after page load for dynamic content

// Message handler
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === 'EXTRACT_SINGLE_PAGE') {
        handleExtractSinglePage(request.url).then(sendResponse);
        return true; // Will respond asynchronously
    } else if (request.action === 'MAP_SITE') {
        handleMapSite(request.url, request.depth).then(sendResponse);
        return true;
    } else if (request.action === 'EXTRACT_MULTIPLE_PAGES') {
        handleExtractMultiplePages(request.urls, request.outputZip).then(sendResponse);
        return true;
    }
});

// Extract a single page
async function handleExtractSinglePage(url) {
    try {
        // Open the page in a new tab
        const tab = await chrome.tabs.create({ url, active: false });

        // Wait for page to load
        await waitForTabLoad(tab.id);

        // Wait additional time for dynamic content
        await sleep(DELAY_AFTER_LOAD);

        // Extract HTML from the page
        const pageData = await extractPageData(tab.id);

        // Close the tab
        await chrome.tabs.remove(tab.id);

        // Send to backend for processing
        const result = await processWithBackend(url, pageData.html, pageData.title);

        // Download the markdown file
        await downloadFile(result.markdown, result.filename);

        // If there are media links, create media_links.txt
        if (result.media_urls && result.media_urls.length > 0) {
            const mediaContent = result.media_urls.join('\n');
            await downloadFile(mediaContent, 'media_links.txt');
        }

        return {
            success: true,
            filename: result.filename,
            wordCount: result.word_count,
            usedAI: result.used_ai
        };
    } catch (error) {
        console.error('Extract single page error:', error);
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
                await chrome.tabs.remove(tab.id);

                // Extract links using backend
                const links = await extractLinks(pageData.html, url);

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
            try {
                // Open tab
                const tab = await chrome.tabs.create({ url, active: false });
                await waitForTabLoad(tab.id);
                await sleep(DELAY_AFTER_LOAD);

                // Extract data
                const pageData = await extractPageData(tab.id);
                await chrome.tabs.remove(tab.id);

                // Process with backend
                const result = await processWithBackend(url, pageData.html, pageData.title);

                results.push(result);

                // Collect media URLs
                if (result.media_urls) {
                    result.media_urls.forEach(url => allMediaUrls.add(url));
                }

                processed++;
                sendProgressUpdate(processed, urls.length, `Processed: ${result.filename}`);

            } catch (error) {
                console.error(`Error processing ${url}:`, error);
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
    const apiUrl = localStorage.getItem('apiEndpoint') || API_BASE_URL;

    const response = await fetch(`${apiUrl}/process-html`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ url, html, title })
    });

    if (!response.ok) {
        throw new Error(`Backend error: ${response.status} ${response.statusText}`);
    }

    return await response.json();
}

// Extract links using backend
async function extractLinks(html, baseUrl) {
    const apiUrl = localStorage.getItem('apiEndpoint') || API_BASE_URL;

    const response = await fetch(`${apiUrl}/extract-links`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ html, base_url: baseUrl })
    });

    if (!response.ok) {
        throw new Error(`Backend error: ${response.status}`);
    }

    return await response.json();
}

// Download file
async function downloadFile(content, filename) {
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);

    await chrome.downloads.download({
        url,
        filename,
        saveAs: false
    });

    // Clean up
    setTimeout(() => URL.revokeObjectURL(url), 1000);
}

// Create and download ZIP file
async function createAndDownloadZip(results, mediaUrls) {
    // We'll use a simple ZIP creation approach
    // For a more robust solution, consider using JSZip library
    // For now, we'll download files individually with a prefix

    const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
    const prefix = `page_saver_${timestamp}_`;

    for (let i = 0; i < results.length; i++) {
        const result = results[i];
        const filename = `${prefix}${i + 1}_${result.filename}`;
        await downloadFile(result.markdown, filename);
    }

    // Download media links
    if (mediaUrls.length > 0) {
        const mediaContent = mediaUrls.join('\n');
        await downloadFile(mediaContent, `${prefix}media_links.txt`);
    }

    console.log('Note: Files downloaded with prefix instead of ZIP (ZIP requires additional library)');
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
