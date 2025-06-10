// Patient Detail - Section History Controls
document.addEventListener('DOMContentLoaded', function() {
    console.log('Patient detail page script loaded');

    // Find all section links and add click event listeners
    document.querySelectorAll('.section-link').forEach(function(link) {
        link.addEventListener('click', function(e) {
            e.preventDefault();

            // Get the section name from data attribute
            const sectionName = this.getAttribute('data-section');
            console.log('Section clicked:', sectionName);

            // Find the corresponding history section
            const historySection = document.getElementById(sectionName + '-history');

            if (historySection) {
                // Hide all history sections first
                document.querySelectorAll('.history-section').forEach(function(section) {
                    section.style.display = 'none';
                });

                // Show the selected history section
                historySection.style.display = 'block';
                historySection.scrollIntoView({behavior: 'smooth'});

                console.log('Displayed section:', sectionName + '-history');
            } else {
                console.error('Could not find history section:', sectionName + '-history');
            }
        });
    });

    // Add close button functionality to history sections
    document.querySelectorAll('.card-header .btn-close').forEach(function(closeBtn) {
        closeBtn.addEventListener('click', function() {
            // Find the parent history section
            const historySection = this.closest('.history-section');
            if (historySection) {
                historySection.style.display = 'none';
            }
        });
    });
});

/**
 * Progressive Patient Detail Loading
 * Load data sections only when needed
 */

class PatientDetailLoader {
    constructor(patientId) {
        this.patientId = patientId;
        this.loadedSections = new Set();
    }

    async loadBasicInfo() {
        if (this.loadedSections.has('basic')) return;

        const data = await apiClient.fetchPatientDetail(this.patientId, []);
        this.renderBasicInfo(data);
        this.loadedSections.add('basic');
    }

    async loadVitals() {
        if (this.loadedSections.has('vitals')) return;

        const data = await apiClient.fetchPatientDetail(this.patientId, ['vitals']);
        this.renderVitals(data.recent_vitals);
        this.loadedSections.add('vitals');
    }

    async loadVisits() {
        if (this.loadedSections.has('visits')) return;

        const data = await apiClient.fetchPatientDetail(this.patientId, ['visits']);
        this.renderVisits(data.recent_visits);
        this.loadedSections.add('visits');
    }

    renderBasicInfo(data) {
        const container = document.getElementById('patient-basic-info');
        if (container) {
            container.innerHTML = `
                <h3>${data.first_name} ${data.last_name}</h3>
                <p>MRN: ${data.mrn} | Age: ${data.age} | Sex: ${data.sex}</p>
                <p>Phone: ${data.phone || 'N/A'}</p>
            `;
        }
    }

    renderVitals(vitals) {
        const container = document.getElementById('patient-vitals');
        if (container && vitals) {
            const vitalsHTML = vitals.map(v => `
                <div class="vital-entry">
                    <span class="date">${v.date}</span>
                    <span class="weight">${v.weight}kg</span>
                    <span class="bp">${v.bp || 'N/A'}</span>
                </div>
            `).join('');
            container.innerHTML = vitalsHTML;
        }
    }

    renderVisits(visits) {
        const container = document.getElementById('patient-visits');
        if (container && visits) {
            const visitsHTML = visits.map(v => `
                <div class="visit-entry">
                    <span class="date">${v.visit_date}</span>
                    <span class="type">${v.visit_type}</span>
                    <span class="provider">${v.provider}</span>
                </div>
            `).join('');
            container.innerHTML = visitsHTML;
        }
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    const patientId = document.querySelector('[data-patient-id]')?.dataset.patientId;
    if (patientId) {
        const loader = new PatientDetailLoader(patientId);
        loader.loadBasicInfo();

        // Load other sections on demand
        document.getElementById('vitals-tab')?.addEventListener('click', () => loader.loadVitals());
        document.getElementById('visits-tab')?.addEventListener('click', () => loader.loadVisits());
    }
});