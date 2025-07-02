/**
 * Prep Sheet JavaScript
 * Handles interactive functionality for the patient prep sheet page
 */

document.addEventListener('DOMContentLoaded', function() {
    console.log('Prep sheet script loaded');

    // Common functions
    function getStorageKey(elementId, type = 'checkbox') {
        // Extract patient ID from URL or data attribute
        const patientId = document.body.getAttribute('data-patient-id') || 
                         window.location.pathname.split('/')[2];
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

// Initialize screening data when page loads
document.addEventListener('DOMContentLoaded', function() {
    console.log('Prep sheet JavaScript loaded');

    // Initialize any existing data including document matches
    const checkedBoxes = document.querySelectorAll('.screening-checkbox:checked');
    checkedBoxes.forEach(checkbox => {
        const screeningName = checkbox.getAttribute('data-screening');
        const statusInput = document.querySelector(`[data-screening="${screeningName}"].screening-status`);
        const statusValue = statusInput ? statusInput.value : '';
        updateScreeningData(screeningName, true, statusValue);
    });

    // Initialize unchecked items that have document matches
    const allScreeningRows = document.querySelectorAll('.screening-row');
    allScreeningRows.forEach(row => {
        const screeningName = row.getAttribute('data-screening');
        const checkbox = row.querySelector('.screening-checkbox');
        const statusInput = row.querySelector('.screening-status');

        // If there's a status but checkbox isn't checked, update the data
        if (statusInput && statusInput.value && !checkbox.checked) {
            updateScreeningData(screeningName, false, statusInput.value);
        }
    });
});

function setStatus(screeningName, status) {
    const statusInput = document.querySelector(`[data-screening="${screeningName}"].screening-status`);
    if (statusInput) {
        statusInput.value = status;
        updateScreeningData(screeningName, null, status);
    }
}

function showDocumentMatchDetails(screeningName) {
    // This function could be expanded to show a modal with detailed document match information
    console.log(`Showing document match details for ${screeningName}`);

    // For now, just highlight the status input
    const statusInput = document.querySelector(`[data-screening="${screeningName}"].screening-status`);
    if (statusInput) {
        statusInput.focus();
        statusInput.select();
    }
}