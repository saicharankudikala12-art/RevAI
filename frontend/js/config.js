/**
 * RevAI - Frontend Configuration
 */
const CONFIG = {
  // Use relative '/api' if hosted on port 8000; fallback to http://127.0.0.1:8000/api
  API_BASE_URL: (window.location.port === '8000') 
    ? '/api' 
    : 'http://127.0.0.1:8000/api',
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

