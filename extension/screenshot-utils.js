// Screenshot Capture Utilities using Chrome DevTools Protocol (CDP)

/**
 * Captures a full-page screenshot using CDP
 * @param {number} tabId - The tab to capture
 * @param {object} options - Screenshot options
 * @returns {Promise<{dataUrl: string, warnings: string[]}>}
 */
async function captureFullPageScreenshot(tabId, options = {}) {
    const {
        preserveColor = false,
        format = 'jpeg',
        quality = 95
    } = options;

    const warnings = [];

    try {
        console.log('[Screenshot] Starting CDP capture for tab:', tabId);

        // Attach debugger
        try {
            await chrome.debugger.attach({ tabId }, '1.3');
            console.log('[Screenshot] Debugger attached');
        } catch (error) {
            if (error.message.includes('Another debugger')) {
                throw new Error('Another debugger is already attached. Please close DevTools and try again.');
            }
            throw error;
        }

        try {
            // Enable Page domain
            await chrome.debugger.sendCommand({ tabId }, 'Page.enable');

            // Get devicePixelRatio from the page for native resolution capture
            const devicePixelRatioResult = await chrome.scripting.executeScript({
                target: { tabId },
                func: () => window.devicePixelRatio || 1
            });
            const devicePixelRatio = devicePixelRatioResult[0].result;
            console.log(`[Screenshot] Device pixel ratio: ${devicePixelRatio}`);

            // Get layout metrics to determine page size
            const { contentSize, visualViewport } = await chrome.debugger.sendCommand(
                { tabId },
                'Page.getLayoutMetrics'
            );

            let pageWidth = contentSize.width;
            let pageHeight = contentSize.height;

            console.log(`[Screenshot] Page dimensions (CSS pixels): ${pageWidth}x${pageHeight}`);
            console.log(`[Screenshot] Physical dimensions (device pixels): ${Math.round(pageWidth * devicePixelRatio)}x${Math.round(pageHeight * devicePixelRatio)}`);

            // CDP maximum dimension limit (in device pixels after scaling)
            const MAX_DIMENSION = 16384;

            // Calculate physical dimensions
            let physicalWidth = Math.round(pageWidth * devicePixelRatio);
            let physicalHeight = Math.round(pageHeight * devicePixelRatio);

            // Check if physical dimensions exceed limits and scale down
            if (physicalHeight > MAX_DIMENSION) {
                const scaleFactor = MAX_DIMENSION / physicalHeight;
                pageHeight = Math.floor(pageHeight * scaleFactor);
                physicalHeight = MAX_DIMENSION;
                warnings.push(
                    `Page height (${Math.round(contentSize.height * devicePixelRatio)}px at ${devicePixelRatio}x) exceeds maximum screenshot limit (${MAX_DIMENSION}px). ` +
                    `Screenshot has been scaled down. Some content at the bottom may be cut off.`
                );
                console.warn('[Screenshot] Page height scaled down to fit', MAX_DIMENSION);
            }

            if (physicalWidth > MAX_DIMENSION) {
                const scaleFactor = MAX_DIMENSION / physicalWidth;
                pageWidth = Math.floor(pageWidth * scaleFactor);
                physicalWidth = MAX_DIMENSION;
                warnings.push(
                    `Page width (${Math.round(contentSize.width * devicePixelRatio)}px at ${devicePixelRatio}x) exceeds maximum screenshot limit (${MAX_DIMENSION}px). ` +
                    `Screenshot has been scaled down. Some content on the right may be cut off.`
                );
                console.warn('[Screenshot] Page width scaled down to fit', MAX_DIMENSION);
            }

            // Capture screenshot using CDP with native device pixel ratio for sharp text
            const screenshot = await chrome.debugger.sendCommand(
                { tabId },
                'Page.captureScreenshot',
                {
                    format: 'png', // Always capture as PNG for maximum quality
                    captureBeyondViewport: true,
                    clip: {
                        x: 0,
                        y: 0,
                        width: pageWidth,
                        height: pageHeight,
                        scale: devicePixelRatio  // Use device pixel ratio for native resolution
                    }
                }
            );

            console.log('[Screenshot] Raw screenshot captured');

            // Convert base64 to data URL
            let dataUrl = `data:image/png;base64,${screenshot.data}`;

            // Process image (convert to B&W or color, and convert to target format)
            const processedImage = await processScreenshot(
                dataUrl,
                preserveColor,
                format,
                quality
            );

            console.log('[Screenshot] Image processed successfully');

            return {
                dataUrl: processedImage.dataUrl,
                format: processedImage.format,
                warnings
            };

        } finally {
            // Always detach debugger
            try {
                await chrome.debugger.detach({ tabId });
                console.log('[Screenshot] Debugger detached');
            } catch (e) {
                console.warn('[Screenshot] Error detaching debugger:', e);
            }
        }

    } catch (error) {
        console.error('[Screenshot] Capture failed:', error);
        throw new Error(`Screenshot capture failed: ${error.message}`);
    }
}

/**
 * Ensure offscreen document is created for image processing
 * Service workers don't have access to DOM APIs, so we need an offscreen document
 */
async function ensureOffscreenDocument() {
    // Check if offscreen document already exists
    const existingContexts = await chrome.runtime.getContexts({
        contextTypes: ['OFFSCREEN_DOCUMENT']
    });

    if (existingContexts.length > 0) {
        return; // Offscreen document already exists
    }

    // Create offscreen document
    await chrome.offscreen.createDocument({
        url: 'offscreen.html',
        reasons: ['DOM_SCRAPING'], // Closest reason for canvas operations
        justification: 'Convert screenshots to black & white and compress to WebP format'
    });

    console.log('[Screenshot] Offscreen document created');
}

/**
 * Process screenshot: convert to B&W (if needed) and target format
 * @param {string} dataUrl - Original screenshot data URL
 * @param {boolean} preserveColor - Whether to keep color
 * @param {string} format - Target format (jpeg/webp)
 * @param {number} quality - Image quality (0-100)
 * @returns {Promise<{dataUrl: string, format: string}>}
 */
async function processScreenshot(dataUrl, preserveColor, format, quality) {
    // Ensure offscreen document exists for image processing
    await ensureOffscreenDocument();

    // Send processing request to offscreen document
    return new Promise((resolve, reject) => {
        chrome.runtime.sendMessage({
            action: 'PROCESS_SCREENSHOT',
            dataUrl,
            preserveColor,
            format,
            quality
        }, (response) => {
            if (chrome.runtime.lastError) {
                reject(new Error(chrome.runtime.lastError.message));
                return;
            }

            if (response.success) {
                resolve(response.result);
            } else {
                reject(new Error(response.error || 'Screenshot processing failed'));
            }
        });
    });
}

/**
 * Detect if page has infinite scroll
 * @param {number} tabId - Tab to check
 * @returns {Promise<{hasInfiniteScroll: boolean, confidence: string}>}
 */
async function detectInfiniteScroll(tabId) {
    try {
        console.log('[InfiniteScroll] Starting detection...');

        // Inject detection script into page
        const results = await chrome.scripting.executeScript({
            target: { tabId },
            func: async () => {
                return new Promise((resolve) => {
                    // Save initial scroll height
                    const initialHeight = document.documentElement.scrollHeight;
                    const initialChildCount = document.body.childElementCount;

                    console.log('[InfiniteScroll] Initial height:', initialHeight);

                    // Scroll to bottom
                    window.scrollTo(0, document.documentElement.scrollHeight);

                    let mutationDetected = false;
                    let contentAdded = false;

                    // Set up MutationObserver to detect new content
                    const observer = new MutationObserver((mutations) => {
                        for (const mutation of mutations) {
                            if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
                                // Filter out trivial additions (script tags, etc.)
                                const substantialAdditions = Array.from(mutation.addedNodes).some(
                                    node => node.nodeType === Node.ELEMENT_NODE &&
                                            !['SCRIPT', 'STYLE', 'LINK'].includes(node.tagName)
                                );
                                if (substantialAdditions) {
                                    mutationDetected = true;
                                    console.log('[InfiniteScroll] New content detected via MutationObserver');
                                }
                            }
                        }
                    });

                    // Observe the body for child additions
                    observer.observe(document.body, {
                        childList: true,
                        subtree: true
                    });

                    // Wait 2 seconds for content to load
                    setTimeout(() => {
                        observer.disconnect();

                        const finalHeight = document.documentElement.scrollHeight;
                        const finalChildCount = document.body.childElementCount;

                        console.log('[InfiniteScroll] Final height:', finalHeight);
                        console.log('[InfiniteScroll] Mutation detected:', mutationDetected);

                        // Check multiple indicators
                        const heightIncreased = finalHeight > initialHeight;
                        const childrenAdded = finalChildCount > initialChildCount;

                        contentAdded = heightIncreased || childrenAdded || mutationDetected;

                        // Scroll back to top
                        window.scrollTo(0, 0);

                        // Determine confidence level
                        let confidence = 'none';
                        if (contentAdded) {
                            // High confidence if multiple indicators
                            if ((heightIncreased ? 1 : 0) + (childrenAdded ? 1 : 0) + (mutationDetected ? 1 : 0) >= 2) {
                                confidence = 'high';
                            } else {
                                confidence = 'medium';
                            }
                        }

                        resolve({
                            hasInfiniteScroll: contentAdded,
                            confidence,
                            details: {
                                heightIncreased,
                                childrenAdded,
                                mutationDetected,
                                initialHeight,
                                finalHeight
                            }
                        });
                    }, 2000);
                });
            }
        });

        const result = results[0].result;
        console.log('[InfiniteScroll] Detection result:', result);

        return result;

    } catch (error) {
        console.error('[InfiniteScroll] Detection failed:', error);
        return {
            hasInfiniteScroll: false,
            confidence: 'error',
            error: error.message
        };
    }
}

// Export functions for use in background.js
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        captureFullPageScreenshot,
        detectInfiniteScroll,
        processScreenshot,
        convertToBlackAndWhite
    };
}
