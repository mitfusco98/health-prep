/**
 * Prep Sheet JavaScript
 * Handles interactive functionality for the patient prep sheet page
 */

document.addEventListener('DOMContentLoaded', function() {
    console.log('Prep sheet script loaded');

    // Common functions
    function getStorageKey(elementId, type = 'checkbox') {
        // Extract patient ID using multiple methods for reliability
        const patientId = window.PATIENT_ID || 
                         window.patientId || 
                         document.body.getAttribute('data-patient-id') || 
                         window.location.pathname.match(/\/patients\/(\d+)/)?.[1];
        return `patient_${patientId}_${elementId}_${type}`;
    }

    // Find all checkboxes in the screening checklist
    const checkboxes = document.querySelectorAll('.screening-container input[type="checkbox"]');
    // Find all status dropdowns
    const statusSelects = document.querySelectorAll('.screening-status-select');
    // Find all note inputs
    const noteInputs = document.querySelectorAll('.screening-note');

    // Toggle weight unit display
    const weightToggleButtons = document.querySelectorAll('.toggle-weight-unit');

    weightToggleButtons.forEach(function(button) {
        const parent = button.closest('.card-body');
        const kgDisplay = parent.querySelector('.weight-kg');
        const lbDisplay = parent.querySelector('.weight-lb');

        button.addEventListener('click', function() {
            // Toggle display
            if (kgDisplay.style.display === 'none') {
                kgDisplay.style.display = 'inline';
                lbDisplay.style.display = 'none';
                button.textContent = 'Show lbs';
                const weightInfo = button.closest('.card-body').querySelector('.weight-info');
                weightInfo.textContent = '(Metric)';
            } else {
                kgDisplay.style.display = 'none';
                lbDisplay.style.display = 'inline';
                button.textContent = 'Show kg';
                const weightInfo = button.closest('.card-body').querySelector('.weight-info');
                weightInfo.textContent = '(Imperial)';
            }
        });

        // Initialize button text
        button.textContent = 'Show lbs';
        const weightInfo = button.closest('.card-body').querySelector('.weight-info');
        weightInfo.textContent = '(Metric)';
    });

    // Load saved states for checkboxes
    checkboxes.forEach(function(checkbox) {
        const checkboxId = checkbox.id;
        const storageKey = getStorageKey(checkboxId);
        const savedState = localStorage.getItem(storageKey);

        if (savedState === 'true') {
            checkbox.checked = true;
        }

        // Add event listener to save state on change
        checkbox.addEventListener('change', function() {
            localStorage.setItem(storageKey, this.checked);
        });
    });

    // Load saved states for status dropdowns
    statusSelects.forEach(function(select) {
        const selectId = select.id;
        const storageKey = getStorageKey(selectId, 'status');
        const savedStatus = localStorage.getItem(storageKey);

        if (savedStatus) {
            select.value = savedStatus;
        }

        // Add event listener to save state on change
        select.addEventListener('change', function() {
            localStorage.setItem(storageKey, this.value);

            // Custom status handling
            if (this.value === 'custom') {
                // Find the associated note field
                const index = this.id.split('_').pop();
                const noteInput = document.getElementById(`screening_note_${index}`);

                if (noteInput) {
                    // Focus the note field
                    noteInput.focus();
                    // Add placeholder to indicate this is a custom status
                    noteInput.placeholder = 'Enter custom status here...';
                    // Add visual indication that this is a custom status input
                    noteInput.classList.add('custom-status-active');
                }
            } else {
                // Find the associated note field
                const index = this.id.split('_').pop();
                const noteInput = document.getElementById(`screening_note_${index}`);

                if (noteInput) {
                    // Reset placeholder
                    noteInput.placeholder = 'Add note...';
                    // Remove visual indication
                    noteInput.classList.remove('custom-status-active');
                }
            }
        });

        // Trigger the change event to initialize custom status fields
        if (select.value === 'custom') {
            select.dispatchEvent(new Event('change'));
        }
    });

    // Load saved notes
    noteInputs.forEach(function(input) {
        const inputId = input.id;
        const storageKey = getStorageKey(inputId, 'note');
        const savedNote = localStorage.getItem(storageKey);

        if (savedNote) {
            input.value = savedNote;
        }

        // Add event listener to save state on change
        input.addEventListener('input', function() {
            localStorage.setItem(storageKey, this.value);
        });
    });

    // Reset checkboxes button
    const resetButton = document.getElementById('reset-checkboxes');
    if (resetButton) {
        resetButton.addEventListener('click', function() {
            // Clear checkbox states
            checkboxes.forEach(function(checkbox) {
                checkbox.checked = false;
                localStorage.removeItem(getStorageKey(checkbox.id));
            });

            // Clear status selections
            statusSelects.forEach(function(select) {
                select.value = '';
                localStorage.removeItem(getStorageKey(select.id, 'status'));
            });

            // Clear notes
            noteInputs.forEach(function(input) {
                input.value = '';
                localStorage.removeItem(getStorageKey(input.id, 'note'));
                input.placeholder = 'Add note...';
                input.classList.remove('custom-status-active');
            });
        });
    }

    // Handle save prep sheet button
    const saveButton = document.getElementById('save-prep-sheet');
    if (saveButton) {
        saveButton.addEventListener('click', function() {
            const patientId = document.body.getAttribute('data-patient-id') || 
                             window.location.pathname.split('/')[2];

            // Create a form to submit
            const form = document.createElement('form');
            form.method = 'POST';
            form.action = `/patients/${patientId}/save_prep_sheet`;

            // Add hidden input for CSRF token
            const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
            if (csrfToken) {
                const csrfInput = document.createElement('input');
                csrfInput.type = 'hidden';
                csrfInput.name = 'csrf_token';
                csrfInput.value = csrfToken;
                form.appendChild(csrfInput);
            }

            // Add to document and submit
            document.body.appendChild(form);
            form.submit();
        });
    }
});

// Add custom CSS for the custom status feature
document.addEventListener('DOMContentLoaded', function() {
    // Create style element
    const style = document.createElement('style');
    style.textContent = `
        .custom-status-active {
            background-color: rgba(var(--bs-warning-rgb), 0.1);
            font-weight: bold;
            border-color: var(--bs-warning);
        }
    `;
    document.head.appendChild(style);
});

// Quick preset for last appointment date - moved to document ready
document.addEventListener('DOMContentLoaded', function() {
    const lastAppointmentButton = document.getElementById('cutoff-last-appointment');
    if (lastAppointmentButton) {
        lastAppointmentButton.addEventListener('click', function() {
            console.log('Last appointment button clicked');
            
            // Try multiple methods to get patient ID with detailed logging
            let patientId = null;
            
            // Method 1: Global variables
            if (window.PATIENT_ID && window.PATIENT_ID !== 'undefined' && window.PATIENT_ID !== 'null') {
                patientId = window.PATIENT_ID;
                console.log('Found patient ID via window.PATIENT_ID:', patientId);
            } else if (window.patientId && window.patientId !== 'undefined' && window.patientId !== 'null') {
                patientId = window.patientId;
                console.log('Found patient ID via window.patientId:', patientId);
            }
            
            // Method 2: URL extraction
            if (!patientId) {
                const urlMatch = window.location.pathname.match(/\/patients\/(\d+)/);
                if (urlMatch && urlMatch[1]) {
                    patientId = urlMatch[1];
                    console.log('Found patient ID via URL:', patientId);
                }
            }
            
            // Method 3: Data attributes
            if (!patientId) {
                const dataPatientId = document.body.getAttribute('data-patient-id');
                if (dataPatientId && dataPatientId !== 'undefined' && dataPatientId !== 'null') {
                    patientId = dataPatientId;
                    console.log('Found patient ID via data attribute:', patientId);
                }
            }

            // Debug all available information
            console.log('Debug info:');
            console.log('- window.PATIENT_ID:', window.PATIENT_ID);
            console.log('- window.patientId:', window.patientId);
            console.log('- URL pathname:', window.location.pathname);
            console.log('- Data attribute:', document.body.getAttribute('data-patient-id'));
            console.log('- Final patientId:', patientId);

            if (!patientId || patientId === 'undefined' || patientId === 'null' || patientId.toString().trim() === '') {
                console.error('Patient ID not found or invalid');
                alert('Patient ID not found. Please refresh the page and try again.');
                return;
            }

            // Get last appointment date from API
            fetch(`/api/patients/${patientId}/last_appointment`)
                .then(response => response.json())
                .then(data => {
                    console.log('Last appointment response:', data);
                    if (data.success && data.last_appointment_date) {
                        // Set all cutoff dates to the last appointment date
                        const cutoffInputs = document.querySelectorAll('.cutoff-date-input');
                        cutoffInputs.forEach(input => {
                            input.value = data.last_appointment_date;
                        });
                        alert(`Set cutoff to last appointment: ${data.formatted_date}`);
                    } else {
                        alert('No previous appointments found');
                    }
                })
                .catch(error => {
                    console.error('Error loading appointment data:', error);
                    alert('Error loading appointment data');
                });
        });
    }
});