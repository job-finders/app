/**
 * Questionnaire JavaScript
 * 
 * Handles the questionnaire completion interface including:
 * - Timer management with warnings
 * - Question navigation
 * - Progress tracking
 * - Auto-save functionality
 * - Form validation and submission
 */

class QuestionnaireManager {
    constructor() {
        this.data = window.questionnaireData || {};
        this.currentQuestion = 1;
        this.totalQuestions = this.data.total_questions || 0;
        this.timeLimit = this.data.time_limit || 30; // minutes
        this.timeRemaining = this.timeLimit * 60; // seconds
        this.timer = null;
        this.isStarted = false;
        this.isSubmitted = false;
        this.answers = {};
        this.autoSaveInterval = null;
        
        this.init();
    }
    
    init() {
        this.bindEvents();
        this.updateProgress();
        this.setupCharacterCounters();
    }
    
    bindEvents() {
        // Start questionnaire
        const startBtn = document.getElementById('start-questionnaire');
        if (startBtn) {
            startBtn.addEventListener('click', () => this.startQuestionnaire());
        }
        
        // Navigation buttons
        const prevBtn = document.getElementById('prev-question');
        const nextBtn = document.getElementById('next-question');
        const submitBtn = document.getElementById('submit-questionnaire');
        
        if (prevBtn) {
            prevBtn.addEventListener('click', () => this.previousQuestion());
        }
        
        if (nextBtn) {
            nextBtn.addEventListener('click', () => this.nextQuestion());
        }
        
        if (submitBtn) {
            submitBtn.addEventListener('click', (e) => this.submitQuestionnaire(e));
        }
        
        // Form submission
        const form = document.getElementById('questionnaire-form');
        if (form) {
            form.addEventListener('submit', (e) => this.submitQuestionnaire(e));
        }
        
        // Answer change events
        document.addEventListener('change', (e) => {
            if (e.target.matches('input[type="radio"], textarea')) {
                this.handleAnswerChange(e);
            }
        });
        
        // Textarea input events for character counting
        document.addEventListener('input', (e) => {
            if (e.target.matches('.question-textarea')) {
                this.updateCharacterCount(e.target);
            }
        });
        
        // Prevent accidental page leave
        window.addEventListener('beforeunload', (e) => {
            if (this.isStarted && !this.isSubmitted) {
                e.preventDefault();
                e.returnValue = 'You have an active questionnaire. Are you sure you want to leave?';
                return e.returnValue;
            }
        });
    }
    
    startQuestionnaire() {
        this.isStarted = true;
        
        // Hide instructions and show form
        const instructionsCard = document.getElementById('instructions-card');
        const form = document.getElementById('questionnaire-form');
        
        if (instructionsCard) instructionsCard.style.display = 'none';
        if (form) form.style.display = 'block';
        
        // Start timer
        this.startTimer();
        
        // Start auto-save
        this.startAutoSave();
        
        // Update timer status
        const timerStatus = document.getElementById('timer-status');
        if (timerStatus) {
            timerStatus.innerHTML = '<i class="fas fa-play text-success"></i><span>Timer started</span>';
        }
        
        // Send start event to server
        this.sendTimerStartEvent();
    }
    
    startTimer() {
        this.timer = setInterval(() => {
            this.timeRemaining--;
            this.updateTimerDisplay();
            
            // Check for warnings
            if (this.timeRemaining === 300) { // 5 minutes
                this.showTimeWarning('You have 5 minutes remaining to complete the questionnaire.');
            } else if (this.timeRemaining === 60) { // 1 minute
                this.showTimeWarning('You have 1 minute remaining to complete the questionnaire.');
            } else if (this.timeRemaining <= 0) {
                this.handleTimeExpired();
            }
        }, 1000);
    }
    
    updateTimerDisplay() {
        const minutes = Math.floor(this.timeRemaining / 60);
        const seconds = this.timeRemaining % 60;
        const timeString = `${minutes}:${seconds.toString().padStart(2, '0')}`;
        
        const timeDisplay = document.getElementById('time-remaining');
        if (timeDisplay) {
            timeDisplay.textContent = timeString;
        }
        
        // Update progress circle
        const progressCircle = document.getElementById('timer-progress-circle');
        if (progressCircle) {
            const totalTime = this.timeLimit * 60;
            const progress = (totalTime - this.timeRemaining) / totalTime;
            const circumference = 2 * Math.PI * 45; // radius = 45
            const offset = circumference * (1 - progress);
            progressCircle.style.strokeDashoffset = offset;
        }
        
        // Update timer styling based on time remaining
        const timerCard = document.querySelector('.timer-card');
        if (timerCard) {
            timerCard.classList.remove('timer-warning', 'timer-danger');
            
            if (this.timeRemaining <= 60) {
                timerCard.classList.add('timer-danger');
            } else if (this.timeRemaining <= 300) {
                timerCard.classList.add('timer-warning');
            }
        }
    }
    
    showTimeWarning(message) {
        const modal = document.getElementById('timeWarningModal');
        const messageElement = document.getElementById('warning-message');
        
        if (modal && messageElement) {
            messageElement.textContent = message;
            const bootstrapModal = new bootstrap.Modal(modal);
            bootstrapModal.show();
        }
    }
    
    handleTimeExpired() {
        clearInterval(this.timer);
        
        // Show auto-submit modal
        const modal = document.getElementById('autoSubmitModal');
        if (modal) {
            const bootstrapModal = new bootstrap.Modal(modal, { backdrop: 'static', keyboard: false });
            bootstrapModal.show();
        }
        
        // Auto-submit after 3 seconds
        setTimeout(() => {
            this.submitQuestionnaire(null, true);
        }, 3000);
    }
    
    previousQuestion() {
        if (this.currentQuestion > 1) {
            this.hideCurrentQuestion();
            this.currentQuestion--;
            this.showCurrentQuestion();
            this.updateNavigation();
            this.updateProgress();
        }
    }
    
    nextQuestion() {
        if (this.validateCurrentQuestion()) {
            if (this.currentQuestion < this.totalQuestions) {
                this.hideCurrentQuestion();
                this.currentQuestion++;
                this.showCurrentQuestion();
                this.updateNavigation();
                this.updateProgress();
            }
        }
    }
    
    hideCurrentQuestion() {
        const currentCard = document.getElementById(`question-${this.currentQuestion}`);
        if (currentCard) {
            currentCard.style.display = 'none';
        }
    }
    
    showCurrentQuestion() {
        const currentCard = document.getElementById(`question-${this.currentQuestion}`);
        if (currentCard) {
            currentCard.style.display = 'block';
            currentCard.classList.add('fade-in');
            
            // Focus first input
            const firstInput = currentCard.querySelector('input, textarea');
            if (firstInput) {
                setTimeout(() => firstInput.focus(), 100);
            }
        }
    }
    
    updateNavigation() {
        const prevBtn = document.getElementById('prev-question');
        const nextBtn = document.getElementById('next-question');
        const submitBtn = document.getElementById('submit-questionnaire');
        
        if (prevBtn) {
            prevBtn.disabled = this.currentQuestion === 1;
        }
        
        if (nextBtn && submitBtn) {
            if (this.currentQuestion === this.totalQuestions) {
                nextBtn.style.display = 'none';
                submitBtn.style.display = 'inline-block';
            } else {
                nextBtn.style.display = 'inline-block';
                submitBtn.style.display = 'none';
            }
        }
    }
    
    updateProgress() {
        const progress = (this.currentQuestion / this.totalQuestions) * 100;
        
        // Update progress bar
        const progressBar = document.getElementById('progress-bar');
        if (progressBar) {
            progressBar.style.width = `${progress}%`;
        }
        
        // Update progress text
        const currentQuestionSpan = document.getElementById('current-question');
        const progressPercentage = document.getElementById('progress-percentage');
        
        if (currentQuestionSpan) {
            currentQuestionSpan.textContent = this.currentQuestion;
        }
        
        if (progressPercentage) {
            progressPercentage.textContent = `${Math.round(progress)}%`;
        }
    }
    
    validateCurrentQuestion() {
        const currentCard = document.getElementById(`question-${this.currentQuestion}`);
        if (!currentCard) return true;
        
        const questionData = this.data.questions[this.currentQuestion - 1];
        if (!questionData || !questionData.required) return true;
        
        const inputs = currentCard.querySelectorAll('input[type="radio"], textarea');
        let hasAnswer = false;
        
        for (const input of inputs) {
            if (input.type === 'radio' && input.checked) {
                hasAnswer = true;
                break;
            } else if (input.type !== 'radio' && input.value.trim()) {
                hasAnswer = true;
                break;
            }
        }
        
        if (!hasAnswer) {
            this.showValidationError('This question is required. Please provide an answer before continuing.');
            return false;
        }
        
        return true;
    }
    
    showValidationError(message) {
        // Create or update validation error message
        let errorDiv = document.querySelector('.validation-error');
        if (!errorDiv) {
            errorDiv = document.createElement('div');
            errorDiv.className = 'alert alert-danger validation-error mt-3';
            
            const currentCard = document.getElementById(`question-${this.currentQuestion}`);
            if (currentCard) {
                currentCard.appendChild(errorDiv);
            }
        }
        
        errorDiv.innerHTML = `<i class="fas fa-exclamation-triangle me-2"></i>${message}`;
        
        // Remove error after 5 seconds
        setTimeout(() => {
            if (errorDiv.parentNode) {
                errorDiv.parentNode.removeChild(errorDiv);
            }
        }, 5000);
    }
    
    handleAnswerChange(event) {
        const input = event.target;
        const questionId = this.extractQuestionId(input.name);
        
        if (questionId) {
            if (input.type === 'radio') {
                this.answers[questionId] = [input.value];
            } else {
                this.answers[questionId] = [input.value];
            }
            
            // Remove validation error if present
            const errorDiv = document.querySelector('.validation-error');
            if (errorDiv) {
                errorDiv.remove();
            }
        }
    }
    
    extractQuestionId(inputName) {
        const match = inputName.match(/question_(.+)/);
        return match ? match[1] : null;
    }
    
    setupCharacterCounters() {
        const textareas = document.querySelectorAll('.question-textarea[maxlength]');
        textareas.forEach(textarea => {
            this.updateCharacterCount(textarea);
        });
    }
    
    updateCharacterCount(textarea) {
        const maxLength = parseInt(textarea.getAttribute('maxlength'));
        const currentLength = textarea.value.length;
        
        const counterElement = textarea.parentNode.querySelector('.char-count');
        if (counterElement) {
            counterElement.textContent = currentLength;
            
            // Update styling based on usage
            const parent = counterElement.closest('.character-count');
            if (parent) {
                parent.classList.remove('text-warning', 'text-danger');
                
                if (currentLength > maxLength * 0.9) {
                    parent.classList.add('text-danger');
                } else if (currentLength > maxLength * 0.8) {
                    parent.classList.add('text-warning');
                }
            }
        }
    }
    
    startAutoSave() {
        this.autoSaveInterval = setInterval(() => {
            this.saveProgress();
        }, 30000); // Save every 30 seconds
    }
    
    async saveProgress() {
        if (!this.isStarted || this.isSubmitted) return;
        
        try {
            const response = await fetch('/api/applications/workflow/questionnaires/save-progress', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: JSON.stringify({
                    application_id: this.data.application_id,
                    questionnaire_id: this.data.questionnaire_id,
                    answers: this.answers,
                    current_question: this.currentQuestion,
                    time_spent: (this.timeLimit * 60) - this.timeRemaining
                })
            });
            
            if (response.ok) {
                console.log('Progress saved successfully');
            }
        } catch (error) {
            console.error('Error saving progress:', error);
        }
    }
    
    async sendTimerStartEvent() {
        try {
            await fetch(`/api/applications/workflow/applications/${this.data.application_id}/questionnaires/timer/start`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });
        } catch (error) {
            console.error('Error sending timer start event:', error);
        }
    }
    
    async submitQuestionnaire(event, isAutoSubmit = false) {
        if (event) {
            event.preventDefault();
        }
        
        if (this.isSubmitted) return;
        
        // Validate all required questions if not auto-submit
        if (!isAutoSubmit && !this.validateAllQuestions()) {
            return;
        }
        
        this.isSubmitted = true;
        
        // Stop timer and auto-save
        if (this.timer) {
            clearInterval(this.timer);
        }
        if (this.autoSaveInterval) {
            clearInterval(this.autoSaveInterval);
        }
        
        // Collect all answers
        this.collectAllAnswers();
        
        // Show loading state
        this.showSubmissionLoading();
        
        try {
            const timeSpent = (this.timeLimit * 60) - this.timeRemaining;
            
            const response = await fetch('/api/applications/workflow/questionnaires/submit', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: JSON.stringify({
                    application_id: this.data.application_id,
                    questionnaire_id: this.data.questionnaire_id,
                    answers: this.answers,
                    time_spent_seconds: timeSpent,
                    is_auto_submit: isAutoSubmit
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showCompletionScreen(timeSpent);
            } else {
                this.showSubmissionError(result.message || 'Failed to submit questionnaire');
            }
        } catch (error) {
            console.error('Error submitting questionnaire:', error);
            this.showSubmissionError('An error occurred while submitting your answers');
        }
    }
    
    validateAllQuestions() {
        const requiredQuestions = this.data.questions.filter(q => q.required);
        const missingAnswers = [];
        
        for (const question of requiredQuestions) {
            if (!this.answers[question.question_id] || 
                this.answers[question.question_id].length === 0 ||
                this.answers[question.question_id][0].trim() === '') {
                missingAnswers.push(question.question_id);
            }
        }
        
        if (missingAnswers.length > 0) {
            this.showValidationError(`Please answer all required questions before submitting (${missingAnswers.length} remaining).`);
            return false;
        }
        
        return true;
    }
    
    collectAllAnswers() {
        const form = document.getElementById('questionnaire-form');
        if (!form) return;
        
        // Collect radio button answers
        const radioInputs = form.querySelectorAll('input[type="radio"]:checked');
        radioInputs.forEach(input => {
            const questionId = this.extractQuestionId(input.name);
            if (questionId) {
                this.answers[questionId] = [input.value];
            }
        });
        
        // Collect textarea answers
        const textareas = form.querySelectorAll('textarea');
        textareas.forEach(textarea => {
            const questionId = this.extractQuestionId(textarea.name);
            if (questionId && textarea.value.trim()) {
                this.answers[questionId] = [textarea.value.trim()];
            }
        });
    }
    
    showSubmissionLoading() {
        const form = document.getElementById('questionnaire-form');
        if (form) {
            const loadingDiv = document.createElement('div');
            loadingDiv.className = 'text-center py-4';
            loadingDiv.innerHTML = `
                <div class="spinner-border text-primary mb-3" role="status">
                    <span class="visually-hidden">Submitting...</span>
                </div>
                <h5>Submitting Your Answers</h5>
                <p class="text-muted">Please wait while we save your responses...</p>
            `;
            
            form.innerHTML = '';
            form.appendChild(loadingDiv);
        }
    }
    
    showSubmissionError(message) {
        const form = document.getElementById('questionnaire-form');
        if (form) {
            form.innerHTML = `
                <div class="alert alert-danger text-center">
                    <h5 class="alert-heading">Submission Failed</h5>
                    <p>${message}</p>
                    <button type="button" class="btn btn-outline-danger" onclick="location.reload()">
                        <i class="fas fa-redo me-2"></i>Try Again
                    </button>
                </div>
            `;
        }
    }
    
    showCompletionScreen(timeSpent) {
        // Hide form and show completion card
        const form = document.getElementById('questionnaire-form');
        const completionCard = document.getElementById('completion-card');
        
        if (form) form.style.display = 'none';
        if (completionCard) {
            completionCard.style.display = 'block';
            completionCard.classList.add('fade-in');
        }
        
        // Update completion stats
        const completionTime = document.getElementById('completion-time');
        const questionsAnswered = document.getElementById('questions-answered');
        
        if (completionTime) {
            completionTime.textContent = Math.ceil(timeSpent / 60);
        }
        
        if (questionsAnswered) {
            questionsAnswered.textContent = Object.keys(this.answers).length;
        }
        
        // Hide timer
        const timerCard = document.querySelector('.timer-card');
        if (timerCard) {
            timerCard.style.display = 'none';
        }
        
        // Update progress to 100%
        const progressBar = document.getElementById('progress-bar');
        const progressPercentage = document.getElementById('progress-percentage');
        
        if (progressBar) progressBar.style.width = '100%';
        if (progressPercentage) progressPercentage.textContent = '100%';
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new QuestionnaireManager();
});