/**
 * Appointment scheduling management
 * Handles time slot selection, availability, and status updates
 */
document.addEventListener('DOMContentLoaded', function() {
    // Handle appointment status updates
    setupStatusUpdates();
    
    
    // Get form elements
    const dateInput = document.getElementById('appointment_date');
    const timeSelect = document.getElementById('appointment_time');
    
    if (!dateInput || !timeSelect) {
        console.log('Appointment form elements not found');
        return; // Exit if not on appointment form page
    }
    
    console.log('Appointment form initialized');
    
    // Function to fetch available time slots for a given date
    function fetchAvailableTimeSlots(date, appointmentId = null) {
        console.log('Fetching time slots for date:', date, 'appointment ID:', appointmentId);
        
        // Show loading message
        const loadingOption = document.createElement('option');
        loadingOption.textContent = 'Loading time slots...';
        timeSelect.innerHTML = '';
        timeSelect.appendChild(loadingOption);
        
        // Build URL with optional appointment ID for editing
        let url = `/get-available-slots?date=${date}`;
        if (appointmentId) {
            url += `&appointment_id=${appointmentId}`;
        }
        
        // Make AJAX request to get available time slots
        fetch(url)
            .then(response => response.json())
            .then(data => {
                // Clear existing options
                timeSelect.innerHTML = '';
                
                if (data.success) {
                    console.log('Available slots:', data.available_slots.length);
                    console.log('Booked slots:', data.booked_slots.length);
                    
                    // Add available time slots
                    data.available_slots.forEach(slot => {
                        const option = document.createElement('option');
                        option.value = slot.value;
                        option.textContent = slot.label;
                        timeSelect.appendChild(option);
                    });
                    
                    // Also add booked slots but mark them as disabled
                    const bookedSlots = data.booked_slots;
                    if (bookedSlots && bookedSlots.length > 0) {
                        // Create an optgroup for booked slots if there are many
                        if (bookedSlots.length > 3) {
                            const bookedGroup = document.createElement('optgroup');
                            bookedGroup.label = 'Booked Time Slots';
                            
                            // Get 12-hour format labels for booked slots
                            bookedSlots.forEach(slot => {
                                const [hour, minute] = slot.split(':').map(Number);
                                let label;
                                
                                if (hour < 12) {
                                    label = `${hour || 12}:${minute.toString().padStart(2, '0')} AM`;
                                } else if (hour === 12) {
                                    label = `12:${minute.toString().padStart(2, '0')} PM`;
                                } else {
                                    label = `${hour-12}:${minute.toString().padStart(2, '0')} PM`;
                                }
                                
                                const option = document.createElement('option');
                                option.value = slot;
                                option.textContent = label + ' (Booked)';
                                option.disabled = true;
                                bookedGroup.appendChild(option);
                            });
                            
                            timeSelect.appendChild(bookedGroup);
                        } else {
                            // Just add them inline if there are only a few
                            bookedSlots.forEach(slot => {
                                const [hour, minute] = slot.split(':').map(Number);
                                let label;
                                
                                if (hour < 12) {
                                    label = `${hour || 12}:${minute.toString().padStart(2, '0')} AM`;
                                } else if (hour === 12) {
                                    label = `12:${minute.toString().padStart(2, '0')} PM`;
                                } else {
                                    label = `${hour-12}:${minute.toString().padStart(2, '0')} PM`;
                                }
                                
                                const option = document.createElement('option');
                                option.value = slot;
                                option.textContent = label + ' (Booked)';
                                option.disabled = true;
                                timeSelect.appendChild(option);
                            });
                        }
                    }
                    
                    // If no available slots
                    if (data.available_slots.length === 0) {
                        const noSlotOption = document.createElement('option');
                        noSlotOption.textContent = 'No available time slots for this date';
                        noSlotOption.disabled = true;
                        timeSelect.appendChild(noSlotOption);
                    }
                    
                    // If we're editing an appointment, try to restore the current time
                    console.log('Debug - appointmentId:', appointmentId);
                    console.log('Debug - window.CURRENT_APPOINTMENT_TIME:', window.CURRENT_APPOINTMENT_TIME);
                    console.log('Debug - window.currentAppointmentTime:', window.currentAppointmentTime);
                    console.log('Debug - timeSelect options:', Array.from(timeSelect.options).map(o => o.value));
                    
                    if (appointmentId && window.CURRENT_APPOINTMENT_TIME) {
                        console.log('Setting timeSelect.value to:', window.CURRENT_APPOINTMENT_TIME);
                        timeSelect.value = window.CURRENT_APPOINTMENT_TIME;
                        console.log('After setting - timeSelect.value:', timeSelect.value);
                        console.log('Restored appointment time:', window.CURRENT_APPOINTMENT_TIME);
                    } else if (appointmentId && window.currentAppointmentTime) {
                        console.log('Using fallback time:', window.currentAppointmentTime);
                        timeSelect.value = window.currentAppointmentTime;
                        console.log('Restored appointment time (fallback):', window.currentAppointmentTime);
                    }
                } else {
                    // Show error message
                    const errorOption = document.createElement('option');
                    errorOption.textContent = 'Error loading time slots';
                    timeSelect.appendChild(errorOption);
                    console.error('Failed to load time slots:', data.message);
                }
            })
            .catch(error => {
                console.error('Error fetching available time slots:', error);
                timeSelect.innerHTML = '';
                const errorOption = document.createElement('option');
                errorOption.textContent = 'Error loading time slots';
                timeSelect.appendChild(errorOption);
            });
    }
    
    // Function to get appointment ID if we're editing
    function getAppointmentId() {
        // Check for global variable set by the template
        if (window.APPOINTMENT_ID) {
            console.log('Found appointment ID from global variable:', window.APPOINTMENT_ID);
            return window.APPOINTMENT_ID;
        }
        
        console.log('No appointment ID found');
        return null;
    }
    
    // Store the current appointment time if editing and get appointment ID
    const appointmentId = getAppointmentId();
    const currentAppointmentTime = timeSelect.value;
    
    // Store the current time globally for restoration after slot loading
    if (appointmentId && window.CURRENT_APPOINTMENT_TIME) {
        window.currentAppointmentTime = window.CURRENT_APPOINTMENT_TIME;
        console.log('Stored current appointment time for editing:', window.CURRENT_APPOINTMENT_TIME);
    } else if (appointmentId && currentAppointmentTime) {
        window.currentAppointmentTime = currentAppointmentTime;
        console.log('Stored current appointment time for editing:', currentAppointmentTime);
    }
    
    // Initial fetch of available time slots if date is already set
    if (dateInput.value) {
        console.log('Initial date set:', dateInput.value, 'Appointment ID:', appointmentId);
        fetchAvailableTimeSlots(dateInput.value, appointmentId);
    }
    
    // Update time slots when date changes
    dateInput.addEventListener('change', function() {
        if (dateInput.value) {
            console.log('Date changed to:', dateInput.value, 'Appointment ID:', appointmentId);
            fetchAvailableTimeSlots(dateInput.value, appointmentId);
        } else {
            console.log('Date cleared');
            // Clear time slots if date is cleared
            timeSelect.innerHTML = '';
            const emptyOption = document.createElement('option');
            emptyOption.textContent = 'Select a date first';
            timeSelect.appendChild(emptyOption);
        }
    });
    
    // Add validation to form submission
    const form = document.getElementById('appointment-form');
    if (form) {
        form.addEventListener('submit', function(event) {
            // Check if a date is selected
            if (!dateInput.value) {
                event.preventDefault();
                alert('Please select an appointment date');
                return false;
            }
            
            // Check if a time is selected
            if (!timeSelect.value) {
                event.preventDefault();
                alert('Please select an appointment time');
                return false;
            }
            
            // Check if the selected time is disabled (already booked)
            const selectedOption = timeSelect.options[timeSelect.selectedIndex];
            if (selectedOption.disabled) {
                event.preventDefault();
                alert('This time slot is already booked. Please select an available time.');
                return false;
            }
            
            return true;
        });
    }
});

/**
 * Setup event handlers for appointment status updates
 */
function setupStatusUpdates() {
    // Find all status link elements
    const statusLinks = document.querySelectorAll('.status-link');
    
    if (statusLinks.length === 0) {
        console.log('No appointment status links found on this page');
        return;
    }
    
    console.log('Setting up status update handlers for', statusLinks.length, 'status options');
    
    // Add click handler to each status link
    statusLinks.forEach(link => {
        link.addEventListener('click', function(event) {
            // Prevent the default link action
            event.preventDefault();
            
            // Get the appointment ID and status from data attributes
            const appointmentId = link.getAttribute('data-appointment-id');
            const status = link.getAttribute('data-status');
            
            // Get the dropdown button that should show the status
            const dropdownButton = link.closest('.dropdown').querySelector('.dropdown-toggle');
            const originalText = dropdownButton.innerHTML;
            
            // Show loading state
            dropdownButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Updating...';
            
            // Create form data
            const formData = new FormData();
            formData.append('status', status);
            
            // Send the request
            fetch(`/appointments/${appointmentId}/update-status`, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok: ' + response.statusText);
                }
                return response.json();
            })
            .then(data => {
                if (data.success) {
                    // Update button text with new status (capitalized)
                    const newStatus = data.status.charAt(0).toUpperCase() + data.status.slice(1);
                    dropdownButton.innerHTML = '<i class="fas fa-user-clock me-1"></i> ' + newStatus;
                    
                    // Update active class on dropdown items
                    link.closest('.dropdown-menu').querySelectorAll('.dropdown-item').forEach(item => {
                        item.classList.remove('active');
                    });
                    link.classList.add('active');
                    
                    // Show success indicator temporarily
                    const successIcon = document.createElement('span');
                    successIcon.innerHTML = ' <i class="fas fa-check text-success"></i>';
                    dropdownButton.appendChild(successIcon);
                    
                    // Remove the success indicator after a delay
                    setTimeout(() => {
                        dropdownButton.innerHTML = '<i class="fas fa-user-clock me-1"></i> ' + newStatus;
                    }, 2000);
                } else {
                    console.error('Error updating status:', data.message);
                    dropdownButton.innerHTML = originalText;
                    alert('Error updating appointment status: ' + data.message);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                dropdownButton.innerHTML = originalText;
                alert('Error updating appointment status. Please try again.');
            });
        });
    });
}