/**
 * RevAI - Frontend Configuration
 */
const CONFIG = {
  // Use relative '/api' if hosted on the same origin as the backend; fallback to localhost:8000 for local dev
  API_BASE_URL: (window.location.port === '8000') 
    ? '/api' 
    : 'http://localhost:8000/api',
  HEALTH_CHECK_INTERVAL_MS: 30000,
  APP_NAME: 'RevAI',
  VERSION: '0.1.0'
};

// Freeze configuration to prevent accidental runtime mutations
Object.freeze(CONFIG);
