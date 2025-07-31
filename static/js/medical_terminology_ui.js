/**
 * Medical Terminology UI Components
 * Provides enhanced autocomplete, validation, and standardization
 * for screening types and medical conditions.
 */

class MedicalTerminologyUI {
    constructor() {
        this.activeAutocompletes = new Map();
        this.validationCache = new Map();
        this.debounceTimeouts = new Map();
    }

    /**
     * Initialize enhanced autocomplete for screening names
     */
    initScreeningAutocomplete(inputId, suggestionsContainerId) {
        const input = document.getElementById(inputId);
        const container = document.getElementById(suggestionsContainerId);
        
        if (!input || !container) {
            console.warn(`Screening autocomplete elements not found: ${inputId}, ${suggestionsContainerId}`);
            return;
        }

        // Add validation feedback container
        const validationFeedback = document.createElement('div');
        validationFeedback.className = 'terminology-validation-feedback mt-2';
        input.parentNode.appendChild(validationFeedback);

        // Setup autocomplete
        input.addEventListener('input', (e) => {
            this.handleScreeningInput(e.target, container, validationFeedback);
        });

        // Handle selection from suggestions
        container.addEventListener('click', (e) => {
            if (e.target.classList.contains('suggestion-item')) {
                const canonical = e.target.dataset.canonical;
                const description = e.target.dataset.description;
                
                input.value = canonical;
                container.innerHTML = '';
                
                // Show success feedback
                this.showValidationSuccess(validationFeedback, `✓ Using standard terminology: ${canonical}`);
                
                // Trigger validation
                this.validateScreeningName(canonical, validationFeedback);
            }
        });

        // Clear suggestions when clicking outside
        document.addEventListener('click', (e) => {
            if (!input.contains(e.target) && !container.contains(e.target)) {
                container.innerHTML = '';
            }
        });
    }

    /**
     * Initialize enhanced autocomplete for condition names
     */
    initConditionAutocomplete(inputId, suggestionsContainerId) {
        const input = document.getElementById(inputId);
        const container = document.getElementById(suggestionsContainerId);
        
        if (!input || !container) {
            console.warn(`Condition autocomplete elements not found: ${inputId}, ${suggestionsContainerId}`);
            return;
        }

        // Add validation feedback container
        const validationFeedback = document.createElement('div');
        validationFeedback.className = 'terminology-validation-feedback mt-2';
        input.parentNode.appendChild(validationFeedback);

        // Setup autocomplete
        input.addEventListener('input', (e) => {
            this.handleConditionInput(e.target, container, validationFeedback);
        });

        // Handle selection from suggestions
        container.addEventListener('click', (e) => {
            if (e.target.classList.contains('suggestion-item')) {
                const canonical = e.target.dataset.canonical;
                
                input.value = canonical;
                container.innerHTML = '';
                
                // Show success feedback
                this.showValidationSuccess(validationFeedback, `✓ Using standard terminology: ${canonical}`);
            }
        });

        // Clear suggestions when clicking outside
        document.addEventListener('click', (e) => {
            if (!input.contains(e.target) && !container.contains(e.target)) {
                container.innerHTML = '';
            }
        });
    }

    /**
     * Handle screening name input with debounced API calls
     */
    handleScreeningInput(input, container, feedbackElement) {
        const query = input.value.trim();
        
        // Clear previous timeout
        if (this.debounceTimeouts.has(input.id)) {
            clearTimeout(this.debounceTimeouts.get(input.id));
        }

        if (query.length < 2) {
            container.innerHTML = '';
            feedbackElement.innerHTML = '';
            return;
        }

        // Debounce API calls
        const timeout = setTimeout(() => {
            this.fetchScreeningSuggestions(query, container);
            this.validateScreeningName(query, feedbackElement);
        }, 300);

        this.debounceTimeouts.set(input.id, timeout);
    }

    /**
     * Handle condition name input with debounced API calls
     */
    handleConditionInput(input, container, feedbackElement) {
        const query = input.value.trim();
        
        // Clear previous timeout
        if (this.debounceTimeouts.has(input.id)) {
            clearTimeout(this.debounceTimeouts.get(input.id));
        }

        if (query.length < 2) {
            container.innerHTML = '';
            feedbackElement.innerHTML = '';
            return;
        }

        // Debounce API calls
        const timeout = setTimeout(() => {
            this.fetchConditionSuggestions(query, container);
            this.validateConditionName(query, feedbackElement);
        }, 300);

        this.debounceTimeouts.set(input.id, timeout);
    }

    /**
     * Fetch screening name suggestions from API
     */
    async fetchScreeningSuggestions(query, container) {
        try {
            const response = await fetch(`/api/terminology/screening/suggestions?q=${encodeURIComponent(query)}&limit=10`);
            const data = await response.json();

            if (data.suggestions && data.suggestions.length > 0) {
                this.renderScreeningSuggestions(data.suggestions, container);
            } else {
                container.innerHTML = '<div class="no-suggestions">No standard screening types found</div>';
            }
        } catch (error) {
            console.error('Error fetching screening suggestions:', error);
            container.innerHTML = '<div class="error-suggestions">Error loading suggestions</div>';
        }
    }

    /**
     * Fetch condition name suggestions from API
     */
    async fetchConditionSuggestions(query, container) {
        try {
            const response = await fetch(`/api/terminology/condition/suggestions?q=${encodeURIComponent(query)}&limit=10`);
            const data = await response.json();

            if (data.suggestions && data.suggestions.length > 0) {
                this.renderConditionSuggestions(data.suggestions, container);
            } else {
                container.innerHTML = '<div class="no-suggestions">No standard conditions found</div>';
            }
        } catch (error) {
            console.error('Error fetching condition suggestions:', error);
            container.innerHTML = '<div class="error-suggestions">Error loading suggestions</div>';
        }
    }

    /**
     * Render screening suggestions dropdown
     */
    renderScreeningSuggestions(suggestions, container) {
        const html = suggestions.map(suggestion => `
            <div class="suggestion-item" 
                 data-canonical="${suggestion.canonical_name}"
                 data-description="${suggestion.description}">
                <div class="suggestion-main">
                    <strong>${suggestion.canonical_name}</strong>
                    <span class="suggestion-category">${suggestion.category.replace('_', ' ')}</span>
                </div>
                <div class="suggestion-description">${suggestion.description}</div>
                <div class="suggestion-frequency">
                    Typical frequency: Every ${suggestion.typical_frequency.number} ${suggestion.typical_frequency.unit}
                </div>
            </div>
        `).join('');

        container.innerHTML = html;
    }

    /**
     * Render condition suggestions dropdown
     */
    renderConditionSuggestions(suggestions, container) {
        const html = suggestions.map(suggestion => `
            <div class="suggestion-item" 
                 data-canonical="${suggestion.canonical_name}">
                <div class="suggestion-main">
                    <strong>${suggestion.canonical_name}</strong>
                    <span class="suggestion-category">${suggestion.category}</span>
                </div>
                <div class="suggestion-codes">
                    SNOMED: ${suggestion.snomed_codes.slice(0, 2).join(', ')}
                    ${suggestion.snomed_codes.length > 2 ? '...' : ''}
                </div>
            </div>
        `).join('');

        container.innerHTML = html;
    }

    /**
     * Validate screening name using API
     */
    async validateScreeningName(name, feedbackElement) {
        try {
            const response = await fetch('/api/terminology/screening/normalize', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ name: name })
            });

            const data = await response.json();

            if (data.normalized) {
                if (data.canonical === name) {
                    this.showValidationSuccess(feedbackElement, '✓ Standard terminology recognized');
                } else {
                    this.showValidationSuggestion(feedbackElement, 
                        `Did you mean "${data.canonical}"? (${Math.round(data.confidence * 100)}% match)`);
                }
            } else if (data.confidence > 0.5) {
                this.showValidationWarning(feedbackElement, 
                    `Similar to "${data.canonical}" - consider using standard terminology`);
            } else {
                this.showValidationError(feedbackElement, 
                    'Non-standard terminology detected. Consider using a standard screening name for better variant detection.');
            }
        } catch (error) {
            console.error('Error validating screening name:', error);
        }
    }

    /**
     * Validate condition name using API
     */
    async validateConditionName(name, feedbackElement) {
        try {
            const response = await fetch('/api/terminology/condition/normalize', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ name: name })
            });

            const data = await response.json();

            if (data.normalized) {
                if (data.canonical === name) {
                    this.showValidationSuccess(feedbackElement, '✓ Standard medical terminology recognized');
                } else {
                    this.showValidationSuggestion(feedbackElement, 
                        `Did you mean "${data.canonical}"? (${Math.round(data.confidence * 100)}% match)`);
                }
            } else if (data.confidence > 0.4) {
                this.showValidationWarning(feedbackElement, 
                    `Similar to "${data.canonical}" - consider using standard terminology`);
            } else {
                this.showValidationInfo(feedbackElement, 
                    'Custom condition name. Standard terminology helps with screening rule matching.');
            }
        } catch (error) {
            console.error('Error validating condition name:', error);
        }
    }

    /**
     * Show validation feedback messages
     */
    showValidationSuccess(element, message) {
        element.innerHTML = `<div class="alert alert-success alert-sm"><i class="fas fa-check-circle me-1"></i>${message}</div>`;
    }

    showValidationSuggestion(element, message) {
        element.innerHTML = `<div class="alert alert-info alert-sm"><i class="fas fa-lightbulb me-1"></i>${message}</div>`;
    }

    showValidationWarning(element, message) {
        element.innerHTML = `<div class="alert alert-warning alert-sm"><i class="fas fa-exclamation-triangle me-1"></i>${message}</div>`;
    }

    showValidationError(element, message) {
        element.innerHTML = `<div class="alert alert-danger alert-sm"><i class="fas fa-exclamation-circle me-1"></i>${message}</div>`;
    }

    showValidationInfo(element, message) {
        element.innerHTML = `<div class="alert alert-secondary alert-sm"><i class="fas fa-info-circle me-1"></i>${message}</div>`;
    }

    /**
     * Validate entire form before submission
     */
    async validateForm(formElement) {
        const nameInput = formElement.querySelector('[name="name"]');
        const triggerConditionsInputs = formElement.querySelectorAll('[data-trigger-condition]');
        
        let isValid = true;
        const errors = [];

        // Validate screening name
        if (nameInput && nameInput.value.trim()) {
            try {
                const response = await fetch('/api/terminology/screening/validate', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        name: nameInput.value.trim(),
                        trigger_conditions: Array.from(triggerConditionsInputs).map(input => input.value.trim()).filter(v => v)
                    })
                });

                const validation = await response.json();

                if (!validation.name_valid && validation.name_confidence < 0.5) {
                    errors.push('Screening name not recognized in standard terminology');
                    isValid = false;
                }

                if (validation.warnings.length > 0) {
                    // Show warnings but don't block submission
                    console.warn('Form validation warnings:', validation.warnings);
                }
            } catch (error) {
                console.error('Error validating form:', error);
            }
        }

        return { isValid, errors };
    }
}

// Global instance
window.medicalTerminologyUI = new MedicalTerminologyUI();

// Auto-initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Initialize screening name autocomplete if elements exist
    if (document.getElementById('screening-name-input')) {
        window.medicalTerminologyUI.initScreeningAutocomplete(
            'screening-name-input',
            'screening-name-suggestions'
        );
    }

    // Initialize condition name autocomplete if elements exist
    if (document.getElementById('conditionName')) {
        window.medicalTerminologyUI.initConditionAutocomplete(
            'conditionName',
            'condition-name-suggestions'
        );
    }

    // Add form validation on submit
    const forms = document.querySelectorAll('form[data-validate-terminology]');
    forms.forEach(form => {
        form.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const validation = await window.medicalTerminologyUI.validateForm(form);
            
            if (validation.isValid) {
                // Allow form submission
                form.removeEventListener('submit', arguments.callee);
                form.submit();
            } else {
                // Show errors
                const errorContainer = form.querySelector('.terminology-errors') || 
                    form.insertBefore(document.createElement('div'), form.firstChild);
                errorContainer.className = 'terminology-errors alert alert-danger';
                errorContainer.innerHTML = `
                    <strong>Validation Errors:</strong>
                    <ul class="mb-0 mt-1">
                        ${validation.errors.map(error => `<li>${error}</li>`).join('')}
                    </ul>
                `;
            }
        });
    });
});