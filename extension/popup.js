// Popup UI Logic for Simple Page Saver

let discoveredUrls = [];
let currentTab = null;
let currentViewMode = 'tree'; // 'tree' or 'flat'

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
    document.getElementById('clear-completed-jobs').addEventListener('click', clearCompletedJobs);
    document.getElementById('extract-current').addEventListener('click', extractCurrentPage);
    document.getElementById('execute-url-action').addEventListener('click', executeUrlAction);
    document.getElementById('open-in-tab').addEventListener('click', openInTab);
    document.getElementById('map-site').addEventListener('click', mapSite);
    document.getElementById('extract-selected').addEventListener('click', extractSelectedPages);
    document.getElementById('settings-link').addEventListener('click', showSettings);

    // Search box filter
    document.getElementById('search-box').addEventListener('input', filterUrls);

    // Link type filters
    document.getElementById('filter-internal').addEventListener('change', filterUrls);
    document.getElementById('filter-external').addEventListener('change', filterUrls);
    document.getElementById('filter-media').addEventListener('change', filterUrls);

    // Tree control buttons
    document.getElementById('expand-all').addEventListener('click', expandAllNodes);
    document.getElementById('collapse-all').addEventListener('click', collapseAllNodes);
    document.getElementById('select-all').addEventListener('click', selectAllNodes);
    document.getElementById('deselect-all').addEventListener('click', deselectAllNodes);

    // View toggle button
    document.getElementById('toggle-view').addEventListener('click', toggleViewMode);

    // Load view mode preference
    const storage = await chrome.storage.local.get(['viewMode']);
    if (storage.viewMode) {
        currentViewMode = storage.viewMode;
    }

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

    // Screenshot checkbox - enable/disable preserve color option
    document.getElementById('include-screenshot').addEventListener('change', (e) => {
        const preserveColorCheckbox = document.getElementById('preserve-color');
        preserveColorCheckbox.disabled = !e.target.checked;
        if (!e.target.checked) {
            preserveColorCheckbox.checked = false;
        }
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

    // Load chunking settings
    await loadChunkingSettings();

    // Save chunking settings on change
    document.getElementById('worker-count').addEventListener('change', async (e) => {
        const value = parseInt(e.target.value);
        if (value >= 1 && value <= 16) {
            await chrome.storage.local.set({ workerCount: value });
            console.log('[Settings] Worker count saved:', value);
            // Also save to backend settings
            await saveBackendSetting('worker_count', value);
        }
    });

    document.getElementById('overlap-percentage').addEventListener('change', async (e) => {
        const value = parseInt(e.target.value);
        if (value >= 0 && value <= 50) {
            await chrome.storage.local.set({ overlapPercentage: value });
            console.log('[Settings] Overlap percentage saved:', value);
            // Also save to backend settings
            await saveBackendSetting('overlap_percentage', value);
        }
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

    // Listen for storage changes from other tabs
    chrome.storage.onChanged.addListener((changes, areaName) => {
        if (areaName === 'local' && changes.activeJobs) {
            console.log('[Jobs] Storage changed in another tab, updating UI');
            displayJobs(changes.activeJobs.newValue || []);
        }
    });
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
        const includeScreenshot = document.getElementById('include-screenshot').checked;
        const preserveColor = document.getElementById('preserve-color').checked;
        const useZip = document.getElementById('single-page-zip').checked;

        // Validate at least one option selected
        if (!downloadContent && !downloadMediaLinks && !downloadExternalLinks && !includeScreenshot) {
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
                externalLinks: downloadExternalLinks,
                screenshot: includeScreenshot,
                preserveColor: preserveColor
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

            // Display URLs in the current view mode
            if (currentViewMode === 'tree') {
                displayUrls(discoveredUrls);
            } else {
                displayUrlsFlat(discoveredUrls);
            }

            showStatus(`✓ Found ${discoveredUrls.length} URLs`, 'success');

            // Show URL list and extraction controls
            document.getElementById('url-list').classList.add('show');
            document.getElementById('extraction-controls').style.display = 'block';
            document.getElementById('search-box').style.display = 'block';
            document.getElementById('link-filters').style.display = 'flex';
            document.getElementById('view-controls').style.display = 'flex';
        } else {
            showStatus(`Error: ${response.error}`, 'error');
        }
    } catch (error) {
        showStatus(`Error: ${error.message}`, 'error');
    } finally {
        disableButtons(false);
    }
}

// Build tree structure from flat URL list
function buildTree(urls) {
    // Create a map of URL to its data
    const urlMap = new Map();
    urls.forEach(urlData => {
        urlMap.set(urlData.url, { ...urlData, children: [] });
    });

    // Build parent-child relationships
    const roots = [];
    urlMap.forEach((urlData, url) => {
        if (urlData.parent && urlMap.has(urlData.parent)) {
            // Add to parent's children
            urlMap.get(urlData.parent).children.push(urlData);
        } else {
            // No parent or parent not in list - treat as root
            roots.push(urlData);
        }
    });

    return roots;
}

// Create a tree node element
function createTreeNode(urlData, index) {
    const node = document.createElement('div');
    node.className = 'tree-node';
    node.dataset.url = urlData.url;
    node.dataset.type = urlData.type;

    const hasChildren = urlData.children && urlData.children.length > 0;

    // Node content
    const content = document.createElement('div');
    content.className = 'tree-node-content';

    // Expand/collapse icon
    const expandIcon = document.createElement('span');
    expandIcon.className = 'tree-expand-icon' + (hasChildren ? '' : ' empty');
    expandIcon.textContent = hasChildren ? '▶' : '';
    expandIcon.onclick = (e) => {
        e.stopPropagation();
        toggleTreeNode(node);
    };

    // Checkbox
    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.className = 'tree-node-checkbox';
    checkbox.id = `url-${index}`;
    checkbox.checked = urlData.type === 'internal'; // Auto-select internal links
    checkbox.dataset.url = urlData.url;
    checkbox.onclick = (e) => {
        e.stopPropagation();
        handleCheckboxChange(node, checkbox.checked);
    };

    // Label
    const label = document.createElement('span');
    label.className = 'tree-node-label';
    label.textContent = urlData.url;
    label.title = urlData.url;

    // Type badge
    const badge = document.createElement('span');
    badge.className = 'tree-node-badge';
    if (urlData.type === 'internal') {
        badge.classList.add('badge-internal');
        badge.textContent = 'INT';
    } else if (urlData.type === 'external') {
        badge.classList.add('badge-external');
        badge.textContent = 'EXT';
    } else {
        badge.classList.add('badge-media');
        badge.textContent = 'MEDIA';
    }

    content.appendChild(expandIcon);
    content.appendChild(checkbox);
    content.appendChild(label);
    content.appendChild(badge);
    node.appendChild(content);

    // Children container
    if (hasChildren) {
        const childrenContainer = document.createElement('div');
        childrenContainer.className = 'tree-children';

        urlData.children.forEach((child, childIndex) => {
            const childNode = createTreeNode(child, `${index}-${childIndex}`);
            childrenContainer.appendChild(childNode);
        });

        node.appendChild(childrenContainer);
    }

    return node;
}

// Toggle tree node expansion
function toggleTreeNode(node) {
    const expandIcon = node.querySelector('.tree-expand-icon');
    const children = node.querySelector('.tree-children');

    if (!children || expandIcon.classList.contains('empty')) return;

    if (children.classList.contains('expanded')) {
        children.classList.remove('expanded');
        expandIcon.textContent = '▶';
    } else {
        children.classList.add('expanded');
        expandIcon.textContent = '▼';
    }
}

// Handle checkbox change with hierarchical selection
function handleCheckboxChange(node, isChecked) {
    // Update all child checkboxes
    const childCheckboxes = node.querySelectorAll('.tree-children .tree-node-checkbox');
    childCheckboxes.forEach(cb => {
        cb.checked = isChecked;
    });

    // Update parent checkbox state (indeterminate if some children are checked)
    updateParentCheckboxState(node);
}

// Update parent checkbox state based on children
function updateParentCheckboxState(node) {
    // Find parent node
    let parent = node.parentElement;
    while (parent && !parent.classList.contains('tree-node')) {
        parent = parent.parentElement;
    }

    if (!parent) return;

    const parentCheckbox = parent.querySelector(':scope > .tree-node-content > .tree-node-checkbox');
    if (!parentCheckbox) return;

    // Get all direct children checkboxes
    const childrenContainer = parent.querySelector(':scope > .tree-children');
    if (!childrenContainer) return;

    const childCheckboxes = Array.from(
        childrenContainer.querySelectorAll(':scope > .tree-node > .tree-node-content > .tree-node-checkbox')
    );

    if (childCheckboxes.length === 0) return;

    const checkedCount = childCheckboxes.filter(cb => cb.checked).length;

    if (checkedCount === 0) {
        parentCheckbox.checked = false;
        parentCheckbox.indeterminate = false;
    } else if (checkedCount === childCheckboxes.length) {
        parentCheckbox.checked = true;
        parentCheckbox.indeterminate = false;
    } else {
        parentCheckbox.checked = false;
        parentCheckbox.indeterminate = true;
    }

    // Recursively update parent's parent
    updateParentCheckboxState(parent);
}

// Display URLs in tree view
function displayUrls(urls) {
    const urlList = document.getElementById('url-list');
    urlList.innerHTML = '';

    if (urls.length === 0) {
        urlList.innerHTML = '<div style="color: #666; text-align: center; padding: 12px;">No URLs found</div>';
        return;
    }

    // Build tree structure
    const tree = buildTree(urls);

    // Create tree nodes
    tree.forEach((rootData, index) => {
        const treeNode = createTreeNode(rootData, index);
        urlList.appendChild(treeNode);
    });

    // Show view controls
    document.getElementById('view-controls').style.display = 'flex';

    // Update expand/collapse button visibility based on view mode
    updateViewControlsVisibility();
}

// Display URLs in flat list view
function displayUrlsFlat(urls) {
    const urlList = document.getElementById('url-list');
    urlList.innerHTML = '';

    if (urls.length === 0) {
        urlList.innerHTML = '<div style="color: #666; text-align: center; padding: 12px;">No URLs found</div>';
        return;
    }

    urls.forEach((urlData, index) => {
        const item = document.createElement('div');
        item.className = 'url-item';
        item.dataset.url = urlData.url;
        item.dataset.type = urlData.type;
        item.style.cssText = 'display: flex; align-items: center; padding: 6px; margin-bottom: 4px; background: #f9f9f9; border-radius: 3px; font-size: 11px;';

        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.className = 'flat-checkbox';
        checkbox.id = `flat-url-${index}`;
        checkbox.checked = urlData.type === 'internal';
        checkbox.dataset.url = urlData.url;
        checkbox.style.marginRight = '8px';

        const label = document.createElement('span');
        label.textContent = urlData.url;
        label.title = urlData.url;
        label.style.cssText = 'flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; margin-right: 8px;';

        const badge = document.createElement('span');
        badge.style.cssText = 'font-size: 10px; padding: 2px 6px; border-radius: 3px; flex-shrink: 0;';
        if (urlData.type === 'internal') {
            badge.style.background = '#e3f2fd';
            badge.style.color = '#1976d2';
            badge.textContent = 'INT';
        } else if (urlData.type === 'external') {
            badge.style.background = '#fff3e0';
            badge.style.color = '#e65100';
            badge.textContent = 'EXT';
        } else {
            badge.style.background = '#f3e5f5';
            badge.style.color = '#7b1fa2';
            badge.textContent = 'MEDIA';
        }

        item.appendChild(checkbox);
        item.appendChild(label);
        item.appendChild(badge);
        urlList.appendChild(item);
    });

    // Show view controls
    document.getElementById('view-controls').style.display = 'flex';

    // Update expand/collapse button visibility based on view mode
    updateViewControlsVisibility();
}

// Toggle between tree and flat view
function toggleViewMode() {
    // Save current checkbox states
    const checkedUrls = new Set();
    if (currentViewMode === 'tree') {
        document.querySelectorAll('.tree-node-checkbox:checked').forEach(cb => {
            checkedUrls.add(cb.dataset.url);
        });
    } else {
        document.querySelectorAll('.flat-checkbox:checked').forEach(cb => {
            checkedUrls.add(cb.dataset.url);
        });
    }

    // Toggle mode
    currentViewMode = currentViewMode === 'tree' ? 'flat' : 'tree';

    // Save preference
    chrome.storage.local.set({ viewMode: currentViewMode });

    // Re-render with new mode
    if (currentViewMode === 'tree') {
        displayUrls(discoveredUrls);
    } else {
        displayUrlsFlat(discoveredUrls);
    }

    // Restore checkbox states
    setTimeout(() => {
        const checkboxes = currentViewMode === 'tree'
            ? document.querySelectorAll('.tree-node-checkbox')
            : document.querySelectorAll('.flat-checkbox');

        checkboxes.forEach(cb => {
            if (checkedUrls.has(cb.dataset.url)) {
                cb.checked = true;
            }
        });
    }, 10);

    // Update toggle button text
    updateViewControlsVisibility();
}

// Update view controls visibility based on current mode
function updateViewControlsVisibility() {
    const toggleButton = document.getElementById('toggle-view');
    const expandButton = document.getElementById('expand-all');
    const collapseButton = document.getElementById('collapse-all');

    if (currentViewMode === 'tree') {
        toggleButton.textContent = '📋 Flat View';
        expandButton.style.display = 'inline-block';
        collapseButton.style.display = 'inline-block';
    } else {
        toggleButton.textContent = '🌳 Tree View';
        expandButton.style.display = 'none';
        collapseButton.style.display = 'none';
    }
}

// Expand all tree nodes
function expandAllNodes() {
    document.querySelectorAll('.tree-children').forEach(children => {
        children.classList.add('expanded');
        const node = children.parentElement;
        const expandIcon = node.querySelector('.tree-expand-icon');
        if (expandIcon && !expandIcon.classList.contains('empty')) {
            expandIcon.textContent = '▼';
        }
    });
}

// Collapse all tree nodes
function collapseAllNodes() {
    document.querySelectorAll('.tree-children').forEach(children => {
        children.classList.remove('expanded');
        const node = children.parentElement;
        const expandIcon = node.querySelector('.tree-expand-icon');
        if (expandIcon && !expandIcon.classList.contains('empty')) {
            expandIcon.textContent = '▶';
        }
    });
}

// Select all checkboxes
function selectAllNodes() {
    const checkboxSelector = currentViewMode === 'tree' ? '.tree-node-checkbox' : '.flat-checkbox';
    document.querySelectorAll(checkboxSelector).forEach(cb => {
        cb.checked = true;
        cb.indeterminate = false;
    });
}

// Deselect all checkboxes
function deselectAllNodes() {
    const checkboxSelector = currentViewMode === 'tree' ? '.tree-node-checkbox' : '.flat-checkbox';
    document.querySelectorAll(checkboxSelector).forEach(cb => {
        cb.checked = false;
        cb.indeterminate = false;
    });
}

// Filter URLs based on search and type filters
function filterUrls() {
    const searchTerm = document.getElementById('search-box').value.toLowerCase();
    const showInternal = document.getElementById('filter-internal').checked;
    const showExternal = document.getElementById('filter-external').checked;
    const showMedia = document.getElementById('filter-media').checked;

    const treeNodes = document.querySelectorAll('.tree-node');

    treeNodes.forEach(node => {
        const url = node.dataset.url.toLowerCase();
        const type = node.dataset.type;

        const matchesSearch = url.includes(searchTerm);
        const matchesType =
            (type === 'internal' && showInternal) ||
            (type === 'external' && showExternal) ||
            (type === 'media' && showMedia);

        node.style.display = (matchesSearch && matchesType) ? 'block' : 'none';
    });
}

// Extract selected pages
async function extractSelectedPages() {
    try {
        // Get checked checkboxes from either view
        const checkboxSelector = currentViewMode === 'tree' ? '.tree-node-checkbox:checked' : '.flat-checkbox:checked';
        const checkboxes = document.querySelectorAll(checkboxSelector);
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

// Load chunking settings
async function loadChunkingSettings() {
    // Try to load from backend settings first
    try {
        const backendUrl = await getBackendUrl();
        const response = await fetch(`${backendUrl}/settings`);
        if (response.ok) {
            const settings = await response.json();
            const workerCount = settings.worker_count || 4;
            const overlapPercentage = settings.overlap_percentage || 10;

            document.getElementById('worker-count').value = workerCount;
            document.getElementById('overlap-percentage').value = overlapPercentage;

            // Save to local storage
            await chrome.storage.local.set({ workerCount, overlapPercentage });

            console.log('[Settings] Chunking settings loaded from backend:', { workerCount, overlapPercentage });
            return;
        }
    } catch (error) {
        console.log('[Settings] Could not load from backend, using local storage:', error.message);
    }

    // Fallback to local storage
    const storage = await chrome.storage.local.get(['workerCount', 'overlapPercentage']);
    const workerCount = storage.workerCount || 4;
    const overlapPercentage = storage.overlapPercentage || 10;

    document.getElementById('worker-count').value = workerCount;
    document.getElementById('overlap-percentage').value = overlapPercentage;

    console.log('[Settings] Chunking settings loaded from local storage:', { workerCount, overlapPercentage });
}

// Save a setting to the backend
async function saveBackendSetting(key, value) {
    try {
        const backendUrl = await getBackendUrl();
        const response = await fetch(`${backendUrl}/settings`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ [key]: value })
        });

        if (response.ok) {
            console.log(`[Settings] Saved ${key}=${value} to backend`);
        } else {
            console.warn(`[Settings] Failed to save ${key} to backend:`, response.statusText);
        }
    } catch (error) {
        console.warn(`[Settings] Could not save ${key} to backend:`, error.message);
    }
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
    const clearButton = document.getElementById('clear-completed-jobs');

    // Show ALL jobs (processing, pending, paused, recently completed/failed)
    // Only filter out old completed jobs (> 1 hour)
    const relevantJobs = jobs.filter(job =>
        job.status === 'processing' ||
        job.status === 'pending' ||
        job.status === 'paused' ||
        (job.status === 'completed' && isRecent(job.completed_at)) ||
        (job.status === 'failed' && isRecent(job.completed_at))
    );

    if (relevantJobs.length === 0) {
        jobsSection.style.display = 'none';
        clearButton.style.display = 'none';
        return;
    }

    // Show "Clear Completed" button if there are completed/failed jobs
    const hasCompletedJobs = relevantJobs.some(job =>
        job.status === 'completed' || job.status === 'failed'
    );
    clearButton.style.display = hasCompletedJobs ? 'inline-block' : 'none';

    jobsSection.style.display = 'block';
    jobsList.innerHTML = '';

    relevantJobs.forEach(job => {
        const jobItem = createJobElement(job);
        jobsList.appendChild(jobItem);
    });

    // Store jobs in chrome.storage for cross-tab access
    chrome.storage.local.set({ activeJobs: relevantJobs });
}

// Create job element
function createJobElement(job) {
    const div = document.createElement('div');
    div.className = `job-item ${job.status}`;
    div.dataset.jobId = job.id;

    // Determine job title with fallbacks
    let title = job.params?.title || job.params?.url || 'Unknown';

    // Fallback for site_map jobs: generate title from start_url if available
    if (title === 'Unknown' && job.type === 'site_map' && job.params?.start_url) {
        title = `Site Map: ${job.params.start_url}`;
    }

    const statusText = job.status.charAt(0).toUpperCase() + job.status.slice(1);
    const progress = job.progress || { current: 0, total: 0, message: '', percent: 0 };

    // Show remove button for completed/failed jobs
    const showRemoveButton = job.status === 'completed' || job.status === 'failed';

    // Show load button for ALL completed jobs
    const showLoadButton = job.status === 'completed';

    // Show pause button for processing jobs
    const showPauseButton = job.status === 'processing';

    // Show resume/view button for paused jobs
    const showResumeButton = job.status === 'paused';

    // Show stop button for processing jobs
    const showStopButton = job.status === 'processing';

    div.innerHTML = `
        <div class="job-header">
            <div class="job-title" title="${title}">${truncate(title, 35)}</div>
            <div style="display: flex; align-items: center; gap: 5px;">
                <div class="job-status ${job.status}">${statusText}</div>
                ${showLoadButton ? '<button class="job-load" title="Load discovered URLs">Load</button>' : ''}
                ${showResumeButton ? '<button class="job-resume" title="Resume job">Resume</button>' : ''}
                ${showResumeButton ? '<button class="job-view-progress" title="View progress">View</button>' : ''}
                ${showPauseButton ? '<button class="job-pause" title="Pause job">Pause</button>' : ''}
                ${showStopButton ? '<button class="job-stop" title="Stop job">Stop</button>' : ''}
                ${showRemoveButton ? '<button class="job-remove" title="Remove from list">×</button>' : ''}
            </div>
        </div>
        ${progress.message ? `<div class="job-progress">${progress.message}</div>` : ''}
        ${job.status === 'processing' || job.status === 'pending' || job.status === 'paused' ? `
            <div class="job-progress-bar">
                <div class="job-progress-fill" style="width: ${progress.percent || 0}%"></div>
            </div>
        ` : ''}
        <div class="job-time">${getTimeAgo(job.created_at)}</div>
    `;

    // Add click handler for job details (not on action buttons)
    div.addEventListener('click', (e) => {
        const isActionButton = e.target.classList.contains('job-remove') ||
                               e.target.classList.contains('job-load') ||
                               e.target.classList.contains('job-pause') ||
                               e.target.classList.contains('job-resume') ||
                               e.target.classList.contains('job-stop') ||
                               e.target.classList.contains('job-view-progress');
        if (!isActionButton) {
            handleJobClick(job);
        }
    });

    // Add click handler for load button
    if (showLoadButton) {
        const loadBtn = div.querySelector('.job-load');
        if (loadBtn) {
            loadBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                loadJobContext(job);
            });
        }
    }

    // Add click handler for pause button
    if (showPauseButton) {
        const pauseBtn = div.querySelector('.job-pause');
        if (pauseBtn) {
            pauseBtn.addEventListener('click', async (e) => {
                e.stopPropagation();
                await pauseJob(job.id);
            });
        }
    }

    // Add click handler for resume button
    if (showResumeButton) {
        const resumeBtn = div.querySelector('.job-resume');
        if (resumeBtn) {
            resumeBtn.addEventListener('click', async (e) => {
                e.stopPropagation();
                await resumeJob(job.id);
            });
        }

        const viewBtn = div.querySelector('.job-view-progress');
        if (viewBtn) {
            viewBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                viewJobProgress(job);
            });
        }
    }

    // Add click handler for stop button
    if (showStopButton) {
        const stopBtn = div.querySelector('.job-stop');
        if (stopBtn) {
            stopBtn.addEventListener('click', async (e) => {
                e.stopPropagation();
                await stopJob(job.id);
            });
        }
    }

    // Add click handler for remove button
    if (showRemoveButton) {
        const removeBtn = div.querySelector('.job-remove');
        if (removeBtn) {
            removeBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                removeJob(job.id);
            });
        }
    }

    return div;
}

// Handle clicking on a job
async function handleJobClick(job) {
    console.log('[Jobs] Clicked job:', job.id);

    // For completed jobs, show result details
    if (job.status === 'completed' && job.result) {
        if (job.type === 'site_map') {
            showStatus(`Site mapping completed: ${job.result.total_discovered} URLs discovered`, 'success');
        } else if (job.result.filename) {
            showStatus(`Job completed: ${job.result.filename} (${job.result.word_count} words)`, 'success');
        }
    } else if (job.status === 'failed') {
        showStatus(`Job failed: ${job.error}`, 'error');
    } else if (job.status === 'processing') {
        const progress = job.progress || {};
        showStatus(`Job in progress: ${progress.message || 'Processing...'}`, 'info');
    }
}

// Load job context (restore job data to UI)
async function loadJobContext(job) {
    console.log('[Jobs] Loading job context:', job);
    console.log('[Jobs] Job type:', job.type);
    console.log('[Jobs] Job status:', job.status);
    console.log('[Jobs] Job result:', job.result);

    try {
        if (job.type === 'site_map' && job.status === 'completed' && job.result) {
            // Load discovered URLs into the site mapping section
            let urlDataList = job.result.urlDataList || [];
            console.log('[Jobs] urlDataList length:', urlDataList.length);
            console.log('[Jobs] urlDataList sample:', urlDataList.slice(0, 3));
            console.log('[Jobs] job.result keys:', Object.keys(job.result));
            console.log('[Jobs] job.result.discovered_urls:', job.result.discovered_urls);
            console.log('[Jobs] job.params:', job.params);

            // Fallback: if urlDataList is missing but discovered_urls exists, reconstruct basic data
            if (urlDataList.length === 0 && job.result.discovered_urls && job.result.discovered_urls.length > 0) {
                console.log('[Jobs] urlDataList missing, reconstructing from discovered_urls');
                const startUrl = job.params?.start_url || job.result.discovered_urls[0];

                // Extract base domain from start URL for type detection
                let startDomain = '';
                try {
                    startDomain = new URL(startUrl).hostname;
                } catch (e) {
                    console.warn('[Jobs] Could not parse start URL:', startUrl);
                }

                urlDataList = job.result.discovered_urls.map((url, index) => {
                    // Detect URL type
                    let type = 'internal';
                    try {
                        const urlObj = new URL(url);
                        const urlDomain = urlObj.hostname;
                        const urlPath = urlObj.pathname.toLowerCase();

                        // Check if it's a media file by extension
                        const mediaExtensions = ['.jpg', '.jpeg', '.png', '.gif', '.svg', '.webp', '.ico',
                                                '.mp4', '.webm', '.ogg', '.mp3', '.wav', '.pdf'];
                        const isMedia = mediaExtensions.some(ext => urlPath.endsWith(ext));

                        if (isMedia) {
                            type = 'media';
                        } else if (urlDomain !== startDomain) {
                            type = 'external';
                        }
                    } catch (e) {
                        // If URL parsing fails, default to internal
                        console.warn('[Jobs] Could not parse URL:', url);
                    }

                    return {
                        url: url,
                        type: type,
                        level: index === 0 ? 0 : 1,
                        parent: index === 0 ? null : startUrl
                    };
                }));

                console.log('[Jobs] Reconstructed urlDataList:', urlDataList.length, 'items');
                console.log('[Jobs] Reconstructed sample:', urlDataList.slice(0, 3));
            } else {
                console.warn('[Jobs] Fallback not triggered. Checks:');
                console.warn('  - urlDataList.length === 0:', urlDataList.length === 0);
                console.warn('  - job.result.discovered_urls exists:', !!job.result.discovered_urls);
                console.warn('  - job.result.discovered_urls.length:', job.result.discovered_urls?.length);
            }

            if (urlDataList.length > 0) {
                // Set URL input field and dropdown to Map Site mode
                const startUrl = job.params?.start_url || urlDataList[0].url;
                document.getElementById('manual-url-input').value = startUrl;
                document.getElementById('url-action-type').value = 'map';

                // Store the URLs globally
                discoveredUrls = urlDataList;

                // Display URLs in the current view mode
                if (currentViewMode === 'tree') {
                    displayUrls(urlDataList);
                } else {
                    displayUrlsFlat(urlDataList);
                }

                // Show URL list and extraction controls
                document.getElementById('url-list').classList.add('show');
                document.getElementById('extraction-controls').style.display = 'block';
                document.getElementById('search-box').style.display = 'block';
                document.getElementById('link-filters').style.display = 'flex';
                document.getElementById('view-controls').style.display = 'flex';

                showStatus(`Loaded ${urlDataList.length} URLs from site mapping job`, 'success');
            } else {
                console.warn('[Jobs] No URLs found. job.result:', job.result);
                showStatus('No URLs found in job result', 'warning');
            }
        } else if (job.type === 'single_page') {
            // For single page jobs, restore the URL in the manual URL input
            const url = job.params.url || '';

            if (url) {
                document.getElementById('manual-url-input').value = url;
                document.getElementById('url-action-type').value = 'scrape';

                // Show progress for in-progress jobs
                if (job.status === 'processing') {
                    updateProgress(job.progress.current, job.progress.total, job.progress.message);
                    showStatus(`Job in progress: ${job.progress.message}`, 'info');
                } else if (job.status === 'completed') {
                    showStatus(`Job completed: ${job.result?.filename || 'page.md'}`, 'success');
                } else if (job.status === 'failed') {
                    showStatus(`Job failed: ${job.error}`, 'error');
                } else {
                    showStatus(`Job loaded: ${url}`, 'success');
                }
            } else {
                showStatus('No URL found in job params', 'warning');
            }
        } else {
            showStatus('Cannot load context for this job type', 'warning');
        }
    } catch (error) {
        console.error('[Jobs] Error loading job context:', error);
        showStatus('Failed to load job context', 'error');
    }
}

// Helper: Check if timestamp is recent (within last hour)
function isRecent(timestamp) {
    if (!timestamp) return false;
    const time = new Date(timestamp);
    const now = new Date();
    return (now - time) < 3600000; // 1 hour in milliseconds
}

// Remove a single job from the backend
async function removeJob(jobId) {
    console.log('[Jobs] Removing job from backend:', jobId);

    try {
        // Get API URL
        const storage = await chrome.storage.local.get(['apiUrl']);
        const apiUrl = storage.apiUrl || 'http://localhost:8077';

        // Delete from backend
        const response = await fetch(`${apiUrl}/jobs/${jobId}`, {
            method: 'DELETE'
        });

        if (!response.ok) {
            throw new Error(`Failed to delete job: ${response.status}`);
        }

        // Refresh jobs list from backend
        await loadJobs();

        showStatus('Job removed', 'info');
    } catch (error) {
        console.error('[Jobs] Error removing job:', error);
        showStatus('Failed to remove job', 'error');
    }
}

// Pause a job
async function pauseJob(jobId) {
    console.log('[Jobs] Pausing job:', jobId);

    try {
        const response = await chrome.runtime.sendMessage({
            action: 'PAUSE_JOB',
            jobId: jobId
        });

        if (response && response.success) {
            showStatus('Job paused successfully', 'success');
            await loadActiveJobs(); // Refresh list
        } else {
            throw new Error(response.error || 'Failed to pause job');
        }
    } catch (error) {
        console.error('[Jobs] Error pausing job:', error);
        showStatus(`Failed to pause job: ${error.message}`, 'error');
    }
}

// Resume a job
async function resumeJob(jobId) {
    console.log('[Jobs] Resuming job:', jobId);

    try {
        const response = await chrome.runtime.sendMessage({
            action: 'RESUME_JOB',
            jobId: jobId
        });

        if (response && response.success) {
            showStatus('Job resumed successfully', 'success');
            await loadActiveJobs(); // Refresh list
        } else {
            throw new Error(response.error || 'Failed to resume job');
        }
    } catch (error) {
        console.error('[Jobs] Error resuming job:', error);
        showStatus(`Failed to resume job: ${error.message}`, 'error');
    }
}

// Stop a job
async function stopJob(jobId) {
    console.log('[Jobs] Stopping job:', jobId);

    try {
        const response = await chrome.runtime.sendMessage({
            action: 'STOP_JOB',
            jobId: jobId
        });

        if (response && response.success) {
            showStatus('Job stopped. Discovered data preserved.', 'success');
            await loadActiveJobs(); // Refresh list
        } else {
            throw new Error(response.error || 'Failed to stop job');
        }
    } catch (error) {
        console.error('[Jobs] Error stopping job:', error);
        showStatus(`Failed to stop job: ${error.message}`, 'error');
    }
}

// View job progress
async function viewJobProgress(job) {
    console.log('[Jobs] Viewing progress for job:', job.id);

    try {
        // For site mapping jobs, load the discovered URLs
        if (job.type === 'site_map') {
            if (job.result && job.result.discovered_urls) {
                // Load URLs into site mapping section
                await loadJobContext(job);
                showStatus(`Loaded ${job.result.discovered_urls.length} discovered URLs`, 'success');
            } else {
                // Fetch current progress from backend
                const storage = await chrome.storage.local.get(['apiUrl']);
                const apiUrl = storage.apiUrl || 'http://localhost:8077';

                const response = await fetch(`${apiUrl}/jobs/${job.id}`);
                if (!response.ok) {
                    throw new Error('Failed to fetch job progress');
                }

                const jobData = await response.json();
                const progress = jobData.progress || {};

                showStatus(`Job progress: ${progress.message || 'No progress data'}`, 'info');
            }
        } else {
            // For other job types, show progress
            const progress = job.progress || {};
            showStatus(`Progress: ${progress.message || 'No progress data available'}`, 'info');
        }
    } catch (error) {
        console.error('[Jobs] Error viewing job progress:', error);
        showStatus(`Failed to view progress: ${error.message}`, 'error');
    }
}

// Clear all completed/failed jobs
async function clearCompletedJobs() {
    console.log('[Jobs] Clearing completed jobs');

    try {
        // Get API URL and current jobs
        const storage = await chrome.storage.local.get(['apiUrl']);
        const apiUrl = storage.apiUrl || 'http://localhost:8077';

        // Get all jobs from backend
        const response = await fetch(`${apiUrl}/jobs?limit=100`);
        if (!response.ok) {
            throw new Error(`Failed to fetch jobs: ${response.status}`);
        }

        const data = await response.json();
        const allJobs = data.jobs || [];

        // Delete completed/failed jobs from backend
        const deletePromises = allJobs
            .filter(job => job.status === 'completed' || job.status === 'failed')
            .map(job => fetch(`${apiUrl}/jobs/${job.id}`, { method: 'DELETE' }));

        await Promise.all(deletePromises);

        // Refresh jobs list from backend
        await loadJobs();

        showStatus('Completed jobs cleared', 'info');
    } catch (error) {
        console.error('[Jobs] Error clearing completed jobs:', error);
        showStatus('Failed to clear completed jobs', 'error');
    }
}

// Execute URL action (scrape or map)
async function executeUrlAction() {
    const urlInput = document.getElementById('manual-url-input');
    const actionType = document.getElementById('url-action-type').value;
    const url = urlInput.value.trim();

    if (!url) {
        showStatus('Please enter a URL', 'error');
        return;
    }

    // Validate URL format
    try {
        new URL(url);
    } catch (e) {
        showStatus('Invalid URL format', 'error');
        return;
    }

    if (actionType === 'map') {
        // Map site - use the existing mapSite logic but with manual URL
        console.log('[URL Action] Mapping site:', url);
        await mapSiteFromUrl(url);
    } else {
        // Scrape page
        console.log('[URL Action] Scraping page:', url);
        await scrapeManualUrl(url);
    }
}

// Map site from manual URL
async function mapSiteFromUrl(url) {
    const depth = document.getElementById('depth-select').value;

    showStatus(`Mapping site: ${url} (depth: ${depth})`, 'info');

    try {
        const result = await chrome.runtime.sendMessage({
            action: 'mapSite',
            url: url,
            depth: parseInt(depth)
        });

        if (result.success) {
            discoveredUrls = result.urls;
            displayDiscoveredUrls(result.urls);
            showStatus(`Discovered ${result.urls.length} URLs`, 'success');
        } else {
            showStatus(`Error: ${result.error}`, 'error');
        }
    } catch (error) {
        console.error('[Map Site] Error:', error);
        showStatus(`Failed to map site: ${error.message}`, 'error');
    }
}

// Scrape manually entered URL
async function scrapeManualUrl(url) {
    showStatus(`Fetching ${url}...`, 'info');

    try {
        // Fetch the URL
        const response = await fetch(url);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const html = await response.text();
        const title = extractTitleFromHTML(html) || url;

        console.log('[Manual Scrape] Fetched HTML, size:', html.length);

        // Process the HTML using the standard extraction flow
        await processPage({
            url: url,
            html: html,
            title: title
        });

        // Clear the input
        document.getElementById('manual-url-input').value = '';
    } catch (error) {
        console.error('[Manual Scrape] Error:', error);
        showStatus(`Failed to scrape URL: ${error.message}`, 'error');
    }
}

// Open extension in a new tab
function openInTab() {
    // Get the extension URL for the popup
    const popupUrl = chrome.runtime.getURL('popup.html');

    // Open in a new tab
    chrome.tabs.create({ url: popupUrl });

    // Close the popup (only works if opened as popup, not if already in tab)
    window.close();
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

// Helper: Extract title from HTML
function extractTitleFromHTML(html) {
    const titleMatch = html.match(/<title[^>]*>([^<]+)<\/title>/i);
    return titleMatch ? titleMatch[1].trim() : null;
}
