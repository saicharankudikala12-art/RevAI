/**
 * RevAI - Main Application Controller
 * Milestone 3: Student-Facing Revision Pipeline Flow
 * PDF Upload -> PDF Processing -> Revision Settings -> Ready to Generate
 */
document.addEventListener('DOMContentLoaded', () => {
  // -------------------------------------------------------------
  // Application State
  // -------------------------------------------------------------
  const state = {
    currentStep: 1, // 1: PDF Upload, 2: Revision Settings, 3: Ready to Generate
    selectedFile: null,
    pdfResult: null, // { filename, page_count, word_count, text_length, preview, extracted_text }
    timeMinutes: 120,
    questionCount: 20,
    isUploading: false
  };

  // -------------------------------------------------------------
  // DOM Elements
  // -------------------------------------------------------------
  // Backend Status
  const statusPill = document.getElementById('backendStatusPill');
  const statusText = document.getElementById('backendStatusText');
  const footerApiUrl = document.getElementById('footerApiUrl');

  // Stepper Elements
  const stepItems = [
    document.getElementById('stepItem1'),
    document.getElementById('stepItem2'),
    document.getElementById('stepItem3'),
    document.getElementById('stepItem4'),
    document.getElementById('stepItem5')
  ];
  const stepIcons = [
    document.getElementById('stepIcon1'),
    document.getElementById('stepIcon2'),
    document.getElementById('stepIcon3'),
    document.getElementById('stepIcon4'),
    document.getElementById('stepIcon5')
  ];

  // Error Banner
  const uploadErrorBanner = document.getElementById('uploadErrorBanner');
  const uploadErrorText = document.getElementById('uploadErrorText');
  const dismissErrorBtn = document.getElementById('dismissErrorBtn');

  // Step 1: Upload Elements
  const stepUploadSection = document.getElementById('stepUploadSection');
  const dropZone = document.getElementById('dropZone');
  const pdfFileInput = document.getElementById('pdfFileInput');
  const choosePdfBtn = document.getElementById('choosePdfBtn');
  const uploadLoadingState = document.getElementById('uploadLoadingState');
  const processingFilename = document.getElementById('processingFilename');

  // Step 1: Processing Result Elements
  const pdfResultSection = document.getElementById('pdfResultSection');
  const resultFilename = document.getElementById('resultFilename');
  const resultPageCount = document.getElementById('resultPageCount');
  const resultWordCount = document.getElementById('resultWordCount');
  const resultCharCount = document.getElementById('resultCharCount');
  const resultPreviewText = document.getElementById('resultPreviewText');
  const changePdfBtn = document.getElementById('changePdfBtn');

  // Step 2: Revision Settings Elements
  const stepSettingsSection = document.getElementById('stepSettingsSection');
  const revisionSettingsForm = document.getElementById('revisionSettingsForm');
  const timeInput = document.getElementById('timeInput');
  const timeError = document.getElementById('timeError');
  const timePresets = document.getElementById('timePresets');
  const questionsInput = document.getElementById('questionsInput');
  const questionsError = document.getElementById('questionsError');
  const questionsPresets = document.getElementById('questionsPresets');
  const paceEstimateText = document.getElementById('paceEstimateText');
  const createTestBtn = document.getElementById('createTestBtn');

  // Step 3: Ready Elements
  const stepReadySection = document.getElementById('stepReadySection');
  const readyFilename = document.getElementById('readyFilename');
  const readyDocStats = document.getElementById('readyDocStats');
  const readyTime = document.getElementById('readyTime');
  const readyQuestions = document.getElementById('readyQuestions');
  const readyPace = document.getElementById('readyPace');
  const editSettingsBtn = document.getElementById('editSettingsBtn');
  const uploadNewPdfBtn = document.getElementById('uploadNewPdfBtn');

  // Set footer API target URL
  if (footerApiUrl) {
    footerApiUrl.textContent = CONFIG.API_BASE_URL.replace(/\/api$/, '');
  }

  // -------------------------------------------------------------
  // Stepper Management
  // -------------------------------------------------------------
  /**
   * Update the stepper visualization to reflect current pipeline progress.
   * Visual indicators per Milestone 3 specification:
   * ✓ for completed, ● for active, ○ for upcoming/locked.
   * @param {number} step - Current step (1, 2, or 3)
   */
  function updateStepper(step) {
    state.currentStep = step;

    // Reset base styles
    stepItems.forEach((item, index) => {
      if (!item) return;
      item.classList.remove('active', 'completed', 'clickable');
      const icon = stepIcons[index];

      const stepNum = index + 1;
      if (stepNum < step) {
        // Step completed
        item.classList.add('completed', 'clickable');
        if (icon) icon.textContent = '✓';
      } else if (stepNum === step) {
        // Current active step
        item.classList.add('active');
        if (icon) icon.textContent = '●';
      } else {
        // Upcoming locked step
        if (icon) icon.textContent = '○';
      }
    });
  }

  // Allow clicking on completed stepper items to return to that step
  stepItems.forEach((item, index) => {
    if (!item) return;
    item.addEventListener('click', () => {
      const targetStep = index + 1;
      // Allow navigation to completed steps or current step
      if (targetStep === 1 && state.currentStep > 1) {
        // Return to upload view (or show upload section)
        transitionToStep(1);
      } else if (targetStep === 2 && state.currentStep === 3) {
        // Return to settings view
        transitionToStep(2);
      }
    });
  });

  /**
   * Transition UI views between steps smoothly.
   * @param {number} targetStep 
   */
  function transitionToStep(targetStep) {
    if (targetStep === 1) {
      // Step 1: Upload & Result view
      stepUploadSection.classList.remove('hidden');
      stepSettingsSection.classList.add('hidden');
      stepReadySection.classList.add('hidden');
      updateStepper(1);
      stepUploadSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    } else if (targetStep === 2) {
      // Step 2: Settings view
      if (!state.pdfResult) {
        showError('Please upload and process a study PDF first.');
        transitionToStep(1);
        return;
      }
      stepUploadSection.classList.remove('hidden');
      stepSettingsSection.classList.remove('hidden');
      stepReadySection.classList.add('hidden');
      updateStepper(2);
      stepSettingsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    } else if (targetStep === 3) {
      // Step 3: Ready view
      stepUploadSection.classList.add('hidden');
      stepSettingsSection.classList.add('hidden');
      stepReadySection.classList.remove('hidden');
      updateStepper(3);
      stepReadySection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }

  // -------------------------------------------------------------
  // Error Banner Helper
  // -------------------------------------------------------------
  function showError(message) {
    if (uploadErrorBanner && uploadErrorText) {
      uploadErrorText.textContent = message;
      uploadErrorBanner.classList.remove('hidden');
      uploadErrorBanner.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }

  function hideError() {
    if (uploadErrorBanner) {
      uploadErrorBanner.classList.add('hidden');
    }
  }

  if (dismissErrorBtn) {
    dismissErrorBtn.addEventListener('click', hideError);
  }

  // -------------------------------------------------------------
  // Step 1: File Validation & Upload Logic
  // -------------------------------------------------------------
  /**
   * Validate file criteria before network transfer.
   * @param {File} file 
   * @returns {{valid: boolean, error?: string}}
   */
  function validateFile(file) {
    if (!file) {
      return { valid: false, error: 'No file was selected. Please choose a PDF file.' };
    }

    const fileName = file.name.trim();
    if (!fileName.toLowerCase().endsWith('.pdf')) {
      return { valid: false, error: 'Invalid file format. Please select a valid PDF file (.pdf extension).' };
    }

    if (file.size === 0) {
      return { valid: false, error: 'The selected file is empty (0 bytes). Please upload a valid PDF.' };
    }

    const maxBytes = CONFIG.MAX_UPLOAD_SIZE_MB * 1024 * 1024;
    if (file.size > maxBytes) {
      const sizeMb = (file.size / (1024 * 1024)).toFixed(1);
      return { 
        valid: false, 
        error: `File size (${sizeMb} MB) exceeds the maximum allowed limit of ${CONFIG.MAX_UPLOAD_SIZE_MB} MB. Please upload a smaller PDF.` 
      };
    }

    return { valid: true };
  }

  /**
   * Handle selected or dropped file.
   * @param {File} file 
   */
  async function handleFileSelected(file) {
    if (state.isUploading) return;

    hideError();

    // Client-side validation
    const validation = validateFile(file);
    if (!validation.valid) {
      showError(validation.error);
      return;
    }

    state.selectedFile = file;
    state.isUploading = true;

    // Show loading state
    dropZone.classList.add('hidden');
    uploadLoadingState.classList.remove('hidden');
    if (processingFilename) {
      processingFilename.textContent = file.name;
    }

    // Call Backend API
    const response = await API.uploadPDF(file);

    state.isUploading = false;
    uploadLoadingState.classList.add('hidden');

    if (!response.success) {
      // Restore dropzone and show error
      dropZone.classList.remove('hidden');
      showError(response.error || 'Failed to process PDF.');
      return;
    }

    // Processing succeeded
    const data = response.data;
    state.pdfResult = data;

    // Display PDF Processing Result in UI
    if (resultFilename) resultFilename.textContent = data.filename;
    if (resultPageCount) {
      resultPageCount.textContent = `${data.page_count} ${data.page_count === 1 ? 'page' : 'pages'}`;
    }
    if (resultWordCount) {
      resultWordCount.textContent = `${data.word_count.toLocaleString()} words`;
    }
    if (resultCharCount) {
      resultCharCount.textContent = `${data.text_length.toLocaleString()} chars`;
    }
    if (resultPreviewText) {
      resultPreviewText.textContent = data.preview || '(No preview text available)';
    }

    // Reveal result card
    pdfResultSection.classList.remove('hidden');

    // Reveal Step 2: Settings section
    stepSettingsSection.classList.remove('hidden');
    updateStepper(2);

    // Smooth scroll down to settings
    setTimeout(() => {
      stepSettingsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 150);
  }

  // -------------------------------------------------------------
  // Drag & Drop Event Listeners
  // -------------------------------------------------------------
  if (dropZone) {
    ['dragenter', 'dragover'].forEach(eventName => {
      dropZone.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        if (state.isUploading) return;
        dropZone.classList.add('dragover');
      });
    });

    ['dragleave', 'drop'].forEach(eventName => {
      dropZone.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropZone.classList.remove('dragover');
      });
    });

    dropZone.addEventListener('drop', (e) => {
      if (state.isUploading) return;
      const files = e.dataTransfer.files;
      if (files && files.length > 0) {
        handleFileSelected(files[0]);
      }
    });

    // Clicking dropzone opens file picker if not clicking Choose PDF button directly
    dropZone.addEventListener('click', (e) => {
      if (state.isUploading) return;
      if (e.target !== choosePdfBtn && !choosePdfBtn.contains(e.target)) {
        if (pdfFileInput) pdfFileInput.click();
      }
    });

    // Keyboard support for drop zone accessibility
    dropZone.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        if (pdfFileInput && !state.isUploading) {
          pdfFileInput.click();
        }
      }
    });
  }

  // Choose PDF Button
  if (choosePdfBtn) {
    choosePdfBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      if (state.isUploading) return;
      if (pdfFileInput) pdfFileInput.click();
    });
  }

  // Hidden File Input Change
  if (pdfFileInput) {
    pdfFileInput.addEventListener('change', () => {
      if (pdfFileInput.files && pdfFileInput.files.length > 0) {
        handleFileSelected(pdfFileInput.files[0]);
        // Reset input value so re-selecting same file triggers change
        pdfFileInput.value = '';
      }
    });
  }

  // Change PDF / Upload Another PDF
  function resetToUpload() {
    state.selectedFile = null;
    state.pdfResult = null;
    state.isUploading = false;

    hideError();

    // Reset UI visibility
    dropZone.classList.remove('hidden');
    uploadLoadingState.classList.add('hidden');
    pdfResultSection.classList.add('hidden');
    stepSettingsSection.classList.add('hidden');
    stepReadySection.classList.add('hidden');
    stepUploadSection.classList.remove('hidden');

    updateStepper(1);
    stepUploadSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  if (changePdfBtn) {
    changePdfBtn.addEventListener('click', resetToUpload);
  }

  if (uploadNewPdfBtn) {
    uploadNewPdfBtn.addEventListener('click', resetToUpload);
  }

  // -------------------------------------------------------------
  // Step 2: Revision Settings Validation & Logic
  // -------------------------------------------------------------
  /**
   * Recalculate and display the pacing estimate.
   */
  function updatePaceEstimate() {
    const rawTime = parseFloat(timeInput.value);
    const rawQuestions = parseFloat(questionsInput.value);

    if (isNaN(rawTime) || rawTime <= 0 || isNaN(rawQuestions) || rawQuestions <= 0) {
      if (paceEstimateText) paceEstimateText.textContent = '--';
      return;
    }

    const pace = (rawTime / rawQuestions).toFixed(1);
    if (paceEstimateText) {
      paceEstimateText.textContent = `~${pace} minutes per question`;
    }
  }

  /**
   * Validate the Time Remaining input.
   * @returns {{valid: boolean, value?: number, error?: string}}
   */
  function validateTimeInput() {
    const rawValue = timeInput.value.trim();
    if (!rawValue) {
      return { valid: false, error: 'Please enter your remaining revision time in minutes.' };
    }

    const num = Number(rawValue);
    if (isNaN(num) || num <= 0) {
      return { valid: false, error: 'Please enter a valid time greater than 0 minutes.' };
    }

    if (!Number.isInteger(num)) {
      return { valid: false, error: 'Please enter a whole number of minutes.' };
    }

    return { valid: true, value: num };
  }

  /**
   * Validate the Target Question Count input.
   * @returns {{valid: boolean, value?: number, error?: string}}
   */
  function validateQuestionsInput() {
    const rawValue = questionsInput.value.trim();
    if (!rawValue) {
      return { valid: false, error: 'Please enter the number of questions you want.' };
    }

    const num = Number(rawValue);
    if (isNaN(num) || num <= 0) {
      return { valid: false, error: 'Please request at least 1 practice question.' };
    }

    if (!Number.isInteger(num)) {
      return { valid: false, error: 'Please enter a whole number of questions.' };
    }

    if (num > CONFIG.MAX_QUESTIONS) {
      return { 
        valid: false, 
        error: `Maximum question limit is ${CONFIG.MAX_QUESTIONS}. Please enter ${CONFIG.MAX_QUESTIONS} or fewer questions.` 
      };
    }

    return { valid: true, value: num };
  }

  // Live input events for Time
  if (timeInput) {
    timeInput.addEventListener('input', () => {
      // Clear error on input
      timeInput.classList.remove('has-error');
      if (timeError) timeError.classList.add('hidden');
      updatePaceEstimate();
      syncPresetChip(timePresets, timeInput.value);
    });
  }

  // Live input events for Questions
  if (questionsInput) {
    questionsInput.addEventListener('input', () => {
      // Clear error on input
      questionsInput.classList.remove('has-error');
      if (questionsError) questionsError.classList.add('hidden');
      updatePaceEstimate();
      syncPresetChip(questionsPresets, questionsInput.value);
    });
  }

  /**
   * Sync active preset chip with manual input value.
   */
  function syncPresetChip(container, value) {
    if (!container) return;
    const chips = container.querySelectorAll('.preset-chip');
    chips.forEach(chip => {
      const chipVal = chip.dataset.time || chip.dataset.questions;
      if (chipVal === String(value)) {
        chip.classList.add('active');
      } else {
        chip.classList.remove('active');
      }
    });
  }

  // Preset Chips: Time
  if (timePresets) {
    timePresets.addEventListener('click', (e) => {
      const chip = e.target.closest('.preset-chip');
      if (!chip) return;
      const minutes = chip.dataset.time;
      if (minutes && timeInput) {
        timeInput.value = minutes;
        timeInput.classList.remove('has-error');
        if (timeError) timeError.classList.add('hidden');
        syncPresetChip(timePresets, minutes);
        updatePaceEstimate();
      }
    });
  }

  // Preset Chips: Questions
  if (questionsPresets) {
    questionsPresets.addEventListener('click', (e) => {
      const chip = e.target.closest('.preset-chip');
      if (!chip) return;
      const count = chip.dataset.questions;
      if (count && questionsInput) {
        questionsInput.value = count;
        questionsInput.classList.remove('has-error');
        if (questionsError) questionsError.classList.add('hidden');
        syncPresetChip(questionsPresets, count);
        updatePaceEstimate();
      }
    });
  }

  // Initialize pace estimate on page load
  updatePaceEstimate();

  // -------------------------------------------------------------
  // Step 2 -> Step 3: Create Revision Test Button
  // -------------------------------------------------------------
  if (createTestBtn) {
    createTestBtn.addEventListener('click', () => {
      // 1. Verify PDF has been processed
      if (!state.pdfResult) {
        showError('Please upload and process a study PDF before configuring settings.');
        transitionToStep(1);
        return;
      }

      let hasValidationErrors = false;

      // 2. Validate Time
      const timeValidation = validateTimeInput();
      if (!timeValidation.valid) {
        timeInput.classList.add('has-error');
        if (timeError) {
          timeError.textContent = timeValidation.error;
          timeError.classList.remove('hidden');
        }
        hasValidationErrors = true;
      } else {
        timeInput.classList.remove('has-error');
        if (timeError) timeError.classList.add('hidden');
      }

      // 3. Validate Questions
      const questionsValidation = validateQuestionsInput();
      if (!questionsValidation.valid) {
        questionsInput.classList.add('has-error');
        if (questionsError) {
          questionsError.textContent = questionsValidation.error;
          questionsError.classList.remove('hidden');
        }
        hasValidationErrors = true;
      } else {
        questionsInput.classList.remove('has-error');
        if (questionsError) questionsError.classList.add('hidden');
      }

      if (hasValidationErrors) {
        return;
      }

      // 4. Store validated values in frontend state
      state.timeMinutes = timeValidation.value;
      state.questionCount = questionsValidation.value;

      // 5. Populate Ready View Summary
      if (readyFilename) readyFilename.textContent = state.pdfResult.filename;
      if (readyDocStats) {
        readyDocStats.textContent = `${state.pdfResult.page_count} ${state.pdfResult.page_count === 1 ? 'page' : 'pages'} · ${state.pdfResult.word_count.toLocaleString()} words`;
      }
      if (readyTime) readyTime.textContent = `${state.timeMinutes} minutes`;
      if (readyQuestions) readyQuestions.textContent = `${state.questionCount}`;
      if (readyPace) {
        const pace = (state.timeMinutes / state.questionCount).toFixed(1);
        readyPace.textContent = `${pace} min per question`;
      }

      // 6. Transition to Step 3 (Ready State)
      transitionToStep(3);

      /* IMPORTANT: DO NOT call Gemini API or generate fake questions here.
         Milestone 3 concludes at this verified 'Ready to Generate' state. */
    });
  }

  // Edit Settings button (returns from Ready state back to Step 2)
  if (editSettingsBtn) {
    editSettingsBtn.addEventListener('click', () => {
      transitionToStep(2);
    });
  }

  // -------------------------------------------------------------
  // Backend Connection Health Monitor
  // -------------------------------------------------------------
  async function performHealthCheck() {
    if (statusText) statusText.textContent = 'Checking...';
    if (statusPill) statusPill.className = 'status-pill';

    const result = await API.checkHealth();

    if (result.success && result.data) {
      if (statusPill) statusPill.className = 'status-pill connected';
      if (statusText) statusText.textContent = `Connected (${result.latencyMs}ms)`;
    } else {
      if (statusPill) statusPill.className = 'status-pill error';
      if (statusText) statusText.textContent = 'Backend Offline';
    }
  }

  // Perform initial health check
  performHealthCheck();

  // Periodically check connection
  setInterval(performHealthCheck, CONFIG.HEALTH_CHECK_INTERVAL_MS);
});
