
/**
 * Loading State Manager
 * Handles loading states for high-traffic, performance-sensitive pages
 */

class LoadingStateManager {
    constructor() {
        this.activeLoadings = new Set();
        this.loadingOverlay = null;
        this.init();
    }

    init() {
        this.createGlobalOverlay();
        this.attachEventListeners();
    }

    createGlobalOverlay() {
        this.loadingOverlay = document.createElement('div');
        this.loadingOverlay.id = 'global-loading-overlay';
        this.loadingOverlay.className = 'loading-overlay';
        this.loadingOverlay.innerHTML = `
            <div class="loading-content">
                <div class="loading-spinner"></div>
                <div class="loading-text">Loading...</div>
                <div class="loading-progress">
                    <div class="progress-bar"></div>
                </div>
            </div>
        `;
        this.loadingOverlay.style.display = 'none';
        document.body.appendChild(this.loadingOverlay);
    }

    showLoading(options = {}) {
        const {
            message = 'Loading...',
            showProgress = false,
            preventInteraction = true,
            target = null,
            id = 'default'
        } = options;

        this.activeLoadings.add(id);

        if (target) {
            this.showTargetedLoading(target, message, showProgress);
        } else {
            this.showGlobalLoading(message, showProgress, preventInteraction);
        }
    }

    showGlobalLoading(message, showProgress, preventInteraction) {
        const textElement = this.loadingOverlay.querySelector('.loading-text');
        const progressElement = this.loadingOverlay.querySelector('.loading-progress');
        
        textElement.textContent = message;
        progressElement.style.display = showProgress ? 'block' : 'none';
        
        if (preventInteraction) {
            this.loadingOverlay.style.pointerEvents = 'all';
        } else {
            this.loadingOverlay.style.pointerEvents = 'none';
        }
        
        this.loadingOverlay.style.display = 'flex';
        document.body.classList.add('loading-active');
    }

    showTargetedLoading(target, message, showProgress) {
        const targetElement = typeof target === 'string' ? document.querySelector(target) : target;
        if (!targetElement) return;

        // Store original content
        if (!targetElement.dataset.originalContent) {
            targetElement.dataset.originalContent = targetElement.innerHTML;
        }

        const loadingHtml = `
            <div class="targeted-loading">
                <div class="loading-spinner-small"></div>
                <span class="loading-text-small">${message}</span>
                ${showProgress ? '<div class="progress-bar-small"></div>' : ''}
            </div>
        `;

        targetElement.innerHTML = loadingHtml;
        targetElement.classList.add('loading-state');
        targetElement.style.pointerEvents = 'none';
    }

    hideLoading(id = 'default') {
        this.activeLoadings.delete(id);

        // Only hide if no other loadings are active
        if (this.activeLoadings.size === 0) {
            this.hideGlobalLoading();
            this.hideAllTargetedLoadings();
        }
    }

    hideGlobalLoading() {
        this.loadingOverlay.style.display = 'none';
        document.body.classList.remove('loading-active');
    }

    hideAllTargetedLoadings() {
        document.querySelectorAll('.loading-state').forEach(element => {
            if (element.dataset.originalContent) {
                element.innerHTML = element.dataset.originalContent;
                delete element.dataset.originalContent;
            }
            element.classList.remove('loading-state');
            element.style.pointerEvents = '';
        });
    }

    updateProgress(percentage, id = 'default') {
        const progressBars = document.querySelectorAll('.progress-bar, .progress-bar-small');
        progressBars.forEach(bar => {
            bar.style.width = `${Math.min(100, Math.max(0, percentage))}%`;
        });
    }

    updateMessage(message, id = 'default') {
        const textElements = document.querySelectorAll('.loading-text, .loading-text-small');
        textElements.forEach(element => {
            element.textContent = message;
        });
    }

    attachEventListeners() {
        // Auto-detect navigation to high-impact pages
        const originalPushState = history.pushState;
        const originalReplaceState = history.replaceState;
        
        history.pushState = (...args) => {
            this.handleNavigation(args[2]);
            return originalPushState.apply(history, args);
        };
        
        history.replaceState = (...args) => {
            this.handleNavigation(args[2]);
            return originalReplaceState.apply(history, args);
        };

        // Handle back/forward navigation
        window.addEventListener('popstate', (e) => {
            this.handleNavigation(location.pathname);
        });

        // Enhanced navigation detection for slow page transitions
        this.detectSlowNavigation();

        // Handle form submissions on problematic pages
        document.addEventListener('submit', (e) => {
            this.handleFormSubmission(e);
        });

        // Handle file uploads
        document.addEventListener('change', (e) => {
            if (e.target.type === 'file') {
                this.handleFileUpload(e);
            }
        });
    }

    handleNavigation(url) {
        const problematicPaths = ['/screenings', '/patients', '/screening-types'];
        
        if (problematicPaths.some(path => url?.includes(path))) {
            this.showLoading({
                message: 'Loading page...',
                id: 'navigation'
            });
            
            // Auto-hide after reasonable timeout
            setTimeout(() => {
                this.hideLoading('navigation');
            }, 5000);
        }
    }

    // Enhanced navigation detection for slow page transitions
    detectSlowNavigation() {
        // Detect clicks on navigation links that lead to slow pages
        document.addEventListener('click', (e) => {
            const link = e.target.closest('a[href]');
            if (!link) return;

            const href = link.getAttribute('href');
            
            // Check for specific slow navigation patterns
            const slowNavigationPatterns = [
                // Home to screenings
                { from: '/', to: '/screenings', message: 'Loading screening list...' },
                // Screenings tab switching  
                { from: '/screenings', to: '/screenings?tab=types', message: 'Loading screening types...' },
                { from: '/screenings', to: '/screenings?tab=screenings', message: 'Loading screenings...' },
                // Any navigation to screenings
                { to: '/screenings', message: 'Loading screening data...' }
            ];

            for (const pattern of slowNavigationPatterns) {
                const currentPath = window.location.pathname + window.location.search;
                
                // Check if this navigation matches a slow pattern
                if (href.includes(pattern.to)) {
                    // If there's a specific 'from' pattern, check it matches
                    if (pattern.from && !currentPath.includes(pattern.from)) {
                        continue;
                    }
                    
                    // Show loading state immediately
                    this.showLoading({
                        message: pattern.message,
                        showProgress: true,
                        id: 'slow-navigation'
                    });
                    
                    // Start progress simulation
                    this.simulateNavigationProgress();
                    break;
                }
            }
        });
    }

    simulateNavigationProgress() {
        let progress = 0;
        const interval = setInterval(() => {
            progress += 10;
            this.updateProgress(progress, 'slow-navigation');
            
            if (progress >= 90) {
                clearInterval(interval);
                // Don't hide automatically, let page load complete it
            }
        }, 200);

        // Safety timeout to hide loading state
        setTimeout(() => {
            clearInterval(interval);
            this.hideLoading('slow-navigation');
        }, 8000);
    }

    handleFormSubmission(event) {
        const form = event.target;
        const currentPath = window.location.pathname;
        
        // Check if this form has already been processed by loading manager
        if (form.dataset.loadingProcessed === 'true') {
            // Allow normal submission
            return;
        }
        
        // Screening types edit form
        if (currentPath.includes('/screening-types/edit') || form.closest('[data-screening-type-form]')) {
            event.preventDefault();
            form.dataset.loadingProcessed = 'true';
            this.handleScreeningTypeSubmission(form);
            return;
        }
        
        // Document upload form
        if (currentPath.includes('/document/add') || form.querySelector('input[type="file"]')) {
            event.preventDefault();
            form.dataset.loadingProcessed = 'true';
            this.handleDocumentUpload(form);
            return;
        }
    }

    async handleScreeningTypeSubmission(form) {
        this.showLoading({
            message: 'Validating screening type data...',
            showProgress: true,
            id: 'screening-form'
        });

        try {
            // Update progress through validation steps
            this.updateProgress(25, 'screening-form');
            this.updateMessage('Updating keywords data...', 'screening-form');
            
            // Ensure keywords are properly formatted - check if function exists
            if (typeof this.updateFormKeywordsData === 'function') {
                this.updateFormKeywordsData('edit-form');
            } else if (typeof window.updateFormKeywordsData === 'function') {
                window.updateFormKeywordsData('edit-form');
            }
            
            this.updateProgress(50, 'screening-form');
            this.updateMessage('Updating trigger conditions...', 'screening-form');
            
            // Ensure trigger conditions are properly formatted - check if function exists
            if (typeof this.updateFormTriggerConditionsData === 'function') {
                this.updateFormTriggerConditionsData('edit-form');
            } else if (typeof window.updateFormTriggerConditionsData === 'function') {
                window.updateFormTriggerConditionsData('edit-form');
            }
            
            this.updateProgress(75, 'screening-form');
            this.updateMessage('Saving screening type...', 'screening-form');
            
            // Validate form before submission
            const formData = new FormData(form);
            const requiredFields = ['name'];
            let isValid = true;
            
            for (const field of requiredFields) {
                if (!formData.get(field) || formData.get(field).trim() === '') {
                    console.error(`Required field missing: ${field}`);
                    isValid = false;
                }
            }
            
            if (!isValid) {
                throw new Error('Required fields are missing');
            }
            
            // Small delay to ensure all operations complete
            await new Promise(resolve => setTimeout(resolve, 300));
            
            this.updateProgress(100, 'screening-form');
            this.updateMessage('Finalizing changes...', 'screening-form');
            
            // Create a new form submission using FormData and fetch API
            const submitUrl = form.action || window.location.pathname;
            const submitMethod = form.method || 'POST';
            
            console.log('Submitting form to:', submitUrl, 'via', submitMethod);
            console.log('Form data:', Object.fromEntries(formData.entries()));
            
            // Submit using fetch to avoid form.submit() issues
            const response = await fetch(submitUrl, {
                method: submitMethod,
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });
            
            if (response.ok) {
                // If successful, redirect or reload
                if (response.redirected) {
                    window.location.href = response.url;
                } else {
                    window.location.reload();
                }
            } else {
                const errorText = await response.text();
                throw new Error(`Server error: ${response.status} - ${errorText}`);
            }
            
        } catch (error) {
            console.error('Error processing screening type form:', error);
            this.hideLoading('screening-form');
            alert(`Error processing form: ${error.message}. Please try again.`);
            
            // Reset the form processing flag so user can try again
            form.dataset.loadingProcessed = 'false';
        }
    }

    async handleDocumentUpload(form) {
        const fileInput = form.querySelector('input[type="file"]');
        const file = fileInput?.files[0];
        
        if (file) {
            this.showLoading({
                message: `Uploading ${file.name}...`,
                showProgress: true,
                id: 'document-upload'
            });
            
            // Simulate upload progress
            for (let i = 0; i <= 100; i += 10) {
                await new Promise(resolve => setTimeout(resolve, 100));
                this.updateProgress(i, 'document-upload');
                
                if (i === 30) this.updateMessage('Processing file...', 'document-upload');
                if (i === 70) this.updateMessage('Saving to database...', 'document-upload');
                if (i === 90) this.updateMessage('Finalizing upload...', 'document-upload');
            }
        } else {
            this.showLoading({
                message: 'Creating document entry...',
                id: 'document-upload'
            });
        }
        
        // Submit the form
        form.submit();
    }

    handleFileUpload(event) {
        const file = event.target.files[0];
        if (!file) return;

        const currentPath = window.location.pathname;
        if (currentPath.includes('/document/add')) {
            this.showLoading({
                message: `Selected: ${file.name} (${this.formatFileSize(file.size)})`,
                target: event.target.closest('.form-group'),
                id: 'file-selected'
            });
            
            // Auto-hide after showing selection
            setTimeout(() => {
                this.hideLoading('file-selected');
            }, 2000);
        }
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    // Helper methods for form data updates (copied from existing code)
    updateFormKeywordsData(formPrefix) {
        const container = document.getElementById(`${formPrefix}-keywords-list`);
        if (!container) return;

        const keywords = Array.from(container.querySelectorAll('.badge')).map(badge => {
            const clone = badge.cloneNode(true);
            const closeButton = clone.querySelector('.btn-close');
            if (closeButton) closeButton.remove();
            return clone.textContent.trim();
        }).filter(keyword => keyword !== '');
        
        const hiddenInput = document.getElementById(`${formPrefix}-keywords-data`);
        if (hiddenInput) {
            hiddenInput.value = JSON.stringify(keywords);
        }
    }

    updateFormTriggerConditionsData(formPrefix) {
        const container = document.getElementById(`${formPrefix}-trigger-conditions-list`);
        if (!container) return;

        const conditions = Array.from(container.querySelectorAll('.badge')).map(badge => {
            return {
                system: badge.getAttribute('data-system'),
                code: badge.getAttribute('data-code'),
                display: badge.getAttribute('data-display')
            };
        });
        
        const hiddenInput = document.getElementById(`${formPrefix}-trigger-conditions-data`);
        if (hiddenInput) {
            hiddenInput.value = JSON.stringify(conditions);
        }
    }
}

// Initialize the loading state manager
window.loadingManager = new LoadingStateManager();

// Export for use in other scripts
window.LoadingStateManager = LoadingStateManager;
