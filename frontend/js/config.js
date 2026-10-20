/**
 * Compute the appropriate API base URL dynamically:
 * - When served from any web origin (unified deployment, production domain, or port 8000),
 *   relative '/api' ensures requests reach the same origin seamlessly without CORS.
 * - When served from a decoupled local dev server (e.g., port 5500, 3000) or file://,
 *   fall back to 'http://127.0.0.1:8000/api'.
 */
function resolveApiBaseUrl() {
  const isLocalDevPort = ['5500', '3000', '5173', '8080'].includes(window.location.port);
  const isLocalHost = ['localhost', '127.0.0.1'].includes(window.location.hostname);

  if (window.location.protocol === 'file:') {
    return 'http://127.0.0.1:8000/api';
  }

  // Local frontend server pointing to backend
  if (isLocalHost && isLocalDevPort) {
    return 'http://127.0.0.1:8000/api';
  }

  // Unified deployment (production or local port 8000) uses same-origin relative '/api'
  return '/api';
}

const CONFIG = {
  API_BASE_URL: resolveApiBaseUrl(),
  HEALTH_CHECK_INTERVAL_MS: 30000,
  APP_NAME: 'RevAI',
  VERSION: '0.1.0',
  MAX_UPLOAD_SIZE_MB: 25,
  MAX_QUESTIONS: 50,
  MIN_QUESTIONS: 1,
  MIN_TIME_MINUTES: 1
};

// Freeze configuration to prevent accidental runtime mutations
Object.freeze(CONFIG);

