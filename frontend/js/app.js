/**
 * RevAI - Main Application Controller
 * Milestone 4: Gemini AI Revision Test Generation & Interactive Question Interface
 * PDF Upload -> PDF Processing -> Revision Settings -> AI Question Generation -> Revision Test
 */
document.addEventListener('DOMContentLoaded', () => {
  // -------------------------------------------------------------
  // Application State
  // -------------------------------------------------------------
  const state = {
    currentStep: 1, // 1: PDF Upload, 2: Revision Settings, 3: Revision Test
    selectedFile: null,
    pdfResult: null, // { filename, page_count, word_count, text_length, preview, extracted_text }
    timeMinutes: 120,
    questionCount: 20,
    isUploading: false,
    isGenerating: false,
    // Milestone 4: Revision Test state
    questions: [], // Array of question objects from Gemini
    provider: 'gemini', // 'gemini' or 'heuristic-fallback'
    currentQuestionIndex: 0,
    userAnswers: {} // Map of question index -> selected option key ("A", "B", "C", "D")
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

  // Step 3: Milestone 4 AI Generation Loading State
  const generatingLoadingSection = document.getElementById('generatingLoadingSection');
  const genPillTime = document.getElementById('genPillTime');
  const genPillQuestions = document.getElementById('genPillQuestions');
  const genPillPace = document.getElementById('genPillPace');

  // Step 3: Milestone 4 Revision Test Question Interface
  const stepTestSection = document.getElementById('stepTestSection');
  const testProviderBadge = document.getElementById('testProviderBadge');
  const testPaceBadge = document.getElementById('testPaceBadge');
  const testTotalBadge = document.getElementById('testTotalBadge');
  const questionCounterText = document.getElementById('questionCounterText');
  const answeredCounterText = document.getElementById('answeredCounterText');
  const testProgressBarFill = document.getElementById('testProgressBarFill');
  const questionBadgeNum = document.getElementById('questionBadgeNum');
  const questionPromptText = document.getElementById('questionPromptText');
  const optionsContainer = document.getElementById('optionsContainer');
  const answerFeedbackNotice = document.getElementById('answerFeedbackNotice');
  const prevQuestionBtn = document.getElementById('prevQuestionBtn');
  const nextQuestionBtn = document.getElementById('nextQuestionBtn');
  const questionQuickNav = document.getElementById('questionQuickNav');
  const returnToSettingsBtn = document.getElementById('returnToSettingsBtn');

  // Set footer API target URL
  if (footerApiUrl) {
    footerApiUrl.textContent = CONFIG.API_BASE_URL.replace(/\/api$/, '');
  }

  // -------------------------------------------------------------
  // Helpers
  // -------------------------------------------------------------
  function escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  // -------------------------------------------------------------
  // Stepper Management
  // -------------------------------------------------------------
  /**
   * Update the stepper visualization to reflect current pipeline progress.
   * Visual indicators per Milestone 4 specification:
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
      if (state.isGenerating || state.isUploading) return;

      if (targetStep === 1 && state.currentStep > 1) {
        transitionToStep(1);
      } else if (targetStep === 2 && state.currentStep > 2) {
        transitionToStep(2);
      } else if (targetStep === 3 && state.questions && state.questions.length > 0) {
        transitionToStep(3);
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
      if (generatingLoadingSection) generatingLoadingSection.classList.add('hidden');
      if (stepTestSection) stepTestSection.classList.add('hidden');
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
      if (generatingLoadingSection) generatingLoadingSection.classList.add('hidden');
      if (stepTestSection) stepTestSection.classList.add('hidden');
      updateStepper(2);
      stepSettingsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    } else if (targetStep === 3) {
      // Step 3: Revision Test view
      if (!state.questions || state.questions.length === 0) {
        showError('No revision test has been generated yet. Please configure your settings and click Create Revision Test.');
        transitionToStep(2);
        return;
      }
      stepUploadSection.classList.add('hidden');
      stepSettingsSection.classList.add('hidden');
      if (generatingLoadingSection) generatingLoadingSection.classList.add('hidden');
      if (stepTestSection) stepTestSection.classList.remove('hidden');
      updateStepper(3);
      stepTestSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
      renderCurrentQuestion();
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

  async function handleFileSelected(file) {
    if (state.isUploading || state.isGenerating) return;

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

    setTimeout(() => {
      stepSettingsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 150);
  }

  // Drag & Drop
  if (dropZone) {
    ['dragenter', 'dragover'].forEach(eventName => {
      dropZone.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        if (state.isUploading || state.isGenerating) return;
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
      if (state.isUploading || state.isGenerating) return;
      const files = e.dataTransfer.files;
      if (files && files.length > 0) {
        handleFileSelected(files[0]);
      }
    });

    dropZone.addEventListener('click', (e) => {
      if (state.isUploading || state.isGenerating) return;
      if (e.target !== choosePdfBtn && !choosePdfBtn.contains(e.target)) {
        if (pdfFileInput) pdfFileInput.click();
      }
    });

    dropZone.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        if (pdfFileInput && !state.isUploading && !state.isGenerating) {
          pdfFileInput.click();
        }
      }
    });
  }

  // Choose PDF Button
  if (choosePdfBtn) {
    choosePdfBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      if (state.isUploading || state.isGenerating) return;
      if (pdfFileInput) pdfFileInput.click();
    });
  }

  // Hidden File Input Change
  if (pdfFileInput) {
    pdfFileInput.addEventListener('change', () => {
      if (pdfFileInput.files && pdfFileInput.files.length > 0) {
        handleFileSelected(pdfFileInput.files[0]);
        pdfFileInput.value = '';
      }
    });
  }

  // Change PDF / Reset
  function resetToUpload() {
    state.selectedFile = null;
    state.pdfResult = null;
    state.isUploading = false;
    state.isGenerating = false;
    state.questions = [];
    state.currentQuestionIndex = 0;
    state.userAnswers = {};

    hideError();

    // Reset UI visibility
    dropZone.classList.remove('hidden');
    uploadLoadingState.classList.add('hidden');
    pdfResultSection.classList.add('hidden');
    stepSettingsSection.classList.add('hidden');
    if (generatingLoadingSection) generatingLoadingSection.classList.add('hidden');
    if (stepTestSection) stepTestSection.classList.add('hidden');
    stepUploadSection.classList.remove('hidden');

    updateStepper(1);
    stepUploadSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  if (changePdfBtn) {
    changePdfBtn.addEventListener('click', resetToUpload);
  }

  // -------------------------------------------------------------
  // Step 2: Revision Settings Validation & Logic
  // -------------------------------------------------------------
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

  if (timeInput) {
    timeInput.addEventListener('input', () => {
      timeInput.classList.remove('has-error');
      if (timeError) timeError.classList.add('hidden');
      updatePaceEstimate();
      syncPresetChip(timePresets, timeInput.value);
    });
  }

  if (questionsInput) {
    questionsInput.addEventListener('input', () => {
      questionsInput.classList.remove('has-error');
      if (questionsError) questionsError.classList.add('hidden');
      updatePaceEstimate();
      syncPresetChip(questionsPresets, questionsInput.value);
    });
  }

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

  updatePaceEstimate();

  // -------------------------------------------------------------
  // Step 2 -> Step 3: Create Revision Test Button (Gemini AI Call)
  // -------------------------------------------------------------
  if (createTestBtn) {
    createTestBtn.addEventListener('click', async () => {
      if (state.isGenerating) return;

      // 1. Verify PDF has been processed
      if (!state.pdfResult || !state.pdfResult.extracted_text) {
        showError('Please upload and process a study PDF before generating a revision test.');
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
      state.isGenerating = true;
      createTestBtn.disabled = true;
      hideError();

      // 5. Update Loading View Details
      const pace = (state.timeMinutes / state.questionCount).toFixed(1);
      if (genPillTime) genPillTime.textContent = `⏱️ ${state.timeMinutes} minutes`;
      if (genPillQuestions) genPillQuestions.textContent = `📝 ${state.questionCount} questions`;
      if (genPillPace) genPillPace.textContent = `⚡ ~${pace} min/q`;

      // 6. Reveal AI Generation Loading Section
      stepUploadSection.classList.add('hidden');
      stepSettingsSection.classList.add('hidden');
      if (stepTestSection) stepTestSection.classList.add('hidden');
      if (generatingLoadingSection) {
        generatingLoadingSection.classList.remove('hidden');
        generatingLoadingSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }

      // 7. Request Question Generation from Backend via POST /api/revision/generate
      const response = await API.generateRevisionTest(
        state.pdfResult.extracted_text,
        state.timeMinutes,
        state.questionCount
      );

      state.isGenerating = false;
      createTestBtn.disabled = false;
      if (generatingLoadingSection) generatingLoadingSection.classList.add('hidden');

      if (!response.success) {
        // Show error and return to settings so student can retry or adjust
        stepUploadSection.classList.remove('hidden');
        stepSettingsSection.classList.remove('hidden');
        updateStepper(2);
        showError(response.error || "We couldn't generate your revision test right now. Please try again.");
        return;
      }

      // 8. Successful AI Generation
      const data = response.data;
      if (!data.questions || data.questions.length === 0) {
        stepUploadSection.classList.remove('hidden');
        stepSettingsSection.classList.remove('hidden');
        updateStepper(2);
        showError("We couldn't generate your revision test right now. Please try again.");
        return;
      }

      // 9. Store Questions in Frontend State (Cached so questions are not re-generated on next/prev)
      state.questions = data.questions;
      state.provider = data.provider || 'gemini';
      state.currentQuestionIndex = 0;
      state.userAnswers = {};

      // 10. Transition to Step 3 (Revision Test)
      transitionToStep(3);
    });
  }

  // -------------------------------------------------------------
  // Milestone 4: Revision Test Interactive UI Logic
  // -------------------------------------------------------------
  /**
   * Render the current question, options, progress counter, and navigation state.
   */
  function renderCurrentQuestion() {
    if (!state.questions || state.questions.length === 0) return;

    const currentQ = state.questions[state.currentQuestionIndex];
    if (!currentQ) return;

    const totalQuestions = state.questions.length;
    const currentNum = state.currentQuestionIndex + 1;

    // 1. Update Header Badges & Progress Labels
    if (questionBadgeNum) questionBadgeNum.textContent = `Q${currentNum}`;
    if (questionPromptText) questionPromptText.textContent = currentQ.question;
    if (questionCounterText) {
      questionCounterText.textContent = `Question ${currentNum} of ${totalQuestions}`;
    }

    const answeredCount = Object.keys(state.userAnswers).length;
    if (answeredCounterText) {
      answeredCounterText.textContent = `${answeredCount} of ${totalQuestions} answered`;
    }

    // 2. Progress Bar Fill
    if (testProgressBarFill) {
      const pct = Math.round((currentNum / totalQuestions) * 100);
      testProgressBarFill.style.width = `${pct}%`;
    }

    // 3. Top Stats
    if (testProviderBadge) {
      if (state.provider === 'heuristic-fallback') {
        testProviderBadge.textContent = '📋 Study Notes Fallback';
        testProviderBadge.title = 'Generated directly from study text sentences without external AI';
      } else {
        testProviderBadge.textContent = '🤖 Gemini AI';
        testProviderBadge.title = 'Generated by Google Gemini AI';
      }
    }
    if (testTotalBadge) testTotalBadge.textContent = `📝 ${totalQuestions} Questions`;
    if (testPaceBadge) {
      const pace = (state.timeMinutes / totalQuestions).toFixed(1);
      testPaceBadge.textContent = `⏱️ Pacing: ~${pace} min/q`;
    }

    // 4. Render Options (A, B, C, D)
    if (optionsContainer) {
      optionsContainer.innerHTML = '';
      const selectedOption = state.userAnswers[state.currentQuestionIndex];

      const optionKeys = ['A', 'B', 'C', 'D'];
      optionKeys.forEach(optKey => {
        const optionContent = (currentQ.options && currentQ.options[optKey]) || '';
        const isSelected = selectedOption === optKey;

        const optBtn = document.createElement('button');
        optBtn.type = 'button';
        optBtn.className = `option-item${isSelected ? ' selected' : ''}`;
        optBtn.setAttribute('role', 'radio');
        optBtn.setAttribute('aria-checked', isSelected ? 'true' : 'false');
        optBtn.dataset.option = optKey;

        optBtn.innerHTML = `
          <span class="option-indicator">${optKey}</span>
          <span class="option-text">${escapeHtml(optionContent)}</span>
          <span class="option-check" aria-hidden="true">✓</span>
        `;

        optBtn.addEventListener('click', () => {
          selectAnswer(optKey);
        });

        optionsContainer.appendChild(optBtn);
      });
    }

    // 5. Answer Feedback
    if (answerFeedbackNotice) {
      if (state.userAnswers[state.currentQuestionIndex]) {
        answerFeedbackNotice.classList.remove('hidden');
      } else {
        answerFeedbackNotice.classList.add('hidden');
      }
    }

    // 6. Navigation Controls
    if (prevQuestionBtn) {
      prevQuestionBtn.disabled = (state.currentQuestionIndex === 0);
    }

    if (nextQuestionBtn) {
      if (state.currentQuestionIndex === totalQuestions - 1) {
        nextQuestionBtn.innerHTML = `
          Finish Review
          <svg class="btn-icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="20 6 9 17 4 12"></polyline>
          </svg>
        `;
      } else {
        nextQuestionBtn.innerHTML = `
          Next Question
          <svg class="btn-icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="9 18 15 12 9 6"></polyline>
          </svg>
        `;
      }
    }

    // 7. Render Quick Question Navigator Dots
    if (questionQuickNav) {
      questionQuickNav.innerHTML = '';
      state.questions.forEach((_, idx) => {
        const dot = document.createElement('button');
        dot.type = 'button';
        const isCurrent = (idx === state.currentQuestionIndex);
        const isAnswered = Boolean(state.userAnswers[idx]);

        dot.className = `quick-dot${isCurrent ? ' current' : ''}${isAnswered && !isCurrent ? ' answered' : ''}`;
        dot.textContent = idx + 1;
        dot.setAttribute('aria-label', `Go to Question ${idx + 1}`);

        dot.addEventListener('click', () => {
          state.currentQuestionIndex = idx;
          renderCurrentQuestion();
        });

        questionQuickNav.appendChild(dot);
      });
    }
  }

  /**
   * Handle user selection of an answer choice.
   * Stored in state only (no Gemini call, no final scoring in Milestone 4).
   * @param {string} optionKey - "A", "B", "C", or "D"
   */
  function selectAnswer(optionKey) {
    state.userAnswers[state.currentQuestionIndex] = optionKey;
    renderCurrentQuestion();
  }

  // Previous Question Button
  if (prevQuestionBtn) {
    prevQuestionBtn.addEventListener('click', () => {
      if (state.currentQuestionIndex > 0) {
        state.currentQuestionIndex--;
        renderCurrentQuestion();
      }
    });
  }

  // Next Question Button
  if (nextQuestionBtn) {
    nextQuestionBtn.addEventListener('click', () => {
      if (state.currentQuestionIndex < state.questions.length - 1) {
        state.currentQuestionIndex++;
        renderCurrentQuestion();
      } else {
        // Student is on the last question
        const answered = Object.keys(state.userAnswers).length;
        const total = state.questions.length;
        if (answerFeedbackNotice) {
          answerFeedbackNotice.classList.remove('hidden');
          const feedbackText = document.getElementById('answerFeedbackText');
          if (feedbackText) {
            feedbackText.textContent = `You've reviewed all ${total} questions (${answered} answered). Answers are stored in session for Milestone 5 scoring!`;
          }
        }
      }
    });
  }

  // Return to Settings / Edit PDF Button
  if (returnToSettingsBtn) {
    returnToSettingsBtn.addEventListener('click', () => {
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
