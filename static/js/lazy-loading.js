
/**
 * Lazy Loading Utility for Healthcare App
 * Reduces initial payload size by loading data on demand
 */

class OptimizedAPIClient {
    constructor(baseURL = '/api') {
        this.baseURL = baseURL;
    }

    async fetchPatients(page = 1, fields = ['id', 'mrn', 'first_name', 'last_name', 'age', 'sex']) {
        const params = new URLSearchParams({
            page: page,
            per_page: 20,
            fields: fields.join(',')
        });
        
        const response = await fetch(`${this.baseURL}/patients?${params}`);
        return response.json();
    }

    async fetchPatientDetail(patientId, includes = []) {
        const params = new URLSearchParams();
        includes.forEach(include => params.append(`include_${include}`, 'true'));
        
        const response = await fetch(`${this.baseURL}/patients/${patientId}?${params}`);
        return response.json();
    }

    async fetchAppointments(date, fields = ['id', 'patient_name', 'appointment_time', 'status']) {
        const params = new URLSearchParams({
            date: date,
            fields: fields.join(',')
        });
        
        const response = await fetch(`${this.baseURL}/appointments?${params}`);
        return response.json();
    }
}

// Initialize optimized API client
const apiClient = new OptimizedAPIClient();

class LazyLoader {
    constructor() {
        this.cache = new Map();
        this.loadingStates = new Map();
    }

    async loadPatientData(patientId, dataType, options = {}) {
        const cacheKey = `${patientId}-${dataType}-${JSON.stringify(options)}`;
        
        // Return cached data if available
        if (this.cache.has(cacheKey)) {
            return this.cache.get(cacheKey);
        }

        // Prevent duplicate requests
        if (this.loadingStates.has(cacheKey)) {
            return this.loadingStates.get(cacheKey);
        }

        // Create loading promise
        const loadingPromise = this._fetchData(patientId, dataType, options);
        this.loadingStates.set(cacheKey, loadingPromise);

        try {
            const data = await loadingPromise;
            this.cache.set(cacheKey, data);
            return data;
        } finally {
            this.loadingStates.delete(cacheKey);
        }
    }

    async _fetchData(patientId, dataType, options) {
        const endpoints = {
            'vitals': `/api/patients/${patientId}/vitals`,
            'visits': `/api/patients/${patientId}/visits`,
            'documents': `/api/patients/${patientId}/documents/summary`
        };

        const url = endpoints[dataType];
        if (!url) {
            throw new Error(`Unknown data type: ${dataType}`);
        }

        // Add query parameters
        const params = new URLSearchParams(options);
        const fullUrl = params.toString() ? `${url}?${params}` : url;

        const response = await fetch(fullUrl, {
            headers: {
                'Authorization': `Bearer ${this.getAuthToken()}`,
                'Accept': 'application/json'
            }
        });

        if (!response.ok) {
            throw new Error(`Failed to load ${dataType}: ${response.statusText}`);
        }

        return response.json();
    }

    getAuthToken() {
        // Get JWT token from localStorage or cookie
        return localStorage.getItem('auth_token') || '';
    }

    // Clear cache for a specific patient
    clearPatientCache(patientId) {
        for (const key of this.cache.keys()) {
            if (key.startsWith(`${patientId}-`)) {
                this.cache.delete(key);
            }
        }
    }

    // Show loading indicators
    showLoading(containerId) {
        const container = document.getElementById(containerId);
        if (container) {
            container.innerHTML = '<div class="loading-spinner">Loading...</div>';
        }
    }

    // Load data into container with error handling
    async loadIntoContainer(patientId, dataType, containerId, options = {}) {
        try {
            this.showLoading(containerId);
            const data = await this.loadPatientData(patientId, dataType, options);
            this.renderData(data, containerId, dataType);
        } catch (error) {
            console.error(`Error loading ${dataType}:`, error);
            this.showError(containerId, `Failed to load ${dataType}`);
        }
    }

    renderData(data, containerId, dataType) {
        const container = document.getElementById(containerId);
        if (!container) return;

        const renderers = {
            'vitals': this.renderVitals,
            'visits': this.renderVisits,
            'documents': this.renderDocuments
        };

        const renderer = renderers[dataType];
        if (renderer) {
            container.innerHTML = renderer(data);
        } else {
            container.innerHTML = JSON.stringify(data, null, 2);
        }
    }

    renderVitals(data) {
        if (!data.vitals || data.vitals.length === 0) {
            return '<p>No vitals data available</p>';
        }

        return `
            <div class="vitals-list">
                ${data.vitals.map(vital => `
                    <div class="vital-item">
                        <span class="vital-date">${vital.date}</span>
                        <span class="vital-data">
                            BP: ${vital.blood_pressure_systolic}/${vital.blood_pressure_diastolic}
                            Pulse: ${vital.pulse}
                            Temp: ${vital.temperature}°F
                        </span>
                    </div>
                `).join('')}
            </div>
        `;
    }

    renderVisits(data) {
        if (!data.visits || data.visits.length === 0) {
            return '<p>No visits data available</p>';
        }

        return `
            <div class="visits-list">
                ${data.visits.map(visit => `
                    <div class="visit-item">
                        <div class="visit-date">${visit.visit_date}</div>
                        <div class="visit-type">${visit.visit_type}</div>
                        <div class="visit-provider">${visit.provider}</div>
                        <div class="visit-reason">${visit.reason}</div>
                    </div>
                `).join('')}
            </div>
        `;
    }

    renderDocuments(data) {
        if (!data.documents || data.documents.length === 0) {
            return '<p>No documents available</p>';
        }

        return `
            <div class="documents-list">
                ${data.documents.map(doc => `
                    <div class="document-item">
                        <span class="doc-filename">${doc.filename}</span>
                        <span class="doc-type">${doc.document_type}</span>
                        <span class="doc-date">${doc.document_date}</span>
                    </div>
                `).join('')}
            </div>
        `;
    }

    showError(containerId, message) {
        const container = document.getElementById(containerId);
        if (container) {
            container.innerHTML = `<div class="error-message">${message}</div>`;
        }
    }
}

// Global instance
const lazyLoader = new LazyLoader();

// Auto-setup for patient detail pages
document.addEventListener('DOMContentLoaded', function() {
    const patientId = document.querySelector('[data-patient-id]')?.dataset.patientId;
    
    if (patientId) {
        // Set up lazy loading for expandable sections
        document.querySelectorAll('[data-lazy-load]').forEach(element => {
            const dataType = element.dataset.lazyLoad;
            const containerId = element.id;
            
            // Load on click or intersection observer
            element.addEventListener('click', () => {
                lazyLoader.loadIntoContainer(patientId, dataType, containerId);
            });
        });
    }
});

window.LazyLoader = LazyLoader;
window.lazyLoader = lazyLoader;
