// main.js - Core JavaScript for HealthPrep application

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
            // Cache DOM elements (equivalent to useMemo)
            const dateInput = document.querySelector('input[name="appointment_date"]');
            let hiddenField = document.querySelector('input[name="fallback_date"]');
            
            // Pre-create hidden field if it doesn't exist (avoid repeated checks)
            if (!hiddenField) {
                hiddenField = document.createElement('input');
                hiddenField.type = 'hidden';
                hiddenField.name = 'fallback_date';
                appointmentForm.appendChild(hiddenField);
            }

            // Optimized click handler (equivalent to useCallback)
            submitBtn.addEventListener('click', function(e) {
                if (dateInput && dateInput.value) {
                    console.log('Adding hidden field with date:', dateInput.value);
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

    // Cache and initialize dropdowns efficiently (equivalent to useMemo)
    const dropdownElements = document.querySelectorAll('.dropdown-toggle');
    if (dropdownElements.length > 0) {
        const dropdownInstances = Array.from(dropdownElements).map(el => new bootstrap.Dropdown(el));
        // Store instances for potential cleanup later
        window._dropdownInstances = dropdownInstances;
    }

    // Handle section history links with advanced caching (useMemo equivalent)
    const sectionContainer = document.querySelector('.patient-detail-container');
    if (sectionContainer) {
        // Pre-build section cache and visibility state (equivalent to useMemo)
        const sectionCache = new Map();
        const allSections = document.querySelectorAll('.history-section');
        allSections.forEach(section => {
            sectionCache.set(section.id, {
                element: section,
                isVisible: false
            });
        });

        // Optimized toggle function (equivalent to useCallback)
        const toggleSection = function(sectionName) {
            const targetId = `${sectionName}-history`;
            const target = sectionCache.get(targetId);
            
            if (!target) return;

            // Batch DOM operations for better performance
            const updates = [];
            
            // Hide all visible sections
            sectionCache.forEach((section, id) => {
                if (section.isVisible && id !== targetId) {
                    updates.push(() => {
                        section.element.classList.add('d-none');
                        section.isVisible = false;
                    });
                }
            });

            // Show target section
            if (!target.isVisible) {
                updates.push(() => {
                    target.element.classList.remove('d-none');
                    target.isVisible = true;
                    target.element.scrollIntoView({behavior: 'smooth', block: 'start'});
                });
            }

            // Execute all updates in a single batch
            updates.forEach(update => update());
        };

        // Use event delegation with cached handler
        sectionContainer.addEventListener('click', function(e) {
            const sectionLink = e.target.closest('.section-link');
            if (sectionLink) {
                e.preventDefault();
                const sectionName = sectionLink.getAttribute('data-section');
                if (sectionName) {
                    toggleSection(sectionName);
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

    // Patient search functionality with debouncing (like useMemo/useCallback)
    const patientSearchInput = document.getElementById('patient-search');
    if (patientSearchInput) {
        // Cache patient rows and their data for better performance
        const patientRows = Array.from(document.querySelectorAll('.patient-row'));
        const patientData = patientRows.map(row => ({
            element: row,
            name: row.getAttribute('data-patient-name')?.toLowerCase() || '',
            mrn: row.getAttribute('data-patient-mrn')?.toLowerCase() || ''
        }));

        // Debounced search function (equivalent to useCallback with dependencies)
        let searchTimeout;
        const debouncedSearch = function(searchTerm) {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                const term = searchTerm.toLowerCase();
                
                // Use cached data instead of re-querying DOM
                patientData.forEach(patient => {
                    if (patient.name.includes(term) || patient.mrn.includes(term)) {
                        patient.element.style.display = '';
                    } else {
                        patient.element.style.display = 'none';
                    }
                });
            }, 150); // Debounce delay
        };

        patientSearchInput.addEventListener('input', function(e) {
            debouncedSearch(e.target.value);
        });
    }
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

// Main JavaScript file for the application
$(document).ready(function() {
    // Initialize tooltips
    $('[data-bs-toggle="tooltip"]').tooltip();

    // Auto-hide alerts after 5 seconds
    setTimeout(function() {
        $('.alert').fadeOut('slow');
    }, 5000);

    // Setup CSRF token for all AJAX requests
    var csrf_token = $('meta[name=csrf-token]').attr('content');

    // Configure jQuery to include CSRF token in all AJAX requests
    $.ajaxSetup({
        beforeSend: function(xhr, settings) {
            if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type) && !this.crossDomain) {
                xhr.setRequestHeader("X-CSRFToken", csrf_token);
            }
        },
        xhrFields: {
            withCredentials: true  // Include cookies in AJAX requests
        }
    });
});