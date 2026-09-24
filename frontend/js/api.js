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
  },

  /**
   * Upload and process a study PDF via multipart/form-data.
   * @param {File} file - The PDF file object selected by the user.
   * @returns {Promise<{success: boolean, data?: object, status?: number, error?: string}>}
   */
  async uploadPDF(file) {
    if (!file) {
      return {
        success: false,
        status: 400,
        error: 'No file was provided for upload.'
      };
    }

    const formData = new FormData();
    formData.append('file', file, file.name);

    try {
      const response = await fetch(`${CONFIG.API_BASE_URL}/pdf/upload`, {
        method: 'POST',
        headers: {
          'Accept': 'application/json'
        },
        body: formData
      });

      let json = null;
      try {
        json = await response.json();
      } catch (parseErr) {
        json = null;
      }

      if (!response.ok) {
        let errorMsg = 'Failed to process PDF.';
        if (json && json.detail) {
          if (typeof json.detail === 'string') {
            errorMsg = json.detail;
          } else if (Array.isArray(json.detail)) {
            errorMsg = json.detail.map(d => d.msg || d.detail || JSON.stringify(d)).join('; ');
          }
        } else if (response.status === 413) {
          errorMsg = `File size exceeds the maximum allowed limit of ${CONFIG.MAX_UPLOAD_SIZE_MB} MB.`;
        } else if (response.status === 500) {
          errorMsg = 'An unexpected server error occurred while processing the PDF.';
        } else {
          errorMsg = `Server error (${response.status}: ${response.statusText})`;
        }

        return {
          success: false,
          status: response.status,
          error: errorMsg
        };
      }

      return {
        success: true,
        data: json
      };
    } catch (err) {
      return {
        success: false,
        status: 0,
        error: 'Unable to connect to RevAI backend server at http://127.0.0.1:8000. Please ensure the backend is running.'
      };
    }
  }
};
