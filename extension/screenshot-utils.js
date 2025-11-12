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
        quality = 85
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

            // Get layout metrics to determine page size
            const { contentSize, visualViewport } = await chrome.debugger.sendCommand(
                { tabId },
                'Page.getLayoutMetrics'
            );

            let pageWidth = contentSize.width;
            let pageHeight = contentSize.height;

            console.log(`[Screenshot] Page dimensions: ${pageWidth}x${pageHeight}`);

            // CDP maximum dimension limit
            const MAX_DIMENSION = 16384;

            // Check if page exceeds limits and auto-crop
            if (pageHeight > MAX_DIMENSION) {
                warnings.push(
                    `Page height (${pageHeight}px) exceeds maximum screenshot limit (${MAX_DIMENSION}px). ` +
                    `Screenshot has been cropped to maximum height. Some content at the bottom may be missing.`
                );
                pageHeight = MAX_DIMENSION;
                console.warn('[Screenshot] Page height cropped to', MAX_DIMENSION);
            }

            if (pageWidth > MAX_DIMENSION) {
                warnings.push(
                    `Page width (${pageWidth}px) exceeds maximum screenshot limit (${MAX_DIMENSION}px). ` +
                    `Screenshot has been cropped to maximum width. Some content on the right may be missing.`
                );
                pageWidth = MAX_DIMENSION;
                console.warn('[Screenshot] Page width cropped to', MAX_DIMENSION);
            }

            // Capture screenshot using CDP
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
                        scale: 1
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
 * Process screenshot: convert to B&W (if needed) and target format
 * @param {string} dataUrl - Original screenshot data URL
 * @param {boolean} preserveColor - Whether to keep color
 * @param {string} format - Target format (jpeg/webp)
 * @param {number} quality - Image quality (0-100)
 * @returns {Promise<{dataUrl: string, format: string}>}
 */
async function processScreenshot(dataUrl, preserveColor, format, quality) {
    return new Promise((resolve, reject) => {
        const img = new Image();

        img.onload = () => {
            try {
                // Create canvas
                const canvas = document.createElement('canvas');
                canvas.width = img.width;
                canvas.height = img.height;
                const ctx = canvas.getContext('2d');

                // Draw original image
                ctx.drawImage(img, 0, 0);

                // Apply B&W conversion if needed
                if (!preserveColor) {
                    console.log('[Screenshot] Converting to true black & white...');
                    convertToBlackAndWhite(ctx, canvas.width, canvas.height);
                }

                // Convert to target format
                let outputFormat = 'image/jpeg';
                let outputQuality = quality / 100;

                if (format === 'webp') {
                    outputFormat = 'image/webp';
                } else if (format === 'png') {
                    outputFormat = 'image/png';
                    outputQuality = undefined; // PNG ignores quality
                }

                const outputDataUrl = canvas.toDataURL(outputFormat, outputQuality);

                console.log(`[Screenshot] Converted to ${outputFormat} (quality: ${quality})`);

                resolve({
                    dataUrl: outputDataUrl,
                    format: format
                });

            } catch (error) {
                reject(error);
            }
        };

        img.onerror = () => {
            reject(new Error('Failed to load screenshot image'));
        };

        img.src = dataUrl;
    });
}

/**
 * Convert canvas to true black and white (no grayscale)
 * Uses threshold-based binarization
 * @param {CanvasRenderingContext2D} ctx - Canvas context
 * @param {number} width - Canvas width
 * @param {number} height - Canvas height
 */
function convertToBlackAndWhite(ctx, width, height) {
    const imageData = ctx.getImageData(0, 0, width, height);
    const data = imageData.data;

    // Threshold value (0-255) - pixels lighter than this become white, darker become black
    const threshold = 128;

    for (let i = 0; i < data.length; i += 4) {
        // Calculate grayscale value using luminosity method (weighted RGB)
        // This gives better perceived brightness than simple averaging
        const gray = 0.299 * data[i] + 0.587 * data[i + 1] + 0.114 * data[i + 2];

        // Apply threshold: convert to pure black or pure white
        const bw = gray > threshold ? 255 : 0;

        // Set R, G, B to same value (black or white)
        data[i] = bw;       // Red
        data[i + 1] = bw;   // Green
        data[i + 2] = bw;   // Blue
        // Alpha channel (data[i + 3]) remains unchanged
    }

    ctx.putImageData(imageData, 0, 0);
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
