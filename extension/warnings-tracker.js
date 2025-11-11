// Warnings Tracker - Collects warnings during extraction process

class WarningsTracker {
    constructor() {
        this.warnings = [];
        this.jobId = null;
    }

    /**
     * Set job ID for tracking
     */
    setJobId(jobId) {
        this.jobId = jobId;
    }

    /**
     * Add a warning message
     * @param {string} category - Warning category (e.g., 'screenshot', 'extraction', 'links')
     * @param {string} message - Warning message
     * @param {object} details - Additional details
     */
    add(category, message, details = {}) {
        const warning = {
            timestamp: new Date().toISOString(),
            category,
            message,
            details,
            jobId: this.jobId
        };

        this.warnings.push(warning);
        console.warn(`[Warning:${category}]`, message, details);
    }

    /**
     * Add infinite scroll warning
     */
    addInfiniteScrollWarning(url, confidence = 'medium') {
        this.add(
            'infinite-scroll',
            `Page may have infinite scroll: ${url}`,
            {
                url,
                confidence,
                impact: 'Screenshot may not capture all content that loads dynamically when scrolling.'
            }
        );
    }

    /**
     * Add screenshot crop warning
     */
    addCropWarning(dimensions, maxDimension) {
        this.add(
            'screenshot',
            `Screenshot was cropped due to size limits`,
            {
                original: dimensions,
                max: maxDimension,
                impact: 'Some content may be missing from the screenshot.'
            }
        );
    }

    /**
     * Add screenshot failure warning
     */
    addScreenshotFailure(url, error) {
        this.add(
            'screenshot',
            `Failed to capture screenshot for: ${url}`,
            {
                url,
                error: error.message,
                suggestion: 'Try restarting your browser or checking if another debugger is attached.'
            }
        );
    }

    /**
     * Add extraction error warning
     */
    addExtractionError(url, error) {
        this.add(
            'extraction',
            `Failed to extract content from: ${url}`,
            {
                url,
                error: error.message
            }
        );
    }

    /**
     * Add link extraction warning
     */
    addLinkWarning(message, details = {}) {
        this.add('links', message, details);
    }

    /**
     * Add generic warning
     */
    addGeneric(category, message, details = {}) {
        this.add(category, message, details);
    }

    /**
     * Get all warnings
     */
    getAll() {
        return this.warnings;
    }

    /**
     * Get warnings by category
     */
    getByCategory(category) {
        return this.warnings.filter(w => w.category === category);
    }

    /**
     * Check if there are any warnings
     */
    hasWarnings() {
        return this.warnings.length > 0;
    }

    /**
     * Get warning count
     */
    count() {
        return this.warnings.length;
    }

    /**
     * Clear all warnings
     */
    clear() {
        this.warnings = [];
    }

    /**
     * Export warnings as formatted text for warnings.txt file
     */
    exportAsText() {
        if (this.warnings.length === 0) {
            return null;
        }

        const lines = [
            '='.repeat(80),
            'WARNINGS AND ISSUES ENCOUNTERED DURING EXTRACTION',
            '='.repeat(80),
            '',
            `Total Warnings: ${this.warnings.length}`,
            `Generated: ${new Date().toISOString()}`,
            ''
        ];

        // Group by category
        const byCategory = {};
        for (const warning of this.warnings) {
            if (!byCategory[warning.category]) {
                byCategory[warning.category] = [];
            }
            byCategory[warning.category].push(warning);
        }

        // Format each category
        for (const [category, warnings] of Object.entries(byCategory)) {
            lines.push('');
            lines.push('-'.repeat(80));
            lines.push(`${category.toUpperCase()} (${warnings.length} warning${warnings.length !== 1 ? 's' : ''})`);
            lines.push('-'.repeat(80));
            lines.push('');

            for (let i = 0; i < warnings.length; i++) {
                const w = warnings[i];
                lines.push(`${i + 1}. ${w.message}`);
                lines.push(`   Time: ${w.timestamp}`);

                if (Object.keys(w.details).length > 0) {
                    lines.push('   Details:');
                    for (const [key, value] of Object.entries(w.details)) {
                        const valueStr = typeof value === 'object' ? JSON.stringify(value) : value;
                        lines.push(`     - ${key}: ${valueStr}`);
                    }
                }
                lines.push('');
            }
        }

        lines.push('');
        lines.push('='.repeat(80));
        lines.push('END OF WARNINGS');
        lines.push('='.repeat(80));

        return lines.join('\n');
    }

    /**
     * Export warnings as JSON
     */
    exportAsJSON() {
        return JSON.stringify({
            count: this.warnings.length,
            generated: new Date().toISOString(),
            jobId: this.jobId,
            warnings: this.warnings
        }, null, 2);
    }
}

// Export for use in background.js
if (typeof module !== 'undefined' && module.exports) {
    module.exports = WarningsTracker;
}
