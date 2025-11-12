// Background Service Worker for Simple Page Saver
// Handles tab management, API communication, and file downloads

// Import JSZip library for creating ZIP files
importScripts('jszip.min.js');

// Import utilities
importScripts('warnings-tracker.js');
importScripts('job-storage.js');

const API_BASE_URL = 'http://localhost:8077';
const DELAY_AFTER_LOAD = 2000; // Wait 2 seconds after page load for dynamic content

console.log('[Simple Page Saver] Background service worker loaded');
console.log('[Simple Page Saver] JSZip available:', typeof JSZip !== 'undefined');

// Initialize job storage
console.log('[JobStorage] Initializing IndexedDB...');
jobStorage.init().then(() => {
    console.log('[JobStorage] IndexedDB initialized successfully');
}).catch(error => {
    console.error('[JobStorage] Failed to initialize IndexedDB:', error);
});

// Connection state management
const connectionState = {
    isConnected: false,
    lastSuccessfulPing: null,
    consecutiveFailures: 0,
    aiEnabled: false,
    monitoring: false,
    isBusy: false,               // New: track if backend is busy
    lastRequestTime: null,       // New: track last request
    averageResponseTime: 0,      // New: track average response time
    slowResponseCount: 0         // New: count slow responses
};

// Site mapping state (for pause/resume)
const siteMappingState = {
    currentJobId: null,
    isPaused: false,
    isCompleting: false,  // New: flag to complete gracefully after current URL
    discoveredUrls: new Set(),
    processedUrls: new Set(),
    urlsToProcess: [],
    urlDataList: [],
    parentMap: new Map(), // Track parent-child relationships
    warnings: null // WarningsTracker instance for collecting warnings during site mapping
};

// Start periodic health monitoring
startHealthMonitoring();

// Periodic health monitoring (every 30 seconds)
function startHealthMonitoring() {
    if (connectionState.monitoring) return;

    connectionState.monitoring = true;
    console.log('[Connection] Starting periodic health monitoring');

    // Initial check
    checkBackendHealthQuiet();

    // Check every 30 seconds
    setInterval(async () => {
        await checkBackendHealthQuiet();
    }, 30000);
}

// Quiet health check (doesn't show notifications)
async function checkBackendHealthQuiet() {
    try {
        const storage = await chrome.storage.local.get(['apiEndpoint']);
        const apiUrl = storage.apiEndpoint || API_BASE_URL;

        const startTime = Date.now();
        const response = await fetch(`${apiUrl}/`, {
            method: 'GET',
            signal: AbortSignal.timeout(10000) // Increased to 10 seconds for busy backend
        });

        const responseTime = Date.now() - startTime;

        if (response.ok) {
            const data = await response.json();
            const wasDisconnected = !connectionState.isConnected;

            connectionState.isConnected = true;
            connectionState.lastSuccessfulPing = Date.now();
            connectionState.consecutiveFailures = 0;
            connectionState.aiEnabled = data.ai_enabled;

            // Update response time tracking
            if (connectionState.averageResponseTime === 0) {
                connectionState.averageResponseTime = responseTime;
            } else {
                connectionState.averageResponseTime =
                    (connectionState.averageResponseTime * 0.7) + (responseTime * 0.3);
            }

            // Check if backend is busy (response time > 3 seconds or > 3x average)
            const isSlow = responseTime > 3000 ||
                          responseTime > (connectionState.averageResponseTime * 3);

            if (isSlow) {
                connectionState.slowResponseCount++;
                connectionState.isBusy = connectionState.slowResponseCount >= 2;
                console.log(`[Connection] Slow response: ${responseTime}ms (avg: ${Math.round(connectionState.averageResponseTime)}ms)`);
            } else {
                connectionState.slowResponseCount = Math.max(0, connectionState.slowResponseCount - 1);
                connectionState.isBusy = false;
            }

            if (wasDisconnected) {
                console.log('[Connection] ✓ Backend reconnected');
            }

            return true;
        } else {
            handleConnectionFailure();
            return false;
        }
    } catch (error) {
        handleConnectionFailure();
        return false;
    }
}

// Handle connection failure
function handleConnectionFailure() {
    connectionState.consecutiveFailures++;
    connectionState.isBusy = false;
    connectionState.slowResponseCount = 0;

    // Only mark as disconnected after 3 consecutive failures (90 seconds total)
    if (connectionState.consecutiveFailures >= 3) {
        if (connectionState.isConnected) {
            console.warn('[Connection] Backend connection lost (after 3 attempts)');
            connectionState.isConnected = false;
        }
    } else {
        console.warn(`[Connection] Health check failed (attempt ${connectionState.consecutiveFailures}/3)`);
    }

    if (connectionState.consecutiveFailures % 5 === 0) {
        console.error(`[Connection] ${connectionState.consecutiveFailures} consecutive failures`);
    }
}

// Retry utility with exponential backoff
async function retryWithBackoff(operation, operationName, maxRetries = 3) {
    let lastError;

    for (let attempt = 1; attempt <= maxRetries; attempt++) {
        try {
            console.log(`[Retry] ${operationName} - Attempt ${attempt}/${maxRetries}`);
            const result = await operation();

            // Success - reset failure counter
            if (connectionState.consecutiveFailures > 0) {
                console.log(`[Retry] ${operationName} succeeded after ${connectionState.consecutiveFailures} failures`);
                connectionState.consecutiveFailures = 0;
            }

            return result;
        } catch (error) {
            lastError = error;
            console.warn(`[Retry] ${operationName} failed on attempt ${attempt}:`, error.message);

            // If it's the last attempt, throw the error
            if (attempt === maxRetries) {
                console.error(`[Retry] ${operationName} failed after ${maxRetries} attempts`);
                break;
            }

            // Check if backend is healthy before retrying
            const health = await checkBackendHealthQuiet();
            if (!health) {
                console.warn(`[Retry] Backend unhealthy, waiting before retry...`);
            }

            // Exponential backoff: 2s, 4s, 8s
            const delay = 1000 * Math.pow(2, attempt);
            console.log(`[Retry] Waiting ${delay}ms before retry...`);
            await sleep(delay);
        }
    }

    throw lastError;
}

// Message handler
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    console.log('[Simple Page Saver] Received message:', request.action);

    if (request.action === 'GET_CONNECTION_STATE') {
        // Return current connection state
        sendResponse({
            success: true,
            state: {
                isConnected: connectionState.isConnected,
                lastSuccessfulPing: connectionState.lastSuccessfulPing,
                consecutiveFailures: connectionState.consecutiveFailures,
                aiEnabled: connectionState.aiEnabled,
                isBusy: connectionState.isBusy,
                averageResponseTime: Math.round(connectionState.averageResponseTime)
            }
        });
        return false;
    } else if (request.action === 'EXTRACT_SINGLE_PAGE') {
        handleExtractSinglePage(request.url, request.outputZip, request.downloadOptions)
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
        handleExtractMultiplePages(request.urls, request.outputZip, request.mergeIntoSingle)
            .then(response => {
                console.log('[Simple Page Saver] Multi-extract complete:', response);
                sendResponse(response);
            })
            .catch(error => {
                console.error('[Simple Page Saver] Multi-extract failed:', error);
                sendResponse({ success: false, error: error.message });
            });
        return true;
    } else if (request.action === 'PAUSE_JOB') {
        handlePauseJob(request.jobId)
            .then(response => sendResponse(response))
            .catch(error => sendResponse({ success: false, error: error.message }));
        return true;
    } else if (request.action === 'RESUME_JOB') {
        handleResumeJob(request.jobId)
            .then(response => sendResponse(response))
            .catch(error => sendResponse({ success: false, error: error.message }));
        return true;
    } else if (request.action === 'STOP_JOB') {
        handleStopJob(request.jobId)
            .then(response => sendResponse(response))
            .catch(error => sendResponse({ success: false, error: error.message }));
        return true;
    } else if (request.action === 'COMPLETE_NOW_JOB') {
        handleCompleteNowJob(request.jobId)
            .then(response => sendResponse(response))
            .catch(error => sendResponse({ success: false, error: error.message }));
        return true;
    }
});

// Show notification
function showNotification(title, message, type = 'basic') {
    chrome.notifications.create({
        type: type,
        iconUrl: chrome.runtime.getURL('icons/icon48.png'),
        title: title,
        message: message,
        priority: 2
    });
}

// Extract a single page
async function handleExtractSinglePage(url, outputZip = false, downloadOptions = null) {
    // Default download options if not provided (backward compatibility)
    if (!downloadOptions) {
        downloadOptions = {
            content: true,
            mediaLinks: false,
            externalLinks: false,
            printToPdf: false
        };
    }

    console.log('[Extract] Starting extraction for:', url);
    console.log('[Extract] Output as ZIP:', outputZip);
    console.log('[Extract] Download options:', downloadOptions);

    // Create a local job to track this extraction
    const jobId = `local-${Date.now()}`;
    const jobData = {
        id: jobId,
        type: 'extract_page',
        status: 'processing',
        params: {
            url: url,
            title: `Extract: ${url}`,
            output_zip: outputZip,
            download_options: downloadOptions
        },
        created_at: new Date().toISOString(),
        progress: 0
    };

    // Save job immediately so it appears in UI
    await jobStorage.saveJob(jobData);
    console.log('[Extract] Created job:', jobId);

    // Initialize warnings tracker
    const warnings = new WarningsTracker();

    // Check backend health first
    const health = await checkBackendHealth();
    if (!health.healthy) {
        // Update job as failed
        jobData.status = 'failed';
        jobData.error = health.error;
        await jobStorage.saveJob(jobData);

        showNotification('Backend Error', health.error);
        return {
            success: false,
            error: health.error
        };
    }

    showNotification('Simple Page Saver', 'Extracting page...');

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

        // Extract HTML from the page first (needed for title)
        console.log('[Extract] Extracting HTML...');
        const pageData = await extractPageData(tab.id);
        console.log('[Extract] HTML extracted, size:', pageData.html.length, 'chars');

        // Generate PDF directly if requested (using Chrome DevTools Protocol)
        if (downloadOptions.printToPdf) {
            try {
                console.log('[Extract] Generating PDF using Chrome DevTools Protocol...');

                // Inject print styles before PDF generation
                await chrome.scripting.executeScript({
                    target: { tabId: tab.id },
                    func: () => {
                        const style = document.createElement('style');
                        style.id = 'simple-page-saver-print-styles';
                        style.textContent = `
                            @page {
                                size: A0;
                                margin: 0.5cm;
                            }
                            @media print {
                                body {
                                    -webkit-print-color-adjust: exact !important;
                                    print-color-adjust: exact !important;
                                }
                                /* Disable background graphics */
                                * {
                                    background: transparent !important;
                                    background-image: none !important;
                                }
                            }
                        `;
                        document.head.appendChild(style);
                    }
                });

                // Generate PDF using Chrome DevTools Protocol
                const pdfData = await generatePdfUsingCDP(tab.id, pageData.title);

                if (pdfData) {
                    console.log('[Extract] PDF generated successfully, size:', pdfData.byteLength, 'bytes');

                    // Download the PDF using data URL (works in service workers, unlike URL.createObjectURL)
                    const blob = new Blob([pdfData], { type: 'application/pdf' });
                    const reader = new FileReader();
                    const filename = sanitizeFilename(pageData.title || 'page') + '.pdf';

                    await new Promise((resolve, reject) => {
                        reader.onloadend = async () => {
                            try {
                                await chrome.downloads.download({
                                    url: reader.result,
                                    filename: filename,
                                    saveAs: false
                                });
                                console.log('[Extract] PDF downloaded:', filename);
                                warnings.addGeneric('print', `PDF saved as ${filename} (A0 size, no backgrounds)`);
                                resolve();
                            } catch (err) {
                                reject(err);
                            }
                        };
                        reader.onerror = reject;
                        reader.readAsDataURL(blob);
                    });
                } else {
                    throw new Error('PDF generation returned no data');
                }

                // Clean up styles
                await chrome.scripting.executeScript({
                    target: { tabId: tab.id },
                    func: () => {
                        const styleEl = document.getElementById('simple-page-saver-print-styles');
                        if (styleEl) styleEl.remove();
                    }
                });

            } catch (error) {
                console.error('[Extract] Failed to generate PDF:', error);
                warnings.addGeneric('print', `Failed to generate PDF: ${error.message}`);
            }
        }

        let result = null;
        let externalLinks = [];

        // Process with backend if content is requested
        if (downloadOptions.content) {
            console.log('[Extract] Sending to backend for processing...');
            result = await processWithBackend(url, pageData.html, pageData.title);
            console.log('[Extract] Backend response received:', result.filename);
        }

        // Extract links if media or external links requested
        if (downloadOptions.mediaLinks || downloadOptions.externalLinks) {
            console.log('[Extract] Extracting links from page...');
            const links = await extractLinks(pageData.html, url);
            console.log('[Extract] Links extracted:', {
                internal: links.internal_links.length,
                external: links.external_links.length,
                media: links.media_links.length
            });

            if (downloadOptions.externalLinks) {
                externalLinks = links.external_links;
            }

            // Override media URLs if explicitly requested
            if (downloadOptions.mediaLinks && result) {
                result.media_urls = links.media_links;
            } else if (downloadOptions.mediaLinks && !result) {
                // Create minimal result object for media links only
                result = {
                    media_urls: links.media_links,
                    filename: 'media_links.txt'
                };
            }
        }

        // Prepare files for download
        const filesToDownload = [];

        if (downloadOptions.content && result && result.markdown) {
            filesToDownload.push({
                content: result.markdown,
                filename: result.filename
            });
        }

        if (downloadOptions.mediaLinks && result && result.media_urls && result.media_urls.length > 0) {
            filesToDownload.push({
                content: result.media_urls.join('\n'),
                filename: 'media_links.txt'
            });
        }

        if (downloadOptions.externalLinks && externalLinks.length > 0) {
            filesToDownload.push({
                content: externalLinks.join('\n'),
                filename: 'external_links.txt'
            });
        }

        // Add warnings.txt if there are any warnings
        if (warnings.hasWarnings()) {
            const warningsText = warnings.exportAsText();
            filesToDownload.push({
                content: warningsText,
                filename: 'warnings.txt'
            });
            console.log(`[Extract] ${warnings.count()} warnings will be included in download`);
        }

        // Download based on ZIP preference
        if (outputZip && filesToDownload.length > 0) {
            // Create ZIP file with selected files
            console.log('[Extract] Creating ZIP file with', filesToDownload.length, 'files...');
            const zip = new JSZip();

            for (const file of filesToDownload) {
                if (file.isDataUrl) {
                    // Convert data URL to binary for ZIP
                    const base64Data = file.content.split(',')[1];
                    zip.file(file.filename, base64Data, {base64: true});
                } else {
                    zip.file(file.filename, file.content);
                }
            }

            const blob = await zip.generateAsync({type: 'blob', compression: 'DEFLATE'});
            const reader = new FileReader();
            const dataUrl = await new Promise((resolve, reject) => {
                reader.onloadend = () => resolve(reader.result);
                reader.onerror = reject;
                reader.readAsDataURL(blob);
            });

            const timestamp = new Date().toISOString().replace(/[:.]/g, '-').split('T')[0];
            const zipFilename = `page_extract_${timestamp}.zip`;
            await chrome.downloads.download({
                url: dataUrl,
                filename: zipFilename,
                saveAs: false
            });

            showNotification('Extraction Complete', `Saved as ZIP: ${zipFilename}\n${filesToDownload.length} files included`);
        } else {
            // Download individual files
            for (const file of filesToDownload) {
                console.log('[Extract] Downloading:', file.filename);

                if (file.isDataUrl) {
                    // For data URLs (images, media), download directly
                    await chrome.downloads.download({
                        url: file.content,
                        filename: file.filename,
                        saveAs: false
                    });
                } else {
                    // For text content, use existing downloadFile function
                    await downloadFile(file.content, file.filename);
                }
            }

            showNotification('Extraction Complete', `Downloaded ${filesToDownload.length} file(s)`);
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

        // Update job as completed
        jobData.status = 'completed';
        jobData.completed_at = new Date().toISOString();
        jobData.result = {
            filename: result?.filename || 'links',
            word_count: result?.word_count || 0,
            used_ai: result?.used_ai || false
        };
        await jobStorage.saveJob(jobData);

        return {
            success: true,
            filename: result?.filename || 'links',
            wordCount: result?.word_count || 0,
            usedAI: result?.used_ai || false
        };
    } catch (error) {
        console.error(`[Extract] Error for job ${jobData.id}:`, error);
        showNotification('Extraction Failed', `Job ${jobData.id}: ${error.message}`);

        // Update job as failed
        jobData.status = 'failed';
        jobData.completed_at = new Date().toISOString();
        jobData.error = error.message;
        await jobStorage.saveJob(jobData);

        return {
            success: false,
            error: error.message
        };
    }
}

// Map site and discover URLs
async function handleMapSite(startUrl, depth) {
    // Check backend health first
    const health = await checkBackendHealth();
    if (!health.healthy) {
        showNotification('Backend Error', health.error);
        return {
            success: false,
            error: health.error,
            urls: []
        };
    }

    // Create descriptive title for the job
    const jobTitle = `Site Map: ${startUrl}`;

    // Create a temporary local job IMMEDIATELY so it appears in UI
    const tempJobId = `temp-${Date.now()}`;
    const tempJobData = {
        id: tempJobId,
        type: 'site_map',
        status: 'processing',
        params: {
            start_url: startUrl,
            max_depth: depth,
            title: jobTitle
        },
        created_at: new Date().toISOString(),
        progress: 0
    };
    await jobStorage.saveJob(tempJobData);
    console.log('[Map] Created temporary local job:', tempJobId);

    showNotification('Site Mapping', `Mapping site with depth ${depth}...`);

    let jobId = null;

    try {
        // Create a site mapping job on backend
        const storage = await chrome.storage.local.get(['apiEndpoint']);
        const apiUrl = storage.apiEndpoint || 'http://localhost:8077';

        const jobResponse = await fetch(`${apiUrl}/site-map/start`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                start_url: startUrl,
                max_depth: depth,
                title: jobTitle
            })
        });

        if (jobResponse.ok) {
            const jobData = await jobResponse.json();
            jobId = jobData.job_id;
            siteMappingState.currentJobId = jobId;
            siteMappingState.isPaused = false;

            // Initialize warnings tracker for site mapping
            siteMappingState.warnings = new WarningsTracker();
            siteMappingState.warnings.setJobId(jobId);
            console.log('[Map] Initialized warnings tracker for job:', jobId);

            console.log('[Map] Created backend job:', jobId);

            // Ensure params has title and start_url for display purposes
            if (!jobData.params) {
                jobData.params = {};
            }
            jobData.params.title = jobTitle;
            jobData.params.start_url = startUrl;

            // Save backend job to IndexedDB (replaces temp job)
            await jobStorage.saveJob(jobData);

            // Remove temporary job
            await jobStorage.deleteJob(tempJobId);
            console.log('[Map] Replaced temp job with backend job');
        } else {
            // Backend job creation failed, keep using temp job
            console.warn('[Map] Backend job creation failed, using temp job');
            jobId = tempJobId;
            siteMappingState.currentJobId = tempJobId;

            // Initialize warnings tracker for temp job too
            siteMappingState.warnings = new WarningsTracker();
            siteMappingState.warnings.setJobId(tempJobId);
            console.log('[Map] Initialized warnings tracker for temp job:', tempJobId);
        }

        const discoveredUrls = new Set([startUrl]);
        const processedUrls = new Set();
        const urlsToProcess = [{ url: startUrl, level: 0, parent: null }];
        const urlDataList = [];

        // Store state in siteMappingState for pause/resume
        siteMappingState.discoveredUrls = discoveredUrls;
        siteMappingState.processedUrls = processedUrls;
        siteMappingState.urlsToProcess = urlsToProcess;
        siteMappingState.urlDataList = urlDataList;

        while (urlsToProcess.length > 0 && !siteMappingState.isPaused && !siteMappingState.isCompleting) {
            const { url, level, parent } = urlsToProcess.shift();

            if (processedUrls.has(url) || level > depth) {
                continue;
            }

            // Check for pause/complete again after async operations
            if (siteMappingState.isPaused) {
                console.log('[Map] Job paused by user');
                break;
            }

            if (siteMappingState.isCompleting) {
                console.log('[Map] Completing job now - will finish after this URL');
            }

            processedUrls.add(url);

            let tab = null;
            try {
                // Open tab with timeout
                console.log(`[Map] Processing URL ${processedUrls.size}/${urlsToProcess.length + processedUrls.size}: ${url}`);

                tab = await Promise.race([
                    chrome.tabs.create({ url, active: false }),
                    new Promise((_, reject) => setTimeout(() => reject(new Error('Tab creation timeout')), 30000))
                ]);

                // Wait for page load with timeout
                await Promise.race([
                    waitForTabLoad(tab.id),
                    new Promise((_, reject) => setTimeout(() => reject(new Error('Page load timeout')), 30000))
                ]);

                await sleep(1000); // Shorter delay for mapping

                const pageData = await extractPageData(tab.id);

                // Extract links using backend
                const links = await extractLinks(pageData.html, url);

                // Close tab after extraction
                try {
                    await chrome.tabs.remove(tab.id);
                    tab = null; // Mark as closed
                } catch (tabError) {
                    console.warn('[Map] Could not close tab:', tabError.message);
                }

                // Process internal links for deeper crawling
                if (level < depth) {
                    for (const link of links.internal_links) {
                        if (!discoveredUrls.has(link)) {
                            discoveredUrls.add(link);
                            urlsToProcess.push({ url: link, level: level + 1, parent: url });
                            urlDataList.push({ url: link, type: 'internal', level: level + 1, parent: url });
                            // Track parent-child relationship (Bug fix #2)
                            siteMappingState.parentMap.set(link, url);
                        }
                    }
                }

                // Add external links (don't crawl them)
                for (const link of links.external_links) {
                    if (!discoveredUrls.has(link)) {
                        discoveredUrls.add(link);
                        urlDataList.push({ url: link, type: 'external', level: level + 1, parent: url });
                        siteMappingState.parentMap.set(link, url);
                    }
                }

                // Add media links
                for (const link of links.media_links) {
                    if (!discoveredUrls.has(link)) {
                        discoveredUrls.add(link);
                        urlDataList.push({ url: link, type: 'media', level: level + 1, parent: url });
                        siteMappingState.parentMap.set(link, url);
                    }
                }

                // Update job progress
                if (jobId) {
                    fetch(`${apiUrl}/site-map/progress`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            job_id: jobId,
                            discovered_count: discoveredUrls.size,
                            total_to_process: urlsToProcess.length + processedUrls.size,
                            message: `Discovered ${discoveredUrls.size} URLs (${processedUrls.size} processed)`
                        })
                    }).catch(err => console.warn('[Map] Failed to update progress:', err));
                }
            } catch (error) {
                console.error(`[Map] Error processing ${url}:`, error);

                // Add warning for failed URL processing
                if (siteMappingState.warnings) {
                    siteMappingState.warnings.addExtractionError(url, error);
                }

                // Try to close tab if it was created
                if (tab) {
                    try {
                        await chrome.tabs.remove(tab.id);
                    } catch (tabError) {
                        console.warn('[Map] Could not close tab after error:', tabError.message);
                    }
                }
            }
        }

        // Add the start URL to the list if not already there
        if (!urlDataList.some(u => u.url === startUrl)) {
            urlDataList.unshift({ url: startUrl, type: 'internal', level: 0, parent: null });
        }

        // Handle completing state (Complete Now was clicked)
        if (siteMappingState.isCompleting) {
            console.log('[Map] Completing job early at user request...');
            siteMappingState.isCompleting = false; // Reset flag
            // Continue to complete the job below (don't return early)
        }

        // Handle paused state (Bug fix #3)
        if (siteMappingState.isPaused) {
            console.log('[Map] Saving paused job state to IndexedDB...');

            // Save complete job state for resume
            const jobState = {
                discoveredUrls: Array.from(discoveredUrls),
                processedUrls: Array.from(processedUrls),
                urlsToProcess: urlsToProcess,
                urlDataList: urlDataList,
                parentMap: Array.from(siteMappingState.parentMap.entries()),
                startUrl: startUrl,
                depth: depth
            };

            // Update job in IndexedDB with saved state
            const job = await jobStorage.getJob(jobId);
            if (job) {
                // Ensure params object exists
                if (!job.params) {
                    job.params = {};
                }
                job.params.saved_state = jobState;
                job.status = 'paused';
                job.result = {
                    discovered_urls: urlDataList.map(u => u.url),
                    total_discovered: discoveredUrls.size,
                    urlDataList: urlDataList,
                    saved_state: jobState  // Also store in result for consistency
                };

                // Save warnings collected so far
                if (siteMappingState.warnings && siteMappingState.warnings.hasWarnings()) {
                    job.result.warnings = siteMappingState.warnings.exportAsText();
                    job.result.warnings_count = siteMappingState.warnings.count();
                    console.log(`[Map] Saved ${job.result.warnings_count} warnings to paused job`);
                }

                await jobStorage.saveJob(job);
                console.log('[Map] Saved state to IndexedDB with', urlsToProcess.length, 'URLs remaining');
            }

            const warningsMsg = siteMappingState.warnings && siteMappingState.warnings.hasWarnings()
                ? ` (${siteMappingState.warnings.count()} warnings)`
                : '';
            showNotification('Mapping Paused', `Paused at ${discoveredUrls.size} URLs discovered${warningsMsg}`);

            return {
                success: true,
                urls: urlDataList,
                jobId: jobId,
                paused: true
            };
        }

        // Complete the job (only if not paused)
        if (jobId) {
            const allUrls = Array.from(discoveredUrls);
            await fetch(`${apiUrl}/site-map/complete`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    job_id: jobId,
                    discovered_urls: allUrls,
                    url_data_list: urlDataList  // Include full URL data for Load button
                })
            }).catch(err => console.warn('[Map] Failed to complete job:', err));

            // Save completed job to IndexedDB
            const job = await jobStorage.getJob(jobId);
            if (job) {
                job.status = 'completed';
                job.result = {
                    discovered_urls: allUrls,
                    total_discovered: discoveredUrls.size,
                    urlDataList: urlDataList
                };

                // Include warnings if any were collected
                if (siteMappingState.warnings && siteMappingState.warnings.hasWarnings()) {
                    job.result.warnings = siteMappingState.warnings.exportAsText();
                    job.result.warnings_count = siteMappingState.warnings.count();
                    console.log(`[Map] Collected ${job.result.warnings_count} warnings during site mapping`);
                }

                await jobStorage.saveJob(job);
            }
        }

        const warningsMsg = siteMappingState.warnings && siteMappingState.warnings.hasWarnings()
            ? ` (${siteMappingState.warnings.count()} warnings)`
            : '';
        showNotification('Mapping Complete', `Found ${urlDataList.length} URLs (Internal: ${urlDataList.filter(u => u.type === 'internal').length}, External: ${urlDataList.filter(u => u.type === 'external').length}, Media: ${urlDataList.filter(u => u.type === 'media').length})${warningsMsg}`);

        return {
            success: true,
            urls: urlDataList,
            jobId: jobId,
            warnings: siteMappingState.warnings && siteMappingState.warnings.hasWarnings()
                ? siteMappingState.warnings.exportAsText()
                : null
        };
    } catch (error) {
        const errorMsg = jobId ? `Job ${jobId}: ${error.message}` : error.message;
        console.error(`[Map] Site mapping error${jobId ? ` for job ${jobId}` : ''}:`, error);
        showNotification('Mapping Failed', errorMsg);

        // Update job as failed if we have a jobId
        if (jobId) {
            try {
                const job = await jobStorage.getJob(jobId);
                if (job) {
                    job.status = 'failed';
                    job.error = error.message;
                    job.completed_at = new Date().toISOString();
                    await jobStorage.saveJob(job);
                }
            } catch (saveError) {
                console.error('[Map] Failed to save error state:', saveError);
            }
        }

        return {
            success: false,
            error: errorMsg,
            urls: []
        };
    }
}

// Pause a job
async function handlePauseJob(jobId) {
    try {
        console.log('[Job] Pausing job:', jobId);

        // Set local pause flag
        if (siteMappingState.currentJobId === jobId) {
            siteMappingState.isPaused = true;
        }

        // Update backend (if job exists there)
        const storage = await chrome.storage.local.get(['apiEndpoint']);
        const apiUrl = storage.apiEndpoint || 'http://localhost:8077';

        let backendJob = null;
        try {
            const response = await fetch(`${apiUrl}/jobs/${jobId}/pause`, {
                method: 'POST'
            });

            if (response.ok) {
                const result = await response.json();
                backendJob = result.job;
            } else if (response.status === 404) {
                // Job doesn't exist on backend (maybe backend restarted)
                console.warn('[Job] Job not found on backend, updating IndexedDB only');
            } else {
                console.warn('[Job] Backend pause failed:', response.statusText);
            }
        } catch (fetchError) {
            // Backend might be down, continue with local update
            console.warn('[Job] Failed to pause job on backend:', fetchError.message);
        }

        // Save complete job to IndexedDB (Bug fix #3)
        const job = await jobStorage.getJob(jobId);
        if (job) {
            // Update with latest from backend
            job.status = 'paused';
            if (backendJob) {
                job.progress = backendJob.progress || job.progress;
                job.result = backendJob.result || job.result;
            }
            await jobStorage.saveJob(job);
        } else if (backendJob) {
            // If not in IndexedDB, save the one from backend
            await jobStorage.saveJob(backendJob);
        }

        console.log('[Job] Job paused successfully and saved to IndexedDB');
        return { success: true, message: 'Job paused', job: backendJob };

    } catch (error) {
        console.error(`[Job] Failed to pause job ${jobId}:`, error);
        return { success: false, error: `Failed to pause job ${jobId}: ${error.message}` };
    }
}

// Resume a job
async function handleResumeJob(jobId) {
    try {
        console.log('[Job] Resuming job:', jobId);

        // Get job from IndexedDB to retrieve saved state
        const job = await jobStorage.getJob(jobId);
        if (!job) {
            throw new Error(`Job ${jobId} not found in IndexedDB`);
        }

        // Clear local pause flag
        siteMappingState.currentJobId = jobId;
        siteMappingState.isPaused = false;

        // Update backend
        const storage = await chrome.storage.local.get(['apiEndpoint']);
        const apiUrl = storage.apiEndpoint || 'http://localhost:8077';

        const response = await fetch(`${apiUrl}/jobs/${jobId}/resume`, {
            method: 'POST'
        });

        if (!response.ok) {
            throw new Error(`Failed to resume job: ${response.statusText}`);
        }

        const result = await response.json();

        // Save to IndexedDB
        await jobStorage.updateJobStatus(jobId, 'processing');

        console.log('[Job] Job resumed successfully');

        // Continue site mapping from saved state (Bug fix: check both params and result)
        const savedState = (job.params && job.params.saved_state) || (job.result && job.result.saved_state);

        if (job.type === 'site_map' && savedState) {
            console.log('[Job] Continuing site mapping from saved state...');
            console.log('[Job] URLs to process:', savedState.urlsToProcess?.length || 0);
            await continueSiteMapping(jobId, savedState);
        } else {
            console.warn('[Job] No saved_state found for job resume');
            console.warn('[Job] Job type:', job.type);
            console.warn('[Job] Has params.saved_state:', !!(job.params && job.params.saved_state));
            console.warn('[Job] Has result.saved_state:', !!(job.result && job.result.saved_state));
        }

        return { success: true, message: 'Job resumed', job: result.job };

    } catch (error) {
        console.error(`[Job] Failed to resume job ${jobId}:`, error);
        return { success: false, error: `Failed to resume job ${jobId}: ${error.message}` };
    }
}

// Continue site mapping from saved state
async function continueSiteMapping(jobId, savedState) {
    try {
        console.log('[Map] Resuming site mapping with saved state');

        // Restore state
        const discoveredUrls = new Set(savedState.discoveredUrls);
        const processedUrls = new Set(savedState.processedUrls);
        const urlsToProcess = savedState.urlsToProcess;
        const urlDataList = savedState.urlDataList;
        const parentMap = new Map(savedState.parentMap);
        const startUrl = savedState.startUrl;
        const depth = savedState.depth;

        // Update siteMappingState
        siteMappingState.discoveredUrls = discoveredUrls;
        siteMappingState.processedUrls = processedUrls;
        siteMappingState.urlsToProcess = urlsToProcess;
        siteMappingState.urlDataList = urlDataList;
        siteMappingState.parentMap = parentMap;

        // Restore or create warnings tracker for resumed job
        siteMappingState.warnings = new WarningsTracker();
        siteMappingState.warnings.setJobId(jobId);
        console.log('[Map] Initialized warnings tracker for resumed job:', jobId);

        const storage = await chrome.storage.local.get(['apiEndpoint']);
        const apiUrl = storage.apiEndpoint || 'http://localhost:8077';

        console.log(`[Map] Resuming with ${urlsToProcess.length} URLs to process, ${discoveredUrls.size} discovered so far`);

        // Continue processing from where we left off
        while (urlsToProcess.length > 0 && !siteMappingState.isPaused) {
            const { url, level, parent } = urlsToProcess.shift();

            if (processedUrls.has(url) || level > depth) {
                continue;
            }

            // Check for pause
            if (siteMappingState.isPaused) {
                console.log('[Map] Job paused during resume');
                break;
            }

            processedUrls.add(url);

            let tab = null;
            try {
                // Open tab with timeout
                console.log(`[Map Resume] Processing URL ${processedUrls.size}/${urlsToProcess.length + processedUrls.size}: ${url}`);

                tab = await Promise.race([
                    chrome.tabs.create({ url, active: false }),
                    new Promise((_, reject) => setTimeout(() => reject(new Error('Tab creation timeout')), 30000))
                ]);

                // Wait for page load with timeout
                await Promise.race([
                    waitForTabLoad(tab.id),
                    new Promise((_, reject) => setTimeout(() => reject(new Error('Page load timeout')), 30000))
                ]);

                await sleep(1000);

                const pageData = await extractPageData(tab.id);
                const links = await extractLinks(pageData.html, url);

                // Close tab
                try {
                    await chrome.tabs.remove(tab.id);
                    tab = null; // Mark as closed
                } catch (tabError) {
                    console.warn('[Map] Could not close tab:', tabError.message);
                }

                // Process internal links
                if (level < depth) {
                    for (const link of links.internal_links) {
                        if (!discoveredUrls.has(link)) {
                            discoveredUrls.add(link);
                            urlsToProcess.push({ url: link, level: level + 1, parent: url });
                            urlDataList.push({ url: link, type: 'internal', level: level + 1, parent: url });
                            siteMappingState.parentMap.set(link, url);
                        }
                    }
                }

                // Add external links
                for (const link of links.external_links) {
                    if (!discoveredUrls.has(link)) {
                        discoveredUrls.add(link);
                        urlDataList.push({ url: link, type: 'external', level: level + 1, parent: url });
                        siteMappingState.parentMap.set(link, url);
                    }
                }

                // Add media links
                for (const link of links.media_links) {
                    if (!discoveredUrls.has(link)) {
                        discoveredUrls.add(link);
                        urlDataList.push({ url: link, type: 'media', level: level + 1, parent: url });
                        siteMappingState.parentMap.set(link, url);
                    }
                }

                // Update job progress
                if (jobId) {
                    fetch(`${apiUrl}/site-map/progress`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            job_id: jobId,
                            discovered_count: discoveredUrls.size,
                            total_to_process: urlsToProcess.length + processedUrls.size,
                            message: `Discovered ${discoveredUrls.size} URLs (${processedUrls.size} processed)`
                        })
                    }).catch(err => console.warn('[Map] Failed to update progress:', err));
                }
            } catch (error) {
                console.error(`[Map Resume] Error processing ${url}:`, error);

                // Add warning for failed URL processing
                if (siteMappingState.warnings) {
                    siteMappingState.warnings.addExtractionError(url, error);
                }

                // Try to close tab if it was created
                if (tab) {
                    try {
                        await chrome.tabs.remove(tab.id);
                    } catch (tabError) {
                        console.warn('[Map] Could not close tab after error:', tabError.message);
                    }
                }
            }
        }

        // Handle completion or pause
        if (siteMappingState.isPaused) {
            console.log('[Map] Saving paused state after resume...');

            const jobState = {
                discoveredUrls: Array.from(discoveredUrls),
                processedUrls: Array.from(processedUrls),
                urlsToProcess: urlsToProcess,
                urlDataList: urlDataList,
                parentMap: Array.from(siteMappingState.parentMap.entries()),
                startUrl: startUrl,
                depth: depth
            };

            const job = await jobStorage.getJob(jobId);
            if (job) {
                // Ensure params object exists
                if (!job.params) {
                    job.params = {};
                }
                job.params.saved_state = jobState;
                job.status = 'paused';
                job.result = {
                    discovered_urls: urlDataList.map(u => u.url),
                    total_discovered: discoveredUrls.size,
                    urlDataList: urlDataList,
                    saved_state: jobState  // Also store in result for consistency
                };

                // Save warnings collected so far
                if (siteMappingState.warnings && siteMappingState.warnings.hasWarnings()) {
                    job.result.warnings = siteMappingState.warnings.exportAsText();
                    job.result.warnings_count = siteMappingState.warnings.count();
                    console.log(`[Map] Saved ${job.result.warnings_count} warnings to paused job (resume)`);
                }

                await jobStorage.saveJob(job);
                console.log('[Map] Saved state to IndexedDB with', urlsToProcess.length, 'URLs remaining');
            }

            const warningsMsg = siteMappingState.warnings && siteMappingState.warnings.hasWarnings()
                ? ` (${siteMappingState.warnings.count()} warnings)`
                : '';
            showNotification('Mapping Paused', `Paused at ${discoveredUrls.size} URLs discovered${warningsMsg}`);
        } else {
            // Complete the job
            console.log('[Map] Job completed after resume');
            const allUrls = Array.from(discoveredUrls);
            await fetch(`${apiUrl}/site-map/complete`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    job_id: jobId,
                    discovered_urls: allUrls,
                    url_data_list: urlDataList  // Include full URL data for Load button
                })
            }).catch(err => console.warn('[Map] Failed to complete job:', err));

            const job = await jobStorage.getJob(jobId);
            if (job) {
                job.status = 'completed';
                job.result = {
                    discovered_urls: allUrls,
                    total_discovered: discoveredUrls.size,
                    urlDataList: urlDataList
                };

                // Include warnings if any were collected
                if (siteMappingState.warnings && siteMappingState.warnings.hasWarnings()) {
                    job.result.warnings = siteMappingState.warnings.exportAsText();
                    job.result.warnings_count = siteMappingState.warnings.count();
                    console.log(`[Map] Collected ${job.result.warnings_count} warnings during resumed site mapping`);
                }

                // Clear saved state
                if (!job.params) {
                    job.params = {};
                }
                job.params.saved_state = null;
                await jobStorage.saveJob(job);
            }

            const warningsMsg = siteMappingState.warnings && siteMappingState.warnings.hasWarnings()
                ? ` (${siteMappingState.warnings.count()} warnings)`
                : '';
            showNotification('Mapping Complete', `Found ${urlDataList.length} URLs${warningsMsg}`);
        }

    } catch (error) {
        console.error(`[Map] Error continuing site mapping for job ${jobId}:`, error);
        showNotification('Mapping Failed', `Job ${jobId}: ${error.message}`);
    }
}

// Stop a job
async function handleStopJob(jobId) {
    try {
        console.log('[Job] Stopping job:', jobId);

        // Stop local processing
        if (siteMappingState.currentJobId === jobId) {
            siteMappingState.isPaused = true;
            siteMappingState.currentJobId = null;
        }

        // Update backend (if job exists there)
        const storage = await chrome.storage.local.get(['apiEndpoint']);
        const apiUrl = storage.apiEndpoint || 'http://localhost:8077';

        let backendJob = null;
        try {
            const response = await fetch(`${apiUrl}/jobs/${jobId}/stop`, {
                method: 'POST'
            });

            if (response.ok) {
                const result = await response.json();
                backendJob = result.job;
            } else if (response.status === 404) {
                // Job doesn't exist on backend (maybe backend restarted)
                console.warn('[Job] Job not found on backend, updating IndexedDB only');
            } else {
                console.warn('[Job] Backend stop failed:', response.statusText);
            }
        } catch (fetchError) {
            // Backend might be down, continue with local update
            console.warn('[Job] Failed to stop job on backend:', fetchError.message);
        }

        // Always update IndexedDB (stopped jobs are paused)
        await jobStorage.updateJobStatus(jobId, 'paused');

        console.log('[Job] Job stopped successfully');
        return { success: true, message: 'Job stopped. Discovered data preserved.', job: backendJob };

    } catch (error) {
        console.error(`[Job] Failed to stop job ${jobId}:`, error);
        return { success: false, error: `Failed to stop job ${jobId}: ${error.message}` };
    }
}

// Complete a job now (gracefully finish current URL and complete)
async function handleCompleteNowJob(jobId) {
    try {
        console.log('[Job] Completing job now:', jobId);

        // Set the completing flag to finish after current URL
        if (siteMappingState.currentJobId === jobId) {
            siteMappingState.isCompleting = true;
            console.log('[Job] Set isCompleting flag - will complete after current URL');
            showNotification('Completing Job', 'Will finish after current URL...');
        } else {
            // Job might be on backend only, not actively mapping
            console.warn('[Job] Job is not actively running in background worker');

            // Mark as completed on backend
            const storage = await chrome.storage.local.get(['apiEndpoint']);
            const apiUrl = storage.apiEndpoint || 'http://localhost:8077';

            try {
                const response = await fetch(`${apiUrl}/jobs/${jobId}/complete`, {
                    method: 'POST'
                });

                if (response.ok) {
                    const result = await response.json();
                    showNotification('Job Completed', 'Job marked as complete');
                    return { success: true, message: 'Job completed', job: result.job };
                }
            } catch (backendError) {
                console.warn('[Job] Could not complete on backend:', backendError.message);
            }
        }

        // The actual completion will happen in the mapping loop when it checks isCompleting
        return { success: true, message: 'Job will complete after current URL' };

    } catch (error) {
        console.error(`[Job] Failed to complete job ${jobId}:`, error);
        return { success: false, error: `Failed to complete job ${jobId}: ${error.message}` };
    }
}

// Extract multiple pages
async function handleExtractMultiplePages(urls, outputZip, mergeIntoSingle = false) {
    // Check backend health first
    const health = await checkBackendHealth();
    if (!health.healthy) {
        showNotification('Backend Error', health.error);
        return {
            success: false,
            error: health.error
        };
    }

    showNotification('Batch Extraction', `Processing ${urls.length} pages...`);

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

                // Add source URL to result for merged output
                result.sourceUrl = url;
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
        if (mergeIntoSingle) {
            // Merge all markdown content into single file
            const mergedContent = createMergedMarkdown(results, Array.from(allMediaUrls));
            const timestamp = new Date().toISOString().replace(/[:.]/g, '-').split('T')[0];
            const mergedFilename = `merged_pages_${results.length}_${timestamp}.md`;

            if (outputZip) {
                // Create ZIP with single merged file
                await createAndDownloadZip([{ markdown: mergedContent, filename: mergedFilename }], Array.from(allMediaUrls));
                showNotification('Batch Extraction Complete', `Merged ${results.length} pages into single file in ZIP`);
            } else {
                // Download single merged file
                await downloadFile(mergedContent, mergedFilename);
                // Download media links file
                if (allMediaUrls.size > 0) {
                    const mediaContent = Array.from(allMediaUrls).join('\n');
                    await downloadFile(mediaContent, 'media_links.txt');
                }
                showNotification('Batch Extraction Complete', `Merged ${results.length} pages into single file`);
            }
        } else {
            // Original behavior: individual files or ZIP with multiple files
            if (outputZip) {
                // Create ZIP file
                await createAndDownloadZip(results, Array.from(allMediaUrls));
                showNotification('Batch Extraction Complete', `Extracted ${results.length} pages into ZIP file`);
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

                showNotification('Batch Extraction Complete', `Extracted ${results.length} pages as individual files`);
            }
        }

        return {
            success: true,
            processed: results.length
        };
    } catch (error) {
        console.error('Extract multiple pages error:', error);
        showNotification('Batch Extraction Failed', error.message);
        return {
            success: false,
            error: error.message
        };
    }
}

// Create merged markdown from multiple results
function createMergedMarkdown(results, mediaUrls) {
    const timestamp = new Date().toISOString();
    const parts = [];

    // Add header
    parts.push(`# Merged Page Extraction\n`);
    parts.push(`**Extracted:** ${timestamp}`);
    parts.push(`**Total Pages:** ${results.length}\n`);
    parts.push(`---\n`);

    // Add table of contents
    parts.push(`## Table of Contents\n`);
    results.forEach((result, index) => {
        const anchor = `page-${index + 1}`;
        const title = result.filename.replace('.md', '');
        parts.push(`${index + 1}. [${title}](#${anchor})`);
    });
    parts.push(`\n---\n`);

    // Add each page's content
    results.forEach((result, index) => {
        const anchor = `page-${index + 1}`;
        parts.push(`\n## <a name="${anchor}"></a>Page ${index + 1}: ${result.filename.replace('.md', '')}\n`);
        if (result.sourceUrl) {
            parts.push(`**Source:** ${result.sourceUrl}`);
        }
        parts.push(`**Words:** ${result.word_count || 'N/A'}`);
        parts.push(`**AI Used:** ${result.used_ai ? 'Yes' : 'No'}\n`);
        parts.push(result.markdown);
        parts.push(`\n---\n`);
    });

    // Add media links section if any
    if (mediaUrls.length > 0) {
        parts.push(`\n## Media Links\n`);
        parts.push(`Total media files found: ${mediaUrls.length}\n`);
        mediaUrls.forEach(url => {
            parts.push(`- ${url}`);
        });
    }

    return parts.join('\n');
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

// Check if backend is running (with retry and user notification)
async function checkBackendHealth() {
    try {
        // Try with retry logic
        await retryWithBackoff(async () => {
            const storage = await chrome.storage.local.get(['apiEndpoint']);
            const apiUrl = storage.apiEndpoint || API_BASE_URL;

            const response = await fetch(`${apiUrl}/`, {
                method: 'GET',
                signal: AbortSignal.timeout(5000)
            });

            if (!response.ok) {
                throw new Error('Backend responded with error');
            }

            const data = await response.json();

            // Update connection state
            connectionState.isConnected = true;
            connectionState.lastSuccessfulPing = Date.now();
            connectionState.consecutiveFailures = 0;
            connectionState.aiEnabled = data.ai_enabled;

            return data;
        }, 'Backend Health Check', 2); // Only 2 retries for interactive operations

        return { healthy: true, aiEnabled: connectionState.aiEnabled };
    } catch (error) {
        console.error('[Backend] Health check failed after retries:', error);

        // Update connection state
        connectionState.isConnected = false;

        return {
            healthy: false,
            error: 'Backend server is not responding. Please ensure the backend is running.\n\nRun: python launcher.py\nor: SimplePageSaver.exe'
        };
    }
}

// Process HTML with backend (with retry logic)
async function processWithBackend(url, html, title) {
    // Get API URL, AI setting, custom prompt, and extraction mode from chrome.storage
    const storage = await chrome.storage.local.get(['apiEndpoint', 'enableAI', 'customPrompt', 'extractionMode']);
    const apiUrl = storage.apiEndpoint || API_BASE_URL;
    const enableAI = storage.enableAI ?? false; // Default to false (use fallback)
    const customPrompt = storage.customPrompt || '';
    const extractionMode = storage.extractionMode || 'balanced'; // Default to balanced

    console.log('[Backend] Using API URL:', apiUrl);
    console.log('[Backend] Storage values:', storage);
    console.log('[Backend] AI enabled:', enableAI);
    console.log('[Backend] Extraction mode:', extractionMode);
    if (customPrompt) {
        console.log('[Backend] Custom prompt:', customPrompt.substring(0, 100) + '...');
    }

    // Extra logging for AI setting to help debug
    if (!enableAI) {
        console.log('[Backend] ⚠️ AI is DISABLED - sending use_ai: false to backend');
    } else {
        console.log('[Backend] ⚠️ AI is ENABLED - sending use_ai: true to backend (will incur costs)');
    }

    console.log('[Backend] Sending request to /process-html');

    // Wrap fetch in retry logic
    return await retryWithBackoff(async () => {
        try {
            const response = await fetch(`${apiUrl}/process-html`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    url,
                    html,
                    title,
                    use_ai: enableAI,
                    custom_prompt: customPrompt,
                    extraction_mode: extractionMode
                }),
                signal: AbortSignal.timeout(120000) // 120 second timeout for large pages
            });

            console.log('[Backend] Response status:', response.status);

            if (!response.ok) {
                const errorText = await response.text();
                console.error('[Backend] Error response:', errorText);
                throw new Error(`Backend error: ${response.status} ${response.statusText}`);
            }

            const result = await response.json();

            // Update connection state on success
            connectionState.isConnected = true;
            connectionState.lastSuccessfulPing = Date.now();

            return result;
        } catch (error) {
            // Mark connection as potentially unhealthy
            if (error.name === 'TypeError' && error.message.includes('fetch')) {
                connectionState.isConnected = false;
            }

            if (error.name === 'TimeoutError') {
                throw new Error('Backend request timed out. The page may be too large.');
            } else if (error.name === 'TypeError' && error.message.includes('fetch')) {
                throw new Error('Cannot connect to backend server. Retrying...');
            }
            throw error;
        }
    }, 'Process HTML', 3); // 3 retries for processing
}

// Extract links using backend (with retry logic)
async function extractLinks(html, baseUrl) {
    // Get API URL from chrome.storage (service workers can't use localStorage)
    const storage = await chrome.storage.local.get(['apiEndpoint']);
    const apiUrl = storage.apiEndpoint || API_BASE_URL;

    console.log('[Backend] Extracting links from:', baseUrl);

    // Wrap fetch in retry logic
    return await retryWithBackoff(async () => {
        const response = await fetch(`${apiUrl}/extract-links`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ html, base_url: baseUrl }),
            signal: AbortSignal.timeout(30000) // 30 second timeout for link extraction
        });

        if (!response.ok) {
            const errorText = await response.text();
            console.error('[Backend] Link extraction error:', errorText);
            throw new Error(`Backend error: ${response.status}`);
        }

        const result = await response.json();

        // Update connection state on success
        connectionState.isConnected = true;
        connectionState.lastSuccessfulPing = Date.now();

        return result;
    }, 'Extract Links', 3); // 3 retries for link extraction
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

// Generate PDF using Chrome DevTools Protocol
async function generatePdfUsingCDP(tabId, title) {
    let debuggee = { tabId: tabId };

    try {
        // Attach debugger
        console.log('[CDP] Attaching debugger to tab:', tabId);
        await chrome.debugger.attach(debuggee, '1.3');

        // A0 paper dimensions in inches (33.1 x 46.8 inches)
        // Chrome uses inches for paper dimensions
        const pdfOptions = {
            printBackground: false,        // Don't print backgrounds
            paperWidth: 33.1,             // A0 width in inches
            paperHeight: 46.8,            // A0 height in inches
            marginTop: 0.2,               // 0.5cm ≈ 0.2 inches
            marginBottom: 0.2,
            marginLeft: 0.2,
            marginRight: 0.2,
            scale: 1.0,                   // 100% scale
            displayHeaderFooter: false,   // No header/footer
            preferCSSPageSize: true,      // Use CSS @page size if specified
            generateTaggedPDF: false,     // Faster generation
            transferMode: 'ReturnAsBase64'
        };

        console.log('[CDP] Sending Page.printToPDF command with options:', pdfOptions);

        // Send printToPDF command
        const result = await chrome.debugger.sendCommand(
            debuggee,
            'Page.printToPDF',
            pdfOptions
        );

        if (result && result.data) {
            console.log('[CDP] PDF data received, converting from base64...');
            // Convert base64 to Uint8Array
            const binaryString = atob(result.data);
            const bytes = new Uint8Array(binaryString.length);
            for (let i = 0; i < binaryString.length; i++) {
                bytes[i] = binaryString.charCodeAt(i);
            }
            return bytes.buffer;
        } else {
            throw new Error('No PDF data returned from Chrome DevTools Protocol');
        }

    } catch (error) {
        console.error('[CDP] Error generating PDF:', error);
        throw error;
    } finally {
        // Always detach debugger
        try {
            await chrome.debugger.detach(debuggee);
            console.log('[CDP] Debugger detached');
        } catch (detachError) {
            console.warn('[CDP] Failed to detach debugger:', detachError);
        }
    }
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
