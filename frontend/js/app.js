/**
 * RevAI - Main Application Logic
 * Milestone 1 Foundation & System Diagnostics
 */
document.addEventListener('DOMContentLoaded', () => {
  const statusPill = document.getElementById('backendStatusPill');
  const statusText = document.getElementById('backendStatusText');
  const pingButton = document.getElementById('pingBackendBtn');
  
  // Diagnostic fields
  const diagEndpoint = document.getElementById('diagEndpoint');
  const diagStatus = document.getElementById('diagStatus');
  const diagLatency = document.getElementById('diagLatency');
  const diagEnv = document.getElementById('diagEnv');
  const diagVersion = document.getElementById('diagVersion');

  // Set initial static config values
  if (diagEndpoint) {
    diagEndpoint.textContent = `${CONFIG.API_BASE_URL}/health`;
  }

  /**
   * Run health check and update UI diagnostics.
   */
  async function performHealthCheck() {
    if (statusText) statusText.textContent = 'Checking...';
    if (statusPill) {
      statusPill.className = 'status-pill';
    }

    const result = await API.checkHealth();

    if (result.success && result.data) {
      const data = result.data;
      if (statusPill) {
        statusPill.className = 'status-pill connected';
      }
      if (statusText) {
        statusText.textContent = `Connected (${result.latencyMs}ms)`;
      }
      if (diagStatus) {
        diagStatus.textContent = data.status || 'healthy';
        diagStatus.style.color = 'var(--color-success)';
      }
      if (diagLatency) {
        diagLatency.textContent = `${result.latencyMs} ms`;
      }
      if (diagEnv) {
        diagEnv.textContent = data.environment || 'development';
      }
      if (diagVersion) {
        diagVersion.textContent = data.version || CONFIG.VERSION;
      }
    } else {
      if (statusPill) {
        statusPill.className = 'status-pill error';
      }
      if (statusText) {
        statusText.textContent = 'Backend Offline';
      }
      if (diagStatus) {
        diagStatus.textContent = 'Offline / Connection Refused';
        diagStatus.style.color = 'var(--color-danger)';
      }
      if (diagLatency) {
        diagLatency.textContent = result.latencyMs ? `${result.latencyMs} ms (failed)` : 'N/A';
      }
      if (diagEnv) {
        diagEnv.textContent = 'Unknown (Server unreachable)';
      }
      if (diagVersion) {
        diagVersion.textContent = 'N/A';
      }
    }
  }

  // Bind ping button
  if (pingButton) {
    pingButton.addEventListener('click', async () => {
      pingButton.disabled = true;
      const originalText = pingButton.textContent;
      pingButton.textContent = 'Testing connection...';
      await performHealthCheck();
      pingButton.textContent = originalText;
      pingButton.disabled = false;
    });
  }

  // Initial health check on page load
  performHealthCheck();

  // Periodically check health
  setInterval(performHealthCheck, CONFIG.HEALTH_CHECK_INTERVAL_MS);
});
