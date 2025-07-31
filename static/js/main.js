` tags.

```
<replit_final_file>
// main.js - Core JavaScript for HealthPrep application

// Configuration will be loaded from AppConfig
let CONFIG = null;

// Wait for configuration to load
document.addEventListener('configLoaded', function(event) {
    CONFIG = event.detail.config;
    console.log('Main.js using configuration:', CONFIG);

    // Initialize components that depend on configuration
    initializeConfigDependentComponents();
});

function initializeConfigDependentComponents() {
    // Initialize components that need configuration here
    if (typeof initializePagination === 'function') {
        initializePagination();
    }
    if (typeof initializeFileUpload === 'function') {
        initializeFileUpload();
    }
}

document.addEventListener('DOMContentLoaded', function() {
    // Handle appointment form submission
    const appointmentForm = document.getElementById('appointment-form');
    console.log('Appointment form found:', appointmentForm);
    if (appointmentForm) {
        // Stop using JavaScript form submission for simplicity - rely on direct form submission
        console.log('Skipping JavaScript form handler for appointments for now - using direct form submission');

        // Add the fallback date field to ensure proper redirect
        const submitBtn = document.getElementById('submit-appointment');
        if (submitBtn) {
            submitBtn.addEventListener('click', function(e) {
                // Don't prevent default, let the form submit normally, but add the fallback date
                const dateInput = document.querySelector('input[name="appointment_date"]');
                if (dateInput && dateInput.value) {
                    console.log('Adding hidden field with date:', dateInput.value);
                    // Check if fallback_date field already exists
                    let hiddenField = document.querySelector('input[name="fallback_date"]');
                    if (!hiddenField) {
                        hiddenField = document.createElement('input');
                        hiddenField.type = 'hidden';
                        hiddenField.name = 'fallback_date';
                        appointmentForm.appendChild(hiddenField);
                    }
                    hiddenField.value = dateInput.value;
                }
            });
        }
    }
    // Initialize any Bootstrap tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize any Bootstrap popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Make sure all dropdowns are properly initialized
    var dropdownElementList = [].slice.call(document.querySelectorAll('.dropdown-toggle'));
    dropdownElementList.map(function (dropdownToggleEl) {
        return new bootstrap.Dropdown(dropdownToggleEl);
    });

    // Handle section history links in patient detail page - optimized for performance
    const sectionContainer = document.querySelector('.patient-detail-container');
    if (sectionContainer) {
        // Use event delegation for better performance
        sectionContainer.addEventListener('click', function(e) {
            const sectionLink = e.target.closest('.section-link');
            if (sectionLink) {
                e.preventDefault();

                const sectionName = sectionLink.getAttribute('data-section');
                if (!sectionName) return;

                // Cache section elements for better performance
                if (!this._sectionCache) {
                    this._sectionCache = {};
                    document.querySelectorAll('.history-section').forEach(section => {
                        this._sectionCache[section.id] = section;
                    });
                }

                // Hide all sections efficiently
                Object.values(this._sectionCache).forEach(section => {
                    section.classList.add('d-none');
                });

                // Show the selected section
                const sectionToShow = this._sectionCache[`${sectionName}-history`];
                if (sectionToShow) {
                    sectionToShow.classList.remove('d-none');
                    sectionToShow.scrollIntoView({behavior: 'smooth', block: 'start'});
                }
            }
        });
    }

    // Form handling for date inputs - but preserve dates in appointment form
    const dateInputs = document.querySelectorAll('input[type="date"]');
    dateInputs.forEach(input => {
        // Skip auto-setting dates for appointment form - let those come from the server
        if (input.name === 'appointment_date' || input.id === 'appointment_date') {
            console.log('Preserving appointment date:', input.value);
            return;
        }

        // If there's no value and it's not required, set to today's date
        if (!input.value && !input.hasAttribute('required') && input.id !== 'date_of_birth') {
            const today = new Date();
            const yyyy = today.getFullYear();
            let mm = today.getMonth() + 1;
            let dd = today.getDate();

            if (dd < 10) dd = '0' + dd;
            if (mm < 10) mm = '0' + mm;

            input.value = `${yyyy}-${mm}-${dd}`;
        }
    });

    // Handle alerts that should auto-dismiss
    const autoDismissAlerts = document.querySelectorAll('.alert-auto-dismiss');
    autoDismissAlerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000); // Auto dismiss after 5 seconds
    });

    // BMI calculation helper for vital signs form
    const weightInput = document.getElementById('weight');
    const heightInput = document.getElementById('height');
    const bmiDisplay = document.getElementById('bmi-display');

    if (weightInput && heightInput && bmiDisplay) {
        const calculateBMI = () => {
            const weight = parseFloat(weightInput.value);
            const height = parseFloat(heightInput.value);

            if (weight > 0 && height > 0) {
                // Convert height from cm to m
                const heightInMeters = height / 100;
                // Calculate BMI: weight (kg) / height (m)^2
                const bmi = weight / (heightInMeters * heightInMeters);
                bmiDisplay.textContent = bmi.toFixed(1);

                // Update BMI classification
                let classification = '';
                if (bmi < 18.5) classification = 'Underweight';
                else if (bmi < 25) classification = 'Normal weight';
                else if (bmi < 30) classification = 'Overweight';
                else classification = 'Obese';

                document.getElementById('bmi-classification').textContent = classification;
            } else {
                bmiDisplay.textContent = '—';
                document.getElementById('bmi-classification').textContent = '';
            }
        };

        weightInput.addEventListener('input', calculateBMI);
        heightInput.addEventListener('input', calculateBMI);

        // Calculate on page load if values are present
        calculateBMI();
    }

    // Patient search functionality
    const patientSearchInput = document.getElementById('patient-search');
    if (patientSearchInput) {
        patientSearchInput.addEventListener('input', function(e) {
            const searchTerm = e.target.value.toLowerCase();
            const patientRows = document.querySelectorAll('.patient-row');

            patientRows.forEach(row => {
                const patientName = row.getAttribute('data-patient-name').toLowerCase();
                const patientMrn = row.getAttribute('data-patient-mrn').toLowerCase();

                if (patientName.includes(searchTerm) || patientMrn.includes(searchTerm)) {
                    row.style.display = '';
                } else {
                    row.style.display = 'none';
                }
            });
        });
    }

    // Handle form submissions with better error handling
    document.querySelectorAll('form').forEach(form => {
        form.addEventListener('submit', function(e) {
            const submitBtn = form.querySelector('button[type="submit"], input[type="submit"]');
            if (submitBtn && !submitBtn.disabled) {
                // Disable submit button to prevent double submission
                submitBtn.disabled = true;

                // Re-enable after a short delay if form doesn't actually submit
                setTimeout(() => {
                    if (submitBtn.disabled) {
                        submitBtn.disabled = false;
                    }
                }, 5000);
            }
        });
    });
});

// Helper function to format dates consistently throughout the application
function formatDate(dateString) {
    if (!dateString) return 'N/A';

    const date = new Date(dateString);
    const options = { year: 'numeric', month: 'short', day: 'numeric' };
    return date.toLocaleDateString('en-US', options);
}

// Helper function to calculate age from DOB
function calculateAge(dateOfBirth) {
    const dob = new Date(dateOfBirth);
    const today = new Date();

    let age = today.getFullYear() - dob.getFullYear();
    const monthDiff = today.getMonth() - dob.getMonth();

    if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < dob.getDate())) {
        age--;
    }

    return age;
}

// Add event handlers for appointment deletion links
document.addEventListener('click', function(e) {
    // Check if the clicked element is an appointment delete link
    if (e.target.matches('a[href*="/appointments/"][href*="/delete"]') || 
        e.target.closest('a[href*="/appointments/"][href*="/delete"]')) {

        // Prevent the default link behavior
        e.preventDefault();

        // Get the link element (could be the icon inside or the link itself)
        const link = e.target.matches('a') ? e.target : e.target.closest('a');
        const deleteUrl = link.getAttribute('href');

        // Confirm deletion (optional)
        if (confirm('Are you sure you want to delete this appointment?')) {
            // Perform AJAX request to delete
            fetch(deleteUrl, {
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Show success message
                    const successMessage = document.createElement('div');
                    successMessage.className = 'alert alert-success alert-dismissible fade show';
                    successMessage.innerHTML = `
                        <strong>Success!</strong> ${data.message}
                        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                    `;
                    document.querySelector('.container').prepend(successMessage);

                    // Redirect to the calendar with the selected date
                    console.log('Appointment deleted, redirecting to:', data.redirect);
                    setTimeout(() => {
                        window.location.href = data.redirect;
                    }, 1000);
                } else {
                    // Show error message
                    const errorMessage = document.createElement('div');
                    errorMessage.className = 'alert alert-danger alert-dismissible fade show';
                    errorMessage.innerHTML = `
                        <strong>Error!</strong> ${data.message}
                        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                    `;
                    document.querySelector('.container').prepend(errorMessage);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                // Fallback to regular link behavior
                window.location.href = deleteUrl;
            });
        }
    }
});

// jQuery functionality consolidated into vanilla JS above
// Removed duplicate jQuery initialization