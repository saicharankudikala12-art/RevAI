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
  },

  /**
   * Request Gemini AI revision test generation.
   * @param {string} extractedText - Text from the study PDF.
   * @param {number} timeRemaining - Available study time in minutes.
   * @param {number} questionCount - Number of questions (1-50).
   * @returns {Promise<{success: boolean, data?: object, status?: number, error?: string}>}
   */
  async generateRevisionTest(extractedText, timeRemaining, questionCount) {
    try {
      const response = await fetch(`${CONFIG.API_BASE_URL}/revision/generate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        body: JSON.stringify({
          extracted_text: extractedText,
          time_remaining: timeRemaining,
          question_count: questionCount
        })
      });

      let json = null;
      try {
        json = await response.json();
      } catch (parseErr) {
        json = null;
      }

      if (!response.ok) {
        let errorMsg = "We couldn't generate your revision test right now. Please try again.";
        if (json && json.detail) {
          if (typeof json.detail === 'string') {
            errorMsg = json.detail;
          } else if (Array.isArray(json.detail)) {
            errorMsg = json.detail.map(d => d.msg || d.detail || JSON.stringify(d)).join('; ');
          }
        } else if (response.status === 503) {
          errorMsg = 'AI generation is not configured yet. Please check the backend Gemini configuration.';
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
  },

  /**
   * Submit test answers for objective server-side scoring and detailed explanation review.
   * @param {object} payload - { test_token?: string, questions?: Array, user_answers: object, time_spent_seconds?: number }
   * @returns {Promise<{success: boolean, data?: object, status?: number, error?: string}>}
   */
  async submitRevisionTest(payload) {
    try {
      const response = await fetch(`${CONFIG.API_BASE_URL}/revision/submit`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        body: JSON.stringify(payload)
      });

      let json = null;
      try {
        json = await response.json();
      } catch (parseErr) {
        json = null;
      }

      if (!response.ok) {
        let errorMsg = 'Failed to submit test.';
        if (json && json.detail) {
          if (typeof json.detail === 'string') {
            errorMsg = json.detail;
          } else if (Array.isArray(json.detail)) {
            errorMsg = json.detail.map(d => d.msg || d.detail || JSON.stringify(d)).join('; ');
          }
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


