// Offscreen document script for image processing
// This runs in a document context where DOM APIs (Image, canvas) are available

console.log('[Offscreen] Offscreen document loaded');

// Listen for messages from background script
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === 'PROCESS_SCREENSHOT') {
        console.log('[Offscreen] Processing screenshot...');

        processScreenshot(
            request.dataUrl,
            request.preserveColor,
            request.format,
            request.quality
        )
            .then(result => {
                console.log('[Offscreen] Screenshot processed successfully');
                sendResponse({ success: true, result });
            })
            .catch(error => {
                console.error('[Offscreen] Screenshot processing failed:', error);
                sendResponse({ success: false, error: error.message });
            });

        return true; // Keep message channel open for async response
    }
});

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
                const canvas = document.getElementById('canvas');
                canvas.width = img.width;
                canvas.height = img.height;
                const ctx = canvas.getContext('2d');

                // Draw original image
                ctx.drawImage(img, 0, 0);

                // Apply B&W conversion if needed
                if (!preserveColor) {
                    console.log('[Offscreen] Converting to true black & white...');
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

                console.log(`[Offscreen] Converted to ${outputFormat} (quality: ${quality})`);

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
