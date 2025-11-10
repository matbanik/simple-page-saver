// Popup UI Logic for Simple Page Saver

let discoveredUrls = [];
let currentTab = null;

console.log('[Popup] Script loaded');

// Initialize popup
document.addEventListener('DOMContentLoaded', async () => {
    console.log('[Popup] DOM loaded, initializing...');

    // Get current tab
    const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
    currentTab = tabs[0];
    console.log('[Popup] Current tab:', currentTab?.url);

    // Check connection state
    updateConnectionStatus();

    // Load and display jobs
    loadJobs();

    // Set up event listeners
    document.getElementById('refresh-jobs').addEventListener('click', loadJobs);
    document.getElementById('extract-current').addEventListener('click', extractCurrentPage);
    document.getElementById('map-site').addEventListener('click', mapSite);
    document.getElementById('extract-selected').addEventListener('click', extractSelectedPages);
    document.getElementById('settings-link').addEventListener('click', showSettings);

    // Search box filter
    document.getElementById('search-box').addEventListener('input', filterUrls);

    // Link type filters
    document.getElementById('filter-internal').addEventListener('change', filterUrls);
    document.getElementById('filter-external').addEventListener('change', filterUrls);
    document.getElementById('filter-media').addEventListener('change', filterUrls);

    // Listen for progress updates
    chrome.runtime.onMessage.addListener((message) => {
        if (message.type === 'PROGRESS_UPDATE') {
            updateProgress(message.current, message.total, message.status);
        }
    });

    // Test button listeners
    document.getElementById('toggle-tests').addEventListener('click', toggleTests);
    document.getElementById('test-backend').addEventListener('click', testBackend);
    document.getElementById('test-ai').addEventListener('click', testAI);
    document.getElementById('test-fallback').addEventListener('click', testFallback);

    // AI toggle listener
    document.getElementById('enable-ai').addEventListener('change', handleAIToggle);

    // Prompt preset listener
    document.getElementById('prompt-presets').addEventListener('change', loadPromptPreset);

    // Custom prompt change listener - save to storage
    document.getElementById('custom-prompt').addEventListener('change', async (e) => {
        await chrome.storage.local.set({ customPrompt: e.target.value });
        console.log('[Prompt] Custom prompt saved');
    });

    // Load AI enabled setting
    await loadAISettings();

    // Load extraction mode setting
    await loadExtractionMode();

    // Save extraction mode on change
    document.getElementById('extraction-mode').addEventListener('change', async (e) => {
        await chrome.storage.local.set({ extractionMode: e.target.value });
        console.log('[Settings] Extraction mode saved:', e.target.value);
    });

    // Load saved custom prompt
    const storage = await chrome.storage.local.get(['customPrompt']);
    const customPromptTextarea = document.getElementById('custom-prompt');
    const promptPresetSelect = document.getElementById('prompt-presets');

    if (storage.customPrompt) {
        // There's a saved custom prompt - show textarea and set to "custom" mode
        customPromptTextarea.value = storage.customPrompt;
        customPromptTextarea.style.display = 'block';
        promptPresetSelect.value = 'custom';
        console.log('[Popup] Loaded saved custom prompt');
    } else {
        // No saved prompt - keep at "None" and textarea hidden
        customPromptTextarea.style.display = 'none';
        promptPresetSelect.value = '';
    }

    console.log('[Popup] Initialization complete');

    // Update connection status periodically
    setInterval(updateConnectionStatus, 10000); // Every 10 seconds

    // Refresh jobs periodically
    setInterval(loadJobs, 5000); // Every 5 seconds
});

// Extract current page
async function extractCurrentPage() {
    console.log('[Popup] Extract button clicked');

    try {
        console.log('[Popup] Sending message to background worker...');
        showStatus('Extracting current page...', 'info');
        disableButtons(true);

        // Get download options
        const downloadContent = document.getElementById('download-content').checked;
        const downloadMediaLinks = document.getElementById('download-media-links').checked;
        const downloadExternalLinks = document.getElementById('download-external-links').checked;
        const useZip = document.getElementById('single-page-zip').checked;

        // Validate at least one option selected
        if (!downloadContent && !downloadMediaLinks && !downloadExternalLinks) {
            showStatus('Please select at least one download option', 'error');
            disableButtons(false);
            return;
        }

        // Send message to background worker
        const response = await chrome.runtime.sendMessage({
            action: 'EXTRACT_SINGLE_PAGE',
            url: currentTab.url,
            outputZip: useZip,
            downloadOptions: {
                content: downloadContent,
                mediaLinks: downloadMediaLinks,
                externalLinks: downloadExternalLinks
            }
        });

        console.log('[Popup] Response received:', response);

        if (response && response.success) {
            showStatus(`✓ Page saved: ${response.filename}`, 'success');
        } else {
            const errorMsg = response?.error || 'Unknown error';
            console.error('[Popup] Extraction failed:', errorMsg);
            showStatus(`Error: ${errorMsg}`, 'error');
        }
    } catch (error) {
        console.error('[Popup] Exception:', error);
        showStatus(`Error: ${error.message}`, 'error');
    } finally {
        disableButtons(false);
    }
}

// Map site and discover URLs
async function mapSite() {
    try {
        const depth = parseInt(document.getElementById('depth-select').value);
        showStatus(`Mapping site (depth: ${depth})...`, 'info');
        disableButtons(true);

        // Send message to background worker
        const response = await chrome.runtime.sendMessage({
            action: 'MAP_SITE',
            url: currentTab.url,
            depth: depth
        });

        if (response.success) {
            discoveredUrls = response.urls;
            displayUrls(discoveredUrls);
            showStatus(`✓ Found ${discoveredUrls.length} URLs`, 'success');

            // Show URL list and extraction controls
            document.getElementById('url-list').classList.add('show');
            document.getElementById('extraction-controls').style.display = 'block';
            document.getElementById('search-box').style.display = 'block';
            document.getElementById('link-filters').style.display = 'flex';
        } else {
            showStatus(`Error: ${response.error}`, 'error');
        }
    } catch (error) {
        showStatus(`Error: ${error.message}`, 'error');
    } finally {
        disableButtons(false);
    }
}

// Display URLs in the list
function displayUrls(urls) {
    const urlList = document.getElementById('url-list');
    urlList.innerHTML = '';

    if (urls.length === 0) {
        urlList.innerHTML = '<div style="color: #666; text-align: center; padding: 12px;">No URLs found</div>';
        return;
    }

    urls.forEach((urlData, index) => {
        const item = document.createElement('div');
        item.className = 'url-item';
        item.dataset.type = urlData.type;
        item.dataset.url = urlData.url;

        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.id = `url-${index}`;
        checkbox.checked = urlData.type === 'internal'; // Auto-select internal links
        checkbox.dataset.url = urlData.url;

        const label = document.createElement('span');
        label.textContent = urlData.url;
        label.title = urlData.url;

        const typeTag = document.createElement('span');
        typeTag.style.cssText = 'font-size: 10px; padding: 2px 6px; border-radius: 3px; margin-left: 6px;';
        if (urlData.type === 'internal') {
            typeTag.style.background = '#e3f2fd';
            typeTag.style.color = '#1976d2';
            typeTag.textContent = 'INT';
        } else if (urlData.type === 'external') {
            typeTag.style.background = '#fff3e0';
            typeTag.style.color = '#e65100';
            typeTag.textContent = 'EXT';
        } else {
            typeTag.style.background = '#f3e5f5';
            typeTag.style.color = '#7b1fa2';
            typeTag.textContent = 'MEDIA';
        }

        item.appendChild(checkbox);
        item.appendChild(label);
        item.appendChild(typeTag);
        urlList.appendChild(item);
    });
}

// Filter URLs based on search and type filters
function filterUrls() {
    const searchTerm = document.getElementById('search-box').value.toLowerCase();
    const showInternal = document.getElementById('filter-internal').checked;
    const showExternal = document.getElementById('filter-external').checked;
    const showMedia = document.getElementById('filter-media').checked;

    const items = document.querySelectorAll('.url-item');

    items.forEach(item => {
        const url = item.dataset.url.toLowerCase();
        const type = item.dataset.type;

        const matchesSearch = url.includes(searchTerm);
        const matchesType =
            (type === 'internal' && showInternal) ||
            (type === 'external' && showExternal) ||
            (type === 'media' && showMedia);

        item.style.display = (matchesSearch && matchesType) ? 'flex' : 'none';
    });
}

// Extract selected pages
async function extractSelectedPages() {
    try {
        const checkboxes = document.querySelectorAll('.url-item input[type="checkbox"]:checked');
        const selectedUrls = Array.from(checkboxes).map(cb => cb.dataset.url);

        if (selectedUrls.length === 0) {
            showStatus('Please select at least one URL', 'error');
            return;
        }

        const outputZip = document.getElementById('output-zip').checked;
        const mergeIntoSingle = document.getElementById('merge-into-single').checked;

        showStatus(`Extracting ${selectedUrls.length} pages...`, 'info');
        disableButtons(true);
        showProgress(true);

        // Send message to background worker
        const response = await chrome.runtime.sendMessage({
            action: 'EXTRACT_MULTIPLE_PAGES',
            urls: selectedUrls,
            outputZip: outputZip,
            mergeIntoSingle: mergeIntoSingle
        });

        if (response.success) {
            showStatus(`✓ Extraction complete! ${response.processed} pages saved.`, 'success');
        } else {
            showStatus(`Error: ${response.error}`, 'error');
        }
    } catch (error) {
        showStatus(`Error: ${error.message}`, 'error');
    } finally {
        disableButtons(false);
        showProgress(false);
    }
}

// Show settings dialog
async function showSettings(e) {
    e.preventDefault();

    // Get current setting from chrome.storage
    const storage = await chrome.storage.local.get(['apiEndpoint']);
    const currentEndpoint = storage.apiEndpoint || 'http://localhost:8077';

    const newEndpoint = prompt('Enter API endpoint URL:', currentEndpoint);

    if (newEndpoint && newEndpoint !== currentEndpoint) {
        // Save to chrome.storage (works in both popup and service worker)
        await chrome.storage.local.set({ apiEndpoint: newEndpoint });
        showStatus('API endpoint updated', 'success');
        console.log('[Popup] API endpoint set to:', newEndpoint);
    }
}

// Update progress bar
function updateProgress(current, total, status) {
    const progressBar = document.getElementById('progress-bar');
    const progressFill = document.getElementById('progress-fill');

    if (total > 0) {
        const percentage = Math.round((current / total) * 100);
        progressFill.style.width = `${percentage}%`;
        progressFill.textContent = `${current}/${total} (${percentage}%)`;
    }

    if (status) {
        showStatus(status, 'info');
    }
}

// Show/hide progress bar
function showProgress(show) {
    const progressBar = document.getElementById('progress-bar');
    if (show) {
        progressBar.classList.add('show');
        document.getElementById('progress-fill').style.width = '0%';
        document.getElementById('progress-fill').textContent = '0%';
    } else {
        progressBar.classList.remove('show');
    }
}

// Show status message
function showStatus(message, type) {
    const statusDiv = document.getElementById('status');
    statusDiv.textContent = message;
    statusDiv.className = `show ${type}`;

    // Auto-hide after 5 seconds for success messages
    if (type === 'success') {
        setTimeout(() => {
            statusDiv.classList.remove('show');
        }, 5000);
    }
}

// Disable/enable buttons
function disableButtons(disabled) {
    document.getElementById('extract-current').disabled = disabled;
    document.getElementById('map-site').disabled = disabled;
    document.getElementById('extract-selected').disabled = disabled;
}

// Load AI settings
async function loadAISettings() {
    const storage = await chrome.storage.local.get(['enableAI']);
    const enableAI = storage.enableAI ?? false; // Default to false (use fallback)

    document.getElementById('enable-ai').checked = enableAI;
    updateAIStatus(enableAI);

    console.log('[Settings] AI enabled:', enableAI);
}

// Load extraction mode settings
async function loadExtractionMode() {
    const storage = await chrome.storage.local.get(['extractionMode']);
    const extractionMode = storage.extractionMode || 'balanced'; // Default to balanced

    document.getElementById('extraction-mode').value = extractionMode;

    console.log('[Settings] Extraction mode:', extractionMode);
}

// Handle AI toggle
async function handleAIToggle(event) {
    const enableAI = event.target.checked;

    await chrome.storage.local.set({ enableAI });
    console.log('[Settings] AI toggled:', enableAI ? 'ON' : 'OFF');

    updateAIStatus(enableAI);

    if (enableAI) {
        showStatus('⚠️ AI Processing Enabled - This will incur costs!', 'info');
    } else {
        showStatus('✓ Using Free Fallback (html2text)', 'success');
    }
}

// Update AI status display
function updateAIStatus(enableAI) {
    const statusDiv = document.getElementById('ai-status');
    const promptSection = document.getElementById('ai-prompt-section');

    if (enableAI) {
        statusDiv.style.display = 'block';
        statusDiv.style.background = '#fff3cd';
        statusDiv.style.color = '#856404';
        statusDiv.textContent = '⚠️ AI enabled - processing will cost money';
        promptSection.style.display = 'block';  // Show custom prompt section
    } else {
        statusDiv.style.display = 'block';
        statusDiv.style.background = '#d4edda';
        statusDiv.style.color = '#155724';
        statusDiv.textContent = '✓ Free fallback mode (html2text)';
        promptSection.style.display = 'none';  // Hide custom prompt section
    }
}

// Load prompt preset
function loadPromptPreset() {
    const preset = document.getElementById('prompt-presets').value;
    const customPrompt = document.getElementById('custom-prompt');

    const presets = {
        'extract_products': 'Extract the following from this page and format as a markdown table:\n- Product Title\n- Price (if available)\n- Description\n- Key Features\n\nCreate a CSV-formatted table in your response.',
        'highlight_keyword': 'Search for the keyword "[KEYWORD]" throughout the content. When you find it, create markdown highlights using **bold** formatting. List all occurrences with their context.',
        'price_comparison': 'Find all products with prices on this page. Create a comparison table with columns: Product Name, Price, Features, Link. Sort by price from lowest to highest.',
        'extract_reviews': 'Find and summarize all customer reviews on this page. Include:\n- Overall rating summary\n- Common positive feedback\n- Common negative feedback\n- Individual review highlights',
        'contact_info': 'Extract all contact information from this page:\n- Phone numbers\n- Email addresses\n- Physical addresses\n- Social media links\n- Business hours (if available)\n\nFormat as a structured list.',
        'specs_table': 'Find product specifications and create a detailed markdown table with two columns: Specification and Value. Include all technical details, dimensions, features, and requirements.',
        'link_summary': 'List all important links and resources mentioned on this page. Categorize them as:\n- Internal Links\n- External Resources\n- Download Links\n- Documentation\n- Related Content\n\nInclude a brief description for each link.'
    };

    // Handle different options
    if (preset === 'custom') {
        // Write your own - show textarea, keep existing content
        customPrompt.style.display = 'block';
        console.log('[Prompt] Custom mode selected');
    } else if (preset === '') {
        // None - hide textarea and clear it
        customPrompt.style.display = 'none';
        customPrompt.value = '';
        chrome.storage.local.set({ customPrompt: '' });
        console.log('[Prompt] None selected');
    } else if (presets[preset]) {
        // Preset selected - show textarea with preset content
        customPrompt.style.display = 'block';
        customPrompt.value = presets[preset];
        chrome.storage.local.set({ customPrompt: presets[preset] });
        console.log('[Prompt] Loaded preset:', preset);
    }
}

// Toggle test buttons visibility
function toggleTests() {
    const testButtons = document.getElementById('test-buttons');
    const toggleBtn = document.getElementById('toggle-tests');

    if (testButtons.style.display === 'none') {
        testButtons.style.display = 'block';
        toggleBtn.textContent = 'Hide';
    } else {
        testButtons.style.display = 'none';
        toggleBtn.textContent = 'Show';
    }
}

// Test backend connection
async function testBackend() {
    console.log('[Test] Testing backend connection...');
    showStatus('Testing backend connection...', 'info');

    try {
        const storage = await chrome.storage.local.get(['apiEndpoint']);
        const apiUrl = storage.apiEndpoint || 'http://localhost:8077';

        console.log('[Test] Connecting to:', apiUrl);

        const response = await fetch(apiUrl);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();
        console.log('[Test] Backend response:', data);

        const aiStatus = data.ai_enabled ? '✓ AI Enabled' : '⚠ AI Disabled (using fallback)';
        showStatus(`✓ Backend Connected! ${aiStatus}`, 'success');
    } catch (error) {
        console.error('[Test] Backend test failed:', error);
        showStatus(`✗ Backend Error: ${error.message}`, 'error');
    }
}

// Test AI processing
async function testAI() {
    console.log('[Test] Testing AI processing...');
    showStatus('Testing AI processing...', 'info');

    try {
        const storage = await chrome.storage.local.get(['apiEndpoint']);
        const apiUrl = storage.apiEndpoint || 'http://localhost:8077';

        const testHTML = `
            <html>
            <body>
                <h1>Test Page</h1>
                <p>This is a <strong>test page</strong> for AI conversion.</p>
                <ul>
                    <li>Item 1</li>
                    <li>Item 2</li>
                </ul>
                <a href="https://example.com">Example Link</a>
            </body>
            </html>
        `;

        console.log('[Test] Sending test HTML to backend...');

        const response = await fetch(`${apiUrl}/process-html`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                url: 'https://test.example.com',
                html: testHTML,
                title: 'Test Page'
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const result = await response.json();
        console.log('[Test] AI processing result:', result);

        const method = result.used_ai ? '✓ AI' : '⚠ Fallback (html2text)';
        const preview = result.markdown.substring(0, 100) + '...';

        showStatus(`✓ Processing Success! Method: ${method}\nPreview: ${preview}`, 'success');
    } catch (error) {
        console.error('[Test] AI test failed:', error);
        showStatus(`✗ AI Test Error: ${error.message}`, 'error');
    }
}

// Test local fallback processing
async function testFallback() {
    console.log('[Test] Testing local fallback...');
    showStatus('Testing local fallback (html2text)...', 'info');

    try {
        const storage = await chrome.storage.local.get(['apiEndpoint']);
        const apiUrl = storage.apiEndpoint || 'http://localhost:8077';

        const testHTML = `
            <html>
            <body>
                <h1>Fallback Test</h1>
                <p>This tests the html2text fallback when AI is unavailable.</p>
                <blockquote>This is a quote</blockquote>
                <code>const x = 42;</code>
            </body>
            </html>
        `;

        console.log('[Test] Testing fallback processing...');

        const response = await fetch(`${apiUrl}/process-html`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                url: 'https://fallback.example.com',
                html: testHTML,
                title: 'Fallback Test'
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const result = await response.json();
        console.log('[Test] Fallback result:', result);

        const method = result.used_ai ? 'AI (not fallback!)' : '✓ Fallback (html2text)';
        showStatus(`✓ Fallback Test Success! Used: ${method}`, 'success');

        if (result.used_ai) {
            showStatus(`⚠ Note: AI was used instead of fallback. This means API key is configured.`, 'info');
        }
    } catch (error) {
        console.error('[Test] Fallback test failed:', error);
        showStatus(`✗ Fallback Test Error: ${error.message}`, 'error');
    }
}

// Update connection status indicator
async function updateConnectionStatus() {
    try {
        const response = await chrome.runtime.sendMessage({ action: 'GET_CONNECTION_STATE' });

        if (response && response.success) {
            const state = response.state;
            const statusDiv = document.getElementById('connection-status');
            const statusText = document.getElementById('connection-text');
            const statusDot = statusDiv.querySelector('.status-dot');

            if (state.isConnected) {
                statusDiv.className = 'connected';
                statusDot.className = 'status-dot green';

                let text = '✓ Backend connected';
                if (state.aiEnabled) {
                    text += ' (AI enabled)';
                } else {
                    text += ' (Fallback mode)';
                }

                // Show time since last ping
                if (state.lastSuccessfulPing) {
                    const secondsAgo = Math.floor((Date.now() - state.lastSuccessfulPing) / 1000);
                    if (secondsAgo < 60) {
                        text += ` • ${secondsAgo}s ago`;
                    }
                }

                statusText.textContent = text;
            } else {
                statusDiv.className = 'disconnected';
                statusDot.className = 'status-dot red';

                let text = '✗ Backend disconnected';
                if (state.consecutiveFailures > 0) {
                    text += ` (${state.consecutiveFailures} failures)`;
                }

                statusText.textContent = text;
            }
        }
    } catch (error) {
        console.warn('[Popup] Could not get connection state:', error);
    }
}

// Load and display jobs from backend
async function loadJobs() {
    try {
        const storage = await chrome.storage.local.get(['apiEndpoint']);
        const apiUrl = storage.apiEndpoint || 'http://localhost:8077';

        const response = await fetch(`${apiUrl}/jobs?limit=20`);
        if (!response.ok) {
            console.warn('[Jobs] Failed to load jobs:', response.status);
            return;
        }

        const data = await response.json();
        displayJobs(data.jobs);
    } catch (error) {
        console.warn('[Jobs] Error loading jobs:', error);
    }
}

// Display jobs in the UI
function displayJobs(jobs) {
    const jobsList = document.getElementById('jobs-list');
    const jobsSection = document.getElementById('jobs-section');

    // Filter for active or recent jobs
    const relevantJobs = jobs.filter(job =>
        job.status === 'processing' ||
        job.status === 'pending' ||
        (job.status === 'completed' && isRecent(job.completed_at)) ||
        (job.status === 'failed' && isRecent(job.completed_at))
    );

    if (relevantJobs.length === 0) {
        jobsSection.style.display = 'none';
        return;
    }

    jobsSection.style.display = 'block';
    jobsList.innerHTML = '';

    relevantJobs.forEach(job => {
        const jobItem = createJobElement(job);
        jobsList.appendChild(jobItem);
    });
}

// Create job element
function createJobElement(job) {
    const div = document.createElement('div');
    div.className = `job-item ${job.status}`;
    div.dataset.jobId = job.id;

    const title = job.params.title || job.params.url || 'Unknown';
    const statusText = job.status.charAt(0).toUpperCase() + job.status.slice(1);
    const progress = job.progress || { current: 0, total: 0, message: '', percent: 0 };

    div.innerHTML = `
        <div class="job-header">
            <div class="job-title" title="${title}">${truncate(title, 40)}</div>
            <div class="job-status ${job.status}">${statusText}</div>
        </div>
        ${progress.message ? `<div class="job-progress">${progress.message}</div>` : ''}
        ${job.status === 'processing' || job.status === 'pending' ? `
            <div class="job-progress-bar">
                <div class="job-progress-fill" style="width: ${progress.percent || 0}%"></div>
            </div>
        ` : ''}
        <div class="job-time">${getTimeAgo(job.created_at)}</div>
    `;

    div.addEventListener('click', () => handleJobClick(job));

    return div;
}

// Handle clicking on a job
async function handleJobClick(job) {
    console.log('[Jobs] Clicked job:', job.id);

    // For completed jobs, show result details
    if (job.status === 'completed' && job.result) {
        showStatus(`Job completed: ${job.result.filename} (${job.result.word_count} words)`, 'success');
    } else if (job.status === 'failed') {
        showStatus(`Job failed: ${job.error}`, 'error');
    } else if (job.status === 'processing') {
        const progress = job.progress || {};
        showStatus(`Job in progress: ${progress.message || 'Processing...'}`, 'info');
    }

    // TODO: Restore job context (for multi-page jobs)
    // This could restore the URL list for site mapping, etc.
}

// Helper: Check if timestamp is recent (within last hour)
function isRecent(timestamp) {
    if (!timestamp) return false;
    const time = new Date(timestamp);
    const now = new Date();
    return (now - time) < 3600000; // 1 hour in milliseconds
}

// Helper: Get time ago string
function getTimeAgo(timestamp) {
    const time = new Date(timestamp);
    const now = new Date();
    const seconds = Math.floor((now - time) / 1000);

    if (seconds < 60) return `${seconds}s ago`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
    return `${Math.floor(seconds / 3600)}h ago`;
}

// Helper: Truncate string
function truncate(str, maxLength) {
    if (str.length <= maxLength) return str;
    return str.substring(0, maxLength - 3) + '...';
}
