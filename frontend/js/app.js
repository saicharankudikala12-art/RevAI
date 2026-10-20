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
    currentStep: 1, // 1: PDF Upload, 2: Revision Settings, 3: Revision Test, 4: Results & Review
    selectedFile: null,
    pdfResult: null, // { filename, page_count, word_count, text_length, preview, extracted_text }
    timeMinutes: 120,
    questionCount: 20,
    isUploading: false,
    isGenerating: false,
    // Milestone 4 & 5: Revision Test state
    questions: [], // Array of question objects from Gemini
    provider: 'gemini', // 'gemini' or 'heuristic-fallback'
    testToken: null, // HMAC signed token from backend
    testStartTime: null, // Timestamp when test began
    currentQuestionIndex: 0,
    userAnswers: {}, // Map of question index (0 to N-1) -> selected option key ("A", "B", "C", "D")
    isSubmitting: false,
    isSubmitted: false,
    submissionResult: null, // TestSubmissionResponse object
    activeReviewFilter: 'all', // 'all', 'incorrect', 'unanswered', 'correct'
    // Milestone 8: Smart Revision Flashcards state
    flashcards: [],
    currentFlashcardIndex: 0,
    isCardFlipped: false,
    isLoadingFlashcards: false
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

  // Step 3: Revision Test Question Interface
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
  const submitTestBtn = document.getElementById('submitTestBtn');
  const questionQuickNav = document.getElementById('questionQuickNav');
  const returnToSettingsBtn = document.getElementById('returnToSettingsBtn');

  // Milestone 5: Submission Confirmation Modal Elements
  const submitConfirmModal = document.getElementById('submitConfirmModal');
  const modalWarningBox = document.getElementById('modalWarningBox');
  const modalWarningText = document.getElementById('modalWarningText');
  const modalTotalQuestions = document.getElementById('modalTotalQuestions');
  const modalAnsweredCount = document.getElementById('modalAnsweredCount');
  const modalUnansweredCount = document.getElementById('modalUnansweredCount');
  const cancelSubmitBtn = document.getElementById('cancelSubmitBtn');
  const confirmSubmitBtn = document.getElementById('confirmSubmitBtn');

  // Step 4: Milestone 5 Results Dashboard Elements
  const stepResultsSection = document.getElementById('stepResultsSection');
  const resultScorePercentage = document.getElementById('resultScorePercentage');
  const resultPerformanceRating = document.getElementById('resultPerformanceRating');
  const resultPerformanceSummary = document.getElementById('resultPerformanceSummary');
  const resultMetaStudyTime = document.getElementById('resultMetaStudyTime');
  const resultMetaProvider = document.getElementById('resultMetaProvider');
  const resultMetaTimeSpent = document.getElementById('resultMetaTimeSpent');
  const statCorrectCount = document.getElementById('statCorrectCount');
  const statIncorrectCount = document.getElementById('statIncorrectCount');
  const statUnansweredCount = document.getElementById('statUnansweredCount');
  const statTotalCount = document.getElementById('statTotalCount');
  const scrollToReviewBtn = document.getElementById('scrollToReviewBtn');
  const restartSameTestBtn = document.getElementById('restartSameTestBtn');
  const newTestSettingsBtn = document.getElementById('newTestSettingsBtn');
  const startOverUploadBtn = document.getElementById('startOverUploadBtn');
  const answerReviewSection = document.getElementById('answerReviewSection');
  const reviewQuestionsContainer = document.getElementById('reviewQuestionsContainer');
  const filterCountAll = document.getElementById('filterCountAll');
  const filterCountIncorrect = document.getElementById('filterCountIncorrect');
  const filterCountUnanswered = document.getElementById('filterCountUnanswered');
  const filterCountCorrect = document.getElementById('filterCountCorrect');

  // Milestone 7: Weak-Topic Analysis Elements
  const weakTopicsSection = document.getElementById('weakTopicsSection');
  const weakTopicsContainer = document.getElementById('weakTopicsContainer');
  const weakTopicsCountBadge = document.getElementById('weakTopicsCountBadge');

  // Milestone 8: Smart Revision Flashcard Elements
  const startFlashcardsBtn = document.getElementById('startFlashcardsBtn');
  const stepFlashcardsSection = document.getElementById('stepFlashcardsSection');
  const backToResultsBtn = document.getElementById('backToResultsBtn');
  const flashcardsLoadingState = document.getElementById('flashcardsLoadingState');
  const flashcardsEmptyState = document.getElementById('flashcardsEmptyState');
  const flashcardsEmptyTitle = document.getElementById('flashcardsEmptyTitle');
  const flashcardsEmptyDesc = document.getElementById('flashcardsEmptyDesc');
  const retryFlashcardsBtn = document.getElementById('retryFlashcardsBtn');
  const flashcardsDeckContainer = document.getElementById('flashcardsDeckContainer');
  const flashcardTopicBadge = document.getElementById('flashcardTopicBadge');
  const flashcardCounter = document.getElementById('flashcardCounter');
  const flashcardProgressPct = document.getElementById('flashcardProgressPct');
  const flashcardProgressBar = document.getElementById('flashcardProgressBar');
  const flashcardScene = document.getElementById('flashcardScene');
  const flashcardCard = document.getElementById('flashcardCard');
  const flashcardFrontText = document.getElementById('flashcardFrontText');
  const flashcardBackText = document.getElementById('flashcardBackText');
  const flashcardMemoryTipWrap = document.getElementById('flashcardMemoryTipWrap');
  const flashcardMemoryTipText = document.getElementById('flashcardMemoryTipText');
  const prevCardBtn = document.getElementById('prevCardBtn');
  const flipCardBtn = document.getElementById('flipCardBtn');
  const flipBtnText = document.getElementById('flipBtnText');
  const nextCardBtn = document.getElementById('nextCardBtn');
  const restartFlashcardsBtn = document.getElementById('restartFlashcardsBtn');
  const shuffleFlashcardsBtn = document.getElementById('shuffleFlashcardsBtn');

  const footerDocsLink = document.getElementById('footerDocsLink');

  // Set footer API target URL and Docs link dynamically
  const displayBackendOrigin = CONFIG.API_BASE_URL.startsWith('http')
    ? CONFIG.API_BASE_URL.replace(/\/api$/, '')
    : window.location.origin;

  if (footerApiUrl) {
    footerApiUrl.textContent = displayBackendOrigin;
  }
  if (footerDocsLink) {
    footerDocsLink.href = `${displayBackendOrigin}/docs`;
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
   * Visual indicators:
   * ✓ for completed, ● for active, ○ for upcoming/locked.
   * @param {number} step - Current step (1, 2, 3, or 4)
   */
  function updateStepper(step) {
    state.currentStep = step;

    stepItems.forEach((item, index) => {
      if (!item) return;
      item.classList.remove('active', 'completed', 'clickable');
      const icon = stepIcons[index];
      const stepNum = index + 1;

      if (stepNum < step) {
        item.classList.add('completed', 'clickable');
        if (icon) icon.textContent = '✓';
      } else if (stepNum === step) {
        item.classList.add('active');
        if (icon) icon.textContent = '●';
      } else {
        if (icon) icon.textContent = '○';
      }
    });
  }

  // Allow clicking on completed stepper items to return to that step
  stepItems.forEach((item, index) => {
    if (!item) return;
    item.addEventListener('click', () => {
      const targetStep = index + 1;
      if (state.isGenerating || state.isUploading || state.isSubmitting) return;

      if (targetStep === 1 && state.currentStep > 1) {
        transitionToStep(1);
      } else if (targetStep === 2 && state.currentStep > 2) {
        transitionToStep(2);
      } else if (targetStep === 3 && state.questions && state.questions.length > 0) {
        transitionToStep(3);
      } else if (targetStep === 4 && state.isSubmitted && state.submissionResult) {
        transitionToStep(4);
      } else if (targetStep === 5 && state.flashcards && state.flashcards.length > 0) {
        transitionToStep(5);
      }
    });
  });

  /**
   * Transition UI views between steps smoothly.
   * @param {number} targetStep 
   */
  function transitionToStep(targetStep) {
    if (targetStep === 1) {
      stepUploadSection.classList.remove('hidden');
      stepSettingsSection.classList.add('hidden');
      if (generatingLoadingSection) generatingLoadingSection.classList.add('hidden');
      if (stepTestSection) stepTestSection.classList.add('hidden');
      if (stepResultsSection) stepResultsSection.classList.add('hidden');
      if (stepFlashcardsSection) stepFlashcardsSection.classList.add('hidden');
      updateStepper(1);
      stepUploadSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    } else if (targetStep === 2) {
      if (!state.pdfResult) {
        showError('Please upload and process a study PDF first.');
        transitionToStep(1);
        return;
      }
      stepUploadSection.classList.remove('hidden');
      stepSettingsSection.classList.remove('hidden');
      if (generatingLoadingSection) generatingLoadingSection.classList.add('hidden');
      if (stepTestSection) stepTestSection.classList.add('hidden');
      if (stepResultsSection) stepResultsSection.classList.add('hidden');
      if (stepFlashcardsSection) stepFlashcardsSection.classList.add('hidden');
      updateStepper(2);
      stepSettingsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    } else if (targetStep === 3) {
      if (!state.questions || state.questions.length === 0) {
        showError('No revision test has been generated yet. Please configure your settings and click Create Revision Test.');
        transitionToStep(2);
        return;
      }
      stepUploadSection.classList.add('hidden');
      stepSettingsSection.classList.add('hidden');
      if (generatingLoadingSection) generatingLoadingSection.classList.add('hidden');
      if (stepResultsSection) stepResultsSection.classList.add('hidden');
      if (stepFlashcardsSection) stepFlashcardsSection.classList.add('hidden');
      if (stepTestSection) stepTestSection.classList.remove('hidden');
      updateStepper(3);
      stepTestSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
      renderCurrentQuestion();
    } else if (targetStep === 4) {
      if (!state.submissionResult) {
        showError('Please complete and submit your revision test to view results.');
        transitionToStep(3);
        return;
      }
      stepUploadSection.classList.add('hidden');
      stepSettingsSection.classList.add('hidden');
      if (generatingLoadingSection) generatingLoadingSection.classList.add('hidden');
      if (stepTestSection) stepTestSection.classList.add('hidden');
      if (stepFlashcardsSection) stepFlashcardsSection.classList.add('hidden');
      if (stepResultsSection) stepResultsSection.classList.remove('hidden');
      updateStepper(4);
      stepResultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
      renderResultsDashboard();
    } else if (targetStep === 5) {
      stepUploadSection.classList.add('hidden');
      stepSettingsSection.classList.add('hidden');
      if (generatingLoadingSection) generatingLoadingSection.classList.add('hidden');
      if (stepTestSection) stepTestSection.classList.add('hidden');
      if (stepResultsSection) stepResultsSection.classList.add('hidden');
      if (stepFlashcardsSection) stepFlashcardsSection.classList.remove('hidden');
      updateStepper(5);
      stepFlashcardsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
      renderCurrentFlashcard();
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
    state.testToken = null;
    state.testStartTime = null;
    state.isSubmitting = false;
    state.isSubmitted = false;
    state.submissionResult = null;
    state.flashcards = [];
    state.currentFlashcardIndex = 0;
    state.isCardFlipped = false;
    state.isLoadingFlashcards = false;

    hideError();
    closeSubmitModal();

    // Reset UI visibility
    dropZone.classList.remove('hidden');
    uploadLoadingState.classList.add('hidden');
    pdfResultSection.classList.add('hidden');
    stepSettingsSection.classList.add('hidden');
    if (generatingLoadingSection) generatingLoadingSection.classList.add('hidden');
    if (stepTestSection) stepTestSection.classList.add('hidden');
    if (stepResultsSection) stepResultsSection.classList.add('hidden');
    if (stepFlashcardsSection) stepFlashcardsSection.classList.add('hidden');
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
      state.testToken = data.test_token || null;
      state.testStartTime = Date.now();
      state.currentQuestionIndex = 0;
      state.userAnswers = {};
      state.isSubmitted = false;
      state.submissionResult = null;

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
   * If test is already submitted, answers are locked.
   * @param {string} optionKey - "A", "B", "C", or "D"
   */
  function selectAnswer(optionKey) {
    if (state.isSubmitted) return;
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
        // When on last question, clicking Next prompts user to submit
        openSubmitModal();
      }
    });
  }

  // Return to Settings / Edit PDF Button
  if (returnToSettingsBtn) {
    returnToSettingsBtn.addEventListener('click', () => {
      if (state.isSubmitted) {
        transitionToStep(2);
      } else {
        const confirmed = window.confirm("Return to revision settings? Your current test answers will be retained in this session.");
        if (confirmed) {
          transitionToStep(2);
        }
      }
    });
  }

  // -------------------------------------------------------------
  // Milestone 5: Submit Confirmation Modal & Test Submission
  // -------------------------------------------------------------
  function openSubmitModal() {
    if (state.isSubmitting || state.isSubmitted) return;

    const totalQuestions = state.questions.length;
    const answeredCount = Object.keys(state.userAnswers).length;
    const unansweredCount = totalQuestions - answeredCount;

    if (modalTotalQuestions) modalTotalQuestions.textContent = totalQuestions;
    if (modalAnsweredCount) modalAnsweredCount.textContent = answeredCount;
    if (modalUnansweredCount) modalUnansweredCount.textContent = unansweredCount;

    if (modalWarningBox && modalWarningText) {
      if (unansweredCount > 0) {
        modalWarningText.textContent = `You have ${unansweredCount} unanswered question${unansweredCount === 1 ? '' : 's'}. They will be marked as unanswered upon submission.`;
        modalWarningBox.classList.remove('hidden');
      } else {
        modalWarningBox.classList.add('hidden');
      }
    }

    if (submitConfirmModal) {
      submitConfirmModal.classList.remove('hidden');
    }
  }

  function closeSubmitModal() {
    if (submitConfirmModal) {
      submitConfirmModal.classList.add('hidden');
    }
  }

  if (submitTestBtn) {
    submitTestBtn.addEventListener('click', openSubmitModal);
  }

  if (cancelSubmitBtn) {
    cancelSubmitBtn.addEventListener('click', closeSubmitModal);
  }

  // Dismiss modal when clicking background overlay
  if (submitConfirmModal) {
    submitConfirmModal.addEventListener('click', (e) => {
      if (e.target === submitConfirmModal) {
        closeSubmitModal();
      }
    });
  }

  // Final Confirmed Submission
  if (confirmSubmitBtn) {
    confirmSubmitBtn.addEventListener('click', async () => {
      if (state.isSubmitting || state.isSubmitted) return;

      state.isSubmitting = true;
      confirmSubmitBtn.disabled = true;
      confirmSubmitBtn.textContent = 'Submitting...';

      const timeSpentSeconds = state.testStartTime
        ? Math.max(1, Math.round((Date.now() - state.testStartTime) / 1000))
        : null;

      // Construct server payload.
      // Use HMAC-signed test_token for tamper-proof verification, or full questions array if token unavailable.
      const payload = {
        test_token: state.testToken || null,
        questions: state.testToken ? null : state.questions,
        user_answers: state.userAnswers,
        time_spent_seconds: timeSpentSeconds
      };

      const response = await API.submitRevisionTest(payload);

      state.isSubmitting = false;
      confirmSubmitBtn.disabled = false;
      confirmSubmitBtn.textContent = 'Confirm & Submit';
      closeSubmitModal();

      if (!response.success) {
        showError(response.error || 'Failed to submit test. Please try again.');
        return;
      }

      // Mark test as submitted & lock answers
      state.isSubmitted = true;
      state.submissionResult = response.data;

      // Transition to Step 4 Results & Analysis
      transitionToStep(4);
    });
  }

  // -------------------------------------------------------------
  // Milestone 5: Results Dashboard & Detailed Answer Review
  // -------------------------------------------------------------
  function renderResultsDashboard() {
    const result = state.submissionResult;
    if (!result) return;

    // 1. Overall Score & Percentage
    if (resultScorePercentage) {
      resultScorePercentage.textContent = `${result.score_percentage}%`;
    }

    // 2. Performance Rating & Summary
    if (resultPerformanceRating) {
      resultPerformanceRating.textContent = result.performance_rating || 'Good';
      const ratingClass = String(result.performance_rating || '').toLowerCase().replace(/\s+/g, '-');
      resultPerformanceRating.className = `rating-badge ${ratingClass}`;
    }

    if (resultPerformanceSummary) {
      resultPerformanceSummary.textContent = result.performance_summary || '';
    }

    // 3. Meta tags (study time, provider, duration)
    if (resultMetaStudyTime) {
      resultMetaStudyTime.textContent = `⏱️ ${state.timeMinutes} min allocated`;
    }
    if (resultMetaProvider) {
      resultMetaProvider.textContent = state.provider === 'heuristic-fallback'
        ? '📋 Study Notes Fallback'
        : '🤖 Gemini AI';
    }
    if (resultMetaTimeSpent) {
      if (result.time_spent_seconds && result.time_spent_seconds > 0) {
        const mins = Math.floor(result.time_spent_seconds / 60);
        const secs = result.time_spent_seconds % 60;
        resultMetaTimeSpent.textContent = `⏳ Test Time: ${mins}m ${secs}s`;
        resultMetaTimeSpent.classList.remove('hidden');
      } else {
        resultMetaTimeSpent.classList.add('hidden');
      }
    }

    // 4. Metrics Grid
    if (statCorrectCount) statCorrectCount.textContent = result.correct_count;
    if (statIncorrectCount) statIncorrectCount.textContent = result.incorrect_count;
    if (statUnansweredCount) statUnansweredCount.textContent = result.unanswered_count;
    if (statTotalCount) statTotalCount.textContent = result.total_questions;

    // 5. Update Filter Tab Counts
    if (filterCountAll) filterCountAll.textContent = result.total_questions;
    if (filterCountCorrect) filterCountCorrect.textContent = result.correct_count;
    if (filterCountIncorrect) filterCountIncorrect.textContent = result.incorrect_count;
    if (filterCountUnanswered) filterCountUnanswered.textContent = result.unanswered_count;

    // 6. Render Milestone 7 Weak-Topic Analysis
    renderWeakTopics();

    // 7. Render Detailed Question Review Items
    renderReviewQuestions();
  }

  function renderWeakTopics() {
    if (!weakTopicsContainer || !state.submissionResult) return;

    const weakTopics = state.submissionResult.weak_topics || [];
    const totalQuestions = state.submissionResult.total_questions || 0;
    const correctCount = state.submissionResult.correct_count || 0;

    weakTopicsContainer.innerHTML = '';

    // Empty state 1: Perfect score (100%)
    if (totalQuestions > 0 && correctCount === totalQuestions) {
      if (weakTopicsCountBadge) {
        weakTopicsCountBadge.textContent = '100% Mastery';
        weakTopicsCountBadge.style.color = 'var(--color-success)';
      }
      weakTopicsContainer.innerHTML = `
        <div class="topic-empty-card">
          <div class="topic-empty-icon" aria-hidden="true">🎉</div>
          <h4 class="topic-empty-title">All Concepts Mastered!</h4>
          <p class="topic-empty-desc">
            Outstanding performance! You answered every question correctly across all evaluated concepts. You are thoroughly prepared for this section of your exam.
          </p>
        </div>
      `;
      return;
    }

    // Empty state 2: No weak topics detected or insufficient questions
    if (!weakTopics || weakTopics.length === 0) {
      if (weakTopicsCountBadge) {
        weakTopicsCountBadge.textContent = 'No critical gaps';
        weakTopicsCountBadge.style.color = 'var(--color-text-secondary)';
      }
      weakTopicsContainer.innerHTML = `
        <div class="topic-empty-card">
          <div class="topic-empty-icon" aria-hidden="true">✨</div>
          <h4 class="topic-empty-title">No Critical Concept Gaps Detected</h4>
          <p class="topic-empty-desc">
            No recurring concept weaknesses were identified from this test session. Keep practicing with additional questions to reinforce your preparation.
          </p>
        </div>
      `;
      return;
    }

    // Update topics badge
    const count = weakTopics.length;
    if (weakTopicsCountBadge) {
      weakTopicsCountBadge.textContent = `${count} topic${count === 1 ? '' : 's'} need focus`;
      weakTopicsCountBadge.style.color = 'var(--color-primary-light)';
    }

    // Render topic cards
    weakTopics.forEach((item, idx) => {
      const card = document.createElement('div');
      const priorityClass = `priority-${item.priority || 'medium'}`;
      card.className = `topic-card ${priorityClass}`;

      let indicatorClass = 'indicator-moderate';
      if (item.priority === 'high' || item.weakness_indicator === 'Critical Weakness') {
        indicatorClass = 'indicator-critical';
      } else if (item.priority === 'low' || item.weakness_indicator === 'Needs Attention') {
        indicatorClass = 'indicator-attention';
      }

      const priorityLabel = (item.priority || 'medium').toUpperCase();

      card.innerHTML = `
        <div class="topic-header">
          <div class="topic-title-wrapper">
            <span class="topic-name">#${idx + 1} ${escapeHtml(item.topic)}</span>
          </div>
          <div class="topic-pills">
            <span class="topic-indicator-pill ${indicatorClass}">
              ${escapeHtml(item.weakness_indicator)}
            </span>
          </div>
        </div>

        <div class="topic-stats-row">
          <span class="topic-stat-item">Priority: <strong>${priorityLabel}</strong></span>
          <span>·</span>
          <span class="topic-stat-item">Tested: <strong>${item.total_questions} question${item.total_questions === 1 ? '' : 's'}</strong></span>
          <span>·</span>
          <span class="topic-stat-item">Missed: <strong class="text-danger">${item.incorrect_count}</strong></span>
          ${item.unanswered_count > 0 ? `<span>·</span><span class="topic-stat-item">Skipped: <strong class="text-warning">${item.unanswered_count}</strong></span>` : ''}
          <span>·</span>
          <span class="topic-stat-item">Accuracy: <strong>${item.accuracy_percentage}%</strong></span>
        </div>

        <div class="topic-diagnostic-box">
          <p class="topic-reason-text">
            <strong>Diagnosis:</strong> ${escapeHtml(item.reason)}
          </p>
          <p class="topic-rec-text">
            <strong>Recommendation:</strong> ${escapeHtml(item.recommendation)}
          </p>
        </div>
      `;

      weakTopicsContainer.appendChild(card);
    });
  }

  function renderReviewQuestions() {
    if (!reviewQuestionsContainer || !state.submissionResult) return;

    const allReviews = state.submissionResult.questions_review || [];
    const filter = state.activeReviewFilter;

    // Filter questions
    const filtered = allReviews.filter(q => {
      if (filter === 'correct') return q.is_correct;
      if (filter === 'incorrect') return q.is_answered && !q.is_correct;
      if (filter === 'unanswered') return !q.is_answered;
      return true; // 'all'
    });

    reviewQuestionsContainer.innerHTML = '';

    if (filtered.length === 0) {
      reviewQuestionsContainer.innerHTML = `
        <div class="empty-state text-center" style="padding: 24px; color: var(--color-text-muted);">
          No questions match the "${filter}" filter.
        </div>
      `;
      return;
    }

    filtered.forEach(q => {
      const card = document.createElement('div');
      let statusClass = 'status-unanswered';
      let statusLabel = 'Unanswered';
      let statusIcon = '―';

      if (q.is_correct) {
        statusClass = 'status-correct';
        statusLabel = 'Correct';
        statusIcon = '✓';
      } else if (q.is_answered) {
        statusClass = 'status-incorrect';
        statusLabel = 'Incorrect';
        statusIcon = '✕';
      }

      card.className = `review-card ${statusClass}`;

      // Build options HTML
      const optKeys = ['A', 'B', 'C', 'D'];
      let optionsHtml = '';

      optKeys.forEach(k => {
        const optText = (q.options && q.options[k]) || '';
        const isCorrectTarget = (k === q.correct_answer);
        const isUserChoice = (k === q.user_answer);

        let optClass = 'review-option';
        let optTag = '';

        if (isCorrectTarget) {
          optClass += ' is-correct-target';
          optTag = '<span class="review-opt-tag">Correct Answer</span>';
        } else if (isUserChoice && !q.is_correct) {
          optClass += ' is-user-incorrect';
          optTag = '<span class="review-opt-tag">Your Choice</span>';
        }

        optionsHtml += `
          <div class="${optClass}">
            <span class="review-opt-key">${k}</span>
            <span class="review-opt-text">${escapeHtml(optText)}</span>
            ${optTag}
          </div>
        `;
      });

      const topicTagHtml = q.topic
        ? `<span class="review-opt-tag" style="background: rgba(99, 102, 241, 0.12); color: var(--color-primary-light); font-size: 11px; padding: 2px 8px; border-radius: var(--radius-full); border: 1px solid rgba(99, 102, 241, 0.25);">📚 ${escapeHtml(q.topic)}</span>`
        : '';

      card.innerHTML = `
        <div class="review-card-header">
          <div class="review-q-num-wrapper" style="display: flex; align-items: center; gap: var(--space-2); flex-wrap: wrap;">
            <span class="review-q-badge">Question ${q.id}</span>
            <span class="review-status-pill">${statusIcon} ${statusLabel}</span>
            ${topicTagHtml}
          </div>
          <div class="review-user-choice-pill" style="font-size: var(--font-size-xs); color: var(--color-text-muted);">
            Your Answer: <strong>${q.user_answer ? 'Option ' + q.user_answer : 'None (Unanswered)'}</strong>
          </div>
        </div>

        <h4 class="review-prompt">${escapeHtml(q.question)}</h4>

        <div class="review-options-list">
          ${optionsHtml}
        </div>

        <div class="review-explanation-box">
          <div class="review-exp-header">
            <svg class="btn-icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"></circle>
              <line x1="12" y1="16" x2="12" y2="12"></line>
              <line x1="12" y1="8" x2="12.01" y2="8"></line>
            </svg>
            Explanation
          </div>
          <p class="review-exp-text">${escapeHtml(q.explanation)}</p>
        </div>
      `;

      reviewQuestionsContainer.appendChild(card);
    });
  }

  // Filter Tabs Event Listeners
  const filterTabs = document.querySelectorAll('.filter-tab');
  filterTabs.forEach(tab => {
    tab.addEventListener('click', () => {
      filterTabs.forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      state.activeReviewFilter = tab.dataset.filter || 'all';
      renderReviewQuestions();
    });
  });

  // Scroll to Review Button
  if (scrollToReviewBtn) {
    scrollToReviewBtn.addEventListener('click', () => {
      if (answerReviewSection) {
        answerReviewSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    });
  }

  // Retake Same Test Button (Clears answers and restarts test timer)
  if (restartSameTestBtn) {
    restartSameTestBtn.addEventListener('click', () => {
      const confirmed = window.confirm("Retake this revision test? Your previous answers will be cleared so you can practice again.");
      if (!confirmed) return;

      state.userAnswers = {};
      state.isSubmitted = false;
      state.submissionResult = null;
      state.currentQuestionIndex = 0;
      state.testStartTime = Date.now();
      transitionToStep(3);
    });
  }

  // Return to Settings Button from Results
  if (newTestSettingsBtn) {
    newTestSettingsBtn.addEventListener('click', () => {
      transitionToStep(2);
    });
  }

  // Start Over / Upload New PDF Button
  if (startOverUploadBtn) {
    startOverUploadBtn.addEventListener('click', () => {
      const confirmed = window.confirm("Upload a new PDF? Current test questions and results will be cleared.");
      if (confirmed) {
        resetToUpload();
      }
    });
  }

  // =============================================================
  // Milestone 8: Smart Revision Flashcards Logic
  // =============================================================

  /**
   * Fetch flashcards from backend API based on current test results and source PDF.
   */
  async function generateAndLoadFlashcards() {
    if (state.isLoadingFlashcards) return;

    if (!state.pdfResult || !state.pdfResult.extracted_text) {
      showError("Study material is required to generate revision flashcards.");
      return;
    }

    state.isLoadingFlashcards = true;
    hideError();

    // Transition to step 5 view
    transitionToStep(5);

    // Show loading state, hide empty and deck
    if (flashcardsLoadingState) flashcardsLoadingState.classList.remove('hidden');
    if (flashcardsEmptyState) flashcardsEmptyState.classList.add('hidden');
    if (flashcardsDeckContainer) flashcardsDeckContainer.classList.add('hidden');

    // Extract weak topics from test submission result
    const weakTopics = (state.submissionResult && state.submissionResult.weak_topics)
      ? state.submissionResult.weak_topics
      : [];

    // Extract missed or unanswered questions from test submission result
    const incorrectQuestions = [];
    if (state.submissionResult && Array.isArray(state.submissionResult.questions_review)) {
      state.submissionResult.questions_review.forEach(item => {
        if (!item.is_correct) {
          incorrectQuestions.push(item);
        }
      });
    }

    try {
      const res = await API.generateRevisionFlashcards(
        state.pdfResult.extracted_text,
        weakTopics,
        incorrectQuestions,
        8
      );

      const cards = res.data ? (res.data.cards || res.data.flashcards || []) : [];
      if (res.success && Array.isArray(cards) && cards.length > 0) {
        state.flashcards = cards;
        state.currentFlashcardIndex = 0;
        state.isCardFlipped = false;

        if (flashcardsLoadingState) flashcardsLoadingState.classList.add('hidden');
        if (flashcardsEmptyState) flashcardsEmptyState.classList.add('hidden');
        if (flashcardsDeckContainer) flashcardsDeckContainer.classList.remove('hidden');

        renderCurrentFlashcard();
      } else {
        const errorMsg = res.error || "Unable to generate flashcards from the study material.";
        showFlashcardsEmptyState("No Flashcards Generated", errorMsg);
      }
    } catch (err) {
      showFlashcardsEmptyState("Generation Error", "An unexpected error occurred while generating flashcards.");
    } finally {
      state.isLoadingFlashcards = false;
      if (flashcardsLoadingState) flashcardsLoadingState.classList.add('hidden');
    }
  }

  function showFlashcardsEmptyState(title, desc) {
    if (flashcardsDeckContainer) flashcardsDeckContainer.classList.add('hidden');
    if (flashcardsLoadingState) flashcardsLoadingState.classList.add('hidden');
    if (flashcardsEmptyState) {
      if (flashcardsEmptyTitle) flashcardsEmptyTitle.textContent = title;
      if (flashcardsEmptyDesc) flashcardsEmptyDesc.textContent = desc;
      flashcardsEmptyState.classList.remove('hidden');
    }
  }

  /**
   * Render currently active flashcard into the 3D card element.
   */
  function renderCurrentFlashcard() {
    if (!state.flashcards || state.flashcards.length === 0) {
      showFlashcardsEmptyState("No Flashcards Available", "Complete a revision test to generate targeted flashcards.");
      return;
    }

    // Ensure valid index
    if (state.currentFlashcardIndex < 0) state.currentFlashcardIndex = 0;
    if (state.currentFlashcardIndex >= state.flashcards.length) {
      state.currentFlashcardIndex = state.flashcards.length - 1;
    }

    const card = state.flashcards[state.currentFlashcardIndex];
    const total = state.flashcards.length;
    const currentNum = state.currentFlashcardIndex + 1;

    // Reset flipped state on card switch
    state.isCardFlipped = false;
    if (flashcardCard) flashcardCard.classList.remove('is-flipped');
    if (flipBtnText) flipBtnText.textContent = "Reveal Answer";

    // Topic badge
    if (flashcardTopicBadge) {
      flashcardTopicBadge.textContent = card.topic ? `Topic: ${card.topic}` : "Topic: General Revision";
      flashcardTopicBadge.title = card.topic || "General Revision";
    }

    // Counter & progress
    if (flashcardCounter) {
      flashcardCounter.textContent = `Card ${currentNum} of ${total}`;
    }

    const progressPctVal = Math.round((currentNum / total) * 100);
    if (flashcardProgressPct) {
      flashcardProgressPct.textContent = `${progressPctVal}%`;
    }
    if (flashcardProgressBar) {
      flashcardProgressBar.style.width = `${progressPctVal}%`;
    }

    // Front content
    if (flashcardFrontText) {
      flashcardFrontText.textContent = card.front || "Concept / Question";
    }

    // Back content
    if (flashcardBackText) {
      flashcardBackText.textContent = card.back || "Answer";
    }

    // Memory tip
    if (flashcardMemoryTipWrap && flashcardMemoryTipText) {
      if (card.memory_tip && card.memory_tip.trim()) {
        flashcardMemoryTipText.textContent = card.memory_tip.trim();
        flashcardMemoryTipWrap.classList.remove('hidden');
      } else {
        flashcardMemoryTipWrap.classList.add('hidden');
      }
    }

    // Nav buttons disabled states
    if (prevCardBtn) {
      prevCardBtn.disabled = (state.currentFlashcardIndex === 0);
      prevCardBtn.style.opacity = (state.currentFlashcardIndex === 0) ? "0.5" : "1";
    }
    if (nextCardBtn) {
      nextCardBtn.disabled = (state.currentFlashcardIndex === total - 1);
      nextCardBtn.style.opacity = (state.currentFlashcardIndex === total - 1) ? "0.5" : "1";
    }
  }

  /**
   * Flip current card.
   */
  function toggleCardFlip() {
    state.isCardFlipped = !state.isCardFlipped;
    if (flashcardCard) {
      flashcardCard.classList.toggle('is-flipped', state.isCardFlipped);
    }
    if (flipBtnText) {
      flipBtnText.textContent = state.isCardFlipped ? "Show Question" : "Reveal Answer";
    }
  }

  // Click card scene to flip
  if (flashcardScene) {
    flashcardScene.addEventListener('click', (e) => {
      // Ignore clicks on buttons if any inside
      if (e.target.closest('button')) return;
      toggleCardFlip();
    });
  }

  // Flip button
  if (flipCardBtn) {
    flipCardBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      toggleCardFlip();
    });
  }

  // Prev / Next button actions
  if (prevCardBtn) {
    prevCardBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      if (state.currentFlashcardIndex > 0) {
        state.currentFlashcardIndex--;
        renderCurrentFlashcard();
      }
    });
  }

  if (nextCardBtn) {
    nextCardBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      if (state.currentFlashcardIndex < state.flashcards.length - 1) {
        state.currentFlashcardIndex++;
        renderCurrentFlashcard();
      }
    });
  }

  // Restart deck
  if (restartFlashcardsBtn) {
    restartFlashcardsBtn.addEventListener('click', () => {
      state.currentFlashcardIndex = 0;
      state.isCardFlipped = false;
      renderCurrentFlashcard();
    });
  }

  // Shuffle deck
  if (shuffleFlashcardsBtn) {
    shuffleFlashcardsBtn.addEventListener('click', () => {
      if (!state.flashcards || state.flashcards.length <= 1) return;
      // Fisher-Yates shuffle
      for (let i = state.flashcards.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [state.flashcards[i], state.flashcards[j]] = [state.flashcards[j], state.flashcards[i]];
      }
      state.currentFlashcardIndex = 0;
      state.isCardFlipped = false;
      renderCurrentFlashcard();
    });
  }

  // Keyboard navigation for Flashcards (Space to flip, arrows for prev/next)
  document.addEventListener('keydown', (e) => {
    if (state.currentStep !== 5) return;
    // Don't intercept if user is typing in an input
    if (['INPUT', 'TEXTAREA'].includes(document.activeElement.tagName)) return;

    if (e.code === 'Space') {
      e.preventDefault();
      toggleCardFlip();
    } else if (e.code === 'ArrowLeft') {
      e.preventDefault();
      if (state.currentFlashcardIndex > 0) {
        state.currentFlashcardIndex--;
        renderCurrentFlashcard();
      }
    } else if (e.code === 'ArrowRight') {
      e.preventDefault();
      if (state.currentFlashcardIndex < state.flashcards.length - 1) {
        state.currentFlashcardIndex++;
        renderCurrentFlashcard();
      }
    }
  });

  // CTA button in Results dashboard to open flashcards
  if (startFlashcardsBtn) {
    startFlashcardsBtn.addEventListener('click', () => {
      if (state.flashcards && state.flashcards.length > 0) {
        transitionToStep(5);
      } else {
        generateAndLoadFlashcards();
      }
    });
  }

  // Back to Results button in Flashcards header
  if (backToResultsBtn) {
    backToResultsBtn.addEventListener('click', () => {
      transitionToStep(4);
    });
  }

  // Retry generating flashcards from empty state
  if (retryFlashcardsBtn) {
    retryFlashcardsBtn.addEventListener('click', () => {
      generateAndLoadFlashcards();
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

