/**
 * RevAI - API Client
 * Modular fetch client for backend communication
 */
const API = {
  /**
   * Health check request to verify backend availability and latency.
   * @returns {Promise<{success: boolean, data?: object, latencyMs?: number, error?: string}>}
   */
  async checkHealth() {
    const startTime = performance.now();
    try {
      const response = await fetch(`${CONFIG.API_BASE_URL}/health`, {
        method: 'GET',
        headers: {
          'Accept': 'application/json'
        }
      });

      const latencyMs = Math.round(performance.now() - startTime);

      if (!response.ok) {
        return {
          success: false,
          error: `Server responded with HTTP ${response.status}: ${response.statusText}`,
          latencyMs
        };
      }

      const data = await response.json();
      return {
        success: true,
        data,
        latencyMs
      };
    } catch (err) {
      const latencyMs = Math.round(performance.now() - startTime);
      return {
        success: false,
        error: err.message || 'Failed to connect to backend server',
        latencyMs
      };
    }
  }
};
