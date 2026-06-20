document.addEventListener('DOMContentLoaded', () => {
    // Elements
    const form = document.getElementById('pipeline-form');
    const sourceUrlInput = document.getElementById('sourceUrl');
    const targetUrlInput = document.getElementById('targetUrl');
    const btnStart = document.getElementById('btn-start');
    const btnVerify = document.getElementById('btn-verify');
    const btnStop = document.getElementById('btn-stop');
    const pipelineBadge = document.getElementById('pipeline-status-badge');
    const statusIndicator = document.querySelector('.status-indicator');
    
    const progressPercent = document.getElementById('progress-percent');
    const progressBarFill = document.getElementById('progress-bar-fill');
    const filesTotal = document.getElementById('files-total');
    
    const activeDocVal = document.getElementById('active-document');
    const statCompleted = document.getElementById('stat-completed');
    const statErrors = document.getElementById('stat-errors');
    const statPending = document.getElementById('stat-pending');
    const targetDocLink = document.getElementById('target-doc-link');
    
    const consoleOutput = document.getElementById('console-output');
    const autoscrollToggle = document.getElementById('autoscroll-toggle');
    const btnCopyLogs = document.getElementById('btn-copy-logs');
    const btnClearConsole = document.getElementById('btn-clear-console');

    let eventSource = null;
    let totalFiles = 0;
    let processedFiles = 0;
    let failedFilesCount = 0;

    // Initialize UI from current server status
    checkStatus();

    // Event Listeners
    form.addEventListener('submit', handleStart);
    btnVerify.addEventListener('click', handleVerify);
    btnStop.addEventListener('click', handleStop);
    btnCopyLogs.addEventListener('click', copyLogsToClipboard);
    btnClearConsole.addEventListener('click', clearConsole);

    targetUrlInput.addEventListener('input', updateDocLink);

    function updateDocLink() {
        const url = targetUrlInput.value.trim();
        if (url && url.startsWith('http')) {
            targetDocLink.href = url;
            targetDocLink.classList.remove('disabled');
        } else {
            targetDocLink.classList.add('disabled');
            targetDocLink.removeAttribute('href');
        }
    }

    function checkStatus() {
        fetch('/status')
            .then(res => res.json())
            .then(data => {
                updateBadge(data.status);
                if (data.sourceUrl) sourceUrlInput.value = data.sourceUrl;
                if (data.targetUrl) {
                    targetUrlInput.value = data.targetUrl;
                    updateDocLink();
                }

                if (data.status === 'RUNNING') {
                    setRunningUI(true);
                    startStreaming();
                } else {
                    setRunningUI(false);
                }
            })
            .catch(err => {
                logLine('system', `[SYSTEM ERROR] Failed to connect to server: ${err.message}`);
            });
    }

    function handleStart(e) {
        e.preventDefault();
        
        const sourceUrl = sourceUrlInput.value.trim();
        const targetUrl = targetUrlInput.value.trim();

        if (!sourceUrl || !targetUrl) return;

        btnStart.disabled = true;
        logLine('system', '🚀 Dispatching start command to pipeline...');

        const formData = new FormData();
        formData.append('sourceUrl', sourceUrl);
        formData.append('targetUrl', targetUrl);
        const isVisible = document.getElementById('visibleBrowser').checked;
        formData.append('visible', isVisible ? 'true' : 'false');

        fetch('/start', {
            method: 'POST',
            body: formData
        })
        .then(res => res.json())
        .then(data => {
            if (data.error) {
                logLine('error', `❌ Startup failed: ${data.error}`);
                btnStart.disabled = false;
            } else {
                totalFiles = 0;
                processedFiles = 0;
                failedFilesCount = 0;
                resetMetrics();
                setRunningUI(true);
                updateBadge('RUNNING');
                targetDocLink.classList.add('hidden');
                targetDocLink.style.display = 'none';
                startStreaming();
            }
        })
        .catch(err => {
            logLine('error', `[SYSTEM ERROR] ${err.message}`);
            btnStart.disabled = false;
        });
    }

    function handleVerify(e) {
        e.preventDefault();
        
        const sourceUrl = sourceUrlInput.value.trim();
        const targetUrl = targetUrlInput.value.trim();

        if (!sourceUrl || !targetUrl) return;

        btnVerify.disabled = true;
        btnStart.disabled = true;
        logLine('system', '🔍 Dispatching standalone verify & heal command...');

        const formData = new FormData();
        formData.append('sourceUrl', sourceUrl);
        formData.append('targetUrl', targetUrl);
        const isVisible = document.getElementById('visibleBrowser').checked;
        formData.append('visible', isVisible ? 'true' : 'false');

        fetch('/verify', {
            method: 'POST',
            body: formData
        })
        .then(res => res.json())
        .then(data => {
            if (data.error) {
                logLine('error', `❌ Startup failed: ${data.error}`);
                btnVerify.disabled = false;
                btnStart.disabled = false;
            } else {
                totalFiles = 0;
                processedFiles = 0;
                failedFilesCount = 0;
                resetMetrics();
                
                setRunningUI(true);
                targetDocLink.classList.add('hidden');
                targetDocLink.style.display = 'none';
                startStreaming();
            }
        })
        .catch(err => {
            logLine('error', `[SYSTEM ERROR] ${err.message}`);
            btnVerify.disabled = false;
            btnStart.disabled = false;
        });
    }

    function handleStop(e) {
        btnStop.disabled = true;
        logLine('warn', '⚠️ Dispatching stop command. Terminating browser automation...');

        fetch('/stop', { method: 'POST' })
            .then(res => res.json())
            .then(data => {
                if (data.error) {
                    logLine('error', `❌ Stop command failed: ${data.error}`);
                    btnStop.disabled = false;
                } else {
                    updateBadge('ABORTED');
                    setRunningUI(false);
                }
            })
            .catch(err => {
                logLine('error', `❌ Network exception on stop: ${err.message}`);
                btnStop.disabled = false;
            });
    }

    function startStreaming() {
        if (eventSource) {
            eventSource.close();
        }

        eventSource = new EventSource('/stream');

        eventSource.onmessage = (event) => {
            const line = event.data;
            parseAndLog(line);
        };

        eventSource.onerror = (err) => {
            logLine('system', '⚠️ Connection to server log stream closed or interrupted.');
            eventSource.close();
            eventSource = null;
            
            // Check status after 3 seconds to see if it ended normally
            setTimeout(checkStatus, 3000);
        };
    }

    function updateBadge(status) {
        statusIndicator.className = 'status-indicator';
        if (status === 'RUNNING') {
            statusIndicator.classList.add('running');
            pipelineBadge.textContent = 'RUNNING';
        } else if (status === 'COMPLETED') {
            statusIndicator.classList.add('completed');
            pipelineBadge.textContent = 'COMPLETED';
        } else if (status === 'ABORTED') {
            statusIndicator.classList.add('error');
            pipelineBadge.textContent = 'ABORTED';
        } else if (status === 'FAILED') {
            statusIndicator.classList.add('error');
            pipelineBadge.textContent = 'FAILED';
        } else {
            statusIndicator.classList.add('idle');
            pipelineBadge.textContent = 'IDLE';
        }
    }

    function setRunningUI(isRunning) {
        btnStart.disabled = isRunning;
        if (btnVerify) btnVerify.disabled = isRunning;
        btnStop.disabled = !isRunning;
        sourceUrlInput.disabled = isRunning;
        targetUrlInput.disabled = isRunning;
    }

    function resetMetrics() {
        progressPercent.textContent = '0%';
        progressBarFill.style.width = '0%';
        if (filesTotal) filesTotal.textContent = '0';
        activeDocVal.textContent = 'None';
        statCompleted.textContent = '0';
        statErrors.textContent = '0';
        statPending.textContent = '0';
    }

    function parseAndLog(line) {
        // Strip out styling wrappers if present
        let cleanLine = line;
        let type = 'info';

        // Categorize lines based on symbols
        if (line.includes('🚀') || line.includes('Phase') || line.includes('LAUNCHING BATCH')) {
            type = 'special';
        } else if (line.includes('✅') || line.includes('SUCCESS')) {
            type = 'success';
        } else if (line.includes('⚠️') || line.includes('retrying')) {
            type = 'warn';
        } else if (line.includes('❌') || line.includes('failed') || line.includes('FAILED')) {
            type = 'error';
        }

        logLine(type, cleanLine);

        // Parse metrics dynamically
        // 1. Total files discovered
        const scanMatch = cleanLine.match(/Scan complete! Total files found in source folder:\s*(\d+)/) || cleanLine.match(/Scanning complete! Found (\d+) files/);
        if (scanMatch) {
            totalFiles = parseInt(scanMatch[1]);
            filesTotal.textContent = totalFiles;
            updateProgress();
        }

        const scanCountMatch = cleanLine.match(/Found file #(\d+):/);
        if (scanCountMatch) {
            const count = parseInt(scanCountMatch[1]);
            if (count > totalFiles) {
                totalFiles = count;
                filesTotal.textContent = totalFiles;
            }
        }

        // 2. Active file being processed
        // Example output: [1/65] Setting up tab for: Physical Security Policy
        const progressMatch = cleanLine.match(/\[(\d+)\/(\d+)\] (?:Setting up tab for|Verifying tab):\s*(.*)/);
        if (progressMatch) {
            processedFiles = parseInt(progressMatch[1]);
            totalFiles = parseInt(progressMatch[2]);
            const title = progressMatch[3].trim();
            
            if (filesTotal) filesTotal.textContent = totalFiles;
            activeDocVal.textContent = title;
            updateProgress();
        }

        // 3. Document details parsed inside copy phase
        const titleMatch = cleanLine.match(/Title\s*→\s*(.*)/);
        if (titleMatch && activeDocVal.textContent === 'None') {
            activeDocVal.textContent = titleMatch[1].trim();
        }

        // 4. Track failures and updates explicit stats
        if (cleanLine.includes('Copy failed') || cleanLine.includes('skipping') || cleanLine.includes('❌') || cleanLine.includes('Failed to set up tab')) {
            // Check if it looks like a skipped file log
            if (cleanLine.includes('skipping') || cleanLine.includes('Copy failed') || cleanLine.includes('Failed to set up tab')) {
                failedFilesCount++;
                updateStatsGrid();
            }
        }

        // 5. Complete state detection
        if (cleanLine.includes('ALL OPERATIONS COMPLETED SUCCESSFULLY') || cleanLine.includes('🎉 SUCCESS!')) {
            updateBadge('COMPLETED');
            setRunningUI(false);
            targetDocLink.classList.remove('hidden');
            targetDocLink.style.display = 'block';
        }
    }

    function updateProgress() {
        if (totalFiles <= 0) return;
        const percent = Math.round((processedFiles / totalFiles) * 100);
        progressPercent.textContent = `${percent}%`;
        progressBarFill.style.width = `${percent}%`;
        
        updateStatsGrid();
    }

    function updateStatsGrid() {
        if (totalFiles <= 0) return;
        const completed = processedFiles - failedFilesCount;
        const pending = totalFiles - processedFiles;
        
        statCompleted.textContent = completed;
        statErrors.textContent = failedFilesCount;
        statPending.textContent = pending;
    }

    function logLine(type, text) {
        const div = document.createElement('div');
        div.className = `console-line ${type}-line`;
        div.textContent = text;
        consoleOutput.appendChild(div);

        if (autoscrollToggle.checked) {
            consoleOutput.scrollTop = consoleOutput.scrollHeight;
        }
    }

    function copyLogsToClipboard() {
        const text = consoleOutput.innerText;
        navigator.clipboard.writeText(text)
            .then(() => {
                logLine('system', '[SYSTEM] Console logs copied to clipboard.');
            })
            .catch(err => {
                alert('Failed to copy logs: ' + err);
            });
    }

    function clearConsole() {
        consoleOutput.innerHTML = '';
        logLine('system', '[SYSTEM] Console buffer cleared.');
    }
});
