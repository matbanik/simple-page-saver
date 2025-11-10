// Popup UI Logic for Simple Page Saver

let discoveredUrls = [];
let currentTab = null;

// Initialize popup
document.addEventListener('DOMContentLoaded', async () => {
    // Get current tab
    const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
    currentTab = tabs[0];

    // Set up event listeners
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
});

// Extract current page
async function extractCurrentPage() {
    try {
        showStatus('Extracting current page...', 'info');
        disableButtons(true);

        // Send message to background worker
        const response = await chrome.runtime.sendMessage({
            action: 'EXTRACT_SINGLE_PAGE',
            url: currentTab.url
        });

        if (response.success) {
            showStatus(`✓ Page saved: ${response.filename}`, 'success');
        } else {
            showStatus(`Error: ${response.error}`, 'error');
        }
    } catch (error) {
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

        showStatus(`Extracting ${selectedUrls.length} pages...`, 'info');
        disableButtons(true);
        showProgress(true);

        // Send message to background worker
        const response = await chrome.runtime.sendMessage({
            action: 'EXTRACT_MULTIPLE_PAGES',
            urls: selectedUrls,
            outputZip: outputZip
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
function showSettings(e) {
    e.preventDefault();
    const currentEndpoint = localStorage.getItem('apiEndpoint') || 'http://localhost:8077';
    const newEndpoint = prompt('Enter API endpoint URL:', currentEndpoint);

    if (newEndpoint && newEndpoint !== currentEndpoint) {
        localStorage.setItem('apiEndpoint', newEndpoint);
        showStatus('API endpoint updated', 'success');
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
