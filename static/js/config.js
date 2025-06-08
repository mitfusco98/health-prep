
/**
 * Frontend Configuration Management
 * Loads configuration from backend and provides constants for JavaScript
 */

class AppConfig {
    constructor() {
        this.config = null;
        this.loaded = false;
    }

    async load() {
        if (this.loaded) {
            return this.config;
        }

        try {
            const response = await fetch('/api/config');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            this.config = await response.json();
            this.loaded = true;
            console.log('Configuration loaded:', this.config);
            return this.config;
        } catch (error) {
            console.error('Failed to load configuration:', error);
            // Fallback to default values
            this.config = this.getDefaultConfig();
            this.loaded = true;
            return this.config;
        }
    }

    getDefaultConfig() {
        return {
            APP_NAME: 'Healthcare Prep',
            APP_VERSION: '1.0.0',
            ENVIRONMENT: 'development',
            PAGINATION_PER_PAGE: 25,
            SEARCH_RESULTS_LIMIT: 100,
            MAX_RECENT_PATIENTS: 10,
            VITAL_SIGNS: ['blood_pressure', 'heart_rate', 'temperature', 'respiratory_rate', 'oxygen_saturation', 'weight', 'height'],
            APPOINTMENT_TYPES: ['routine', 'urgent', 'follow_up', 'consultation', 'procedure'],
            VISIT_TYPES: ['office_visit', 'telemedicine', 'hospital_visit', 'emergency_visit'],
            MAX_NAME_LENGTH: 100,
            MAX_NOTE_LENGTH: 5000,
            MAX_EMAIL_LENGTH: 254,
            MAX_PHONE_LENGTH: 20,
            MAX_FILE_SIZE_MB: 1,
            ALLOWED_FILE_EXTENSIONS: ['.pdf', '.jpg', '.jpeg', '.png', '.gif', '.txt', '.csv', '.xlsx', '.xls', '.doc', '.docx']
        };
    }

    // Convenience methods
    get(key, defaultValue = null) {
        if (!this.loaded) {
            console.warn('Configuration not loaded yet. Call load() first.');
            return defaultValue;
        }
        return this.config[key] !== undefined ? this.config[key] : defaultValue;
    }

    isProduction() {
        return this.get('ENVIRONMENT') === 'production';
    }

    isDevelopment() {
        return this.get('ENVIRONMENT') === 'development';
    }

    getAppName() {
        return this.get('APP_NAME');
    }

    getAppVersion() {
        return this.get('APP_VERSION');
    }

    getMaxFileSize() {
        return this.get('MAX_FILE_SIZE_MB') * 1024 * 1024; // Convert to bytes
    }

    getAllowedFileExtensions() {
        return this.get('ALLOWED_FILE_EXTENSIONS', []);
    }

    getVitalSigns() {
        return this.get('VITAL_SIGNS', []);
    }

    getAppointmentTypes() {
        return this.get('APPOINTMENT_TYPES', []);
    }

    getVisitTypes() {
        return this.get('VISIT_TYPES', []);
    }

    getPaginationPerPage() {
        return this.get('PAGINATION_PER_PAGE', 25);
    }

    getSearchResultsLimit() {
        return this.get('SEARCH_RESULTS_LIMIT', 100);
    }

    getMaxRecentPatients() {
        return this.get('MAX_RECENT_PATIENTS', 10);
    }

    // Validation helpers
    validateName(name) {
        const maxLength = this.get('MAX_NAME_LENGTH', 100);
        return name && name.length <= maxLength && /^[a-zA-Z\s\-\'\.]+$/.test(name);
    }

    validateEmail(email) {
        const maxLength = this.get('MAX_EMAIL_LENGTH', 254);
        const emailRegex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
        return email && email.length <= maxLength && emailRegex.test(email);
    }

    validatePhone(phone) {
        const maxLength = this.get('MAX_PHONE_LENGTH', 20);
        const digitsOnly = phone.replace(/\D/g, '');
        return phone && phone.length <= maxLength && digitsOnly.length >= 10 && digitsOnly.length <= 15;
    }

    validateNote(note) {
        const maxLength = this.get('MAX_NOTE_LENGTH', 5000);
        return !note || note.length <= maxLength;
    }

    validateFileSize(file) {
        const maxSize = this.getMaxFileSize();
        return file.size <= maxSize;
    }

    validateFileExtension(filename) {
        const allowedExtensions = this.getAllowedFileExtensions();
        const extension = '.' + filename.split('.').pop().toLowerCase();
        return allowedExtensions.includes(extension);
    }
}

// Global configuration instance
const appConfig = new AppConfig();

// Auto-load configuration when DOM is ready
document.addEventListener('DOMContentLoaded', async function() {
    try {
        await appConfig.load();
        
        // Dispatch a custom event when config is loaded
        const configLoadedEvent = new CustomEvent('configLoaded', {
            detail: { config: appConfig.config }
        });
        document.dispatchEvent(configLoadedEvent);
        
    } catch (error) {
        console.error('Failed to auto-load configuration:', error);
    }
});

// Export for use in other modules
window.AppConfig = appConfig;
